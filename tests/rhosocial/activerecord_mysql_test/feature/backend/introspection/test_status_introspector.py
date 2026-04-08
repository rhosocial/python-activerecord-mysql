# tests/rhosocial/activerecord_mysql_test/feature/backend/introspection/test_status_introspector.py
"""
Tests for MySQL status introspector.

This module tests the SyncMySQLStatusIntrospector functionality
for retrieving server status information via SHOW VARIABLES, SHOW STATUS,
and other system commands.
"""

import pytest

from rhosocial.activerecord.backend.introspection.status import (
    StatusItem,
    StatusCategory,
    ServerOverview,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
    InnoDBInfo,
    BinaryLogInfo,
    SlowQueryInfo,
    MySQLReplicationInfo,
)


class TestSyncMySQLStatusIntrospector:
    """Tests for synchronous MySQL status introspector."""

    def test_get_overview(self, mysql_backend):
        """Test get_overview returns valid ServerOverview."""
        status = mysql_backend.introspector.status

        overview = status.get_overview()

        assert isinstance(overview, ServerOverview)
        assert overview.server_vendor == "MySQL"
        assert overview.server_version is not None
        assert isinstance(overview.configuration, list)
        assert isinstance(overview.performance, list)
        assert isinstance(overview.storage, StorageInfo)
        assert isinstance(overview.databases, list)
        # MySQL has users (unlike SQLite)
        assert isinstance(overview.users, list)

    def test_get_overview_version_matches_dialect(self, mysql_backend):
        """Test that overview version matches dialect version."""
        status = mysql_backend.introspector.status
        overview = status.get_overview()

        expected_version = ".".join(map(str, mysql_backend.dialect.version))
        assert overview.server_version == expected_version

    def test_get_overview_contains_mysql_version_info(self, mysql_backend):
        """Test that overview contains MySQL version info in extra."""
        status = mysql_backend.introspector.status
        overview = status.get_overview()

        # MySQL should have version info
        assert "version" in overview.extra or overview.server_version is not None

    def test_list_configuration(self, mysql_backend):
        """Test list_configuration returns configuration items."""
        status = mysql_backend.introspector.status

        items = status.list_configuration()

        assert isinstance(items, list)
        assert len(items) > 0

        # Check that all items are StatusItem instances
        for item in items:
            assert isinstance(item, StatusItem)
            assert item.name is not None
            assert item.value is not None

    def test_list_configuration_with_category_filter(self, mysql_backend):
        """Test list_configuration with category filter."""
        status = mysql_backend.introspector.status

        config_items = status.list_configuration(category=StatusCategory.CONFIGURATION)

        for item in config_items:
            assert item.category == StatusCategory.CONFIGURATION

    def test_list_configuration_contains_expected_items(self, mysql_backend):
        """Test that configuration contains expected MySQL variables."""
        status = mysql_backend.introspector.status

        items = status.list_configuration()
        item_names = [item.name for item in items]

        # Check for some common MySQL variables
        assert "port" in item_names
        assert "version" in item_names

    def test_list_configuration_values_are_parsed(self, mysql_backend):
        """Test that configuration values are properly parsed."""
        status = mysql_backend.introspector.status

        items = status.list_configuration()

        # port should be an integer
        port_item = next((i for i in items if i.name == "port"), None)
        if port_item:
            assert isinstance(port_item.value, int)

    def test_list_performance_metrics(self, mysql_backend):
        """Test list_performance_metrics returns status items."""
        status = mysql_backend.introspector.status

        items = status.list_performance_metrics()

        assert isinstance(items, list)
        # Items should have various categories (PERFORMANCE, CONNECTION, etc.)
        for item in items:
            assert isinstance(item, StatusItem)

    def test_get_connection_info(self, mysql_backend):
        """Test get_connection_info returns ConnectionInfo."""
        status = mysql_backend.introspector.status

        conn_info = status.get_connection_info()

        assert isinstance(conn_info, ConnectionInfo)
        # MySQL has connection info
        assert conn_info.active_count is not None or conn_info.max_connections is not None

    def test_get_storage_info(self, mysql_backend):
        """Test get_storage_info returns StorageInfo."""
        status = mysql_backend.introspector.status

        storage = status.get_storage_info()

        assert isinstance(storage, StorageInfo)
        # MySQL should have data directory info
        assert storage.extra is not None

    def test_list_databases(self, mysql_backend):
        """Test list_databases returns database list."""
        status = mysql_backend.introspector.status

        databases = status.list_databases()

        assert isinstance(databases, list)
        assert len(databases) >= 1

        # All items should be DatabaseBriefInfo instances
        for db in databases:
            assert isinstance(db, DatabaseBriefInfo)
            assert db.name is not None

    def test_list_databases_with_tables(self, backend_with_tables):
        """Test list_databases includes table count."""
        status = backend_with_tables.introspector.status

        databases = status.list_databases()

        # At least one database should have tables
        assert len(databases) >= 1

    def test_list_users(self, mysql_backend):
        """Test list_users returns user list."""
        status = mysql_backend.introspector.status

        users = status.list_users()

        assert isinstance(users, list)

        # MySQL typically has at least one user
        for user in users:
            assert isinstance(user, UserInfo)
            assert user.name is not None

    def test_get_innodb_info(self, mysql_backend):
        """Test get_innodb_info returns InnoDBInfo."""
        status = mysql_backend.introspector.status

        innodb_info = status.get_innodb_info()

        assert isinstance(innodb_info, InnoDBInfo)
        # InnoDB is the default engine, should have info
        assert innodb_info.extra is not None

    def test_get_binary_log_info(self, mysql_backend):
        """Test get_binary_log_info returns BinaryLogInfo."""
        status = mysql_backend.introspector.status

        binlog_info = status.get_binary_log_info()

        assert isinstance(binlog_info, BinaryLogInfo)
        # Binary log may or may not be enabled

    def test_get_slow_query_info(self, mysql_backend):
        """Test get_slow_query_info returns SlowQueryInfo."""
        status = mysql_backend.introspector.status

        slow_query_info = status.get_slow_query_info()

        assert isinstance(slow_query_info, SlowQueryInfo)
        # Slow query log info should be available

    def test_status_item_has_description(self, mysql_backend):
        """Test that status items have descriptions."""
        status = mysql_backend.introspector.status

        items = status.list_configuration()

        # Check that items have descriptions
        for item in items:
            assert item.description is not None

    def test_status_item_readonly_flag(self, mysql_backend):
        """Test that readonly items are marked correctly."""
        status = mysql_backend.introspector.status

        items = status.list_configuration()

        # version should be readonly
        version_item = next((i for i in items if i.name == "version"), None)
        if version_item:
            assert version_item.is_readonly is True


