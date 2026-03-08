# tests/rhosocial/activerecord_mysql_test/feature/backend/test_json_functions_backend.py
"""
MySQL JSON function integration tests using real database connection.

This module tests the MySQL-specific JSON function functionality with actual database operations.

Note: JSON type and functions require MySQL 5.7.8+
Tests are skipped for MySQL 5.6 which doesn't support JSON.

IMPORTANT: mysql-connector-python returns JSON columns as strings, not Python dicts/lists.
Tests that expect automatic JSON parsing must use the column_adapters parameter to specify
the MySQLJSONAdapter for columns that should be parsed.
"""
import pytest


class TestMySQLJSONFunctionBackend:
    """Synchronous tests for MySQL JSON functions with real database."""

    def test_supports_json_function(self, mysql_backend):
        """Test that JSON functions are supported."""
        dialect = mysql_backend.dialect
        if dialect.version >= (5, 7, 8):
            assert dialect.supports_json_function('JSON_EXTRACT')
        else:
            assert not dialect.supports_json_function('JSON_EXTRACT')

    def test_create_table_with_json_column(self, mysql_backend, json_column_adapter):
        """Test creating table with JSON column type."""
        if mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON type requires MySQL 5.7.8+")

        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_json_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        mysql_backend.execute(
            "INSERT INTO test_json_table (data) VALUES ('{\"name\": \"John\"}')"
        )

        # Use column_adapters to parse JSON string to dict
        result = mysql_backend.execute(
            "SELECT data FROM test_json_table WHERE id = 1",
            column_adapters={'data': (json_column_adapter, dict)}
        )

        assert result.data[0]['data']['name'] == 'John'

        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_json_table")

    def test_json_extract_function(self, mysql_backend):
        """Test JSON_EXTRACT function."""
        if mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_json_extract (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        mysql_backend.execute(
            "INSERT INTO test_json_extract (data) VALUES ('{\"name\": \"John\", \"age\": 30}')"
        )

        result = mysql_backend.execute(
            "SELECT JSON_EXTRACT(data, '$.name') as name FROM test_json_extract"
        )

        assert result.data[0]['name'] == '"John"'

        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_json_extract")

    def test_json_object_function(self, mysql_backend, json_column_adapter):
        """Test JSON_OBJECT function."""
        if mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        # Use column_adapters to parse JSON string to dict
        result = mysql_backend.execute(
            "SELECT JSON_OBJECT('name', 'John', 'age', 30) as obj",
            column_adapters={'obj': (json_column_adapter, dict)}
        )

        assert result.data[0]['obj']['name'] == 'John'

    def test_json_array_function(self, mysql_backend, json_column_adapter):
        """Test JSON_ARRAY function."""
        if mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        # Use column_adapters to parse JSON string to list
        result = mysql_backend.execute(
            "SELECT JSON_ARRAY(1, 2, 3) as arr",
            column_adapters={'arr': (json_column_adapter, list)}
        )

        assert result.data[0]['arr'] == [1, 2, 3]

    def test_json_contains_function(self, mysql_backend):
        """Test JSON_CONTAINS function."""
        if mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_json_contains (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        mysql_backend.execute(
            "INSERT INTO test_json_contains (data) VALUES ('{\"tags\": [\"mysql\", \"database\"]}')"
        )

        result = mysql_backend.execute(
            "SELECT id FROM test_json_contains WHERE JSON_CONTAINS(data, '\"mysql\"', '$.tags')"
        )

        assert len(result.data) == 1

        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_json_contains")

    def test_format_json_extract_integration(self, mysql_backend):
        """Test format_json_extract with database execution."""
        if mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_format_json_extract (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        mysql_backend.execute(
            "INSERT INTO test_format_json_extract (data) VALUES ('{\"name\": \"John\"}')"
        )

        dialect = mysql_backend.dialect
        sql, params = dialect.format_json_extract('data', '$.name')

        result = mysql_backend.execute(
            f"SELECT {sql} as name FROM test_format_json_extract",
            params
        )

        assert '"John"' in str(result.data[0]['name'])

        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_format_json_extract")


class TestAsyncMySQLJSONFunctionBackend:
    """Asynchronous tests for MySQL JSON functions with real database."""

    @pytest.mark.asyncio
    async def test_async_supports_json_function(self, async_mysql_backend):
        """Test that JSON functions are supported (async)."""
        dialect = async_mysql_backend.dialect
        if dialect.version >= (5, 7, 8):
            assert dialect.supports_json_function('JSON_EXTRACT')
        else:
            assert not dialect.supports_json_function('JSON_EXTRACT')

    @pytest.mark.asyncio
    async def test_async_create_table_with_json_column(self, async_mysql_backend, json_column_adapter):
        """Test creating table with JSON column type (async)."""
        if async_mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON type requires MySQL 5.7.8+")

        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_json_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        await async_mysql_backend.execute(
            "INSERT INTO test_async_json_table (data) VALUES ('{\"name\": \"Jane\"}')"
        )

        # Use column_adapters to parse JSON string to dict
        result = await async_mysql_backend.execute(
            "SELECT data FROM test_async_json_table WHERE id = 1",
            column_adapters={'data': (json_column_adapter, dict)}
        )

        assert result.data[0]['data']['name'] == 'Jane'

        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_json_table")

    @pytest.mark.asyncio
    async def test_async_json_extract_function(self, async_mysql_backend):
        """Test JSON_EXTRACT function (async)."""
        if async_mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_json_extract (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        await async_mysql_backend.execute(
            "INSERT INTO test_async_json_extract (data) VALUES ('{\"name\": \"Jane\"}')"
        )

        result = await async_mysql_backend.execute(
            "SELECT JSON_EXTRACT(data, '$.name') as name FROM test_async_json_extract"
        )

        assert result.data[0]['name'] == '"Jane"'

        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_json_extract")

    @pytest.mark.asyncio
    async def test_async_json_object_function(self, async_mysql_backend, json_column_adapter):
        """Test JSON_OBJECT function (async)."""
        if async_mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        # Use column_adapters to parse JSON string to dict
        result = await async_mysql_backend.execute(
            "SELECT JSON_OBJECT('name', 'Jane') as obj",
            column_adapters={'obj': (json_column_adapter, dict)}
        )

        assert result.data[0]['obj']['name'] == 'Jane'

    @pytest.mark.asyncio
    async def test_async_json_array_function(self, async_mysql_backend, json_column_adapter):
        """Test JSON_ARRAY function (async)."""
        if async_mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        # Use column_adapters to parse JSON string to list
        result = await async_mysql_backend.execute(
            "SELECT JSON_ARRAY('a', 'b', 'c') as arr",
            column_adapters={'arr': (json_column_adapter, list)}
        )

        assert result.data[0]['arr'] == ['a', 'b', 'c']

    @pytest.mark.asyncio
    async def test_async_json_contains_function(self, async_mysql_backend):
        """Test JSON_CONTAINS function (async)."""
        if async_mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_json_contains (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        await async_mysql_backend.execute(
            "INSERT INTO test_async_json_contains (data) VALUES ('{\"tags\": [\"async\", \"test\"]}')"
        )

        result = await async_mysql_backend.execute(
            "SELECT id FROM test_async_json_contains WHERE JSON_CONTAINS(data, '\"async\"', '$.tags')"
        )

        assert len(result.data) == 1

        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_json_contains")

    @pytest.mark.asyncio
    async def test_async_format_json_extract_integration(self, async_mysql_backend):
        """Test format_json_extract with database execution (async)."""
        if async_mysql_backend.dialect.version < (5, 7, 8):
            pytest.skip("JSON functions require MySQL 5.7.8+")

        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_format_json_extract (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data JSON
            )
            """)

        await async_mysql_backend.execute(
            "INSERT INTO test_async_format_json_extract (data) VALUES ('{\"name\": \"Jane\"}')"
        )

        dialect = async_mysql_backend.dialect
        sql, params = dialect.format_json_extract('data', '$.name')

        result = await async_mysql_backend.execute(
            f"SELECT {sql} as name FROM test_async_format_json_extract",
            params
        )

        assert '"Jane"' in str(result.data[0]['name'])

        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_format_json_extract")
