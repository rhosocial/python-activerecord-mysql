# tests/rhosocial/activerecord_mysql_test/feature/backend/test_enum_adapter_backend.py
"""
MySQL ENUM type adapter integration tests using real database connection.

This module tests the MySQL-specific ENUM adapter with actual database operations.
"""
import pytest
import pytest_asyncio
from enum import Enum
from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLEnumAdapter


# Test Enum definitions
class Status(str, Enum):
    """String-based enum for testing."""
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'


class Priority(int, Enum):
    """Integer-based enum for testing."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TestMySQLEnumAdapterBackend:
    """Synchronous tests for MySQL ENUM adapter with real database."""

    def test_adapter_registered_in_backend(self, mysql_backend):
        """Test that MySQLEnumAdapter is registered in backend."""
        from enum import Enum
        
        # Get adapter for Enum -> str
        adapter = mysql_backend.adapter_registry.get_adapter(Enum, str)
        
        # Should return MySQLEnumAdapter instance
        assert adapter is not None
        assert isinstance(adapter, MySQLEnumAdapter)

    def test_string_enum_round_trip(self, mysql_backend):
        """Test string enum round trip through adapter registry."""
        from enum import Enum
        
        # Get adapter for generic Enum -> str (registered type)
        adapter = mysql_backend.adapter_registry.get_adapter(Enum, str)
        
        # Should be MySQLEnumAdapter
        assert isinstance(adapter, MySQLEnumAdapter)
        
        # Test to_database
        db_value = adapter.to_database(Status.PUBLISHED, str)
        assert db_value == 'published'
        
        # Test from_database
        py_value = adapter.from_database('published', Status)
        assert py_value == Status.PUBLISHED

    def test_int_enum_round_trip(self, mysql_backend):
        """Test integer enum round trip through adapter registry."""
        from enum import Enum
        
        # Get adapter for generic Enum -> int (registered type)
        adapter = mysql_backend.adapter_registry.get_adapter(Enum, int)
        
        # Should be MySQLEnumAdapter
        assert isinstance(adapter, MySQLEnumAdapter)
        
        # Test to_database
        db_value = adapter.to_database(Priority.HIGH, int)
        assert db_value == 3
        
        # Test from_database
        py_value = adapter.from_database(3, Priority)
        assert py_value == Priority.HIGH

    def test_enum_with_sql_execution(self, mysql_backend):
        """Test enum handling in actual SQL execution."""
        # Create temporary table with ENUM column
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_enum_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status VARCHAR(20),
                priority INT
            )
        """)
        
        # Insert with enum values
        mysql_backend.execute(
            "INSERT INTO test_enum_table (status, priority) VALUES (%s, %s)",
            ('published', 3)
        )
        
        # Query and verify
        result = mysql_backend.execute(
            "SELECT status, priority FROM test_enum_table WHERE id = %s",
            (1,)
        )
        
        assert result.data[0]['status'] == 'published'
        assert result.data[0]['priority'] == 3
        
        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_enum_table")

    def test_enum_null_handling_with_database(self, mysql_backend):
        """Test NULL enum handling with database."""
        # Create temporary table
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_enum_null (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status VARCHAR(20) NULL
            )
        """)
        
        # Insert NULL
        mysql_backend.execute(
            "INSERT INTO test_enum_null (status) VALUES (NULL)"
        )
        
        # Query and verify NULL
        result = mysql_backend.execute(
            "SELECT status FROM test_enum_null WHERE id = %s",
            (1,)
        )
        
        assert result.data[0]['status'] is None
        
        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_enum_null")

    def test_native_mysql_enum_type(self, mysql_backend):
        """Test integration with MySQL native ENUM column type."""
        # Create table with native ENUM type
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_native_enum (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status ENUM('draft', 'published', 'archived')
            )
        """)
        
        # Get adapter
        from enum import Enum
        adapter = mysql_backend.adapter_registry.get_adapter(Enum, str)
        
        # Insert using adapter
        db_value = adapter.to_database(Status.PUBLISHED, str)
        mysql_backend.execute(
            "INSERT INTO test_native_enum (status) VALUES (%s)",
            (db_value,)
        )
        
        # Query and convert back
        result = mysql_backend.execute(
            "SELECT status FROM test_native_enum WHERE id = %s",
            (1,)
        )
        
        db_result = result.data[0]['status']
        py_status = adapter.from_database(db_result, Status)
        
        assert py_status == Status.PUBLISHED
        
        # Cleanup
        mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_native_enum")