class TestMySQLStatusIntrospectorMixin:
    """Tests for MySQLStatusIntrospectorMixin helper methods."""

    def test_parse_variable_value_int(self, mysql_backend):
        """Test _parse_variable_value handles integers."""
        status = mysql_backend.introspector.status

        result = status._parse_variable_value("42")
        assert result == 42
        assert isinstance(result, int)

    def test_parse_variable_value_str(self, mysql_backend):
        """Test _parse_variable_value preserves non-integer strings."""
        status = mysql_backend.introspector.status

        result = status._parse_variable_value("utf8mb4")
        assert result == "utf8mb4"
        assert isinstance(result, str)

    def test_create_status_item(self, mysql_backend):
        """Test _create_status_item creates proper StatusItem."""
        status = mysql_backend.introspector.status

        item = status._create_status_item(
            name="test_param",
            value="42",
            category=StatusCategory.CONFIGURATION,
            description="Test parameter",
            unit="ms",
            is_readonly=False,
        )

        assert isinstance(item, StatusItem)
        assert item.name == "test_param"
        assert item.value == 42  # Should be parsed to int
        assert item.category == StatusCategory.CONFIGURATION
        assert item.description == "Test parameter"
        assert item.unit == "ms"
        assert item.is_readonly is False

    def test_get_vendor_name(self, mysql_backend):
        """Test _get_vendor_name returns MySQL."""
        status = mysql_backend.introspector.status

        vendor = status._get_vendor_name()
        assert vendor == "MySQL"


