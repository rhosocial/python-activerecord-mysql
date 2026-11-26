# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/mysql/introspection/test_catalogue_capabilities.py
"""The version-gated ``information_schema`` statements, checked without a server.

The live suite runs on MySQL 5.6, 5.7, 8.0, 8.4 and 9.x, so a statement that
names a relation or column an older server does not have can pass review and
still fail in CI. That is what happened to the constraint listing:
``information_schema.CHECK_CONSTRAINTS`` does not exist below 8.0.16, and
``TABLE_CONSTRAINTS.ENFORCED`` does not either, yet both were named
unconditionally and the whole statement was refused with ``1109 unknown table``
on 5.6 / 5.7.

This guard reads the recorded surface in
``impl.mysql.catalogue.CAPABILITY_MATRIX`` -- measured on 5.6.51, 5.7.44,
8.0.15, 8.0.16 and 8.4.13 -- and renders every introspection statement for
every recorded version. Every ``information_schema`` relation and every column
the rendered SQL names must be one the version's entry records, so a statement
that reaches for a newer relation or column fails here instead of on the oldest
server.

The measured versions are pinned by name as well: deleting 5.6 from the matrix,
varying 8.0.15 from 5.7, or claiming ``ENFORCED`` for 5.6 fails rather than
silently reducing coverage.
"""

import re
from types import SimpleNamespace

import pytest

from rhosocial.activerecord.backend.expression.introspection import (
    ColumnInfoQueryStatement,
    DatabaseInfoQueryStatement,
    ForeignKeyQueryStatement,
    IndexInfoQueryStatement,
    TableListQueryStatement,
)

