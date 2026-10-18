# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_classed_functions_and_bare_values.py
"""Follow-up coverage for the classed function entry points and the bare VALUES cells.

Two threads of the core waves land in this dialect here:

* :class:`CharLengthFunction` carries a declared ``unit`` (char / octet /
  bit), and core's default ``LENGTH`` spelling counts **bytes** on MySQL --
  measured on 8.0.46: ``LENGTH('aé')`` answers 3 where ``CHAR_LENGTH('aé')``
  answers 2, so the default would answer a different question than the
  unit records. MySQL has a native spelling for each unit, so the dialect
  override maps char -> ``CHAR_LENGTH``, octet -> ``LENGTH`` (bytes,
  measured: ``LENGTH(X'0102')`` answers 2), bit -> ``BIT_LENGTH`` (measured:
  ``BIT_LENGTH('abc')`` answers 24).
* An INSERT's VALUES cells may be bare host values since core ``8e2e4d82``
  -- a cell is either an expression, rendered through its own ``to_sql()``,
  or a plain value that becomes a bind parameter -- and this dialect now
  delegates that branch to the base ``format_insert_values_source`` instead
  of re-implementing the per-cell loop (the old loop called
  ``val.to_sql()`` on every cell and could not accept a bare value at all).
"""

import pytest

from rhosocial.activerecord.backend.expression import CharLengthFunction, Column, Literal
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import InsertStatement, ValuesSource
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import MySQLInsertExpression
from rhosocial.activerecord.backend.impl.mysql.functions.math_enhanced import round_


@pytest.fixture
def dialect():
    return MySQLDialect()


class TestCharLengthSpelling:
    """The unit the node declares picks this engine's native spelling."""

    def test_char_unit_spells_char_length(self, dialect):
        sql, params = CharLengthFunction(dialect, Column(dialect, "name")).to_sql()
        assert sql == "CHAR_LENGTH(`name`)"
        assert params == ()

    def test_octet_unit_spells_length(self, dialect):
        sql, params = CharLengthFunction(
            dialect, Column(dialect, "payload"), unit="octet"
        ).to_sql()
        assert sql == "LENGTH(`payload`)"
        assert params == ()

    def test_bit_unit_spells_bit_length(self, dialect):
        sql, params = CharLengthFunction(
            dialect, Column(dialect, "payload"), unit="bit"
        ).to_sql()
        assert sql == "BIT_LENGTH(`payload`)"
        assert params == ()

    def test_alias_survives_the_override(self, dialect):
        sql, _ = CharLengthFunction(
            dialect, Column(dialect, "name"), unit="octet"
        ).as_("len").to_sql()
        assert sql == "LENGTH(`name`) AS `len`"

    def test_the_override_resolves_from_the_mysql_function_mixin(self, dialect):
        assert dialect.format_char_length_function.__func__.__qualname__.startswith(
            "MySQLFunctionMixin"
        )

    def test_the_unknown_unit_is_refused_at_construction(self, dialect):
        with pytest.raises(ValueError, match="unknown length unit"):
            CharLengthFunction(dialect, Column(dialect, "name"), unit="words")


class TestInsertBareValuesCells:
    """A VALUES cell is an expression or a bare host value, per the base contract."""

    def _insert(self, d, rows, columns=("a", "b")):
        return InsertStatement(
            d,
            into=Table(d, "t"),
            source=ValuesSource(d, [list(row) for row in rows]),
            columns=list(columns),
        )

    def test_expression_and_bare_cells_share_one_row(self, dialect):
        stmt = self._insert(dialect, [(Column(dialect, "cnt"), 5)])
        sql, params = stmt.to_sql()
        assert sql == "INSERT INTO `t` (`a`, `b`) VALUES (`cnt`, %s)"
        assert params == (5,)

    def test_all_bare_cells_become_bind_parameters(self, dialect):
        stmt = self._insert(dialect, [(1, "x"), (2, "y")])
        sql, params = stmt.to_sql()
        assert sql == "INSERT INTO `t` (`a`, `b`) VALUES (%s, %s), (%s, %s)"
        assert params == (1, "x", 2, "y")

    def test_expression_cells_still_render_through_their_own_formatters(self, dialect):
        stmt = self._insert(dialect, [(Literal(dialect, "a"), Literal(dialect, 7))])
        sql, params = stmt.to_sql()
        assert sql == "INSERT INTO `t` (`a`, `b`) VALUES (%s, %s)"
        assert params == ("a", 7)

    def test_a_typed_value_cell_binds_like_a_literal(self, dialect):
        from rhosocial.activerecord.backend.expression.values import IntegerValue

        stmt = self._insert(dialect, [(IntegerValue(dialect, 3), 4)])
        sql, params = stmt.to_sql()
        assert sql == "INSERT INTO `t` (`a`, `b`) VALUES (%s, %s)"
        assert params == (3, 4)

    def test_replace_keeps_working_over_bare_cells(self, dialect):
        stmt = MySQLInsertExpression(
            dialect,
            into=Table(dialect, "t"),
            source=ValuesSource(dialect, [[1, "x"]]),
            columns=["a", "b"],
            replace=True,
        )
        sql, params = stmt.to_sql()
        assert sql == "REPLACE INTO `t` (`a`, `b`) VALUES (%s, %s)"
        assert params == (1, "x")


class TestClassedEntryPointsCompose:
    """The classed nodes keep working inside the statements that carry them."""

    def test_a_round_function_inside_a_values_cell(self, dialect):
        stmt = InsertStatement(
            dialect,
            into=Table(dialect, "t"),
            source=ValuesSource(dialect, [[round_(dialect, Literal(dialect, 3.14159), 2)]]),
            columns=["a"],
        )
        sql, params = stmt.to_sql()
        assert sql == "INSERT INTO `t` (`a`) VALUES (ROUND(%s, %s))"
        assert params == (3.14159, 2)
