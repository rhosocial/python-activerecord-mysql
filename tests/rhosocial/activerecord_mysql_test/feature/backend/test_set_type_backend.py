# tests/rhosocial/activerecord_mysql_test/feature/backend/test_set_type_backend.py
"""
MySQL SET type integration tests using real database connection.

This module tests the MySQL-specific SET type functionality with actual database operations.
"""
import pytest
import pytest_asyncio


class TestMySQLSetTypeBackend:
    """Synchronous tests for MySQL SET type with real database."""

    def test_supports_set_type(self, mysql_backend):
        """Test that SET type is supported."""
        dialect = mysql_backend.dialect
        assert dialect.supports_set_type()

    def test_create_table_with_set_column(self, mysql_backend):
        """Test creating table with SET column type."""
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_set_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('red', 'green', 'blue', 'yellow'),
                status SET('active', 'pending', 'archived')
            )
        """)

        # Verify table was created by inserting and querying
        mysql_backend.execute(
            "INSERT INTO test_set_table (tags, status) VALUES ('red', 'active')"
        )

        result = mysql_backend.execute(
            "SELECT tags, status FROM test_set_table WHERE id = 1"
        )

        assert len(result.data) == 1
        assert result.data[0]['tags'] == {'red'}
        assert result.data[0]['status'] == {'active'}

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_set_table")

    def test_insert_and_query_set_value(self, mysql_backend):
        """Test inserting and querying SET values."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_set_insert (
                id INT AUTO_INCREMENT PRIMARY KEY,
                colors SET('red', 'green', 'blue')
            )
        """)

        # Insert single value
        mysql_backend.execute(
            "INSERT INTO test_set_insert (colors) VALUES ('red')"
        )

        # Insert multiple values
        mysql_backend.execute(
            "INSERT INTO test_set_insert (colors) VALUES ('red,green')"
        )

        # Insert all values (MySQL sorts automatically)
        mysql_backend.execute(
            "INSERT INTO test_set_insert (colors) VALUES ('blue,red,green')"
        )

        # Query and verify
        result = mysql_backend.execute(
            "SELECT colors FROM test_set_insert ORDER BY id"
        )

        # MySQL connector returns SET values as Python set
        assert result.data[0]['colors'] == {'red'}
        assert result.data[1]['colors'] == {'green', 'red'}
        assert result.data[2]['colors'] == {'blue', 'green', 'red'}

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_set_insert")

    def test_find_in_set_function(self, mysql_backend):
        """Test FIND_IN_SET function for SET columns."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_find_in_set (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('mysql', 'python', 'database', 'backend')
            )
        """)

        # Insert test data
        mysql_backend.execute(
            "INSERT INTO test_find_in_set (tags) VALUES ('mysql,python')"
        )
        mysql_backend.execute(
            "INSERT INTO test_find_in_set (tags) VALUES ('database')"
        )
        mysql_backend.execute(
            "INSERT INTO test_find_in_set (tags) VALUES ('backend,mysql')"
        )

        # Query using FIND_IN_SET
        result = mysql_backend.execute(
            "SELECT id, tags FROM test_find_in_set WHERE FIND_IN_SET('mysql', tags) > 0"
        )

        assert len(result.data) == 2
        assert result.data[0]['id'] == 1
        assert result.data[1]['id'] == 3

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_find_in_set")

    def test_format_set_literal_integration(self, mysql_backend):
        """Test format_set_literal with database execution."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_set_literal (
                id INT AUTO_INCREMENT PRIMARY KEY,
                colors SET('red', 'green', 'blue')
            )
        """)

        # Use dialect to format literal
        dialect = mysql_backend.dialect
        sql_literal, params = dialect.format_set_literal(['red', 'blue'], ['red', 'green', 'blue'])

        # Insert using formatted literal
        mysql_backend.execute(
            f"INSERT INTO test_set_literal (colors) VALUES ({sql_literal})",
            params
        )

        # Query and verify
        result = mysql_backend.execute(
            "SELECT colors FROM test_set_literal WHERE id = 1"
        )

        # MySQL connector returns SET values as Python set
        assert result.data[0]['colors'] == {'blue', 'red'}

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_set_literal")

    def test_format_find_in_set_integration(self, mysql_backend):
        """Test format_find_in_set with database execution."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_find_format (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('a', 'b', 'c', 'd')
            )
        """)

        # Insert test data
        mysql_backend.execute("INSERT INTO test_find_format (tags) VALUES ('a,b')")
        mysql_backend.execute("INSERT INTO test_find_format (tags) VALUES ('c,d')")
        mysql_backend.execute("INSERT INTO test_find_format (tags) VALUES ('a,c')")

        # Use dialect to format FIND_IN_SET
        dialect = mysql_backend.dialect
        condition, params = dialect.format_find_in_set('a', 'tags')

        # Query using formatted condition
        result = mysql_backend.execute(
            f"SELECT id, tags FROM test_find_format WHERE {condition}",
            params
        )

        assert len(result.data) == 2
        ids = [row['id'] for row in result.data]
        assert 1 in ids
        assert 3 in ids

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_find_format")

    def test_format_set_contains_integration(self, mysql_backend):
        """Test format_set_contains with database execution."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_contains_format (
                id INT AUTO_INCREMENT PRIMARY KEY,
                permissions SET('read', 'write', 'execute', 'admin')
            )
        """)

        # Insert test data
        mysql_backend.execute("INSERT INTO test_contains_format (permissions) VALUES ('read,write')")
        mysql_backend.execute("INSERT INTO test_contains_format (permissions) VALUES ('read,execute')")
        mysql_backend.execute("INSERT INTO test_contains_format (permissions) VALUES ('read,write,admin')")

        # Use dialect to format SET contains check
        dialect = mysql_backend.dialect
        condition, params = dialect.format_set_contains('permissions', ['read', 'write'])

        # Query using formatted condition
        result = mysql_backend.execute(
            f"SELECT id, permissions FROM test_contains_format WHERE {condition}",
            params
        )

        assert len(result.data) == 2
        # MySQL connector returns SET values as Python set
        permissions_values = [row['permissions'] for row in result.data]
        assert {'read', 'write'} in permissions_values or {'write', 'read'} in permissions_values

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_contains_format")

    def test_set_with_null_value(self, mysql_backend):
        """Test SET column with NULL values."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_set_null (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('a', 'b', 'c') NULL
            )
        """)

        # Insert NULL
        mysql_backend.execute("INSERT INTO test_set_null (tags) VALUES (NULL)")

        # Insert non-NULL
        mysql_backend.execute("INSERT INTO test_set_null (tags) VALUES ('a,b')")

        # Query and verify
        result = mysql_backend.execute(
            "SELECT tags FROM test_set_null ORDER BY id"
        )

        assert result.data[0]['tags'] is None
        # MySQL connector returns SET values as Python set
        assert result.data[1]['tags'] == {'a', 'b'}

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_set_null")

    def test_set_count_function(self, mysql_backend):
        """Test counting SET values."""
        # Create table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_set_count (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('a', 'b', 'c', 'd')
            )
        """)

        # Insert test data
        mysql_backend.execute("INSERT INTO test_set_count (tags) VALUES ('a')")
        mysql_backend.execute("INSERT INTO test_set_count (tags) VALUES ('a,b')")
        mysql_backend.execute("INSERT INTO test_set_count (tags) VALUES ('a,b,c,d')")

        # Count rows with specific value
        result = mysql_backend.execute(
            "SELECT COUNT(*) as cnt FROM test_set_count WHERE FIND_IN_SET('a', tags) > 0"
        )

        assert result.data[0]['cnt'] == 3

        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_set_count")


