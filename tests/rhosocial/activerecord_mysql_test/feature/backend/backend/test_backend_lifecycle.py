# tests/rhosocial/activerecord_mysql_test/feature/backend/backend/test_backend_lifecycle.py
"""
Offline tests for the synchronous MySQLBackend lifecycle.

These tests exercise ``src/rhosocial/activerecord/backend/impl/mysql/backend.py``
without a live server by mocking ``mysql.connector.connect`` and the internal
cursor pipeline:

- ``__init__`` parameter extraction and defaults
- connect/disconnect and connection health checking (_get_cursor)
- get_server_version / ping / _reconnect
- auto-commit helpers
- execute() options construction and connection-error retry logic
- execute_many / executescript
- introspect_and_adapt and _parse_explain_result
"""

from unittest.mock import MagicMock

import mysql.connector
import pytest
from mysql.connector.errors import Error as MySQLError
from mysql.connector.errors import IntegrityError as MySQLIntegrityError
from mysql.connector.errors import OperationalError as MySQLOperationalError

from rhosocial.activerecord.backend.errors import ConnectionError, DatabaseError, IntegrityError, QueryError
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig
from rhosocial.activerecord.backend.options import StatementType
from rhosocial.activerecord.backend.result import QueryResult


@pytest.fixture
def backend():
    """Return a MySQLBackend configured for offline testing (no connection)."""
    return MySQLBackend(
        connection_config=MySQLConnectionConfig(
            host="127.0.0.1",
            port=3306,
            database="test_db",
            username="root",
            password="secret",
        )
    )


def _mock_connection():
    """Return a MagicMock connection with a usable cursor."""
    conn = MagicMock()
    conn.is_connected.return_value = True
    conn.cursor.return_value = MagicMock()
    return conn


def _patch_connect(monkeypatch, conn=None):
    """Patch mysql.connector.connect and return the captured call kwargs."""
    if conn is None:
        conn = _mock_connection()
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return conn

    monkeypatch.setattr("mysql.connector.connect", fake_connect)
    return captured, conn


class TestBackendInit:
    """Verify __init__ parameter extraction, defaults, and component setup."""

    def test_kwargs_extracted_to_config(self):
        """MySQL-specific kwargs should be folded into the connection config."""
        backend = MySQLBackend(
            host="db.example.com", port=4406, database="shop", username="app", password="pw"
        )
        assert backend.config.host == "db.example.com", "host should be extracted from kwargs"
        assert backend.config.port == 4406, "port should be extracted from kwargs"
        assert backend.config.database == "shop", "database should be extracted from kwargs"
        assert backend.config.username == "app", "username should be extracted from kwargs"
        assert backend.config.password == "pw", "password should be extracted from kwargs"

    def test_defaults_applied(self):
        """charset/autocommit/host/port defaults should be applied when absent."""
        backend = MySQLBackend(database="test")
        assert backend.config.charset == "utf8mb4", "charset should default to utf8mb4"
        assert backend.config.autocommit is True, "autocommit should default to True"
        assert backend.config.host == "localhost", "host should default to localhost"
        assert backend.config.port == 3306, "port should default to 3306"

    def test_connection_config_passthrough(self, backend):
        """An explicit connection_config should be used as-is."""
        assert backend.config.host == "127.0.0.1", "connection_config host should be preserved"

    def test_version_stored(self):
        """The version kwarg should be stored for dialect initialization."""
        backend = MySQLBackend(
            connection_config=MySQLConnectionConfig(host="h", database="d", username="u", password="p"),
            version=(8, 0, 0),
        )
        assert backend._version == (8, 0, 0), "version should be stored"

    def test_dialect_lazy(self, backend):
        """The dialect should be None until first access, then lazily created."""
        assert backend._dialect is None, "dialect should not be created during __init__"
        assert backend.dialect is not None, "dialect should be created on first access"

    def test_transaction_manager_created(self, backend):
        """A MySQL transaction manager should be attached."""
        assert backend.transaction_manager is not None, "transaction manager should be created"

    def test_adapters_registered(self, backend):
        """MySQL-specific type adapters should be registered in the registry."""
        from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLJSONAdapter

        adapter = backend.adapter_registry.get_adapter(dict, str)
        assert isinstance(adapter, MySQLJSONAdapter), "dict -> str adapter should be the MySQL JSON adapter"


