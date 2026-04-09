# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_math_enhanced_functions.py
"""
Tests for MySQL-specific enhanced math functions.

These include additional mathematical functions beyond the basic math module.
"""
from rhosocial.activerecord.backend.expression import Column
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
        result = round_(mysql_dialect, 3.14159, 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_pow(self, mysql_dialect: MySQLDialect):
        """Test pow() function."""
        result = pow(mysql_dialect, Column(mysql_dialect, "base"), 2)
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_pow_both_columns(self, mysql_dialect: MySQLDialect):
        """Test pow() with both column references."""
        result = pow(
            mysql_dialect,
            Column(mysql_dialect, "x"),
            Column(mysql_dialect, "y")
        )
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_power(self, mysql_dialect: MySQLDialect):
        """Test power() function (alias for POW)."""
        result = power(mysql_dialect, 2, 3)
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
        result = sqrt(mysql_dialect, 16)
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod(self, mysql_dialect: MySQLDialect):
        """Test mod() function."""
        result = mod(mysql_dialect, Column(mysql_dialect, "total"), 10)
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_mod_both_columns(self, mysql_dialect: MySQLDialect):
        """Test mod() with both column references."""
        result = mod(
            mysql_dialect,
            Column(mysql_dialect, "dividend"),
            Column(mysql_dialect, "divisor")
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
        result = ceil(mysql_dialect, 3.14)
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
        result = floor(mysql_dialect, 3.14)
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
        result = trunc(mysql_dialect, 3.14)
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_trunc_with_precision(self, mysql_dialect: MySQLDialect):
        """Test trunc() with precision."""
        result = trunc(mysql_dialect, 3.14159, 2)
        sql, _ = result.to_sql()
        assert "TRUNCATE(" in sql

    def test_max__two_args(self, mysql_dialect: MySQLDialect):
        """Test max_() with two arguments (uses GREATEST)."""
        result = max_(mysql_dialect, Column(mysql_dialect, "a"), Column(mysql_dialect, "b"))
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__multiple_args(self, mysql_dialect: MySQLDialect):
        """Test max_() with multiple arguments (uses GREATEST)."""
        result = max_(
            mysql_dialect,
            Column(mysql_dialect, "a"),
            Column(mysql_dialect, "b"),
            Column(mysql_dialect, "c")
        )
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__with_literals(self, mysql_dialect: MySQLDialect):
        """Test max_() with literal values (uses GREATEST)."""
        result = max_(mysql_dialect, 1, 2, 3)
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql

    def test_max__single_arg(self, mysql_dialect: MySQLDialect):
        """Test max_() with single column argument (uses MAX aggregate)."""
        result = max_(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_min__two_args(self, mysql_dialect: MySQLDialect):
        """Test min_() with two arguments (uses LEAST)."""
        result = min_(mysql_dialect, Column(mysql_dialect, "a"), Column(mysql_dialect, "b"))
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__multiple_args(self, mysql_dialect: MySQLDialect):
        """Test min_() with multiple arguments (uses LEAST)."""
        result = min_(
            mysql_dialect,
            Column(mysql_dialect, "a"),
            Column(mysql_dialect, "b"),
            Column(mysql_dialect, "c")
        )
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__with_literals(self, mysql_dialect: MySQLDialect):
        """Test min_() with literal values (uses LEAST)."""
        result = min_(mysql_dialect, 1, 2, 3)
        sql, _ = result.to_sql()
        assert "LEAST(" in sql

    def test_min__single_arg(self, mysql_dialect: MySQLDialect):
        """Test min_() with single column argument (uses MIN aggregate)."""
        result = min_(mysql_dialect, Column(mysql_dialect, "value"))
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_avg(self, mysql_dialect: MySQLDialect):
        """Test avg() aggregate function."""
        result = avg(mysql_dialect, Column(mysql_dialect, "price"))
        sql, _ = result.to_sql()
        assert "AVG(" in sql
        assert "`price`" in sql

    def test_avg_with_literal(self, mysql_dialect: MySQLDialect):
        """Test avg() with literal value."""
        result = avg(mysql_dialect, 100)
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_round__with_string_integer(self, mysql_dialect: MySQLDialect):
        """Test round_() with string integer value."""
        result = round_(mysql_dialect, "123", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_float(self, mysql_dialect: MySQLDialect):
        """Test round_() with string float value."""
        result = round_(mysql_dialect, "3.14159", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_column_name(self, mysql_dialect: MySQLDialect):
        """Test round_() with non-numeric string treated as column."""
        result = round_(mysql_dialect, "column_name", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert "`column_name`" in sql

    def test_pow_with_string_integer(self, mysql_dialect: MySQLDialect):
        """Test pow() with string integer exponent."""
        result = pow(mysql_dialect, Column(mysql_dialect, "base"), "2")
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_sqrt_with_string_integer(self, mysql_dialect: MySQLDialect):
        """Test sqrt() with string integer value."""
        result = sqrt(mysql_dialect, "16")
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod_with_string_divisor(self, mysql_dialect: MySQLDialect):
        """Test mod() with string divisor."""
        result = mod(mysql_dialect, Column(mysql_dialect, "total"), "10")
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_max__with_string_literals(self, mysql_dialect: MySQLDialect):
        """Test max_() with non-numeric string values (treated as columns in GREATEST)."""
        result = max_(mysql_dialect, "a", "b", "c")
        sql, _ = result.to_sql()
        assert "GREATEST(" in sql
        # Non-numeric strings should be treated as column names and quoted with backticks
        assert "`a`" in sql

    def test_min__with_string_literals(self, mysql_dialect: MySQLDialect):
        """Test min_() with non-numeric string values (treated as columns in LEAST)."""
        result = min_(mysql_dialect, "a", "b", "c")
        sql, _ = result.to_sql()
        assert "LEAST(" in sql
        # Non-numeric strings should be treated as column names and quoted with backticks
        assert "`a`" in sql

    def test_avg_with_string_literal(self, mysql_dialect: MySQLDialect):
        """Test avg() with string numeric value."""
        result = avg(mysql_dialect, "100")
        sql, _ = result.to_sql()
        assert "AVG(" in sql
