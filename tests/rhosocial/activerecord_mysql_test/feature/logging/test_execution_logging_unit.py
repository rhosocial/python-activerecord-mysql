# tests/rhosocial/activerecord_mysql_test/feature/logging/test_execution_logging_unit.py
"""Database-free unit tests for MySQL execution logging.

These tests never open a connection. They import every module touched by the
logging change, use synthetic connections/cursors to drive the batch and
script logging paths, and exercise the error/isolation branches directly.
"""

import importlib
import logging

import pytest

pytest.importorskip("mysql.connector")

from mysql.connector.errors import (  # noqa: E402
    DatabaseError as MySQLDatabaseError,
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
)
from rhosocial.activerecord.backend.errors import (  # noqa: E402
    DatabaseError,
    DeadlockError,
    IntegrityError,
    QueryError,
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

LIBRARY_LOGGER = "rhosocial.activerecord.backend.mysql"


class FakeCursor:
    """Minimal DB-API cursor used by the sync backend paths."""

    def __init__(self, rowcount=1):
        self.rowcount = rowcount
        self.executed = []
        self.closed = False
        self.with_rows = False

    def execute(self, sql, params=None, *args, **kwargs):
        self.executed.append((sql, params))

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
        ("error", "expected", "log_fragment"),
        [
            (
                MySQLIntegrityError(1062, "Duplicate entry 'x' for key 'uniq'"),
                IntegrityError,
                "Unique constraint violation",
            ),
            (
                MySQLIntegrityError(1451, "Cannot delete or update a parent row"),
                IntegrityError,
                "Foreign key constraint violation",
            ),
            (
                MySQLIntegrityError(1062, "some other integrity failure"),
                IntegrityError,
                "Integrity error",
            ),
            (
                MySQLDatabaseError("Deadlock found when trying to get lock"),
                DeadlockError,
                "Deadlock error",
            ),
            (
                MySQLDatabaseError("generic database failure"),
                DatabaseError,
                "Database error",
            ),
            (
                MySQLError("plain mysql failure"),
                DatabaseError,
                "MySQL error",
            ),
            (
                ValueError("unexpected failure"),
                ValueError,
                "Unexpected error",
            ),
        ],
    )
    def test_driver_errors_map_and_log(self, caplog, error, expected, log_fragment):
        backend = make_backend()

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
    """Batch failures log a redaction-safe note and re-raise a QueryError."""

    def test_unexpected_batch_error_is_wrapped(self, caplog):
        backend = make_backend()

        class ExplodingCursor(FakeCursor):
            def execute(self, sql, params=None, *args, **kwargs):
                raise RuntimeError("boom after password=secret")

        backend._connection = FakeConnection(ExplodingCursor())

        with caplog.at_level(logging.DEBUG, logger=LIBRARY_LOGGER):
            with pytest.raises(QueryError):
                backend.execute_many("INSERT INTO users VALUES (%s)", [(1,)])

        messages = "\n".join(caplog.messages)
        assert "Query failed, exception will be re-raised" in messages