class TestConnect:
    """Verify connect builds connection parameters and handles failures."""

    def test_connect_success(self, backend, monkeypatch):
        """connect should pass MySQL connection parameters to the driver."""
        captured, conn = _patch_connect(monkeypatch)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend.connect()
        assert backend._connection is conn, "connection should be stored"
        assert captured["host"] == "127.0.0.1", "host should be forwarded"
        assert captured["port"] == 3306, "port should be forwarded"
        assert captured["database"] == "test_db", "database should be forwarded"
        assert captured["user"] == "root", "username should map to user"
        assert captured["password"] == "secret", "password should be forwarded"
        assert captured["charset"] == "utf8mb4", "charset should be forwarded"
        assert captured["autocommit"] is True, "autocommit should be forwarded"
        assert captured["connection_timeout"] == 10, "connection timeout should be forwarded"
        assert captured["sql_mode"] == "STRICT_TRANS_TABLES", "sql_mode should be forwarded"

    def test_connect_ssl_params(self, backend, monkeypatch):
        """SSL config attributes should be forwarded when present."""
        backend.config.ssl_ca = "/ca.pem"
        backend.config.ssl_cert = "/cert.pem"
        backend.config.ssl_key = "/key.pem"
        backend.config.ssl_verify_cert = True
        backend.config.ssl_verify_identity = True
        captured, _ = _patch_connect(monkeypatch)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend.connect()
        assert captured["ssl_ca"] == "/ca.pem", "ssl_ca should be forwarded"
        assert captured["ssl_cert"] == "/cert.pem", "ssl_cert should be forwarded"
        assert captured["ssl_key"] == "/key.pem", "ssl_key should be forwarded"
        assert captured["ssl_verify_cert"] is True, "ssl_verify_cert should be forwarded"
        assert captured["ssl_verify_identity"] is True, "ssl_verify_identity should be forwarded"

    def test_connect_additional_params(self, backend, monkeypatch):
        """Additional supported params should be forwarded and pool params skipped."""
        backend.config.auth_plugin = "caching_sha2_password"
        backend.config.use_pure = True
        backend.config.pool_size = 5
        captured, _ = _patch_connect(monkeypatch)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend.connect()
        assert captured["auth_plugin"] == "caching_sha2_password", "auth_plugin should be forwarded"
        assert captured["use_pure"] is True, "use_pure should be forwarded"
        assert "pool_size" not in captured, "pool parameters should be skipped"

    def test_connect_init_command(self, backend, monkeypatch):
        """A configured init_command should be executed on a fresh cursor."""
        backend.config.init_command = "SET SESSION time_zone = '+00:00'"
        conn = _mock_connection()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        _patch_connect(monkeypatch, conn=conn)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend.connect()
        cursor.execute.assert_called_once_with("SET SESSION time_zone = '+00:00'"), "init_command should be executed"
        cursor.close.assert_called_once(), "init command cursor should be closed"

    def test_connect_failure_raises_connection_error(self, backend, monkeypatch):
        """A driver MySQLError during connect should raise ConnectionError."""
        def fail_connect(**kwargs):
            raise MySQLError("can't connect")

        monkeypatch.setattr("mysql.connector.connect", fail_connect)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        with pytest.raises(ConnectionError, match="Failed to connect to MySQL"):
            backend.connect()


class TestDisconnect:
    """Verify disconnect clears the connection and tolerates close failures."""

    def test_disconnect_closes_connection(self, backend):
        """disconnect should close the connection and clear the reference."""
        conn = _mock_connection()
        backend._connection = conn
        backend.disconnect()
        conn.close.assert_called_once(), "connection should be closed"
        assert backend._connection is None, "connection reference should be cleared"

    def test_disconnect_no_connection(self, backend):
        """disconnect with no active connection should be a no-op."""
        backend.disconnect()
        assert backend._connection is None, "no connection should remain"

    def test_disconnect_rolls_back_active_transaction(self, backend):
        """An active transaction should be rolled back during disconnect."""
        conn = _mock_connection()
        backend._connection = conn
        manager = MagicMock()
        manager.is_active = True
        backend._transaction_manager = manager
        backend.disconnect()
        manager.rollback.assert_called_once(), "active transaction should be rolled back"

    def test_disconnect_ignores_close_error(self, backend):
        """Close failures (MySQLError/BrokenPipe/OSError) should be logged, not raised."""
        conn = _mock_connection()
        conn.close.side_effect = MySQLError("broken pipe")
        backend._connection = conn
        backend.disconnect()
        assert backend._connection is None, "connection reference should be cleared even on close failure"


