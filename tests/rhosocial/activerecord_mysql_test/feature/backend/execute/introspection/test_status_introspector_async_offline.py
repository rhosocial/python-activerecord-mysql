# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/introspection/
# test_status_introspector_async_offline.py
"""
Pure-mock unit tests for ``AsyncMySQLStatusIntrospector``.

MySQL has a native async driver, so the async status introspector must be
covered independently of a live server. Every I/O seam of the async class is
replaced here:

* ``backend.introspector.show.variables / status / databases`` are async mocks;
* ``backend.execute`` is an async mock dispatching on a tagged statement;
* the statement-building mixin helpers are replaced with tag producers so no
  real expression tree / dialect is required.

No socket, no driver, no database is touched -- the module is imported and
driven entirely in memory.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from rhosocial.activerecord.backend.impl.mysql.introspection.status_introspector import (
    AsyncMySQLStatusIntrospector,
)
from rhosocial.activerecord.backend.impl.mysql.introspection.status_types import (
    BinaryLogInfo,
    InnoDBInfo,
    MySQLReplicationInfo,
    MySQLServerOverview,
    SlowQueryInfo,
)
from rhosocial.activerecord.backend.introspection.status import (
    ConnectionInfo,
    DatabaseBriefInfo,
    ProcessInfo,
    SessionInfo,
    StatusCategory,
    StatusItem,
    StorageInfo,
    UserInfo,
)


def _v(name, value):
    """A SHOW VARIABLES / SHOW STATUS row as returned by the async show facade."""
    return SimpleNamespace(variable_name=name, value=value)


class _Env:
    """Bundle an introspector with the knobs that drive its mocked seams."""

    def __init__(self):
        self.status = None
        self.backend = None
        self.var_rows = {}  # like -> list[_v]
        self.status_rows = {}  # like -> list[_v]
        self.db_names = []
        self.results = {}  # statement tag -> list[dict]
        self.fail_tags = set()  # statement tags that raise when executed


def _patch_statement_builders(status):
    """Replace expression-tree builders with deterministic statement tags."""
    status._database_size_query = lambda: ("DATABASE_SIZE", ())
    status._table_type_counts_query = lambda db_names: ("TABLE_COUNTS", ())
    status._users_query = lambda: ("USERS", ())
    status._current_user_query = lambda: ("CURRENT_USER", ())
    status._show_status = lambda like=None, session=True: (f"STATUS:{like}", ())
    status._show_variables = lambda like=None, session=True: (f"VARIABLES:{like}", ())
    status._show_binary_logs = lambda: ("BINARY_LOGS", ())
    status._version_query = lambda: ("VERSION", ())
    status._log_status_query = lambda with_gtid=False: (f"LOG_STATUS:{with_gtid}", ())
    status._show_master_status = lambda: ("MASTER_STATUS", ())
    status._show_processlist = lambda full=False: (f"PROCESSLIST:{full}", ())
    status._replication_connection_status_query = lambda limit=None: (f"REPL_CONN:{limit}", ())
    status._show_slave_status = lambda: ("SLAVE_STATUS", ())


@pytest.fixture
def env():
    """A fully mocked async introspector plus handles to configure its seams."""
    backend = MagicMock()
    backend.config.database = "testdb"
    backend.config.password = "secret"
    backend._version = (8, 0, 36)

    state = _Env()
    state.backend = backend

    async def variables(like=None, session=True):
        return state.var_rows.get(like, [])

    async def statuses(like=None, session=True):
        return state.status_rows.get(like, [])

    async def databases():
        return [SimpleNamespace(name=name) for name in state.db_names]

    show = backend.introspector.show
    show.variables = AsyncMock(side_effect=variables)
    show.status = AsyncMock(side_effect=statuses)
    show.databases = AsyncMock(side_effect=databases)

    async def execute(sql, params=()):
        if sql in state.fail_tags:
            raise RuntimeError(f"mocked execute failure: {sql}")
        return SimpleNamespace(data=state.results.get(sql, []))

    backend.execute = AsyncMock(side_effect=execute)

    introspector = AsyncMySQLStatusIntrospector(backend)
    _patch_statement_builders(introspector)
    state.status = introspector
    return state


class TestAsyncVersionString:
    """``_get_version_string`` reads the version variable, else falls back."""

    async def test_version_from_show_variables(self, env):
        env.var_rows["version"] = [_v("version", "8.0.36")]
        assert await env.status._get_version_string() == "8.0.36"
        env.backend.introspector.show.variables.assert_awaited_once_with(like="version")

    async def test_version_falls_back_to_backend_attribute(self, env):
        assert await env.status._get_version_string() == "8.0.36"

    @pytest.mark.parametrize(
        ("version", "expected"),
        [((9, 6, 0), "9.6.0"), ((10, 1, 2), "10.1.2"), ((5, 7, 42), "5.7.42")],
    )
    async def test_version_fallback_uses_backend_tuple(self, env, version, expected):
        env.backend._version = version
        assert await env.status._get_version_string() == expected

    async def test_version_ignores_non_version_rows(self, env):
        env.var_rows["version"] = [_v("version_comment", "MySQL Community Server")]
        assert await env.status._get_version_string() == "8.0.36"


class TestAsyncListConfiguration:
    """``list_configuration`` maps SHOW VARIABLES rows onto StatusItems."""

    async def test_maps_known_variables_and_parses_values(self, env):
        env.var_rows[None] = [
            _v("version", "8.0.36"),
            _v("port", "3306"),
            _v("character_set_server", "utf8mb4"),
            _v("innodb_buffer_pool_size", "134217728"),
            _v("totally_unknown_var", "1"),
        ]

        items = await env.status.list_configuration()
        by_name = {item.name: item for item in items}

        assert set(by_name) == {"version", "port", "character_set_server", "innodb_buffer_pool_size"}
        assert by_name["port"].value == 3306
        assert isinstance(by_name["port"].value, int)
        assert by_name["port"].category is StatusCategory.CONFIGURATION
        assert by_name["port"].description == "MySQL port"
        assert by_name["port"].is_readonly is True
        assert by_name["character_set_server"].value == "utf8mb4"
        assert by_name["character_set_server"].is_readonly is False
        assert by_name["innodb_buffer_pool_size"].value == 134217728
        assert by_name["innodb_buffer_pool_size"].category is StatusCategory.PERFORMANCE
        assert by_name["innodb_buffer_pool_size"].unit == "bytes"

    @pytest.mark.parametrize(
        ("category", "expected"),
        [
            (StatusCategory.CONFIGURATION, {"version", "port"}),
            (StatusCategory.CONNECTION, {"max_connections"}),
            (StatusCategory.STORAGE, {"datadir"}),
        ],
    )
    async def test_category_filter(self, env, category, expected):
        env.var_rows[None] = [
            _v("version", "8.0.36"),
            _v("port", "3306"),
            _v("max_connections", "151"),
            _v("datadir", "/var/lib/mysql"),
        ]

        items = await env.status.list_configuration(category=category)
        assert {item.name for item in items} == expected
        assert all(item.category is category for item in items)

    async def test_empty_variables_yield_no_items(self, env):
        assert await env.status.list_configuration() == []

    async def test_only_unknown_variables_yield_no_items(self, env):
        env.var_rows[None] = [_v("not_a_mysql_variable", "x")]
        assert await env.status.list_configuration() == []

    async def test_items_are_status_items_with_metadata(self, env):
        env.var_rows[None] = [_v("sql_mode", "STRICT_TRANS_TABLES")]
        items = await env.status.list_configuration()
        assert len(items) == 1
        assert isinstance(items[0], StatusItem)
        assert items[0].category is StatusCategory.CONFIGURATION
        assert items[0].description == "SQL mode"


class TestAsyncListPerformanceMetrics:
    """``list_performance_metrics`` maps SHOW STATUS rows onto StatusItems."""

    async def test_maps_known_status_variables(self, env):
        env.status_rows[None] = [
            _v("Threads_connected", "12"),
            _v("Queries", "5000"),
            _v("Unknown_status", "1"),
        ]

        items = await env.status.list_performance_metrics()
        by_name = {item.name: item for item in items}
        assert set(by_name) == {"Threads_connected", "Queries"}
        assert by_name["Queries"].value == 5000
        assert by_name["Queries"].category is StatusCategory.PERFORMANCE
        assert by_name["Queries"].description == "Total queries"
        assert by_name["Queries"].unit == "queries"
        assert by_name["Threads_connected"].unit == "connections"

    async def test_category_filter(self, env):
        env.status_rows[None] = [_v("Threads_connected", "12"), _v("Queries", "5000")]
        items = await env.status.list_performance_metrics(category=StatusCategory.CONNECTION)
        assert [item.name for item in items] == ["Threads_connected"]

    async def test_empty_status_yields_no_items(self, env):
        assert await env.status.list_performance_metrics() == []


class TestAsyncConnectionInfo:
    """``get_connection_info`` combines status and variable counters."""

    async def test_full_connection_info(self, env):
        env.status_rows[None] = [
            _v("Threads_connected", "7"),
            _v("Threads_cached", "3"),
            _v("Threads_running", "2"),
        ]
        env.var_rows[None] = [_v("max_connections", "151")]

        info = await env.status.get_connection_info()
        assert isinstance(info, ConnectionInfo)
        assert info.active_count == 7
        assert info.max_connections == 151
        assert info.idle_count == 3
        assert info.extra["threads_running"] == 2

    async def test_missing_values_are_none(self, env):
        info = await env.status.get_connection_info()
        assert info.active_count is None
        assert info.max_connections is None
        assert info.idle_count is None
        assert info.extra["threads_running"] is None


class TestAsyncStorageInfo:
    """``get_storage_info`` uses database-size query with graceful fallback."""

    async def test_size_query_results_are_parsed(self, env):
        env.var_rows[None] = [
            _v("datadir", "/var/lib/mysql"),
            _v("innodb_buffer_pool_size", "134217728"),
        ]
        env.results["DATABASE_SIZE"] = [
            {"total_size": "1000", "data_size": "700", "index_size": "300"}
        ]

        storage = await env.status.get_storage_info()
        assert isinstance(storage, StorageInfo)
        assert storage.total_size_bytes == 1000
        assert storage.data_size_bytes == 700
        assert storage.index_size_bytes == 300
        assert storage.extra["datadir"] == "/var/lib/mysql"
        assert storage.extra["innodb_buffer_pool_size"] == 134217728

    async def test_no_size_rows_still_reports_variables(self, env):
        env.var_rows[None] = [_v("datadir", "/data")]
        storage = await env.status.get_storage_info()
        assert storage.total_size_bytes is None
        assert storage.extra["datadir"] == "/data"

    async def test_execute_failure_falls_back_without_raising(self, env):
        env.var_rows[None] = [_v("datadir", "/data")]
        env.fail_tags.add("DATABASE_SIZE")
        storage = await env.status.get_storage_info()
        assert storage.total_size_bytes is None
        assert storage.extra["datadir"] == "/data"


class TestAsyncListDatabases:
    """``list_databases`` augments database names with table/view counts."""

    async def test_counts_are_mapped_by_schema(self, env):
        env.db_names = ["db1", "db2"]
        env.results["TABLE_COUNTS"] = [
            {"TABLE_SCHEMA": "db1", "TABLE_TYPE": "BASE TABLE", "count": "5"},
            {"TABLE_SCHEMA": "db1", "TABLE_TYPE": "VIEW", "count": "2"},
            {"table_schema": "db2", "table_type": "BASE TABLE", "COUNT": "3"},
        ]

        databases = await env.status.list_databases()
        by_name = {db.name: db for db in databases}
        assert set(by_name) == {"db1", "db2"}
        assert all(isinstance(db, DatabaseBriefInfo) for db in databases)
        assert by_name["db1"].table_count == "5"
        assert by_name["db1"].view_count == "2"
        assert by_name["db2"].table_count == "3"
        assert by_name["db2"].view_count == 0

    async def test_count_query_failure_defaults_to_zero(self, env):
        env.db_names = ["db1"]
        env.fail_tags.add("TABLE_COUNTS")
        databases = await env.status.list_databases()
        assert len(databases) == 1
        assert databases[0].table_count == 0
        assert databases[0].view_count == 0

    async def test_no_databases(self, env):
        assert await env.status.list_databases() == []


class TestAsyncListUsers:
    """``list_users`` maps mysql.user rows onto UserInfo objects."""

    async def test_maps_user_rows(self, env):
        env.results["USERS"] = [
            {"User": "root", "Host": "localhost", "Super_priv": "Y"},
            {"User": "app", "Host": "%", "Super_priv": "N"},
        ]

        users = await env.status.list_users()
        assert len(users) == 2
        assert all(isinstance(user, UserInfo) for user in users)
        assert users[0].name == "root"
        assert users[0].host == "localhost"
        assert users[0].is_superuser is True
        assert users[1].name == "app"
        assert users[1].is_superuser is False

    async def test_empty_user_table(self, env):
        assert await env.status.list_users() == []

    async def test_permission_error_falls_back_to_empty(self, env):
        env.fail_tags.add("USERS")
        assert await env.status.list_users() == []


class TestAsyncSessionInfo:
    """``get_session_info`` gathers user, database, SSL and password flags."""

    async def test_full_session_info(self, env):
        env.results["CURRENT_USER"] = [{"CURRENT_USER": "alice@%"}]
        env.results["STATUS:Ssl_version"] = [{"Value": "TLSv1.3"}]
        env.results["STATUS:Ssl_cipher"] = [{"Value": "AES256-GCM"}]

        session = await env.status.get_session_info()
        assert isinstance(session, SessionInfo)
        assert session.user == "alice"
        assert session.host == "%"
        assert session.database == "testdb"
        assert session.ssl_enabled is True
        assert session.ssl_version == "TLSv1.3"
        assert session.ssl_cipher == "AES256-GCM"
        assert session.password_used is True

    async def test_session_without_host_or_ssl(self, env):
        env.results["CURRENT_USER"] = [{"CURRENT_USER": "bob"}]
        env.backend.config.password = ""

        session = await env.status.get_session_info()
        assert session.user == "bob"
        assert session.host is None
        assert session.ssl_enabled is None
        assert session.ssl_version is None
        assert session.ssl_cipher is None
        assert session.password_used is False

    async def test_queries_fail_softly(self, env):
        env.fail_tags.update({"CURRENT_USER", "STATUS:Ssl_version", "STATUS:Ssl_cipher"})
        session = await env.status.get_session_info()
        assert session.user is None
        assert session.database == "testdb"


class TestAsyncInnodbInfo:
    """``get_innodb_info`` collects buffer-pool, variable and row-lock families."""

    async def test_buffer_pool_status_rows(self, env):
        env.results["STATUS:Innodb_buffer_pool%"] = [
            {"Variable_name": "Innodb_buffer_pool_pages_total", "Value": "8192"},
            {"Variable_name": "Innodb_buffer_pool_pages_data", "Value": "4000"},
            {"Variable_name": "Innodb_buffer_pool_pages_dirty", "Value": "10"},
            {"Variable_name": "Innodb_buffer_pool_pages_free", "Value": "4000"},
            {"Variable_name": "Innodb_buffer_pool_read_requests", "Value": "100000"},
            {"Variable_name": "Innodb_buffer_pool_reads", "Value": "500"},
            {"Variable_name": "Innodb_buffer_pool_wait_free", "Value": "2"},
        ]

        info = await env.status.get_innodb_info()
        assert isinstance(info, InnoDBInfo)
        assert info.buffer_pool_pages_total == 8192
        assert info.buffer_pool_pages_data == 4000
        assert info.buffer_pool_pages_dirty == 10
        assert info.buffer_pool_pages_free == 4000
        assert info.buffer_pool_read_requests == 100000
        assert info.buffer_pool_reads == 500
        assert info.buffer_pool_wait_free == 2

    async def test_innodb_variable_rows(self, env):
        env.results["VARIABLES:innodb%"] = [
            {"Variable_name": "innodb_buffer_pool_size", "Value": "134217728"},
            {"Variable_name": "innodb_buffer_pool_instances", "Value": "1"},
            {"Variable_name": "innodb_log_file_size", "Value": "50331648"},
            {"Variable_name": "innodb_log_buffer_size", "Value": "16777216"},
            {"Variable_name": "innodb_lock_wait_timeout", "Value": "50"},
        ]

        info = await env.status.get_innodb_info()
        assert info.buffer_pool_size == 134217728
        assert info.buffer_pool_instances == 1
        assert info.log_file_size == 50331648
        assert info.log_buffer_size == 16777216
        assert info.lock_wait_timeout == 50

    async def test_row_lock_rows_and_average(self, env):
        env.results["STATUS:Innodb_row_lock%"] = [
            {"Variable_name": "Innodb_row_lock_time", "Value": "100"},
            {"Variable_name": "Innodb_row_lock_waits", "Value": "4"},
            {"Variable_name": "Innodb_row_lock_time_avg", "Value": "0"},
            {"Variable_name": "Innodb_rows_read", "Value": "1000"},
            {"Variable_name": "Innodb_rows_inserted", "Value": "100"},
            {"Variable_name": "Innodb_rows_updated", "Value": "20"},
            {"Variable_name": "Innodb_rows_deleted", "Value": "5"},
            {"Variable_name": "Innodb_data_reads", "Value": "300"},
            {"Variable_name": "Innodb_data_writes", "Value": "200"},
            {"Variable_name": "Innodb_os_log_fsyncs", "Value": "30"},
            {"Variable_name": "Innodb_os_file_reads", "Value": "40"},
            {"Variable_name": "Innodb_os_file_writes", "Value": "50"},
        ]

        info = await env.status.get_innodb_info()
        assert info.row_lock_time == 100
        assert info.row_lock_waits == 4
        assert info.row_lock_time_avg == 25.0
        assert info.rows_read == 1000
        assert info.rows_inserted == 100
        assert info.rows_updated == 20
        assert info.rows_deleted == 5
        assert info.data_reads == 300
        assert info.data_writes == 200
        assert info.os_fsyncs == 30
        assert info.os_file_reads == 40
        assert info.os_file_writes == 50

    async def test_all_innodb_queries_fail_softly(self, env):
        env.fail_tags.update(
            {"STATUS:Innodb_buffer_pool%", "VARIABLES:innodb%", "STATUS:Innodb_row_lock%"}
        )
        info = await env.status.get_innodb_info()
        assert isinstance(info, InnoDBInfo)
        assert info.buffer_pool_pages_total is None
        assert info.buffer_pool_size is None
        assert info.row_lock_waits is None


class TestAsyncBinaryLogInfo:
    """``get_binary_log_info`` covers modern/legacy branches and off state."""

    async def test_enabled_modern_server_full_info(self, env):
        env.results["VARIABLES:log_bin"] = [
            {"Variable_name": "log_bin", "Value": "ON"},
            {"Variable_name": "binlog_format", "Value": "ROW"},
        ]
        env.results["BINARY_LOGS"] = [
            {"Log_name": "binlog.000001", "File_size": "120"},
            {"Log_name": "binlog.000002", "File_size": "456"},
        ]
        env.results["VERSION"] = [{"VERSION()": "8.4.0"}]
        env.results["LOG_STATUS:True"] = [
            {"File": "binlog.000002", "Position": "456", "Gtid": "uuid:1"}
        ]
        env.results["VARIABLES:gtid_mode"] = [{"Variable_name": "gtid_mode", "Value": "ON"}]

        info = await env.status.get_binary_log_info()
        assert isinstance(info, BinaryLogInfo)
        assert info.log_enabled is True
        assert info.log_format == "ROW"
        assert info.log_files == ["binlog.000001", "binlog.000002"]
        assert info.log_size_bytes == 576
        assert info.current_log_file == "binlog.000002"
        assert info.current_log_position == 456
        assert info.gtid_mode == "ON"
        # Unlike the sync class, the async path takes gtid_executed from
        # performance_schema.log_status only; there is no global-variable query.
        assert info.gtid_executed == "uuid:1"

    async def test_disabled_logging_adds_guidance(self, env):
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "OFF"}]

        info = await env.status.get_binary_log_info()
        assert info.log_enabled is False
        assert "note" in info.extra
        assert "hint" in info.extra
        called = [call.args[0] for call in env.backend.execute.await_args_list]
        assert "BINARY_LOGS" not in called
        assert "LOG_STATUS:True" not in called

    async def test_legacy_server_uses_master_status(self, env):
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "ON"}]
        env.results["VERSION"] = [{"VERSION()": "5.7.42-log"}]
        env.results["MASTER_STATUS"] = [{"File": "mysql-bin.000003", "Position": "123"}]

        info = await env.status.get_binary_log_info()
        assert info.current_log_file == "mysql-bin.000003"
        assert info.current_log_position == 123
        called = [call.args[0] for call in env.backend.execute.await_args_list]
        assert "LOG_STATUS:True" not in called

    async def test_master_status_failure_does_not_raise(self, env):
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "ON"}]
        env.fail_tags.add("VERSION")
        info = await env.status.get_binary_log_info()
        assert info.log_enabled is True
        assert info.current_log_file is None

    async def test_log_file_listing_failure_leaves_defaults(self, env):
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "1"}]
        env.fail_tags.add("BINARY_LOGS")
        info = await env.status.get_binary_log_info()
        assert info.log_enabled is True
        assert info.log_files == []
        assert info.log_size_bytes is None

    async def test_gtid_mode_query_failure_is_non_fatal(self, env):
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "OFF"}]
        env.fail_tags.add("VARIABLES:gtid_mode")
        info = await env.status.get_binary_log_info()
        assert info.gtid_mode is None
        assert info.log_enabled is False

    async def test_log_bin_variable_query_failure_is_non_fatal(self, env):
        env.fail_tags.add("VARIABLES:log_bin")
        info = await env.status.get_binary_log_info()
        assert info.log_enabled is None
        assert info.log_files == []


class TestAsyncProcesses:
    """``list_processes`` maps SHOW PROCESSLIST rows."""

    async def test_maps_process_rows(self, env):
        env.results["PROCESSLIST:True"] = [
            {
                "Id": 1,
                "User": "root",
                "Host": "localhost",
                "db": "testdb",
                "Command": "Query",
                "Time": 0,
                "State": "executing",
                "Info": "SELECT 1",
            }
        ]

        processes = await env.status.list_processes()
        assert len(processes) == 1
        assert isinstance(processes[0], ProcessInfo)
        assert processes[0].id == 1
        assert processes[0].user == "root"
        assert processes[0].database == "testdb"
        assert processes[0].command == "Query"
        assert processes[0].info == "SELECT 1"

    async def test_empty_processlist(self, env):
        assert await env.status.list_processes() == []

    async def test_processlist_failure_falls_back(self, env):
        env.fail_tags.add("PROCESSLIST:True")
        assert await env.status.list_processes() == []


class TestAsyncSlowQueryInfo:
    """``get_slow_query_info`` reads slow-log variables and the counter."""

    async def test_full_slow_query_info(self, env):
        env.results["VARIABLES:slow_query_log%"] = [
            {"Variable_name": "slow_query_log", "Value": "ON"},
            {"Variable_name": "slow_query_log_file", "Value": "/var/log/slow.log"},
        ]
        env.results["VARIABLES:long_query_time"] = [{"Value": "2.5"}]
        env.results["STATUS:Slow_queries"] = [{"Value": "42"}]

        info = await env.status.get_slow_query_info()
        assert isinstance(info, SlowQueryInfo)
        assert info.slow_query_log_enabled is True
        assert info.slow_query_log_file == "/var/log/slow.log"
        assert info.long_query_time == 2.5
        assert info.slow_queries_count == 42

    @pytest.mark.parametrize("value", ["OFF", "0", "", "no"])
    async def test_slow_query_log_falsey_values(self, env, value):
        env.results["VARIABLES:slow_query_log%"] = [
            {"Variable_name": "slow_query_log", "Value": value}
        ]
        info = await env.status.get_slow_query_info()
        assert info.slow_query_log_enabled is False

    async def test_empty_results_leave_defaults(self, env):
        info = await env.status.get_slow_query_info()
        # The async path sets slow_query_log_enabled only when a row exists.
        assert getattr(info, "slow_query_log_enabled", None) is None
        assert info.long_query_time is None
        assert info.slow_queries_count is None

    async def test_blank_values_are_ignored(self, env):
        env.results["VARIABLES:long_query_time"] = [{"Value": ""}]
        env.results["STATUS:Slow_queries"] = [{"Value": ""}]
        info = await env.status.get_slow_query_info()
        assert info.long_query_time is None
        assert info.slow_queries_count is None

    async def test_variable_query_failure_is_non_fatal(self, env):
        env.fail_tags.add("VARIABLES:slow_query_log%")
        info = await env.status.get_slow_query_info()
        assert info.slow_query_log_file is None

    async def test_long_query_time_and_count_queries_fail_softly(self, env):
        env.fail_tags.update({"VARIABLES:long_query_time", "STATUS:Slow_queries"})
        info = await env.status.get_slow_query_info()
        assert info.long_query_time is None
        assert info.slow_queries_count is None


class TestAsyncReplicationInfo:
    """``get_mysql_replication_info`` covers master/slave branches."""

    async def test_modern_master(self, env):
        env.results["VERSION"] = [{"VERSION()": "8.4.0"}]
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "ON"}]
        env.results["LOG_STATUS:False"] = [{"File": "binlog.000002", "Position": "456"}]

        info = await env.status.get_mysql_replication_info()
        assert isinstance(info, MySQLReplicationInfo)
        assert info.is_master is True
        assert info.master_log_file == "binlog.000002"
        assert info.master_log_position == 456
        assert info.is_slave is None

    async def test_legacy_master(self, env):
        env.results["VERSION"] = [{"VERSION()": "5.7.42"}]
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "ON"}]
        env.results["MASTER_STATUS"] = [
            {"File": "mysql-bin.000009", "Position": "777"}
        ]

        info = await env.status.get_mysql_replication_info()
        assert info.is_master is True
        assert info.master_log_file == "mysql-bin.000009"
        assert info.master_log_position == 777

    async def test_legacy_slave(self, env):
        env.results["VERSION"] = [{"VERSION()": "5.7.42"}]
        env.results["SLAVE_STATUS"] = [
            {
                "Slave_IO_Running": "Yes",
                "Slave_SQL_Running": "Yes",
                "Master_Host": "10.0.0.1",
                "Master_Port": "3306",
                "Relay_Log_File": "relay.000001",
                "Relay_Log_Pos": "100",
                "Last_Error": "none",
            }
        ]

        info = await env.status.get_mysql_replication_info()
        assert info.is_slave is True
        assert info.slave_io_running is True
        assert info.slave_sql_running is True
        assert info.slave_master_host == "10.0.0.1"
        assert info.slave_relay_log_pos == 100
        assert info.is_master is None

    async def test_modern_slave_from_performance_schema(self, env):
        env.results["VERSION"] = [{"VERSION()": "9.0.0"}]
        env.results["REPL_CONN:1"] = [{"SERVICE_STATE": "ON"}]

        info = await env.status.get_mysql_replication_info()
        assert info.is_slave is True
        assert info.slave_io_running is True

    async def test_empty_server_has_no_replication_flags(self, env):
        info = await env.status.get_mysql_replication_info()
        assert info.is_master is None
        assert info.is_slave is None
        # master/slave detail fields are attached only on the matching branch.
        assert getattr(info, "master_log_file", None) is None
        assert getattr(info, "slave_io_running", None) is None

    async def test_replication_queries_fail_softly(self, env):
        env.fail_tags.update({"VERSION", "VARIABLES:log_bin", "SLAVE_STATUS", "REPL_CONN:1"})
        info = await env.status.get_mysql_replication_info()
        assert info.is_master is None
        assert info.is_slave is None

    async def test_master_status_failure_keeps_is_master_none(self, env):
        env.results["VERSION"] = [{"VERSION()": "5.7.42"}]
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "ON"}]
        env.fail_tags.add("MASTER_STATUS")
        info = await env.status.get_mysql_replication_info()
        assert info.is_master is None
        assert getattr(info, "master_log_file", None) is None


class TestAsyncOverview:
    """``get_overview`` composes all async collectors into one object."""

    async def test_overview_composes_collected_parts(self, env):
        env.var_rows["version"] = [_v("version", "8.0.36")]
        env.var_rows[None] = [_v("port", "3306"), _v("datadir", "/data")]
        env.status_rows[None] = [_v("Threads_connected", "4")]
        env.db_names = ["db1"]
        env.results["USERS"] = [{"User": "root", "Host": "localhost", "Super_priv": "Y"}]
        env.results["VARIABLES:log_bin"] = [{"Variable_name": "log_bin", "Value": "OFF"}]

        overview = await env.status.get_overview()

        assert isinstance(overview, MySQLServerOverview)
        assert overview.server_vendor == "MySQL"
        assert overview.server_version == "8.0.36"
        assert isinstance(overview.configuration, list)
        assert overview.configuration
        assert isinstance(overview.performance, list)
        assert isinstance(overview.connections, ConnectionInfo)
        assert isinstance(overview.storage, StorageInfo)
        assert len(overview.databases) == 1
        assert len(overview.users) == 1
        assert isinstance(overview.session, SessionInfo)
        assert isinstance(overview.innodb, InnoDBInfo)
        assert isinstance(overview.binary_log, BinaryLogInfo)
        assert isinstance(overview.slow_query, SlowQueryInfo)
        assert isinstance(overview.mysql_replication, MySQLReplicationInfo)
        assert overview.processes == []

    async def test_overview_with_empty_server(self, env):
        overview = await env.status.get_overview()
        assert overview.server_version == "8.0.36"
        assert overview.configuration == []
        assert overview.performance == []
        assert overview.databases == []
        assert overview.users == []
