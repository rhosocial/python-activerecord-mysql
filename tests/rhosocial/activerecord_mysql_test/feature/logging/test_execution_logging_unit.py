# tests/rhosocial/activerecord_mysql_test/feature/logging/test_execution_logging_unit.py
"""Database-free unit tests for MySQL execution logging.

These tests never open a connection. They import every module touched by the
logging change, use synthetic connections/cursors to drive the batch and
script logging paths, and exercise the error/isolation branches directly.

The module itself must import even when ``mysql-connector-python`` cannot be
imported (for example on a free-threaded interpreter).  A lightweight stub is
installed into ``sys.modules`` only when the real driver is unavailable; the
tests that need driver error classes resolve them lazily from whichever
package is loaded.
"""

import importlib
import logging
import sys
import types

import pytest

LIBRARY_LOGGER = "rhosocial.activerecord.backend.mysql"


def _install_mysql_stub() -> None:
    """Register a minimal mysql.connector package in ``sys.modules``."""
    mysql_module = types.ModuleType("mysql")
    mysql_module.__path__ = []

    connector_module = types.ModuleType("mysql.connector")
    connector_module.__path__ = []

    class StubError(Exception):
        def __str__(self):
            return str(self.args[-1]) if self.args else ""

    class StubDatabaseError(StubError):
        pass

    class StubIntegrityError(StubDatabaseError):
        pass

    class StubOperationalError(StubDatabaseError):
        pass

    errors_module = types.ModuleType("mysql.connector.errors")
    errors_module.Error = StubError
    errors_module.DatabaseError = StubDatabaseError
    errors_module.IntegrityError = StubIntegrityError
    errors_module.OperationalError = StubOperationalError
    errors_module.PoolError = StubError

    aio_module = types.ModuleType("mysql.connector.aio")
    version_module = types.ModuleType("mysql.connector.version")
    version_module.VERSION = (9, 2, 0)

    connector_module.errors = errors_module
    connector_module.aio = aio_module
    connector_module.version = version_module
    connector_module.threadsafety = 2

    mysql_module.connector = connector_module

    sys.modules["mysql"] = mysql_module
    sys.modules["mysql.connector"] = connector_module
    sys.modules["mysql.connector.errors"] = errors_module
    sys.modules["mysql.connector.aio"] = aio_module
    sys.modules["mysql.connector.version"] = version_module


def _ensure_mysql_driver() -> None:
    """Use the real driver when importable, otherwise install the stub."""
    try:
        importlib.import_module("mysql.connector")
        importlib.import_module("mysql.connector.aio")
        importlib.import_module("mysql.connector.errors")
    except ImportError:
        _install_mysql_stub()


_ensure_mysql_driver()

from rhosocial.activerecord.backend.errors import (  # noqa: E402
    DatabaseError,
    DeadlockError,
    IntegrityError,
)
from rhosocial.activerecord.backend.impl.mysql.backend.async_backend import (  # noqa: E402
    AsyncMySQLBackend,
)
from rhosocial.activerecord.backend.impl.mysql.backend.backend import MySQLBackend  # noqa: E402
from rhosocial.activerecord.backend.impl.mysql.cli import info as cli_info  # noqa: E402
from rhosocial.activerecord.backend.impl.mysql.cli import query as cli_query  # noqa: E402
from rhosocial.activerecord.backend.impl.mysql.mixins import (  # noqa: E402
    MySQLBackendMixin,
    MySQLTransactionMixin,
)
from rhosocial.activerecord.backend.transaction import (  # noqa: E402
    IsolationLevel,
    IsolationLevelError,
)
from rhosocial.activerecord.logging.redaction import SensitiveValue  # noqa: E402


class FakeCursor:
    """Minimal DB-API cursor used by the sync backend paths."""

    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.executed = []
        self.closed = False
        self.with_rows = False

    def execute(self, sql, params=None, *args, **kwargs):
        self.executed.append((sql, params))
        # mysql-connector < 9.2 returns an iterable when multi=True.
        return [self]

    def fetchall(self):
        return []

    def nextset(self):
        return False

    def close(self):
        self.closed = True