class TestGetCursor:
    """Verify _get_cursor performs automatic connection health checking."""

    def test_no_connection_connects(self, backend, monkeypatch):
        """_get_cursor should connect when no connection exists."""
        conn = _mock_connection()
        _patch_connect(monkeypatch, conn=conn)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend._connection = None
        cursor = backend._get_cursor()
        assert backend._connection is conn, "a connection should be established"
        assert cursor is not None, "a cursor should be returned"
        conn.cursor.assert_called(), "the connection should be asked for a cursor"

    def test_healthy_connection_returns_cursor(self, backend):
        """A healthy connection should return its cursor without reconnecting."""
        conn = _mock_connection()
        backend._connection = conn
        cursor = backend._get_cursor()
        assert cursor is conn.cursor.return_value, "cursor should come from the healthy connection"

    def test_stale_connection_reconnects(self, backend, monkeypatch):
        """A dead connection should be disconnected and reconnected."""
        conn = _mock_connection()
        conn.is_connected.return_value = False
        backend._connection = conn
        disconnect = MagicMock()
        connect = MagicMock()
        monkeypatch.setattr(backend, "disconnect", disconnect)
        monkeypatch.setattr(backend, "connect", connect)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend._get_cursor()
        disconnect.assert_called_once(), "stale connection should be disconnected"
        connect.assert_called_once(), "a new connection should be established"

    def test_is_connected_raises_broken_pipe(self, backend, monkeypatch):
        """BrokenPipeError from is_connected() should trigger a reconnect."""
        conn = _mock_connection()
        conn.is_connected.side_effect = BrokenPipeError("pipe broken")
        backend._connection = conn
        disconnect = MagicMock()
        connect = MagicMock()
        monkeypatch.setattr(backend, "disconnect", disconnect)
        monkeypatch.setattr(backend, "connect", connect)
        backend._get_cursor()
        disconnect.assert_called_once(), "broken pipe should trigger a reconnect"
        connect.assert_called_once(), "a new connection should be established"


class TestGetServerVersion:
    """Verify get_server_version parses version strings and falls back to defaults."""

    def test_cached_version_returned(self, backend, monkeypatch):
        """A stored version should be returned without touching the connection."""
        backend._version = (5, 7, 8)
        connect = MagicMock()
        monkeypatch.setattr(backend, "connect", connect)
        assert backend.get_server_version() == (5, 7, 8), "cached version should be returned"
        connect.assert_not_called(), "no connection needed for a cached version"

    def test_parses_version_string(self, backend, monkeypatch):
        """A VERSION() row like 8.0.26-log should parse to (8, 0, 26)."""
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.execute.return_value = None
        cursor.fetchone.return_value = ("8.0.26-log",)
        conn.cursor.return_value = cursor
        backend._connection = conn
        assert backend.get_server_version() == (8, 0, 26), "version string should be parsed"

    def test_empty_result_defaults(self, backend, monkeypatch):
        """A missing VERSION() row should default to (8, 0, 0)."""
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        backend._connection = conn
        assert backend.get_server_version() == (8, 0, 0), "empty row should default to 8.0.0"

    def test_exception_defaults(self, backend, monkeypatch):
        """A query exception should default to (8, 0, 0) and log a warning."""
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.execute.side_effect = MySQLError("syntax")
        conn.cursor.return_value = cursor
        backend._connection = conn
        assert backend.get_server_version() == (8, 0, 0), "query failure should default to 8.0.0"


