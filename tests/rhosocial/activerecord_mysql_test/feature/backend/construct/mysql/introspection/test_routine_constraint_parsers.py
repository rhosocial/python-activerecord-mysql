# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/mysql/introspection/test_routine_constraint_parsers.py
"""Offline parser tests for routines, constraints and the auto-increment audit.

No server is needed: the parsers are pure functions over the rows an
:class:`IntrospectorExecutor` would have returned. What is pinned here is the
grouping the join relies on, the ordinal-zero convention that separates a
function's return value from its arguments, the CHECK-only expression rule,
and that ``is_auto_increment`` is still read from ``EXTRA``.
"""

from types import SimpleNamespace

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.introspection.introspector import (
    MySQLIntrospectorMixin,
)
from rhosocial.activerecord.backend.impl.mysql.introspection.types import (
    MySQLConstraintInfo,
    MySQLRoutineInfo,
    MySQLRoutineParameter,
)


def _mixin() -> MySQLIntrospectorMixin:
    mixin = MySQLIntrospectorMixin()
    mixin._backend = SimpleNamespace(
        dialect=MySQLDialect(version=(8, 0, 46)),
        config=SimpleNamespace(database="app"),
    )
    return mixin


def _routine_row(ordinal, *, mode=None, name=None, data_type=None, dtype=None):
    return {
        "ROUTINE_SCHEMA": "app",
        "ROUTINE_NAME": "f",
        "ROUTINE_TYPE": "FUNCTION",
        "DATA_TYPE": "int",
        "DTD_IDENTIFIER": "int",
        "ROUTINE_BODY": "SQL",
        "EXTERNAL_LANGUAGE": None,
        "IS_DETERMINISTIC": "YES",
        "SQL_DATA_ACCESS": "READS SQL DATA",
        "SECURITY_TYPE": "INVOKER",
        "ROUTINE_COMMENT": "comment",
        "DEFINER": "root@localhost",
        "CREATED": "2026-01-01 00:00:00",
        "LAST_ALTERED": "2026-01-02 00:00:00",
        "SQL_MODE": "STRICT_TRANS_TABLES",
        "PARAM_ORDINAL_POSITION": ordinal,
        "PARAMETER_MODE": mode,
        "PARAMETER_NAME": name,
        "PARAM_DATA_TYPE": data_type,
        "PARAM_DTD_IDENTIFIER": dtype,
    }


class TestParseRoutines:
    def test_groups_arguments_by_routine_and_keeps_declaration_order(self):
        rows = [
            _routine_row(0, data_type="int", dtype="int"),
            _routine_row(2, mode="IN", name="b", data_type="varchar", dtype="varchar(5)"),
            _routine_row(1, mode="IN", name="a", data_type="int", dtype="int"),
        ]

        routines = _mixin().parse_routines(rows)

        assert len(routines) == 1
        routine = routines[0]
        assert isinstance(routine, MySQLRoutineInfo)
        assert routine.kind == "FUNCTION"
        assert routine.return_type == "int"
        assert [p.name for p in routine.parameters] == ["a", "b"]
        assert all(isinstance(p, MySQLRoutineParameter) for p in routine.parameters)
        assert routine.parameters[1].data_type_full == "varchar(5)"

    def test_ordinal_zero_is_the_return_value_not_an_argument(self):
        rows = [_routine_row(0, data_type="int", dtype="int")]

        routine = _mixin().parse_routines(rows)[0]

        assert routine.parameters == ()
        assert routine.return_type == "int"

    def test_a_procedure_has_no_return_type(self):
        row = _routine_row(None)
        row.update(
            {
                "ROUTINE_NAME": "p",
                "ROUTINE_TYPE": "PROCEDURE",
                "DATA_TYPE": None,
                "DTD_IDENTIFIER": None,
            }
        )

        routine = _mixin().parse_routines([row])[0]

        assert routine.kind == "PROCEDURE"
        assert routine.return_type is None

    def test_deterministic_yes_no_reaches_a_bool(self):
        row = _routine_row(1, mode="IN", name="a", data_type="int", dtype="int")
        row["IS_DETERMINISTIC"] = "NO"

        routine = _mixin().parse_routines([row])[0]

        assert routine.is_deterministic is False

    def test_language_falls_back_to_the_routine_body(self):
        row = _routine_row(1, mode="IN", name="a", data_type="int", dtype="int")
        row["EXTERNAL_LANGUAGE"] = None
        row["ROUTINE_BODY"] = "SQL"

        routine = _mixin().parse_routines([row])[0]

        assert routine.language == "SQL"


def _constraint_row(constraint_type, *, name="c", table="t", column=None, ordinal=None,
                    check_clause=None, enforced="YES"):
    return {
        "CONSTRAINT_SCHEMA": "app",
        "TABLE_NAME": table,
        "CONSTRAINT_NAME": name,
        "CONSTRAINT_TYPE": constraint_type,
        "ENFORCED": enforced,
        "CHECK_CLAUSE": check_clause,
        "COLUMN_NAME": column,
        "ORDINAL_POSITION": ordinal,
    }