class TestAsyncMySQLEnumAdapterBackend:
    """Asynchronous tests for MySQL ENUM adapter with real database."""

    @pytest.mark.asyncio
    async def test_async_adapter_registered_in_backend(self, async_mysql_backend):
        """Test that MySQLEnumAdapter is registered in async backend."""
        from enum import Enum
        
        # Get adapter for Enum -> str
        adapter = async_mysql_backend.adapter_registry.get_adapter(Enum, str)
        
        # Should return MySQLEnumAdapter instance
        assert adapter is not None
        assert isinstance(adapter, MySQLEnumAdapter)

    @pytest.mark.asyncio
    async def test_async_string_enum_round_trip(self, async_mysql_backend):
        """Test string enum round trip through adapter registry (async)."""
        from enum import Enum
        
        # Get adapter for generic Enum -> str
        adapter = async_mysql_backend.adapter_registry.get_adapter(Enum, str)
        
        # Should be MySQLEnumAdapter
        assert isinstance(adapter, MySQLEnumAdapter)
        
        # Test to_database
        db_value = adapter.to_database(Status.DRAFT, str)
        assert db_value == 'draft'
        
        # Test from_database
        py_value = adapter.from_database('draft', Status)
        assert py_value == Status.DRAFT

    @pytest.mark.asyncio
    async def test_async_int_enum_round_trip(self, async_mysql_backend):
        """Test integer enum round trip through adapter registry (async)."""
        from enum import Enum
        
        # Get adapter for generic Enum -> int
        adapter = async_mysql_backend.adapter_registry.get_adapter(Enum, int)
        
        # Should be MySQLEnumAdapter
        assert isinstance(adapter, MySQLEnumAdapter)
        
        # Test to_database
        db_value = adapter.to_database(Priority.MEDIUM, int)
        assert db_value == 2
        
        # Test from_database
        py_value = adapter.from_database(2, Priority)
        assert py_value == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_async_enum_with_sql_execution(self, async_mysql_backend):
        """Test enum handling in actual SQL execution (async)."""
        # Create temporary table with ENUM column
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_enum_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status VARCHAR(20),
                priority INT
            )
        """)
        
        # Insert with enum values
        await async_mysql_backend.execute(
            "INSERT INTO test_async_enum_table (status, priority) VALUES (%s, %s)",
            ('archived', 1)
        )
        
        # Query and verify
        result = await async_mysql_backend.execute(
            "SELECT status, priority FROM test_async_enum_table WHERE id = %s",
            (1,)
        )
        
        assert result.data[0]['status'] == 'archived'
        assert result.data[0]['priority'] == 1
        
        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_enum_table")

    @pytest.mark.asyncio
    async def test_async_enum_null_handling_with_database(self, async_mysql_backend):
        """Test NULL enum handling with database (async)."""
        # Create temporary table
        await async_mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_async_enum_null (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status VARCHAR(20) NULL
            )
        """)
        
        # Insert NULL
        await async_mysql_backend.execute(
            "INSERT INTO test_async_enum_null (status) VALUES (NULL)"
        )
        
        # Query and verify NULL
        result = await async_mysql_backend.execute(
            "SELECT status FROM test_async_enum_null WHERE id = %s",
            (1,)
        )
        
        assert result.data[0]['status'] is None
        
        # Cleanup
        await async_mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_async_enum_null")