class TestPing:
    """Verify ping checks liveness and reconnects on demand."""

    def test_no_connection_reconnect(self, backend, monkeypatch):
        """ping(reconnect=True) with no connection should connect and return True."""
        connect = MagicMock()
        monkeypatch.setattr(backend, "connect", connect)
        assert backend.ping(reconnect=True) is True, "ping should connect when reconnecting"
        connect.assert_called_once(), "connect should be attempted"

    def test_no_connection_no_reconnect(self, backend):
        """ping(reconnect=False) with no connection should return False."""
        assert backend.ping(reconnect=False) is False, "ping should not connect when reconnecting is disabled"

    def test_alive_no_reconnect(self, backend):
        """An alive connection with reconnect=False should return True without SELECT 1."""
        conn = _mock_connection()
        backend._connection = conn
        assert backend.ping(reconnect=False) is True, "alive connection should report healthy"
        conn.cursor.assert_not_called(), "no SELECT 1 should be issued with reconnect=False"

    def test_alive_with_reconnect(self, backend):
        """An alive connection with reconnect=True should verify via SELECT 1."""
        conn = _mock_connection()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        backend._connection = conn
        assert backend.ping(reconnect=True) is True, "SELECT 1 verification should succeed"
        cursor.execute.assert_called_once_with("SELECT 1"), "SELECT 1 should be issued"
        cursor.fetchone.assert_called_once(), "the verification row should be consumed"

    def test_dead_reconnect(self, backend, monkeypatch):
        """A dead connection with reconnect=True should reconnect and return True."""
        conn = _mock_connection()
        conn.is_connected.return_value = False
        backend._connection = conn
        disconnect = MagicMock()
        connect = MagicMock()
        monkeypatch.setattr(backend, "disconnect", disconnect)
        monkeypatch.setattr(backend, "connect", connect)
        assert backend.ping(reconnect=True) is True, "ping should reconnect a dead connection"
        disconnect.assert_called_once(), "dead connection should be disconnected"
        connect.assert_called_once(), "a new connection should be established"

    def test_dead_no_reconnect(self, backend):
        """A dead connection with reconnect=False should return False."""
        conn = _mock_connection()
        conn.is_connected.return_value = False
        backend._connection = conn
        assert backend.ping(reconnect=False) is False, "dead connection should report unhealthy"

    def test_is_connected_broken_pipe(self, backend, monkeypatch):
        """BrokenPipeError from is_connected() should be treated as a dead connection."""
        conn = _mock_connection()
        conn.is_connected.side_effect = BrokenPipeError("pipe")
        backend._connection = conn
        connect = MagicMock()
        monkeypatch.setattr(backend, "connect", connect)
        assert backend.ping(reconnect=True) is True, "broken pipe should trigger reconnect"
        connect.assert_called_once(), "reconnect should be attempted"

    def test_select1_broken_pipe_reconnects(self, backend, monkeypatch):
        """BrokenPipeError during SELECT 1 should trigger reconnect."""
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.execute.side_effect = BrokenPipeError("pipe")
        conn.cursor.return_value = cursor
        backend._connection = conn
        disconnect = MagicMock()
        connect = MagicMock()
        monkeypatch.setattr(backend, "disconnect", disconnect)
        monkeypatch.setattr(backend, "connect", connect)
        assert backend.ping(reconnect=True) is True, "SELECT 1 failure should trigger reconnect"
        connect.assert_called_once(), "reconnect should be attempted"

    def test_mysql_error_reconnect_failure(self, backend, monkeypatch):
        """A driver error with failed reconnect should return False."""
        conn = _mock_connection()
        conn.is_connected.side_effect = MySQLError("gone away")
        backend._connection = conn

        def fail_connect():
            raise MySQLError("cannot connect")

        monkeypatch.setattr(backend, "connect", fail_connect)
        assert backend.ping(reconnect=True) is False, "ping should report failure when reconnect fails"


class TestReconnect:
    """Verify _reconnect disconnects and reconnects safely."""

    def test_reconnect_success(self, backend, monkeypatch):
        """_reconnect should return True when both steps succeed."""
        disconnect = MagicMock()
        connect = MagicMock()
        monkeypatch.setattr(backend, "disconnect", disconnect)
        monkeypatch.setattr(backend, "connect", connect)
        assert backend._reconnect() is True, "reconnect should succeed"
        disconnect.assert_called_once(), "disconnect should run first"
        connect.assert_called_once(), "connect should run after disconnect"

    def test_reconnect_failure(self, backend, monkeypatch):
        """_reconnect should return False when connect raises."""
        disconnect = MagicMock()
        connect = MagicMock(side_effect=MySQLError("cannot connect"))
        monkeypatch.setattr(backend, "disconnect", disconnect)
        monkeypatch.setattr(backend, "connect", connect)
        assert backend._reconnect() is False, "reconnect should report failure"