class TestStatusIntrospectorCategories:
    """Tests for different status categories."""

    def test_configuration_category_items(self, mysql_backend):
        """Test items in CONFIGURATION category."""
        status = mysql_backend.introspector.status

        items = status.list_configuration(category=StatusCategory.CONFIGURATION)

        for item in items:
            assert item.category == StatusCategory.CONFIGURATION

    def test_performance_category_items(self, mysql_backend):
        """Test items in PERFORMANCE category."""
        status = mysql_backend.introspector.status

        items = status.list_configuration(category=StatusCategory.PERFORMANCE)

        for item in items:
            assert item.category == StatusCategory.PERFORMANCE

    def test_storage_category_items(self, mysql_backend):
        """Test items in STORAGE category."""
        status = mysql_backend.introspector.status

        items = status.list_configuration(category=StatusCategory.STORAGE)

        for item in items:
            assert item.category == StatusCategory.STORAGE

    def test_security_category_items(self, mysql_backend):
        """Test items in SECURITY category."""
        status = mysql_backend.introspector.status

        items = status.list_configuration(category=StatusCategory.SECURITY)

        for item in items:
            assert item.category == StatusCategory.SECURITY


class TestMySQLReplicationInfo:
    """Tests for MySQL replication status."""

    def test_get_mysql_replication_info(self, mysql_backend):
        """Test get_mysql_replication_info returns MySQLReplicationInfo."""
        status = mysql_backend.introspector.status

        repl_info = status.get_mysql_replication_info()

        assert isinstance(repl_info, MySQLReplicationInfo)
        # Replication may or may not be configured


class TestAsyncMySQLStatusIntrospector:
    """Tests for asynchronous MySQL status introspector."""

    @pytest.mark.asyncio
    async def test_get_overview(self, async_mysql_backend):
        """Test async get_overview returns valid ServerOverview."""
        status = async_mysql_backend.introspector.status

        overview = await status.get_overview()

        assert isinstance(overview, ServerOverview)
        assert overview.server_vendor == "MySQL"
        assert overview.server_version is not None
        assert isinstance(overview.configuration, list)
        assert isinstance(overview.performance, list)
        assert isinstance(overview.storage, StorageInfo)
        assert isinstance(overview.databases, list)

    @pytest.mark.asyncio
    async def test_get_overview_version_matches_dialect(self, async_mysql_backend):
        """Test that async overview version matches dialect version."""
        status = async_mysql_backend.introspector.status
        overview = await status.get_overview()

        expected_version = ".".join(map(str, async_mysql_backend.dialect.version))
        assert overview.server_version == expected_version

    @pytest.mark.asyncio
    async def test_list_configuration(self, async_mysql_backend):
        """Test async list_configuration returns configuration items."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration()

        assert isinstance(items, list)
        assert len(items) > 0

        # Check that all items are StatusItem instances
        for item in items:
            assert isinstance(item, StatusItem)
            assert item.name is not None
            assert item.value is not None

    @pytest.mark.asyncio
    async def test_list_configuration_with_category_filter(self, async_mysql_backend):
        """Test async list_configuration with category filter."""
        status = async_mysql_backend.introspector.status

        config_items = await status.list_configuration(category=StatusCategory.CONFIGURATION)

        for item in config_items:
            assert item.category == StatusCategory.CONFIGURATION

    @pytest.mark.asyncio
    async def test_list_configuration_contains_expected_items(self, async_mysql_backend):
        """Test that async configuration contains expected MySQL variables."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration()
        item_names = [item.name for item in items]

        # Check for some common MySQL variables
        assert "port" in item_names
        assert "version" in item_names

    @pytest.mark.asyncio
    async def test_list_performance_metrics(self, async_mysql_backend):
        """Test async list_performance_metrics returns status items."""
        status = async_mysql_backend.introspector.status

        items = await status.list_performance_metrics()

        assert isinstance(items, list)
        # Items should have various categories (PERFORMANCE, CONNECTION, etc.)
        for item in items:
            assert isinstance(item, StatusItem)

    @pytest.mark.asyncio
    async def test_get_connection_info(self, async_mysql_backend):
        """Test async get_connection_info returns ConnectionInfo."""
        status = async_mysql_backend.introspector.status

        conn_info = await status.get_connection_info()

        assert isinstance(conn_info, ConnectionInfo)
        assert conn_info.active_count is not None or conn_info.max_connections is not None

    @pytest.mark.asyncio
    async def test_get_storage_info(self, async_mysql_backend):
        """Test async get_storage_info returns StorageInfo."""
        status = async_mysql_backend.introspector.status

        storage = await status.get_storage_info()

        assert isinstance(storage, StorageInfo)

    @pytest.mark.asyncio
    async def test_list_databases(self, async_mysql_backend):
        """Test async list_databases returns database list."""
        status = async_mysql_backend.introspector.status

        databases = await status.list_databases()

        assert isinstance(databases, list)
        assert len(databases) >= 1

        for db in databases:
            assert isinstance(db, DatabaseBriefInfo)

    @pytest.mark.asyncio
    async def test_list_users(self, async_mysql_backend):
        """Test async list_users returns user list."""
        status = async_mysql_backend.introspector.status

        users = await status.list_users()

        assert isinstance(users, list)

        for user in users:
            assert isinstance(user, UserInfo)

    @pytest.mark.asyncio
    async def test_get_innodb_info(self, async_mysql_backend):
        """Test async get_innodb_info returns InnoDBInfo."""
        status = async_mysql_backend.introspector.status

        innodb_info = await status.get_innodb_info()

        assert isinstance(innodb_info, InnoDBInfo)

    @pytest.mark.asyncio
    async def test_get_binary_log_info(self, async_mysql_backend):
        """Test async get_binary_log_info returns BinaryLogInfo."""
        status = async_mysql_backend.introspector.status

        binlog_info = await status.get_binary_log_info()

        assert isinstance(binlog_info, BinaryLogInfo)

    @pytest.mark.asyncio
    async def test_get_slow_query_info(self, async_mysql_backend):
        """Test async get_slow_query_info returns SlowQueryInfo."""
        status = async_mysql_backend.introspector.status

        slow_query_info = await status.get_slow_query_info()

        assert isinstance(slow_query_info, SlowQueryInfo)

    @pytest.mark.asyncio
    async def test_get_mysql_replication_info(self, async_mysql_backend):
        """Test async get_mysql_replication_info returns MySQLReplicationInfo."""
        status = async_mysql_backend.introspector.status

        repl_info = await status.get_mysql_replication_info()

        assert isinstance(repl_info, MySQLReplicationInfo)

    @pytest.mark.asyncio
    async def test_status_item_has_description(self, async_mysql_backend):
        """Test that async status items have descriptions."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration()

        for item in items:
            assert item.description is not None

    @pytest.mark.asyncio
    async def test_status_item_readonly_flag(self, async_mysql_backend):
        """Test that async readonly items are marked correctly."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration()

        version_item = next((i for i in items if i.name == "version"), None)
        if version_item:
            assert version_item.is_readonly is True