class FakeConnection:
    """Minimal connection that reports itself healthy and hands out a cursor."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def is_connected(self):
        return True

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


class AsyncFakeCursor:
    """Minimal async cursor used by the async backend paths."""

    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.executed = []
        self.closed = False
        self.description = None

    async def execute(self, sql, params=None, *args, **kwargs):
        self.executed.append((sql, params))

    async def fetchall(self):
        return []

    async def close(self):
        self.closed = True


class AsyncFakeConnection:
    """Minimal async connection that reports itself healthy."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    async def is_connected(self):
        return True

    async def cursor(self):
        return self._cursor

    async def close(self):
        self.closed = True


def make_backend():
    """Create a sync backend without connecting to a server."""
    return MySQLBackend(version=(8, 0, 36), host="localhost", database="test")


def make_async_backend():
    """Create an async backend without connecting to a server."""
    return AsyncMySQLBackend(version=(8, 0, 36), host="localhost", database="test")


def make_driver_error(error_name, message, errno=None):
    """Build an instance of the currently loaded mysql driver error class."""
    if error_name is None:
        return ValueError(message)

    errors = importlib.import_module("mysql.connector.errors")
    error_class = getattr(errors, error_name)
    if errno is None:
        return error_class(message)
    try:
        return error_class(errno, message)
    except TypeError:
        return error_class(message)


class TestBackendWiring:
    """Module imports and the shared canonical logger name."""

    def test_sync_and_async_backends_share_library_logger(self):
        backend = make_backend()
        async_backend = make_async_backend()

        assert backend._get_logger_name() == LIBRARY_LOGGER
        assert async_backend._get_logger_name() == LIBRARY_LOGGER
        assert backend.logger.name == LIBRARY_LOGGER
        assert async_backend.logger.name == LIBRARY_LOGGER

    def test_mixins_and_cli_loggers_are_library_loggers(self):
        assert MySQLBackendMixin._logger_name == LIBRARY_LOGGER
        assert issubclass(MySQLTransactionMixin, object)
        assert cli_info.logger.name == f"{LIBRARY_LOGGER}.cli.info"
        assert cli_query.logger.name == f"{LIBRARY_LOGGER}.cli.query"

    def test_cli_modules_reload_with_library_loggers(self):
        # Other test modules may import these before coverage starts; reload
        # re-executes the module-level logger assignment under coverage.
        info = importlib.reload(cli_info)
        query = importlib.reload(cli_query)

        assert info.logger.name == f"{LIBRARY_LOGGER}.cli.info"
        assert query.logger.name == f"{LIBRARY_LOGGER}.cli.query"

    def test_driver_stub_has_the_error_attributes_handle_error_needs(self):
        errors = importlib.import_module("mysql.connector.errors")
        for name in ("Error", "DatabaseError", "IntegrityError", "OperationalError"):
            assert issubclass(getattr(errors, name), Exception)


class TestExecuteManyLogging:
    """Batch execution logs counts but never parameter values."""

    def test_batch_logging_hides_parameter_values(self, caplog):
        backend = make_backend()
        cursor = FakeCursor(rowcount=1)
        backend._connection = FakeConnection(cursor)
        params_list = [
            (1, SensitiveValue("first-secret")),
            (2, SensitiveValue("second-secret")),
        ]

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            result = backend.execute_many(
                "INSERT INTO users (id, secret) VALUES (%s, %s)", params_list
            )

        assert result.affected_rows == 2
        assert cursor.executed[-1][1][1] == "second-secret"
        assert cursor.closed is True

        messages = "\n".join(caplog.messages)
        assert "first-secret" not in messages
        assert "second-secret" not in messages
        assert "parameter_sets: 2" in messages


class TestAsyncExecuteManyLogging:
    """Async batch execution mirrors the sync logging contract."""

    @pytest.mark.asyncio
    async def test_batch_logging_hides_parameter_values(self, caplog):
        backend = make_async_backend()
        cursor = AsyncFakeCursor(rowcount=1)
        backend._connection = AsyncFakeConnection(cursor)
        params_list = [
            (1, SensitiveValue("first-secret")),
            (2, SensitiveValue("second-secret")),
        ]

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            result = await backend.execute_many(
                "INSERT INTO users (id, secret) VALUES (%s, %s)", params_list
            )

        assert result.affected_rows == 2
        assert cursor.executed[-1][1][1] == "second-secret"
        assert cursor.closed is True

        messages = "\n".join(caplog.messages)
        assert "first-secret" not in messages
        assert "second-secret" not in messages
        assert "parameter_sets: 2" in messages