class TestAutoCommit:
    """Verify _handle_auto_commit and _handle_auto_commit_if_needed."""

    def test_no_connection_noop(self, backend):
        """_handle_auto_commit with no connection should be a no-op."""
        backend._connection = None
        backend._handle_auto_commit()
        assert backend._connection is None, "no connection should be created"

    def test_commits_when_autocommit_disabled(self, backend):
        """A commit should be issued when autocommit is disabled and not in a transaction."""
        conn = _mock_connection()
        backend._connection = conn
        backend.config.autocommit = False
        backend._handle_auto_commit()
        conn.commit.assert_called_once(), "commit should be issued"

    def test_no_commit_when_autocommit_enabled(self, backend):
        """No commit should be issued when autocommit is enabled."""
        conn = _mock_connection()
        backend._connection = conn
        backend.config.autocommit = True
        backend._handle_auto_commit()
        conn.commit.assert_not_called(), "no commit needed under autocommit"

    def test_no_commit_inside_transaction(self, backend):
        """No commit should be issued inside an active transaction."""
        conn = _mock_connection()
        backend._connection = conn
        backend.config.autocommit = False
        manager = MagicMock()
        manager.is_active = True
        backend._transaction_manager = manager
        backend._handle_auto_commit()
        conn.commit.assert_not_called(), "no commit inside a transaction"

    def test_commit_error_logged(self, backend):
        """A commit failure should be logged, not raised."""
        conn = _mock_connection()
        conn.commit.side_effect = MySQLError("commit failed")
        backend._connection = conn
        backend.config.autocommit = False
        backend._handle_auto_commit()

    def test_if_needed_commits(self, backend):
        """_handle_auto_commit_if_needed should commit when eligible."""
        conn = _mock_connection()
        backend._connection = conn
        backend.config.autocommit = False
        backend._handle_auto_commit_if_needed()
        conn.commit.assert_called_once(), "commit should be issued by _handle_auto_commit_if_needed"

    def test_if_needed_skips_inside_transaction(self, backend):
        """_handle_auto_commit_if_needed should skip inside a transaction."""
        conn = _mock_connection()
        backend._connection = conn
        backend.config.autocommit = False
        manager = MagicMock()
        manager.is_active = True
        backend._transaction_manager = manager
        backend._handle_auto_commit_if_needed()
        conn.commit.assert_not_called(), "no commit inside a transaction"