class TestAsyncMySQLStatusIntrospectorMixin:
    """Tests for async MySQLStatusIntrospectorMixin helper methods."""

    @pytest.mark.asyncio
    async def test_parse_variable_value_int(self, async_mysql_backend):
        """Test _parse_variable_value handles integers."""
        status = async_mysql_backend.introspector.status

        result = status._parse_variable_value("42")
        assert result == 42
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_parse_variable_value_str(self, async_mysql_backend):
        """Test _parse_variable_value preserves non-integer strings."""
        status = async_mysql_backend.introspector.status

        result = status._parse_variable_value("utf8mb4")
        assert result == "utf8mb4"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_vendor_name(self, async_mysql_backend):
        """Test _get_vendor_name returns MySQL."""
        status = async_mysql_backend.introspector.status

        vendor = status._get_vendor_name()
        assert vendor == "MySQL"


class TestAsyncStatusIntrospectorCategories:
    """Tests for different async status categories."""

    @pytest.mark.asyncio
    async def test_configuration_category_items(self, async_mysql_backend):
        """Test async items in CONFIGURATION category."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.CONFIGURATION)

        for item in items:
            assert item.category == StatusCategory.CONFIGURATION

    @pytest.mark.asyncio
    async def test_performance_category_items(self, async_mysql_backend):
        """Test async items in PERFORMANCE category."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.PERFORMANCE)

        for item in items:
            assert item.category == StatusCategory.PERFORMANCE

    @pytest.mark.asyncio
    async def test_storage_category_items(self, async_mysql_backend):
        """Test async items in STORAGE category."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.STORAGE)

        for item in items:
            assert item.category == StatusCategory.STORAGE

    @pytest.mark.asyncio
    async def test_security_category_items(self, async_mysql_backend):
        """Test async items in SECURITY category."""
        status = async_mysql_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.SECURITY)

        for item in items:
            assert item.category == StatusCategory.SECURITY
