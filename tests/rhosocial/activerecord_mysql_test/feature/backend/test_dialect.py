# tests/rhosocial/activerecord_mysql_test/feature/backend/test_dialect.py
"""
MySQL backend dialect tests using real database connection.

This module tests MySQL dialect formatting using real database.
Each test has sync and async versions for complete coverage.
"""
import pytest
import pytest_asyncio


class TestMySQLDialectBackend:
    """Synchronous dialect tests for MySQL backend."""

    def test_format_identifier(self, mysql_backend):
        """Test identifier formatting."""
        dialect = mysql_backend.dialect

        result = dialect.format_identifier("test_table")
        assert result == "`test_table`"

        result = dialect.format_identifier("user_name")
        assert result == "`user_name`"

    def test_quote_parameter(self, mysql_backend):
        """Test parameter quoting for MySQL."""
        sql = "SELECT * FROM users WHERE name = %s"
        params = ("John",)

        result_sql, result_params = mysql_backend._prepare_sql_and_params(sql, params)

        assert "%s" in result_sql or "?" in result_sql


class TestAsyncMySQLDialectBackend:
    """Asynchronous dialect tests for MySQL backend."""

    @pytest.mark.asyncio
    async def test_async_format_identifier(self, async_mysql_backend):
        """Test identifier formatting (async)."""
        dialect = async_mysql_backend.dialect

        result = dialect.format_identifier("test_table")
        assert result == "`test_table`"

        result = dialect.format_identifier("user_name")
        assert result == "`user_name`"

    @pytest.mark.asyncio
    async def test_async_quote_parameter(self, async_mysql_backend):
        """Test parameter quoting for MySQL (async)."""
        sql = "SELECT * FROM users WHERE name = %s"
        params = ("John",)

        result_sql, result_params = async_mysql_backend._prepare_sql_and_params(sql, params)

        assert "%s" in result_sql or "?" in result_sql