class TestExecute:
    """Verify execute() options construction and connection-error retry logic."""

    @pytest.fixture(autouse=True)
    def patch_super_execute(self, monkeypatch):
        """Route super().execute to a configurable stub."""
        import rhosocial.activerecord.backend.base.execution as execution_base

        stub = MagicMock(return_value=QueryResult(data=[], affected_rows=0))
        monkeypatch.setattr(execution_base.ExecutionMixin, "execute", stub)
        return stub

    def test_dql_options(self, backend, patch_super_execute):
        """A SELECT statement should be classified as DQL."""
        backend.execute("SELECT * FROM users")
        options = patch_super_execute.call_args.kwargs["options"]
        assert options.stmt_type == StatementType.DQL, "SELECT should map to DQL"

    def test_dml_options(self, backend, patch_super_execute):
        """INSERT/UPDATE/DELETE/REPLACE statements should be classified as DML."""
        backend.execute("INSERT INTO users (id) VALUES (1)")
        options = patch_super_execute.call_args.kwargs["options"]
        assert options.stmt_type == StatementType.DML, "INSERT should map to DML"

    def test_ddl_options(self, backend, patch_super_execute):
        """Other statements should be classified as DDL."""
        backend.execute("CREATE TABLE users (id INT)")
        options = patch_super_execute.call_args.kwargs["options"]
        assert options.stmt_type == StatementType.DDL, "CREATE TABLE should map to DDL"

    def test_kwargs_forwarded_to_options(self, backend, patch_super_execute):
        """column_mapping and column_adapters kwargs should populate the options."""
        mapping = {"id": "identifier"}
        backend.execute("SELECT id FROM users", column_mapping=mapping, column_adapters={"id": object})
        options = patch_super_execute.call_args.kwargs["options"]
        assert options.column_mapping == mapping, "column_mapping should be forwarded"
        assert options.column_adapters == {"id": object}, "column_adapters should be forwarded"

    def test_explicit_options_updated_with_kwargs(self, backend, patch_super_execute):
        """Provided options should be updated with explicit kwargs."""
        from rhosocial.activerecord.backend.options import ExecutionOptions

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        backend.execute("SELECT 1", options=options, column_mapping={"a": "b"})
        assert options.column_mapping == {"a": "b"}, "explicit options should be updated with column_mapping"

    def test_returns_result(self, backend, patch_super_execute):
        """execute should return the underlying QueryResult."""
        result = backend.execute("SELECT 1")
        assert isinstance(result, QueryResult), "execute should return a QueryResult"

    def test_retry_on_connection_error(self, backend, patch_super_execute, monkeypatch):
        """A connection error should trigger a reconnect and retry."""
        connection_error = MySQLOperationalError(errno=2006, msg="server has gone away")
        patch_super_execute.side_effect = [connection_error, QueryResult(data=[], affected_rows=0)]
        monkeypatch.setattr(backend, "_reconnect", lambda: True)
        result = backend.execute("SELECT 1")
        assert isinstance(result, QueryResult), "retry should succeed with a QueryResult"
        assert patch_super_execute.call_count == 2, "execute should be attempted twice"

    def test_handle_error_after_retries(self, backend, patch_super_execute, monkeypatch):
        """Exhausted retries should surface the underlying error via _handle_error."""
        patch_super_execute.side_effect = MySQLOperationalError(errno=2006, msg="gone away")
        monkeypatch.setattr(backend, "_reconnect", lambda: True)
        with pytest.raises(DatabaseError):
            backend.execute("SELECT 1")

    def test_non_connection_error_raised(self, backend, patch_super_execute):
        """A non-connection MySQL error should be raised immediately."""
        patch_super_execute.side_effect = MySQLOperationalError(errno=1045, msg="access denied")
        with pytest.raises(DatabaseError):
            backend.execute("SELECT 1")

    def test_reconnect_failure_raises(self, backend, patch_super_execute, monkeypatch):
        """A failed reconnect should abort retrying and raise the error."""
        patch_super_execute.side_effect = MySQLOperationalError(errno=2006, msg="gone away")
        monkeypatch.setattr(backend, "_reconnect", lambda: False)
        with pytest.raises(DatabaseError):
            backend.execute("SELECT 1")


class TestExecuteMany:
    """Verify execute_many batch execution and error classification."""

    def _setup_cursor(self, backend):
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.rowcount = 2
        conn.cursor.return_value = cursor
        backend._connection = conn
        return cursor

    def test_success_aggregates_rowcount(self, backend):
        """execute_many should aggregate rowcount over all parameter sets."""
        cursor = self._setup_cursor(backend)
        result = backend.execute_many("INSERT INTO t VALUES (%s)", [(1,), (2,), (3,)])
        assert cursor.execute.call_count == 3, "each parameter set should be executed"
        assert result.affected_rows == 6, "rowcounts should be aggregated"
        assert result.data is None, "batch operations carry no result data"

    def test_no_connection_connects(self, backend, monkeypatch):
        """execute_many should connect when no connection exists."""
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.rowcount = 1
        conn.cursor.return_value = cursor
        _patch_connect(monkeypatch, conn=conn)
        monkeypatch.setattr(backend, "_fetch_concurrency_hint", lambda: None)
        backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])
        assert backend._connection is conn, "connection should be established"

    def test_integrity_error(self, backend):
        """A MySQLIntegrityError should be converted to IntegrityError."""
        cursor = self._setup_cursor(backend)
        cursor.execute.side_effect = MySQLIntegrityError("Duplicate entry '1'")
        with pytest.raises(IntegrityError):
            backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

    def test_mysql_error(self, backend):
        """A generic MySQLError should be converted to DatabaseError."""
        cursor = self._setup_cursor(backend)
        cursor.execute.side_effect = MySQLError("syntax error")
        with pytest.raises(DatabaseError):
            backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

    def test_other_error(self, backend):
        """An unexpected exception should be converted to QueryError."""
        cursor = self._setup_cursor(backend)
        cursor.execute.side_effect = ValueError("boom")
        with pytest.raises(QueryError):
            backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

    def test_cursor_closed(self, backend):
        """The cursor should be closed in a finally block even on error."""
        cursor = self._setup_cursor(backend)
        cursor.execute.side_effect = MySQLError("syntax error")
        with pytest.raises(DatabaseError):
            backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])
        cursor.close.assert_called_once(), "cursor should be closed after the batch"