from rhosocial.activerecord.backend.impl.mysql.catalogue import (
    CAPABILITY_MATRIX,
    capabilities_for_version,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.introspection import (
    MySQLConstraintListQueryStatement,
    MySQLPartitionStateQueryStatement,
    MySQLRoutineListQueryStatement,
    MySQLTableOptionsInfoQueryStatement,
    MySQLTableOptionsListQueryStatement,
)
from rhosocial.activerecord.backend.impl.mysql.introspection import (
    MySQLIntrospector,
)

#: The versions the matrix must keep, oldest first.
MEASURED_VERSIONS = [(5, 6, 0), (5, 7, 0), (8, 0, 16), (8, 4, 0)]

#: A statement is the projection plus a single relation's aliases; the relation
#: span is read first so the aliases can be resolved before they are stripped.
_RELATION = re.compile(r"`information_schema`\s*\.\s*`([A-Z_]+)`" r"(?:\s+AS\s+`([^`]+)`)?")
_AS_ALIAS = re.compile(r"\bAS\s+`([^`]+)`")
_PAIR = re.compile(r"`([^`]+)`\s*\.\s*`([^`]+)`")
_SINGLE = re.compile(r"`([^`]+)`")


def _strip(sql, pattern):
    """Remove every match of *pattern*, leaving the rest of the SQL intact."""
    return pattern.sub(" ", sql)


def _catalogue_objects(sql):
    """``(relations, alias_map, pairs, singles)`` named by one rendered statement.

    The relation span (``information_schema``.``TABLE`` AS ``alias``) is read
    first and stripped. What remains is the projection, the conditions and the
    ordering: qualified pairs (``alias``.``COLUMN``), output aliases declared
    with ``AS``, and unqualified column names belonging to the single relation
    the statement reads.
    """
    relations = []
    alias_map = {}
    for matched in _RELATION.finditer(sql):
        relation = matched.group(1)
        relations.append(relation)
        if matched.group(2):
            alias_map[matched.group(2)] = relation

    remainder = _strip(sql, _RELATION)
    remainder = _strip(remainder, _AS_ALIAS)
    pairs = _PAIR.findall(remainder)
    remainder = _strip(remainder, _PAIR)
    singles = _SINGLE.findall(remainder)
    return relations, alias_map, pairs, singles


def _assert_only_recorded(sql, capabilities):
    """The statement names only relations and columns the version records."""
    relations, alias_map, pairs, singles = _catalogue_objects(sql)
    assert relations, sql

    for relation in relations:
        assert capabilities.has_relation(
            relation
        ), f"{relation} does not exist on {capabilities.version}"

    for qualifier, column in pairs:
        assert qualifier in alias_map, f"{qualifier}.{column} names no relation"
        relation = alias_map[qualifier]
        recorded = capabilities.columns_of(relation)
        assert column in recorded, f"{relation} on {capabilities.version} has no {column}"

    # An unqualified column belongs to the relation the statement reads. Every
    # statement with a join qualifies its columns, so this is never ambiguous.
    primary = relations[0]
    recorded = capabilities.columns_of(primary)
    for column in singles:
        assert column in recorded, f"{primary} on {capabilities.version} has no {column}"


def _dialect(version):
    return MySQLDialect(version=version)


def _statements(version):
    """Every introspection statement this backend renders, for one version.

    The partition statement asks for its statistics too: that is the larger
    projection, so a column missing from it would be missing from the lean one.
    """
    dialect = _dialect(version)
    return {
        "database_info": DatabaseInfoQueryStatement(dialect, schema="app").to_sql()[0],
        "table_list": TableListQueryStatement(dialect, schema="app").to_sql()[0],
        "column_info": ColumnInfoQueryStatement(dialect, "users", schema="app").to_sql()[0],
        "index_info": IndexInfoQueryStatement(dialect, "users", schema="app").to_sql()[0],
        "foreign_keys": ForeignKeyQueryStatement(dialect, "users", schema="app").to_sql()[0],
        "table_options_list": MySQLTableOptionsListQueryStatement(dialect, schema="app").to_sql()[
            0
        ],
        "table_options_info": MySQLTableOptionsInfoQueryStatement(
            dialect, "users", schema="app"
        ).to_sql()[0],
        "partition_state": MySQLPartitionStateQueryStatement(
            dialect, "users", schema="app", include_stats=True
        ).to_sql()[0],
        "routine_list": MySQLRoutineListQueryStatement(dialect, schema="app").to_sql()[0],
        "constraint_list": MySQLConstraintListQueryStatement(
            dialect, "users", schema="app"
        ).to_sql()[0],
    }


class TestTheGuardDetectsAViolation:
    """The checker is exercised on fabricated statements, so it cannot pass vacuously."""

    def test_a_relation_the_version_does_not_have_is_flagged(self):
        sql = (
            "SELECT `tc`.`CONSTRAINT_NAME`, `cc`.`CHECK_CLAUSE` "
            "FROM `information_schema`.`TABLE_CONSTRAINTS` AS `tc` "
            "LEFT JOIN `information_schema`.`CHECK_CONSTRAINTS` AS `cc` "
            "ON `tc`.`CONSTRAINT_NAME` = `cc`.`CONSTRAINT_NAME`"
        )
        with pytest.raises(AssertionError, match="CHECK_CONSTRAINTS"):
            _assert_only_recorded(sql, CAPABILITY_MATRIX[(5, 6, 0)])

    def test_a_column_the_version_does_not_have_is_flagged(self):
        sql = (
            "SELECT `tc`.`CONSTRAINT_NAME`, `tc`.`ENFORCED` "
            "FROM `information_schema`.`TABLE_CONSTRAINTS` AS `tc`"
        )
        with pytest.raises(AssertionError, match="ENFORCED"):
            _assert_only_recorded(sql, CAPABILITY_MATRIX[(5, 6, 0)])

    def test_a_statement_the_version_answers_is_accepted(self):
        sql = (
            "SELECT `tc`.`CONSTRAINT_NAME`, `tc`.`CONSTRAINT_TYPE`, "
            "`kcu`.`COLUMN_NAME` "
            "FROM `information_schema`.`TABLE_CONSTRAINTS` AS `tc` "
            "LEFT JOIN `information_schema`.`KEY_COLUMN_USAGE` AS `kcu` "
            "ON `tc`.`CONSTRAINT_NAME` = `kcu`.`CONSTRAINT_NAME`"
        )
        _assert_only_recorded(sql, CAPABILITY_MATRIX[(5, 6, 0)])


class TestTheRecordedSurfaceIsMeasured:
    """The facts the live failures turned on are pinned by version."""

    def test_every_measured_version_is_recorded_in_order(self):
        assert list(CAPABILITY_MATRIX) == MEASURED_VERSIONS
        assert all(CAPABILITY_MATRIX[version].version == version for version in MEASURED_VERSIONS)

    def test_the_check_catalogue_does_not_exist_before_8_0_16(self):
        for version in [(5, 6, 0), (5, 7, 0)]:
            capabilities = CAPABILITY_MATRIX[version]
            assert not capabilities.has_relation("CHECK_CONSTRAINTS")
            assert capabilities.columns_of("CHECK_CONSTRAINTS") is None
            assert "ENFORCED" not in capabilities.columns_of("TABLE_CONSTRAINTS")

    def test_the_check_catalogue_and_enforcement_arrive_together(self):
        for version in [(8, 0, 16), (8, 4, 0)]:
            capabilities = CAPABILITY_MATRIX[version]
            assert capabilities.columns_of("CHECK_CONSTRAINTS") == {
                "CONSTRAINT_SCHEMA",
                "CONSTRAINT_NAME",
                "CHECK_CLAUSE",
            }
            assert "ENFORCED" in capabilities.columns_of("TABLE_CONSTRAINTS")

    def test_the_5_7_surface_matches_5_6(self):
        """5.7 was measured identical for every relation this backend names."""
        assert CAPABILITY_MATRIX[(5, 7, 0)].relations == CAPABILITY_MATRIX[(5, 6, 0)].relations


class TestTheStatementsNameOnlyRecordedObjects:
    """Every introspection statement, rendered for every measured version."""

    @pytest.mark.parametrize("version", MEASURED_VERSIONS)
    @pytest.mark.parametrize(
        "statement",
        [
            "database_info",
            "table_list",
            "column_info",
            "index_info",
            "foreign_keys",
            "table_options_list",
            "table_options_info",
            "partition_state",
            "routine_list",
            "constraint_list",
        ],
    )
    def test_every_statement(self, version, statement):
        sql = _statements(version)[statement]
        _assert_only_recorded(sql, CAPABILITY_MATRIX[version])

    def test_the_oldest_constraint_statement_has_no_check_catalogue(self):
        sql = _statements((5, 6, 0))["constraint_list"]
        assert "CHECK_CONSTRAINTS" not in sql
        assert "`ENFORCED`" not in sql
        assert "`information_schema`.`TABLE_CONSTRAINTS`" in sql
        assert "`information_schema`.`KEY_COLUMN_USAGE`" in sql

    def test_the_newest_constraint_statement_names_both(self):
        sql = _statements((8, 4, 0))["constraint_list"]
        assert "`information_schema`.`CHECK_CONSTRAINTS`" in sql
        assert "`ENFORCED`" in sql

    def test_an_unadapted_dialect_never_names_the_check_catalogue(self):
        """A version nobody has resolved cannot name what it cannot prove."""
        sql = MySQLConstraintListQueryStatement(MySQLDialect(), "users", schema="app").to_sql()[0]
        assert "CHECK_CONSTRAINTS" not in sql
        assert "`ENFORCED`" not in sql


class TestUnrecordedVersionsFallBackConservatively:
    """A version nobody measured never inherits a newer surface."""

    def test_8_0_before_the_enforcement_floor_keeps_the_5_7_surface(self):
        capabilities = capabilities_for_version((8, 0, 15))
        assert capabilities.version == (5, 7, 0)
        assert not capabilities.has_relation("CHECK_CONSTRAINTS")
        assert "ENFORCED" not in capabilities.columns_of("TABLE_CONSTRAINTS")

    def test_8_0_15_renders_the_5_7_constraint_statement(self):
        """Measured: 8.0.15 has neither object; 8.0.16 has both."""
        sql = _statements((8, 0, 15))["constraint_list"]
        assert "CHECK_CONSTRAINTS" not in sql
        assert "`ENFORCED`" not in sql
        assert "`ENFORCED`" in _statements((8, 0, 16))["constraint_list"]

    def test_a_version_after_the_newest_measurement_keeps_the_newest_surface(self):
        capabilities = capabilities_for_version((9, 7, 0))
        assert capabilities.version == (8, 4, 0)
        assert capabilities.has_relation("CHECK_CONSTRAINTS")

    def test_an_unknown_version_answers_the_oldest_surface(self):
        assert capabilities_for_version(None).version == (5, 6, 0)


class _StubExecutor:
    """Answers a 5.6-shaped constraint row stream without a server.

    The rows carry no ``ENFORCED`` and no ``CHECK_CLAUSE``, which is exactly
    what the gated statement asks for on those releases.
    """

    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, params=()):
        assert "CHECK_CONSTRAINTS" not in sql
        assert "`ENFORCED`" not in sql
        return self.rows