class TestExecuteScriptLogging:
    """executescript success paths emit the start and duration records."""

    def test_sync_executescript_logs_lifecycle(self, caplog):
        backend = make_backend()
        cursor = FakeCursor(rowcount=0)
        backend._connection = FakeConnection(cursor)

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            backend.executescript("SELECT 1; SELECT 2")

        assert cursor.closed is True
        messages = "\n".join(caplog.messages)
        assert "Executing SQL script." in messages
        assert "SQL script executed successfully" in messages

    @pytest.mark.asyncio
    async def test_async_executescript_logs_lifecycle(self, caplog):
        backend = make_async_backend()
        cursor = AsyncFakeCursor(rowcount=0)
        backend._connection = AsyncFakeConnection(cursor)

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            await backend.executescript("SELECT 1; SELECT 2")

        assert cursor.closed is True
        messages = "\n".join(caplog.messages)
        assert "Executing SQL script asynchronously." in messages
        assert "Async SQL script executed successfully" in messages


class TestHandleError:
    """MySQL driver exceptions map to the library error classes."""

    @pytest.mark.parametrize(
        ("error_name", "message", "errno", "expected", "log_fragment"),
        [
            (
                "IntegrityError",
                "Duplicate entry 'x' for key 'uniq'",
                1062,
                IntegrityError,
                "Unique constraint violation",
            ),
            (
                "IntegrityError",
                "Cannot delete or update a parent row",
                1451,
                IntegrityError,
                "Foreign key constraint violation",
            ),
            (
                "IntegrityError",
                "some other integrity failure",
                1062,
                IntegrityError,
                "Integrity error",
            ),
            (
                "DatabaseError",
                "Deadlock found when trying to get lock",
                None,
                DeadlockError,
                "Deadlock error",
            ),
            (
                "DatabaseError",
                "generic database failure",
                None,
                DatabaseError,
                "Database error",
            ),
            (
                "Error",
                "plain mysql failure",
                None,
                DatabaseError,
                "MySQL error",
            ),
            (
                None,
                "unexpected failure",
                None,
                ValueError,
                "Unexpected error",
            ),
        ],
    )
    def test_driver_errors_map_and_log(
        self, caplog, error_name, message, errno, expected, log_fragment
    ):
        backend = make_backend()
        error = make_driver_error(error_name, message, errno)

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            with pytest.raises(expected):
                backend._handle_error(error)

        assert any(log_fragment in message for message in caplog.messages)


class TestTransactionIsolationGuard:
    """Isolation level changes are refused while a transaction is active."""

    def test_setter_rejects_change_while_active(self, caplog):
        backend = make_backend()
        manager = backend.transaction_manager
        manager._transaction_level = 1

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            with pytest.raises(IsolationLevelError):
                manager.isolation_level = IsolationLevel.READ_COMMITTED

        assert "Cannot change isolation level during active transaction" in caplog.messages
        assert manager.isolation_level is None

    def test_setter_logs_value_when_inactive(self, caplog):
        backend = make_backend()
        manager = backend.transaction_manager

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            manager.isolation_level = IsolationLevel.READ_COMMITTED

        assert manager.isolation_level is IsolationLevel.READ_COMMITTED
        assert any("Isolation level set to" in message for message in caplog.messages)

    @pytest.mark.asyncio
    async def test_async_setter_rejects_change_while_active(self):
        backend = make_async_backend()
        manager = backend.transaction_manager
        manager._transaction_level = 1

        with pytest.raises(IsolationLevelError):
            manager.isolation_level = IsolationLevel.READ_COMMITTED

        assert manager.isolation_level is None


class TestExecuteManyFailureLogging:
    """Batch failures log a redaction-safe note and re-raise the original error."""

    def test_unexpected_batch_error_is_reraised(self, caplog):
        backend = make_backend()

        class ExplodingCursor(FakeCursor):
            def execute(self, sql, params=None, *args, **kwargs):
                raise RuntimeError("boom after password=secret")

        backend._connection = FakeConnection(ExplodingCursor())

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            with pytest.raises(RuntimeError, match="boom after password=secret"):
                backend.execute_many("INSERT INTO users VALUES (%s)", [(1,)])

        messages = "\n".join(caplog.messages)
        assert "Query failed, exception will be re-raised" in messages