class TestParseConstraints:
    def test_check_constraint_carries_its_expression_and_no_columns(self):
        rows = [
            _constraint_row(
                "CHECK", name="ck", check_clause="(`age` > 0)", enforced="YES"
            )
        ]

        constraints = _mixin().parse_constraints(rows)

        assert isinstance(constraints[0], MySQLConstraintInfo)
        assert constraints[0].expression == "(`age` > 0)"
        assert constraints[0].columns == ()
        assert constraints[0].enforced is True
        assert constraints[0].comment is None

    def test_column_constraints_group_their_columns_in_ordinal_order(self):
        rows = [
            _constraint_row("UNIQUE", name="uq", column="b", ordinal=2),
            _constraint_row("UNIQUE", name="uq", column="a", ordinal=1),
        ]

        constraint = _mixin().parse_constraints(rows)[0]

        assert constraint.columns == ("a", "b")
        assert constraint.expression is None

    def test_a_check_clause_is_ignored_for_a_non_check_constraint(self):
        """A name can be shared across kinds; the clause belongs to the CHECK."""
        rows = [
            _constraint_row(
                "UNIQUE", name="shared", column="a", ordinal=1,
                check_clause="other table's clause",
            )
        ]

        constraint = _mixin().parse_constraints(rows)[0]

        assert constraint.expression is None

    def test_enforced_no_reaches_false(self):
        rows = [_constraint_row("CHECK", check_clause="(1)", enforced="NO")]

        assert _mixin().parse_constraints(rows)[0].enforced is False


class TestAutoIncrementAudit:
    """``is_auto_increment`` must survive a row that reports it in ``EXTRA``."""

    def _column_row(self, extra):
        return {
            "COLUMN_NAME": "id",
            "ORDINAL_POSITION": 1,
            "COLUMN_DEFAULT": None,
            "IS_NULLABLE": "NO",
            "DATA_TYPE": "int",
            "CHARACTER_MAXIMUM_LENGTH": None,
            "NUMERIC_PRECISION": 10,
            "NUMERIC_SCALE": 0,
            "COLUMN_TYPE": "int",
            "COLUMN_KEY": "PRI",
            "EXTRA": extra,
            "COLUMN_COMMENT": "",
            "CHARACTER_SET_NAME": None,
            "COLLATION_NAME": None,
        }

    def test_auto_increment_extra_is_reported(self):
        column = _mixin().parse_columns(
            [self._column_row("auto_increment")], "t", "app"
        )[0]

        assert column.is_auto_increment is True

    def test_a_plain_column_is_not_auto_increment(self):
        column = _mixin().parse_columns([self._column_row("")], "t", "app")[0]

        assert column.is_auto_increment is False


class _RecordingExecutor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self.rows


class _AsyncRecordingExecutor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self.rows


def _backend():
    return SimpleNamespace(
        dialect=MySQLDialect(version=(8, 0, 46)),
        config=SimpleNamespace(database="app"),
    )


class TestTheIntrospectorMethods:
    """Sync and async read the same statement and parse the same rows."""

    def test_sync_list_and_get_routines_use_the_routine_statements(self):
        from rhosocial.activerecord.backend.impl.mysql.introspection import (
            MySQLIntrospector,
        )

        rows = [
            _routine_row(1, mode="IN", name="a", data_type="int", dtype="int")
        ]
        executor = _RecordingExecutor(rows)
        introspector = MySQLIntrospector(_backend(), executor)

        assert introspector.list_routines() == introspector.parse_routines(rows)
        assert executor.calls[0][1] == ("app",)

        executor.rows = [
            _routine_row(1, mode="IN", name="a", data_type="int", dtype="int")
        ]
        assert introspector.get_routine_info("f") is not None
        assert executor.calls[-1][1] == ("app", "f")

    def test_sync_list_constraints_uses_the_constraint_statement(self):
        from rhosocial.activerecord.backend.impl.mysql.introspection import (
            MySQLIntrospector,
        )

        rows = [_constraint_row("CHECK", check_clause="(1)")]
        executor = _RecordingExecutor(rows)
        introspector = MySQLIntrospector(_backend(), executor)

        assert introspector.list_constraints("t") == introspector.parse_constraints(rows)
        assert executor.calls[0][1] == ("app", "t")

    @pytest.mark.asyncio
    async def test_async_methods_ask_the_same_questions(self):
        from rhosocial.activerecord.backend.impl.mysql.introspection import (
            AsyncMySQLIntrospector,
        )

        routine_rows = [
            _routine_row(1, mode="IN", name="a", data_type="int", dtype="int")
        ]
        constraint_rows = [_constraint_row("CHECK", check_clause="(1)")]
        executor = _AsyncRecordingExecutor(routine_rows)
        introspector = AsyncMySQLIntrospector(_backend(), executor)

        routines = await introspector.list_routines()
        assert [r.name for r in routines] == ["f"]
        assert executor.calls[0][1] == ("app",)

        executor.rows = routine_rows
        routine = await introspector.get_routine_info("f", kind="FUNCTION")
        assert routine is not None
        assert executor.calls[-1][1] == ("app", "f", "FUNCTION")

        executor.rows = constraint_rows
        constraints = await introspector.list_constraints()
        assert constraints == introspector.parse_constraints(constraint_rows)

