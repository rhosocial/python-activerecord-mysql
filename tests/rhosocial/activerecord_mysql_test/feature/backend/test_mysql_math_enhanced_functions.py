# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_math_enhanced_functions.py
"""
Tests for MySQL-specific enhanced math functions.

These include additional mathematical functions beyond the basic math module.

Every value argument is an expression: a `Column` to read a column, a `Literal`
to write a value. The tests below spell both out, including for names that look
like numbers -- `sqrt(dialect, "16")` used to parse "16" into the number
sixteen, so a column named `16` could not be read at all.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal, NumericColumn
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.functions.math_enhanced import (
    round_,
    pow,
    power,
    sqrt,
    mod,
    ceil,
    floor,
    trunc,
    max_,
    min_,
    avg,
)


class TestMySQLMathEnhancedFunctions:
    """Tests for MySQL enhanced math functions."""

    def test_round__default(self, mysql_dialect: MySQLDialect):
        """Test round_() with default precision."""
        result = round_(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert "`value`" in sql

    def test_round__with_precision(self, mysql_dialect: MySQLDialect):
        """Test round_() with precision."""
        result = round_(mysql_dialect, Column(mysql_dialect, "price"), 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_literal(self, mysql_dialect: MySQLDialect):
        """Test round_() with literal value."""
        result = round_(mysql_dialect, Literal(mysql_dialect, 3.14159), 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert "`price`" not in sql

    def test_pow(self, mysql_dialect: MySQLDialect):
        """Test pow() function."""
        result = pow(
            mysql_dialect, Column(mysql_dialect, "base"), Literal(mysql_dialect, 2)
        )
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_pow_both_columns(self, mysql_dialect: MySQLDialect):
        """Test pow() with both column references."""
        result = pow(
            mysql_dialect,
            Column(mysql_dialect, "x"),
            NumericColumn(mysql_dialect, "y"),
        )
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_power(self, mysql_dialect: MySQLDialect):
        """Test power() function (alias for POW)."""
        result = power(
            mysql_dialect, Literal(mysql_dialect, 2), Literal(mysql_dialect, 3)
        )
        sql, _ = result.to_sql()
        assert "POWER(" in sql

    def test_sqrt(self, mysql_dialect: MySQLDialect):
        """Test sqrt() function."""
        result = sqrt(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql
        assert "`value`" in sql

    def test_sqrt_with_literal(self, mysql_dialect: MySQLDialect):
        """Test sqrt() with literal value."""
        result = sqrt(mysql_dialect, Literal(mysql_dialect, 16))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod(self, mysql_dialect: MySQLDialect):
        """Test mod() function."""
        result = mod(
            mysql_dialect, Column(mysql_dialect, "total"), Literal(mysql_dialect, 10)
        )
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_mod_both_columns(self, mysql_dialect: MySQLDialect):
        """Test mod() with both column references."""
        result = mod(
            mysql_dialect,
            NumericColumn(mysql_dialect, "dividend"),
            NumericColumn(mysql_dialect, "divisor"),
        )
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_ceil(self, mysql_dialect: MySQLDialect):
        """Test ceil() function."""
        result = ceil(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "CEIL(" in sql
        assert "`value`" in sql

    def test_ceil_with_literal(self, mysql_dialect: MySQLDialect):
        """Test ceil() with literal value."""
        result = ceil(mysql_dialect, Literal(mysql_dialect, 3.14))
        sql, _ = result.to_sql()
        assert "CEIL(" in sql

    def test_floor(self, mysql_dialect: MySQLDialect):
        """Test floor() function."""
        result = floor(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql
        assert "`value`" in sql

    def test_floor_with_literal(self, mysql_dialect: MySQLDialect):
        """Test floor() with literal value."""
        result = floor(mysql_dialect, Literal(mysql_dialect, 3.14))
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql

    def test_trunc(self, mysql_dialect: MySQLDialect):
        """Test trunc() function (becomes TRUNCATE in MySQL)."""
        result = trunc(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql
        assert "`value`" in sql

    def test_trunc_with_literal(self, mysql_dialect: MySQLDialect):
        """Test trunc() with literal value."""
        result = trunc(mysql_dialect, Literal(mysql_dialect, 3.14))
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_trunc_with_precision(self, mysql_dialect: MySQLDialect):
        """Test trunc() with precision."""
        result = trunc(mysql_dialect, Literal(mysql_dialect, 3.14159), 2)
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_max__two_args(self, mysql_dialect: MySQLDialect):
        """Test max_() with two arguments (uses GREATEST)."""
        result = max_(
            mysql_dialect,
            Column(mysql_dialect, "a"),
            NumericColumn(mysql_dialect, "b"),
        )
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__multiple_args(self, mysql_dialect: MySQLDialect):
        """Test max_() with multiple arguments (uses GREATEST)."""
        result = max_(
            mysql_dialect,
            NumericColumn(mysql_dialect, "a"),
            NumericColumn(mysql_dialect, "b"),
            NumericColumn(mysql_dialect, "c"),
        )
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__with_literals(self, mysql_dialect: MySQLDialect):
        """Test max_() with literal values (uses GREATEST)."""
        result = max_(
            mysql_dialect,
            Literal(mysql_dialect, 1),
            Literal(mysql_dialect, 2),
            Literal(mysql_dialect, 3),
        )
        sql, params = result.to_sql()
        assert "GREATEST(" in sql
        assert params == (1, 2, 3)

    def test_max__single_arg(self, mysql_dialect: MySQLDialect):
        """Test max_() with single column argument (uses MAX aggregate)."""
        result = max_(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_min__two_args(self, mysql_dialect: MySQLDialect):
        """Test min_() with two arguments (uses LEAST)."""
        result = min_(
            mysql_dialect,
            NumericColumn(mysql_dialect, "a"),
            NumericColumn(mysql_dialect, "b"),
        )
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__multiple_args(self, mysql_dialect: MySQLDialect):
        """Test min_() with multiple arguments (uses LEAST)."""
        result = min_(
            mysql_dialect,
            NumericColumn(mysql_dialect, "a"),
            NumericColumn(mysql_dialect, "b"),
            NumericColumn(mysql_dialect, "c"),
        )
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__with_literals(self, mysql_dialect: MySQLDialect):
        """Test min_() with literal values (uses LEAST)."""
        result = min_(
            mysql_dialect,
            Literal(mysql_dialect, 1),
            Literal(mysql_dialect, 2),
            Literal(mysql_dialect, 3),
        )
        sql, params = result.to_sql()
        assert "LEAST(" in sql
        assert params == (1, 2, 3)

    def test_min__single_arg(self, mysql_dialect: MySQLDialect):
        """Test min_() with single column argument (uses MIN aggregate)."""
        result = min_(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_avg(self, mysql_dialect: MySQLDialect):
        """Test avg() aggregate function."""
        result = avg(mysql_dialect, NumericColumn(mysql_dialect, "price"))
        sql, _ = result.to_sql()
        assert "AVG(" in sql
        assert "`price`" in sql

    def test_avg_with_literal(self, mysql_dialect: MySQLDialect):
        """Test avg() with literal value."""
        result = avg(mysql_dialect, Literal(mysql_dialect, 100))
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_round__numeric_looking_name_is_a_column(self, mysql_dialect: MySQLDialect):
        """A name that spells a number is still a column, not that number."""
        result = round_(mysql_dialect, NumericColumn(mysql_dialect, "123"), 2)
        sql, params = result.to_sql()
        assert "ROUND(" in sql
        assert "`123`" in sql
        assert 123 not in params

    def test_round__numeric_looking_float_name_is_a_column(
        self, mysql_dialect: MySQLDialect
    ):
        """A decimal name is a column too; it used to become a float literal."""
        result = round_(mysql_dialect, NumericColumn(mysql_dialect, "3.14159"), 2)
        sql, params = result.to_sql()
        assert "ROUND(" in sql
        assert "`3.14159`" in sql
        assert 3.14159 not in params

    def test_round__with_column_name(self, mysql_dialect: MySQLDialect):
        """Test round_() with a non-numeric column."""
        result = round_(mysql_dialect, Column(mysql_dialect, "column_name"), 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert "`column_name`" in sql

    def test_pow_with_numeric_looking_exponent(self, mysql_dialect: MySQLDialect):
        """The exponent "2" is a column named 2, not the number two."""
        result = pow(
            mysql_dialect, Column(mysql_dialect, "base"), NumericColumn(mysql_dialect, "2")
        )
        sql, params = result.to_sql()
        assert "POW(" in sql
        assert "`2`" in sql
        assert 2 not in params

    def test_sqrt_with_numeric_looking_name(self, mysql_dialect: MySQLDialect):
        """`16` is a column: sqrt(dialect, "16") used to compute sqrt(16) = 4."""
        result = sqrt(mysql_dialect, NumericColumn(mysql_dialect, "16"))
        sql, params = result.to_sql()
        assert "SQRT(" in sql
        assert "`16`" in sql
        assert 16 not in params

    def test_mod_with_numeric_looking_divisor(self, mysql_dialect: MySQLDialect):
        """The divisor "10" is a column named 10, not the number ten."""
        result = mod(
            mysql_dialect, Column(mysql_dialect, "total"), NumericColumn(mysql_dialect, "10")
        )
        sql, params = result.to_sql()
        assert "MOD(" in sql
        assert "`10`" in sql
        assert 10 not in params

    def test_max__with_column_names(self, mysql_dialect: MySQLDialect):
        """max_() over three columns (uses GREATEST)."""
        result = max_(
            mysql_dialect,
            Column(mysql_dialect, "a"),
            Column(mysql_dialect, "b"),
            Column(mysql_dialect, "c"),
        )
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql
        assert "`a`" in sql

    def test_min__with_column_names(self, mysql_dialect: MySQLDialect):
        """min_() over three columns (uses LEAST)."""
        result = min_(
            mysql_dialect,
            Column(mysql_dialect, "a"),
            Column(mysql_dialect, "b"),
            Column(mysql_dialect, "c"),
        )
        sql, _ = result.to_sql()
        assert "LEAST(" in sql
        assert "`a`" in sql

    def test_avg_with_numeric_looking_name(self, mysql_dialect: MySQLDialect):
        """`100` is a column named 100, not the number one hundred."""
        result = avg(mysql_dialect, NumericColumn(mysql_dialect, "100"))
        sql, params = result.to_sql()
        assert "AVG(" in sql
        assert "`100`" in sql
        assert 100 not in params

    def test_bare_string_is_rejected_not_guessed(self, mysql_dialect: MySQLDialect):
        """A bare string used to be parsed into a number or a column, silently.

        The factory no longer decides what an argument meant: an argument that
        is not an expression fails to render instead of quietly becoming one.
        """
        with pytest.raises(AttributeError):
            sqrt(mysql_dialect, "16").to_sql()