class TestExecuteScript:
    """Verify executescript handles connector 9.2+ and legacy APIs."""

    def _cursor(self):
        conn = _mock_connection()
        cursor = MagicMock()
        cursor.with_rows = False
        cursor.nextset.return_value = False
        conn.cursor.return_value = cursor
        return conn, cursor

    def test_new_api_path(self, backend, monkeypatch):
        """9.2.0+ should use execute() + nextset() without the multi parameter."""
        conn, cursor = self._cursor()
        backend._connection = conn
        monkeypatch.setattr(mysql.connector.version, "VERSION", (9, 2, 0))
        backend.executescript("SELECT 1; SELECT 2")
        cursor.execute.assert_called_once_with("SELECT 1; SELECT 2"), "script should be executed directly"
        cursor.nextset.assert_called(), "result sets should be consumed via nextset"

    def test_new_api_consumes_result_sets(self, backend, monkeypatch):
        """9.2.0+ should fetch rows from result sets and continue with nextset."""
        conn, cursor = self._cursor()
        cursor.with_rows = True
        cursor.nextset.side_effect = [True, False]
        backend._connection = conn
        monkeypatch.setattr(mysql.connector.version, "VERSION", (9, 3, 0))
        backend.executescript("SELECT 1; SELECT 2")
        assert cursor.fetchall.call_count >= 1, "rows should be fetched from result sets"

    def test_legacy_api_path(self, backend, monkeypatch):
        """Pre-9.2.0 should use execute(sql, multi=True)."""
        conn, cursor = self._cursor()
        backend._connection = conn
        monkeypatch.setattr(mysql.connector.version, "VERSION", (8, 4, 0))
        results = [MagicMock()]
        results[0].with_rows = False
        cursor.execute.return_value = results
        backend.executescript("SELECT 1; SELECT 2")
        cursor.execute.assert_called_once_with("SELECT 1; SELECT 2", multi=True), "multi=True should be used"

    def test_mysql_error_handled(self, backend, monkeypatch):
        """A MySQLError during the script should be raised via _handle_error."""
        conn, cursor = self._cursor()
        backend._connection = conn
        monkeypatch.setattr(mysql.connector.version, "VERSION", (9, 2, 0))
        cursor.execute.side_effect = MySQLError("syntax")
        with pytest.raises(DatabaseError):
            backend.executescript("BAD SQL")


class TestIntrospectAndAdapt:
    """Verify introspect_and_adapt connects and adapts to the server version."""

    def test_connects_when_missing(self, backend, monkeypatch):
        """introspect_and_adapt should connect when no connection exists."""
        connect = MagicMock()
        monkeypatch.setattr(backend, "connect", connect)
        monkeypatch.setattr(backend, "get_server_version", lambda: (8, 0, 0))
        monkeypatch.setattr(backend, "_register_mysql_adapters", lambda: None)
        backend._connection = None
        backend.introspect_and_adapt()
        connect.assert_called_once(), "connect should be called when no connection exists"

    def test_adapts_when_version_differs(self, backend, monkeypatch):
        """A different server version should recreate the dialect and adapters."""
        backend._connection = _mock_connection()
        backend._version = (5, 7, 0)
        monkeypatch.setattr(backend, "get_server_version", lambda: (8, 0, 26))
        registered = []
        monkeypatch.setattr(backend, "_register_mysql_adapters", lambda: registered.append(True))
        backend.introspect_and_adapt()
        assert backend._version == (8, 0, 26), "version should be updated"
        assert backend._dialect is not None, "a new dialect should be created"
        assert backend._dialect.version == (8, 0, 26), "dialect should use the detected version"
        assert registered, "adapters should be re-registered"

    def test_no_adapt_when_same_version(self, backend, monkeypatch):
        """A matching version should not recreate the dialect or adapters."""
        backend._connection = _mock_connection()
        backend._version = (8, 0, 0)
        monkeypatch.setattr(backend, "get_server_version", lambda: (8, 0, 0))
        registered = []
        monkeypatch.setattr(backend, "_register_mysql_adapters", lambda: registered.append(True))
        old_dialect = backend._dialect
        backend.introspect_and_adapt()
        assert backend._dialect is old_dialect, "dialect should be reused for the same version"
        assert registered == [], "adapters should not be re-registered for the same version"