class _StubBackend:
    """The two attributes the introspector reads before it builds SQL."""

    def __init__(self, dialect):
        self.dialect = dialect
        self.config = SimpleNamespace(database="app")


_ROWS_5_6 = [
    {
        "CONSTRAINT_SCHEMA": "app",
        "TABLE_NAME": "users",
        "CONSTRAINT_NAME": "PRIMARY",
        "CONSTRAINT_TYPE": "PRIMARY KEY",
        "COLUMN_NAME": "id",
        "ORDINAL_POSITION": 1,
    },
    {
        "CONSTRAINT_SCHEMA": "app",
        "TABLE_NAME": "users",
        "CONSTRAINT_NAME": "email",
        "CONSTRAINT_TYPE": "UNIQUE",
        "COLUMN_NAME": "email",
        "ORDINAL_POSITION": 1,
    },
    {
        "CONSTRAINT_SCHEMA": "app",
        "TABLE_NAME": "users",
        "CONSTRAINT_NAME": "fk_users_parent",
        "CONSTRAINT_TYPE": "FOREIGN KEY",
        "COLUMN_NAME": "parent_id",
        "ORDINAL_POSITION": 1,
    },
]


class TestTheStateMethodAnswersWhatItCanRead:
    """The method, not only the formatter, answers the readable constraints."""

    def test_a_5_6_server_reports_key_constraints_and_no_check(self):
        introspector = MySQLIntrospector(
            _StubBackend(_dialect((5, 6, 0))), executor=_StubExecutor(_ROWS_5_6)
        )
        states = introspector.list_constraint_states("users")

        assert {state.kind for state in states} == {
            "primary_key",
            "unique",
            "foreign_key",
        }
        assert all(state.enforced and state.validated for state in states)
        assert all(not state.deferred and not state.disabled for state in states)
        primary = next(state for state in states if state.kind == "primary_key")
        assert primary.name == "PRIMARY"
        assert primary.backing_index == "PRIMARY"
        assert not any(state.kind == "check" for state in states)

    def test_the_answer_is_not_an_empty_list(self):
        introspector = MySQLIntrospector(
            _StubBackend(_dialect((5, 7, 0))), executor=_StubExecutor(_ROWS_5_6)
        )
        assert len(introspector.list_constraint_states("users")) == 3
