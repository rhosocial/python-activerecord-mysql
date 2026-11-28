# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/ddl/test_mysql_alter_table_modifiers.py
"""MySQL ``ALTER TABLE ... ALGORITHM=..., LOCK=...`` execution modifiers.

Sources (MySQL 8.0 Reference Manual):

* §15.1.9 ``ALTER TABLE Statement`` --
  https://dev.mysql.com/doc/refman/8.0/en/alter-table.html

      ALTER TABLE tbl_name [alter_option [, alter_option] ...] [partition_options]
      ... | ALGORITHM [=] {DEFAULT | INSTANT | INPLACE | COPY}
      ... | LOCK [=] {DEFAULT | NONE | SHARED | EXCLUSIVE}

  Both modifiers are alter_options, so they share the comma-separated list
  with the ordinary actions; they are not trailing clauses after the list.
* §17.12 ``InnoDB and Online DDL`` --
  https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl.html

      ALGORITHM=INSTANT support is available for ADD COLUMN and other
      operations in MySQL 8.0.12.
      Only LOCK=DEFAULT is supported for operations that are performed
      instantly.

Floors modelled here: ``DEFAULT``/``INPLACE``/``COPY`` and all four ``LOCK``
words come in with online DDL in MySQL 5.6 (§17.12); ``INSTANT`` alone needs
8.0.12. The probe docstrings carry the same markers so a verdict cannot lose
its evidence.

Core has no counterpart for either clause, so the node is MySQL-proprietary:
``MySQLAlterTableStatement`` wraps the table, the two modifiers and the same
``AlterTableAction`` objects core's ``AlterTableStatement`` already carries.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import statements as core_statements
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddColumnAction
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.statements.alter_table_modifiers import (
    MYSQL_ALGORITHM_WORDS,
    MYSQL_LOCK_WORDS,
    MySQLAlterTableStatement,
)

MEASURED_VERSION = (26, 7, 0)

#: Every probe this feature adds, with the answer on the measured server.
ALTER_MODIFIER_SWITCHES = {
    "supports_alter_table_algorithm": True,
    "supports_alter_table_algorithm_instant": True,
    "supports_alter_table_lock": True,
}

#: The marker that must appear in each probe's docstring: the floor or the
#: official section that settles the verdict.
EVIDENCE = {
    "supports_alter_table_algorithm": "5.6",
    "supports_alter_table_algorithm_instant": "8.0.12",
    "supports_alter_table_lock": "5.6",
}


def _dialect(version=MEASURED_VERSION):
    return MySQLDialect(version=version)


def _action(dialect, name="c"):
    return AddColumnAction(dialect, ColumnDefinition(dialect, name, IntegerType(dialect)))


def _statement(dialect, *, algorithm=None, lock=None, action=None):
    return MySQLAlterTableStatement(
        dialect,
        Table(dialect, "t"),
        _action(dialect) if action is None else action,
        algorithm=algorithm,
        lock=lock,
    )


class TestProbeValues:
    """What the probes answer, and where their floors sit."""

    @pytest.mark.parametrize(
        "probe, expected", ALTER_MODIFIER_SWITCHES.items(), ids=sorted(ALTER_MODIFIER_SWITCHES)
    )
    def test_probe_answers_the_measured_value(self, probe, expected):
        assert getattr(_dialect(), probe)() is expected

    @pytest.mark.parametrize("probe", ["supports_alter_table_algorithm", "supports_alter_table_lock"])
    def test_clauses_start_at_56(self, probe):
        """Both clauses came in with online DDL; 5.5 has neither."""
        assert getattr(_dialect((5, 5, 62)), probe)() is False
        assert getattr(_dialect((5, 6, 0)), probe)() is True
        assert getattr(_dialect((5, 7, 44)), probe)() is True

    def test_instant_starts_at_8012(self):
        """8.0.11 parses ALGORITHM but has no INSTANT; 8.0.12 does (§17.12)."""
        assert _dialect((8, 0, 11)).supports_alter_table_algorithm_instant() is False
        assert _dialect((8, 0, 12)).supports_alter_table_algorithm_instant() is True
        assert _dialect((8, 4, 0)).supports_alter_table_algorithm_instant() is True


class TestProbeDocstringsCarryTheMeasurement:
    """A probe without its evidence is a number with no source."""

    @pytest.mark.parametrize("probe, marker", EVIDENCE.items(), ids=sorted(EVIDENCE))
    def test_docstring_records_the_floor(self, probe, marker):
        doc = getattr(MySQLDialect, probe).__doc__ or ""
        assert doc, f"{probe} has no docstring: the floor has nowhere to live"
        assert marker in doc, f"{probe} docstring does not record {marker!r}"

    def test_floors_are_exactly_the_official_words(self):
        """The vocabularies are the ones §15.1.9 prints, no local invention."""
        assert MYSQL_ALGORITHM_WORDS == ("DEFAULT", "INSTANT", "INPLACE", "COPY")
        assert MYSQL_LOCK_WORDS == ("DEFAULT", "NONE", "SHARED", "EXCLUSIVE")


class TestExactSQL:
    """One expression, one statement, with the modifiers ahead of the actions."""

    @pytest.mark.parametrize("word", MYSQL_ALGORITHM_WORDS)
    def test_each_algorithm_word(self, word):
        expected = {
            "DEFAULT": "ALGORITHM=DEFAULT",
            "INSTANT": "ALGORITHM=INSTANT",
            "INPLACE": "ALGORITHM=INPLACE",
            "COPY": "ALGORITHM=COPY",
        }[word]
        sql, params = _statement(_dialect(), algorithm=word).to_sql()
        assert sql == f"ALTER TABLE `t` {expected}, ADD COLUMN `c` INT"
        assert params == ()

    @pytest.mark.parametrize("word", MYSQL_LOCK_WORDS)
    def test_each_lock_word(self, word):
        sql, params = _statement(_dialect(), lock=word).to_sql()
        assert sql == f"ALTER TABLE `t` LOCK={word}, ADD COLUMN `c` INT"
        assert params == ()

    def test_both_modifiers_with_a_real_action(self):
        sql, params = _statement(_dialect(), algorithm="INPLACE", lock="NONE").to_sql()
        assert sql == "ALTER TABLE `t` ALGORITHM=INPLACE, LOCK=NONE, ADD COLUMN `c` INT"
        assert params == ()

    def test_modifiers_with_one_action(self):
        d = _dialect()
        sql, params = _statement(d, algorithm="COPY", lock="EXCLUSIVE", action=_action(d, "a")).to_sql()
        assert sql == "ALTER TABLE `t` ALGORITHM=COPY, LOCK=EXCLUSIVE, ADD COLUMN `a` INT"
        assert params == ()

    def test_action_rendering_is_reused_unchanged(self):
        from rhosocial.activerecord.backend.expression.value_types.parameter import Parameter
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
            AlterColumnAction,
            ColumnAlterOperation,
        )

        d = _dialect()
        action = AlterColumnAction(d, "c", ColumnAlterOperation.SET_DEFAULT, new_value=Parameter(d, 7))
        sql, params = _statement(d, algorithm="INPLACE", action=action).to_sql()
        assert sql == "ALTER TABLE `t` ALGORITHM=INPLACE, ALTER COLUMN `c` SET DEFAULT 7"
        assert params == ()

    def test_omitting_modifiers_is_byte_identical_to_core(self):
        d = _dialect()
        action = _action(d, "a")
        wrapped = _statement(d, action=action).to_sql()
        plain = core_statements.AlterTableStatement(d, Table(d, "t"), action).to_sql()
        assert wrapped == plain

    def test_explicit_default_words_render_the_clauses(self):
        """DEFAULT is a real spelling; only omission is byte-identical."""
        d = _dialect()
        sql, _ = _statement(d, algorithm="DEFAULT", lock="DEFAULT").to_sql()
        assert sql == "ALTER TABLE `t` ALGORITHM=DEFAULT, LOCK=DEFAULT, ADD COLUMN `c` INT"
        plain = core_statements.AlterTableStatement(
            d, Table(d, "t"), _action(d)
        ).to_sql()[0]
        assert sql != plain


class TestRefusals:
    """Version, word, conflict and kind errors are all raised by the formatter."""

    def test_instant_is_refused_below_8012(self):
        with pytest.raises(UnsupportedFeatureError, match="INSTANT"):
            _statement(_dialect((8, 0, 11)), algorithm="INSTANT").to_sql()

    def test_algorithm_clause_is_refused_below_56(self):
        with pytest.raises(UnsupportedFeatureError, match="ALGORITHM"):
            _statement(_dialect((5, 5, 62)), algorithm="COPY").to_sql()

    def test_lock_clause_is_refused_below_56(self):
        with pytest.raises(UnsupportedFeatureError, match="LOCK"):
            _statement(_dialect((5, 5, 62)), lock="SHARED").to_sql()

    @pytest.mark.parametrize("word", ["BOGUS", "INSTANTLY", ""])
    def test_unknown_algorithm_word_is_refused(self, word):
        with pytest.raises(UnsupportedFeatureError, match="ALGORITHM"):
            _statement(_dialect(), algorithm=word).to_sql()

    @pytest.mark.parametrize("word", ["BOGUS", "EXCLUSIVE SHARED", ""])
    def test_unknown_lock_word_is_refused(self, word):
        with pytest.raises(UnsupportedFeatureError, match="LOCK"):
            _statement(_dialect(), lock=word).to_sql()

    @pytest.mark.parametrize("word", ["NONE", "SHARED", "EXCLUSIVE"])
    def test_instant_rejects_any_lock_but_default(self, word):
        """§17.12: only LOCK=DEFAULT is supported for instant operations."""
        with pytest.raises(UnsupportedFeatureError, match="INSTANT"):
            _statement(_dialect(), algorithm="INSTANT", lock=word).to_sql()

    def test_instant_with_default_lock_renders(self):
        sql, _ = _statement(_dialect(), algorithm="INSTANT", lock="DEFAULT").to_sql()
        assert sql == "ALTER TABLE `t` ALGORITHM=INSTANT, LOCK=DEFAULT, ADD COLUMN `c` INT"

    @pytest.mark.parametrize("bad", ["t", 1, None, Table(_dialect(), "other")])
    def test_wrong_table_type_is_refused(self, bad):
        d = _dialect()
        # The last case is a Table, so it must be replaced by a genuinely
        # wrong kind to keep the parameter meaningful.
        wrong = object() if isinstance(bad, Table) else bad
        expr = MySQLAlterTableStatement(d, wrong, _action(d), algorithm="INPLACE")
        # ``None`` passes construction as a missing required parameter and is
        # refused only when rendered; a wrong *kind* keeps the qualified message.
        expected = (
            r"required parameter\(s\) table are None"
            if wrong is None
            else r"MySQLAlterTableStatement\.table"
        )
        with pytest.raises(TypeError, match=expected):
            expr.to_sql()

    @pytest.mark.parametrize("bad", ["ADD COLUMN", 7, object()])
    def test_wrong_action_type_is_refused(self, bad):
        d = _dialect()
        expr = MySQLAlterTableStatement(d, Table(d, "t"), bad, lock="NONE")
        with pytest.raises(TypeError, match="MySQLAlterTableStatement.action"):
            expr.to_sql()


class TestProprietaryNode:
    """The node stays in MySQL's package and collects parameters only."""

    def test_constructor_keeps_the_values_without_a_dialect(self):
        d = None
        expr = MySQLAlterTableStatement(d, Table(d, "t"), "add", algorithm="inplace", lock="none")
        assert expr._dialect is None
        assert expr.algorithm == "inplace"
        assert expr.lock == "none"
        assert expr.action == "add"
        assert expr.format_method == "format_mysql_alter_table_statement"

    def test_kind_is_mysql_prefixed_and_core_does_not_export_it(self):
        assert MySQLAlterTableStatement.kind() == "mysql_alter_table_statement"
        assert not hasattr(core_statements, "MySQLAlterTableStatement")

    def test_lowercase_words_normalise_at_render_time(self):
        sql, _ = _statement(_dialect(), algorithm="copy", lock="shared").to_sql()
        assert sql == "ALTER TABLE `t` ALGORITHM=COPY, LOCK=SHARED, ADD COLUMN `c` INT"