class TestParseExplainResult:
    """Verify _parse_explain_result builds typed MySQL explain rows."""

    def test_parses_rows(self, backend):
        """Raw EXPLAIN rows should become MySQLExplainRow objects."""
        raw = [{"id": 1, "select_type": "SIMPLE", "table": "users", "type": "ALL"}]
        result = backend._parse_explain_result(raw, "SELECT 1", 0.01)
        assert result.sql == "SELECT 1", "sql should be preserved"
        assert result.duration == 0.01, "duration should be preserved"
        assert len(result.rows) == 1, "one row should be produced"
        assert result.rows[0].table == "users", "row table should be parsed"
        assert result.rows[0].type == "ALL", "row access type should be parsed"


class TestCreateIntrospector:
    """Verify _create_introspector builds a sync MySQL introspector."""

    def test_returns_introspector(self, backend):
        """_create_introspector should return a SyncMySQLIntrospector."""
        introspector = backend._create_introspector()
        from rhosocial.activerecord.backend.impl.mysql.introspection import SyncMySQLIntrospector

        assert isinstance(introspector, SyncMySQLIntrospector), "introspector should be a SyncMySQLIntrospector"


class TestHandleError:
    """Verify _handle_error classifies MySQL driver errors (mixin coverage)."""

    def test_duplicate_entry(self, backend):
        """A duplicate-entry integrity error should raise IntegrityError."""
        error = MySQLIntegrityError("Duplicate entry 'x' for key 'email'")
        with pytest.raises(IntegrityError, match="Unique constraint violation"):
            backend._handle_error(error)

    def test_foreign_key_violation(self, backend):
        """A foreign key violation should raise IntegrityError."""
        error = MySQLIntegrityError("a foreign key constraint fails")
        with pytest.raises(IntegrityError, match="Foreign key constraint violation"):
            backend._handle_error(error)

    def test_deadlock(self, backend):
        """A deadlock database error should raise the deadlock-specific error."""
        from mysql.connector.errors import DatabaseError as MySQLDatabaseError

        from rhosocial.activerecord.backend.errors import DeadlockError

        error = MySQLDatabaseError("Deadlock found when trying to get lock")
        with pytest.raises(DeadlockError):
            backend._handle_error(error)

    def test_generic_integrity(self, backend):
        """An unmatched integrity error should still raise IntegrityError."""
        error = MySQLIntegrityError("some integrity problem")
        with pytest.raises(IntegrityError):
            backend._handle_error(error)

    def test_generic_mysql_error(self, backend):
        """A generic MySQLError should raise DatabaseError."""
        error = MySQLError("some mysql error")
        with pytest.raises(DatabaseError):
            backend._handle_error(error)

    def test_unexpected_error_reraised(self, backend):
        """A non-driver error should be re-raised unchanged."""
        error = ValueError("boom")
        with pytest.raises(ValueError, match="boom"):
            backend._handle_error(error)


class TestIsConnectionError:
    """Verify _is_connection_error recognizes connection-loss errnos and messages."""

    def test_errno_in_known_codes(self, backend):
        """Known connection errnos should be classified as connection errors."""
        error = MySQLOperationalError(errno=2006, msg="x")
        assert backend._is_connection_error(error) is True, "2006 is a connection error"

    def test_unknown_errno(self, backend):
        """An unrelated errno should not be classified as a connection error."""
        error = MySQLOperationalError(errno=1045, msg="x")
        assert backend._is_connection_error(error) is False, "1045 is not a connection error"

    def test_message_pattern(self, backend):
        """A connection-loss message should be recognized even without an errno."""
        error = MySQLOperationalError(errno=0, msg="Server has gone away")
        assert backend._is_connection_error(error) is True, "gone-away message recognized"