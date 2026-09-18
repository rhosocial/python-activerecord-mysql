# tests/rhosocial/activerecord_mysql_test/feature/backend/test_set_type.py
"""
MySQL SET type support tests.

This module tests MySQL-specific SET type functionality including:
- Protocol support detection
- SET literal formatting
- FIND_IN_SET function formatting
- SET contains check formatting
"""

import pytest
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLFindInSetExpression,
    MySQLSetContainsExpression,
    MySQLSetLiteralExpression,
)


class TestSetTypeProtocol:
    """Test SET type protocol implementation."""

    def test_supports_set_type(self):
        """Test that SET type is always supported."""
        dialect_55 = MySQLDialect(version=(5, 5, 0))
        assert dialect_55.supports_set_type()

        dialect_56 = MySQLDialect(version=(5, 6, 0))
        assert dialect_56.supports_set_type()

        dialect_80 = MySQLDialect(version=(8, 0, 0))
        assert dialect_80.supports_set_type()

    def test_format_set_literal_single_value(self):
        """Test SET literal with single value."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetLiteralExpression(dialect, ["value1"])
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert params == ("value1",)

    def test_format_set_literal_multiple_values(self):
        """Test SET literal with multiple values."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetLiteralExpression(dialect, ["value3", "value1", "value2"])
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert params == ("value1,value2,value3",)

    def test_format_set_literal_empty(self):
        """Test SET literal with empty list."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetLiteralExpression(dialect, [])
        sql, params = expr.to_sql()

        assert sql == "'"
        assert params == ()

    def test_format_set_literal_with_validation(self):
        """Test SET literal with column values validation."""
        dialect = MySQLDialect(version=(8, 0, 0))
        column_values = ["red", "green", "blue"]

        expr = MySQLSetLiteralExpression(dialect, ["red", "blue"], column_values)
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert params == ("blue,red",)

    def test_format_set_literal_invalid_value_raises_error(self):
        """Test that invalid SET values raise error."""
        dialect = MySQLDialect(version=(8, 0, 0))
        column_values = ["red", "green", "blue"]

        with pytest.raises(ValueError, match="Invalid SET values"):
            MySQLSetLiteralExpression(dialect, ["red", "yellow"], column_values).to_sql()

    def test_format_set_literal_max_members_exceeded(self):
        """Test that exceeding 64 members raises error."""
        dialect = MySQLDialect(version=(8, 0, 0))
        values = [f"val{i}" for i in range(65)]

        with pytest.raises(ValueError, match="maximum 64 members"):
            MySQLSetLiteralExpression(dialect, values).to_sql()

    def test_format_set_literal_max_members_allowed(self):
        """Test that 64 members is allowed."""
        dialect = MySQLDialect(version=(8, 0, 0))
        values = [f"val{i:02d}" for i in range(64)]

        expr = MySQLSetLiteralExpression(dialect, values)
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert len(params[0].split(",")) == 64

    def test_format_find_in_set(self):
        """Test FIND_IN_SET function formatting."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLFindInSetExpression(dialect, "value1", "tags")
        sql, params = expr.to_sql()

        assert sql == "FIND_IN_SET(%s, `tags`) > 0"
        assert params == ("value1",)

    def test_format_find_in_set_different_column(self):
        """Test FIND_IN_SET with different column name."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLFindInSetExpression(dialect, "active", "status")
        sql, params = expr.to_sql()

        assert sql == "FIND_IN_SET(%s, `status`) > 0"
        assert params == ("active",)

    def test_format_set_contains_single_value(self):
        """Test SET contains check with single value."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetContainsExpression(dialect, "tags", ["value1"])
        sql, params = expr.to_sql()

        assert sql == "FIND_IN_SET(%s, `tags`) > 0"
        assert params == ("value1",)

    def test_format_set_contains_multiple_values(self):
        """Test SET contains check with multiple values."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetContainsExpression(dialect, "tags", ["value1", "value2"])
        sql, params = expr.to_sql()

        assert "FIND_IN_SET(%s, `tags`) > 0" in sql
        assert " AND " in sql
        assert params == ("value1", "value2")

    def test_format_set_contains_three_values(self):
        """Test SET contains check with three values."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetContainsExpression(dialect, "status", ["active", "pending", "verified"])
        sql, params = expr.to_sql()

        assert sql.count("FIND_IN_SET") == 3
        assert sql.count(" AND ") == 2
        assert params == ("active", "pending", "verified")


class TestAsyncSetTypeProtocol:
    """Test async SET type protocol (same as sync, but verifies parity)."""

    @pytest.mark.asyncio
    async def test_async_supports_set_type(self):
        """Test async version of supports_set_type."""
        dialect = MySQLDialect(version=(8, 0, 0))
        assert dialect.supports_set_type()

    @pytest.mark.asyncio
    async def test_async_format_set_literal(self):
        """Test async version of SET literal formatting."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetLiteralExpression(dialect, ["a", "b", "c"])
        sql, params = expr.to_sql()

        assert sql == "%s"
        assert params == ("a,b,c",)

    @pytest.mark.asyncio
    async def test_async_format_find_in_set(self):
        """Test async version of FIND_IN_SET formatting."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLFindInSetExpression(dialect, "test", "column")
        sql, params = expr.to_sql()

        assert "FIND_IN_SET" in sql
        assert params == ("test",)

    @pytest.mark.asyncio
    async def test_async_format_set_contains(self):
        """Test async version of SET contains formatting."""
        dialect = MySQLDialect(version=(8, 0, 0))

        expr = MySQLSetContainsExpression(dialect, "tags", ["a", "b"])
        sql, params = expr.to_sql()

        assert " AND " in sql
        assert params == ("a", "b")