class TestAsyncMySQLSetTypeBackend:
    """Asynchronous tests for MySQL SET type with real database."""

    @pytest.mark.asyncio
    async def test_async_supports_set_type(self, async_mysql_backend):
        """Test that SET type is supported (async)."""
        dialect = async_mysql_backend.dialect
        assert dialect.supports_set_type()

    @pytest.mark.asyncio
    async def test_async_create_table_with_set_column(self, async_mysql_backend):
        """Test creating table with SET column type (async)."""
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_set_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                categories SET('news', 'sports', 'tech', 'entertainment')
            )
        """)

        # Verify table was created by inserting and querying
        await async_mysql_backend.execute(
            "INSERT INTO test_async_set_table (categories) VALUES ('news,sports')"
        )

        result = await async_mysql_backend.execute(
            "SELECT categories FROM test_async_set_table WHERE id = 1"
        )

        assert len(result.data) == 1
        assert result.data[0]['categories'] == {'news', 'sports'}

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_set_table")

    @pytest.mark.asyncio
    async def test_async_insert_and_query_set_value(self, async_mysql_backend):
        """Test inserting and querying SET values (async)."""
        # Create table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_set_insert (
                id INT AUTO_INCREMENT PRIMARY KEY,
                colors SET('red', 'green', 'blue')
            )
        """)

        # Insert single value
        await async_mysql_backend.execute(
            "INSERT INTO test_async_set_insert (colors) VALUES ('red')"
        )

        # Insert multiple values
        await async_mysql_backend.execute(
            "INSERT INTO test_async_set_insert (colors) VALUES ('green,blue')"
        )

        # Query and verify
        result = await async_mysql_backend.execute(
            "SELECT colors FROM test_async_set_insert ORDER BY id"
        )

        # MySQL connector returns SET values as Python set
        assert result.data[0]['colors'] == {'red'}
        assert result.data[1]['colors'] == {'blue', 'green'}

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_set_insert")

    @pytest.mark.asyncio
    async def test_async_find_in_set_function(self, async_mysql_backend):
        """Test FIND_IN_SET function for SET columns (async)."""
        # Create table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_find (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('mysql', 'python', 'database')
            )
        """)

        # Insert test data
        await async_mysql_backend.execute(
            "INSERT INTO test_async_find (tags) VALUES ('mysql,python')"
        )
        await async_mysql_backend.execute(
            "INSERT INTO test_async_find (tags) VALUES ('database')"
        )

        # Query using FIND_IN_SET
        result = await async_mysql_backend.execute(
            "SELECT id, tags FROM test_async_find WHERE FIND_IN_SET('mysql', tags) > 0"
        )

        assert len(result.data) == 1
        assert result.data[0]['id'] == 1

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_find")

    @pytest.mark.asyncio
    async def test_async_format_set_literal_integration(self, async_mysql_backend):
        """Test format_set_literal with database execution (async)."""
        # Create table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_set_literal (
                id INT AUTO_INCREMENT PRIMARY KEY,
                colors SET('red', 'green', 'blue')
            )
        """)

        # Use dialect to format literal
        dialect = async_mysql_backend.dialect
        sql_literal, params = dialect.format_set_literal(['green', 'red'], ['red', 'green', 'blue'])

        # Insert using formatted literal
        await async_mysql_backend.execute(
            f"INSERT INTO test_async_set_literal (colors) VALUES ({sql_literal})",
            params
        )

        # Query and verify
        result = await async_mysql_backend.execute(
            "SELECT colors FROM test_async_set_literal WHERE id = 1"
        )

        # MySQL connector returns SET values as Python set
        assert result.data[0]['colors'] == {'green', 'red'}

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_set_literal")

    @pytest.mark.asyncio
    async def test_async_format_find_in_set_integration(self, async_mysql_backend):
        """Test format_find_in_set with database execution (async)."""
        # Create table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_find_format (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tags SET('x', 'y', 'z')
            )
        """)

        # Insert test data
        await async_mysql_backend.execute("INSERT INTO test_async_find_format (tags) VALUES ('x,y')")
        await async_mysql_backend.execute("INSERT INTO test_async_find_format (tags) VALUES ('z')")

        # Use dialect to format FIND_IN_SET
        dialect = async_mysql_backend.dialect
        condition, params = dialect.format_find_in_set('x', 'tags')

        # Query using formatted condition
        result = await async_mysql_backend.execute(
            f"SELECT id, tags FROM test_async_find_format WHERE {condition}",
            params
        )

        assert len(result.data) == 1
        assert result.data[0]['id'] == 1

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_find_format")

    @pytest.mark.asyncio
    async def test_async_format_set_contains_integration(self, async_mysql_backend):
        """Test format_set_contains with database execution (async)."""
        # Create table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_contains (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roles SET('admin', 'user', 'guest', 'moderator')
            )
        """)

        # Insert test data
        await async_mysql_backend.execute("INSERT INTO test_async_contains (roles) VALUES ('admin,user')")
        await async_mysql_backend.execute("INSERT INTO test_async_contains (roles) VALUES ('guest')")
        await async_mysql_backend.execute("INSERT INTO test_async_contains (roles) VALUES ('admin,moderator')")

        # Use dialect to format SET contains check
        dialect = async_mysql_backend.dialect
        condition, params = dialect.format_set_contains('roles', ['admin'])

        # Query using formatted condition
        result = await async_mysql_backend.execute(
            f"SELECT id, roles FROM test_async_contains WHERE {condition}",
            params
        )

        assert len(result.data) == 2
        ids = [row['id'] for row in result.data]
        assert 1 in ids
        assert 3 in ids

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_contains")

    @pytest.mark.asyncio
    async def test_async_set_with_null_value(self, async_mysql_backend):
        """Test SET column with NULL values (async)."""
        # Create table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_set_null (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status SET('active', 'inactive') NULL
            )
        """)

        # Insert NULL
        await async_mysql_backend.execute("INSERT INTO test_async_set_null (status) VALUES (NULL)")

        # Insert non-NULL
        await async_mysql_backend.execute("INSERT INTO test_async_set_null (status) VALUES ('active')")

        # Query and verify
        result = await async_mysql_backend.execute(
            "SELECT status FROM test_async_set_null ORDER BY id"
        )

        assert result.data[0]['status'] is None
        # MySQL connector returns SET values as Python set
        assert result.data[1]['status'] == {'active'}

        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_set_null")
