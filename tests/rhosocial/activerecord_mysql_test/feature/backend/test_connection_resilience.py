# tests/rhosocial/activerecord_mysql_test/feature/backend/test_connection_resilience.py
"""
Connection Resilience Tests

Tests for MySQL backend's ability to handle connection loss scenarios:
1. Connection timeout (wait_timeout)
2. Connection killed by KILL CONNECTION
3. Automatic reconnection via ping method
4. is_connected() method accuracy

These tests verify the implementation of:
- Plan A: Pre-query connection check in _get_cursor()
- Plan B: Error retry mechanism in execute()

Both synchronous (MySQLBackend) and asynchronous (AsyncMySQLBackend) are tested.
"""
import pytest
import pytest_asyncio
import asyncio
import time
import logging

from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, AsyncMySQLBackend


logger = logging.getLogger(__name__)


def print_separator(title: str):
    """Print a visual separator for test sections."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ============================================================================
# Synchronous Backend Tests
# ============================================================================


class TestIsConnectedMethod:
    """Tests for the is_connected() method accuracy."""

    def test_is_connected_when_connected(self, mysql_backend_single: MySQLBackend):
        """Verify is_connected() returns True for active connection."""
        assert mysql_backend_single._connection is not None
        assert mysql_backend_single._connection.is_connected() is True

    def test_is_connected_after_disconnect(self, mysql_backend_single: MySQLBackend):
        """Verify is_connected() returns False after explicit disconnect."""
        mysql_backend_single.disconnect()
        # After disconnect, _connection should be None
        assert mysql_backend_single._connection is None

    def test_is_connected_after_kill(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """Verify is_connected() correctly detects killed connections."""
        # Get current connection ID
        result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        connection_id = result.data[0]['id']
        print(f"Test connection ID: {connection_id}")

        # Kill the connection
        mysql_control_backend.execute(f"KILL CONNECTION {connection_id}")
        time.sleep(1)  # Wait for connection to be terminated

        # Verify is_connected() detects the disconnection
        # Note: _connection is not None, but is_connected() should return False
        assert mysql_backend_single._connection is not None
        is_connected = mysql_backend_single._connection.is_connected()
        assert is_connected is False, "is_connected() should return False for killed connection"


class TestWaitTimeoutRecovery:
    """Tests for wait_timeout connection recovery."""

    def test_wait_timeout_triggers_reconnection(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """
        Test that wait_timeout expiration triggers automatic reconnection.

        This test:
        1. Gets the original wait_timeout value
        2. Sets a short timeout (5 seconds)
        3. Waits for timeout
        4. Verifies query succeeds with automatic reconnection
        """
        print_separator("Test: wait_timeout Recovery")

        # 1. Get original wait_timeout
        result = mysql_backend_single.introspector.show.variables(like="wait_timeout")
        original_timeout = int(result[0].value)
        print(f"Original wait_timeout: {original_timeout} seconds")

        # 2. Set short timeout
        test_timeout = 5
        print(f"Setting wait_timeout to {test_timeout} seconds...")
        mysql_backend_single.execute(f"SET SESSION wait_timeout = {test_timeout}")

        # Verify setting
        result = mysql_backend_single.introspector.show.variables(like="wait_timeout")
        current_timeout = int(result[0].value)
        assert current_timeout == test_timeout
        print(f"Current wait_timeout: {current_timeout} seconds")

        # 3. Wait for timeout (plus buffer)
        print(f"Waiting {test_timeout + 2} seconds for timeout...")
        time.sleep(test_timeout + 2)

        # 4. Execute query - should trigger reconnection
        print("Executing query after timeout...")
        try:
            result = mysql_backend_single.execute("SELECT 1 AS test")
            print(f"Query succeeded: {result}")
            assert result.data[0]['test'] == 1

            # Verify we have a new connection
            new_conn_result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
            print(f"New connection ID: {new_conn_result.data[0]['id']}")
        finally:
            # Restore original timeout via control backend
            try:
                mysql_control_backend.execute(f"SET GLOBAL wait_timeout = {original_timeout}")
            except Exception:
                pass  # Ignore cleanup errors


class TestKillConnectionRecovery:
    """Tests for KILL CONNECTION recovery."""

    def test_kill_connection_triggers_reconnection(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """
        Test that KILL CONNECTION triggers automatic reconnection.

        This test:
        1. Gets current connection ID
        2. Kills the connection
        3. Verifies next query succeeds with automatic reconnection
        """
        print_separator("Test: KILL CONNECTION Recovery")

        # 1. Get current connection ID
        result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)  # Wait for termination

        # 3. Execute query - should trigger reconnection
        print("Executing query after connection killed...")
        result = mysql_backend_single.execute("SELECT 1 AS test")
        print(f"Query succeeded: {result}")
        assert result.data[0]['test'] == 1

        # 4. Verify new connection ID
        new_conn_result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id, "Should have a new connection ID"

    def test_multiple_queries_after_reconnection(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """
        Test that multiple queries work correctly after reconnection.

        This verifies that the reconnection is stable and the backend
        remains in a consistent state.
        """
        print_separator("Test: Multiple Queries After Reconnection")

        # Kill connection
        result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)

        # Execute multiple queries
        for i in range(5):
            result = mysql_backend_single.execute(f"SELECT {i} AS value")
            assert result.data[0]['value'] == i
            print(f"Query {i + 1}/5 succeeded")


class TestPingReconnect:
    """Tests for manual ping reconnection."""

    def test_ping_reconnect_after_kill(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """
        Test that ping(reconnect=True) can restore a killed connection.

        This test:
        1. Gets current connection ID
        2. Kills the connection
        3. Calls ping(reconnect=True)
        4. Verifies connection is restored with new ID
        """
        print_separator("Test: Ping Reconnect")

        # 1. Get current connection ID
        result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)

        # 3. Verify connection is dead
        assert mysql_backend_single._connection.is_connected() is False
        print("Connection confirmed dead")

        # 4. Ping with reconnect
        print("Calling ping(reconnect=True)...")
        ping_result = mysql_backend_single.ping(reconnect=True)
        print(f"Ping result: {ping_result}")
        assert ping_result is True, "Ping should succeed with reconnect=True"

        # 5. Verify connection is restored
        assert mysql_backend_single._connection.is_connected() is True

        # 6. Verify new connection ID
        new_conn_result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id

    def test_ping_no_reconnect_keeps_dead_connection(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """
        Test that ping(reconnect=False) returns False for dead connections
        without attempting reconnection.
        """
        print_separator("Test: Ping No Reconnect")

        # Get current connection ID
        result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']

        # Kill the connection
        mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)

        # Verify connection is dead
        assert mysql_backend_single._connection.is_connected() is False

        # Ping without reconnect
        ping_result = mysql_backend_single.ping(reconnect=False)
        print(f"Ping result (reconnect=False): {ping_result}")
        assert ping_result is False, "Ping should return False for dead connection"

        # Connection should still be dead
        assert mysql_backend_single._connection.is_connected() is False


class TestGetCursorAutoReconnect:
    """Tests for _get_cursor() automatic reconnection behavior."""

    def test_get_cursor_reconnects_killed_connection(
        self,
        mysql_backend_single: MySQLBackend,
        mysql_control_backend: MySQLBackend
    ):
        """
        Test that _get_cursor() automatically reconnects when connection is dead.

        This verifies Plan A: Pre-query connection check.
        """
        print_separator("Test: _get_cursor Auto Reconnect")

        # Get current connection ID
        result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # Kill the connection
        mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        time.sleep(1)

        # Verify connection is dead
        assert mysql_backend_single._connection.is_connected() is False

        # Call _get_cursor - should trigger reconnection
        cursor = mysql_backend_single._get_cursor()
        print("_get_cursor() returned cursor successfully")

        # Verify connection is now alive
        assert mysql_backend_single._connection.is_connected() is True

        # Clean up cursor
        cursor.close()

        # Verify new connection ID
        new_conn_result = mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id


# ============================================================================
# Asynchronous Backend Tests
# ============================================================================


class TestAsyncIsConnectedMethod:
    """Async tests for the is_connected() method accuracy."""

    @pytest.mark.asyncio
    async def test_is_connected_when_connected(self, async_mysql_backend_single: AsyncMySQLBackend):
        """Verify is_connected() returns True for active connection."""
        assert async_mysql_backend_single._connection is not None
        assert await async_mysql_backend_single._connection.is_connected() is True

    @pytest.mark.asyncio
    async def test_is_connected_after_disconnect(self, async_mysql_backend_single: AsyncMySQLBackend):
        """Verify is_connected() returns False after explicit disconnect."""
        await async_mysql_backend_single.disconnect()
        # After disconnect, _connection should be None
        assert async_mysql_backend_single._connection is None

    @pytest.mark.asyncio
    async def test_is_connected_after_kill(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """Verify is_connected() correctly detects killed connections."""
        # Get current connection ID
        result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        connection_id = result.data[0]['id']
        print(f"Test connection ID: {connection_id}")

        # Kill the connection
        await async_mysql_control_backend.execute(f"KILL CONNECTION {connection_id}")
        await asyncio.sleep(1)  # Wait for connection to be terminated

        # Verify is_connected() detects the disconnection
        assert async_mysql_backend_single._connection is not None
        is_connected = await async_mysql_backend_single._connection.is_connected()
        assert is_connected is False, "is_connected() should return False for killed connection"


class TestAsyncWaitTimeoutRecovery:
    """Async tests for wait_timeout connection recovery."""

    @pytest.mark.asyncio
    async def test_wait_timeout_triggers_reconnection(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """
        Test that wait_timeout expiration triggers automatic reconnection.
        """
        print_separator("Test: Async wait_timeout Recovery")

        # 1. Get original wait_timeout
        result = await async_mysql_backend_single.introspector.show.variables(like="wait_timeout")
        original_timeout = int(result[0].value)
        print(f"Original wait_timeout: {original_timeout} seconds")

        # 2. Set short timeout
        test_timeout = 5
        print(f"Setting wait_timeout to {test_timeout} seconds...")
        await async_mysql_backend_single.execute(f"SET SESSION wait_timeout = {test_timeout}")

        # Verify setting
        result = await async_mysql_backend_single.introspector.show.variables(like="wait_timeout")
        current_timeout = int(result[0].value)
        assert current_timeout == test_timeout

        # 3. Wait for timeout
        print(f"Waiting {test_timeout + 2} seconds for timeout...")
        await asyncio.sleep(test_timeout + 2)

        # 4. Execute query - should trigger reconnection
        print("Executing query after timeout...")
        try:
            result = await async_mysql_backend_single.execute("SELECT 1 AS test")
            print(f"Query succeeded: {result}")
            assert result.data[0]['test'] == 1
        finally:
            # Restore original timeout via control backend
            try:
                await async_mysql_control_backend.execute(f"SET GLOBAL wait_timeout = {original_timeout}")
            except Exception:
                pass


class TestAsyncKillConnectionRecovery:
    """Async tests for KILL CONNECTION recovery."""

    @pytest.mark.asyncio
    async def test_kill_connection_triggers_reconnection(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """Test that KILL CONNECTION triggers automatic reconnection."""
        print_separator("Test: Async KILL CONNECTION Recovery")

        # 1. Get current connection ID
        result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        await async_mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # 3. Execute query - should trigger reconnection
        print("Executing query after connection killed...")
        result = await async_mysql_backend_single.execute("SELECT 1 AS test")
        print(f"Query succeeded: {result}")
        assert result.data[0]['test'] == 1

        # 4. Verify new connection ID
        new_conn_result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id

    @pytest.mark.asyncio
    async def test_multiple_queries_after_reconnection(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """Test that multiple queries work correctly after reconnection."""
        print_separator("Test: Async Multiple Queries After Reconnection")

        # Kill connection
        result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        await async_mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # Execute multiple queries
        for i in range(5):
            result = await async_mysql_backend_single.execute(f"SELECT {i} AS value")
            assert result.data[0]['value'] == i
            print(f"Query {i + 1}/5 succeeded")


class TestAsyncPingReconnect:
    """Async tests for manual ping reconnection."""

    @pytest.mark.asyncio
    async def test_ping_reconnect_after_kill(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """Test that ping(reconnect=True) can restore a killed connection."""
        print_separator("Test: Async Ping Reconnect")

        # 1. Get current connection ID
        result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # 2. Kill the connection
        print(f"Killing connection {original_conn_id}...")
        await async_mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # 3. Verify connection is dead
        assert await async_mysql_backend_single._connection.is_connected() is False
        print("Connection confirmed dead")

        # 4. Ping with reconnect
        print("Calling ping(reconnect=True)...")
        ping_result = await async_mysql_backend_single.ping(reconnect=True)
        print(f"Ping result: {ping_result}")
        assert ping_result is True, "Ping should succeed with reconnect=True"

        # 5. Verify connection is restored
        assert await async_mysql_backend_single._connection.is_connected() is True

        # 6. Verify new connection ID
        new_conn_result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id

    @pytest.mark.asyncio
    async def test_ping_no_reconnect_keeps_dead_connection(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """Test that ping(reconnect=False) returns False for dead connections."""
        print_separator("Test: Async Ping No Reconnect")

        # Get current connection ID
        result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']

        # Kill the connection
        await async_mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # Verify connection is dead
        assert await async_mysql_backend_single._connection.is_connected() is False

        # Ping without reconnect
        ping_result = await async_mysql_backend_single.ping(reconnect=False)
        print(f"Ping result (reconnect=False): {ping_result}")
        assert ping_result is False, "Ping should return False for dead connection"

        # Connection should still be dead
        assert await async_mysql_backend_single._connection.is_connected() is False


class TestAsyncGetCursorAutoReconnect:
    """Async tests for _get_cursor() automatic reconnection behavior."""

    @pytest.mark.asyncio
    async def test_get_cursor_reconnects_killed_connection(
        self,
        async_mysql_backend_single: AsyncMySQLBackend,
        async_mysql_control_backend: AsyncMySQLBackend
    ):
        """Test that _get_cursor() automatically reconnects when connection is dead."""
        print_separator("Test: Async _get_cursor Auto Reconnect")

        # Get current connection ID
        result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        original_conn_id = result.data[0]['id']
        print(f"Original connection ID: {original_conn_id}")

        # Kill the connection
        await async_mysql_control_backend.execute(f"KILL CONNECTION {original_conn_id}")
        await asyncio.sleep(1)

        # Verify connection is dead
        assert await async_mysql_backend_single._connection.is_connected() is False

        # Call _get_cursor - should trigger reconnection
        cursor = await async_mysql_backend_single._get_cursor()
        print("_get_cursor() returned cursor successfully")

        # Verify connection is now alive
        assert await async_mysql_backend_single._connection.is_connected() is True

        # Clean up cursor
        await cursor.close()

        # Verify new connection ID
        new_conn_result = await async_mysql_backend_single.execute("SELECT CONNECTION_ID() AS id")
        new_conn_id = new_conn_result.data[0]['id']
        print(f"New connection ID: {new_conn_id}")
        assert new_conn_id != original_conn_id
