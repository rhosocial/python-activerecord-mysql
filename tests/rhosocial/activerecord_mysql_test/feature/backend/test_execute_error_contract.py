# tests/rhosocial/activerecord_mysql_test/feature/backend/test_execute_error_contract.py
"""Execute error-phase contract for the MySQL backend (no database required)."""

import pytest

mysql_errors = pytest.importorskip("mysql.connector.errors")

from rhosocial.activerecord.backend.base import AsyncExecutionMixin, ExecutionMixin  # noqa: E402
from rhosocial.activerecord.backend.errors import (  # noqa: E402
    DeadlockError,
    IntegrityError,
    OperationalError,
    TransactionError,
)
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend  # noqa: E402
from rhosocial.activerecord.backend.impl.mysql.backend.async_backend import (  # noqa: E402
    AsyncMySQLBackend,
)
from rhosocial.activerecord.backend.options import (  # noqa: E402
    ExecutionOptions,
    StatementType,
)
from rhosocial.activerecord.backend.result import QueryResult  # noqa: E402


class _FakeCursor:
    def __init__(self, execute_error=None, close_error=None, rowcount=1):
        self.execute_error = execute_error
        self.close_error = close_error
        self.rowcount = rowcount
        self.executed = []

    def execute(self, sql, params=None):
        if self.execute_error is not None:
            raise self.execute_error
        self.executed.append((sql, params))
        return self

    def close(self):
        if self.close_error is not None:
            raise self.close_error


class _FakeAsyncCursor:
    def __init__(self, execute_error=None, close_error=None, rowcount=1):
        self.execute_error = execute_error
        self.close_error = close_error
        self.rowcount = rowcount
        self.executed = []

    async def execute(self, sql, params=None):
        if self.execute_error is not None:
            raise self.execute_error
        self.executed.append((sql, params))
        return self

    async def close(self):
        if self.close_error is not None:
            raise self.close_error


class _FakeConnection:
    def __init__(self, commit_error=None):
        self.commit_error = commit_error
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1
        if self.commit_error is not None:
            raise self.commit_error


class _FakeAsyncConnection:
    def __init__(self, commit_error=None):
        self.commit_error = commit_error
        self.commit_calls = 0

    async def commit(self):
        self.commit_calls += 1
        if self.commit_error is not None:
            raise self.commit_error


@pytest.fixture
def backend():
    return MySQLBackend(host="localhost", database="db", user="u", password="p")


@pytest.fixture
def async_backend():
    return AsyncMySQLBackend(host="localhost", database="db", user="u", password="p")


def _transient_operational_error(message="Lost connection to MySQL server"):
    error = OperationalError(message)
    error.transient = True
    return error


class TestExecuteErrorPhases:
    def test_transient_error_reconnects_and_retries(self, backend, monkeypatch):
        error = _transient_operational_error()
        expected = QueryResult(data=None, affected_rows=1, duration=0.0)
        attempts = []

        def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            if len(attempts) == 1:
                raise error
            return expected

        reconnects = []
        monkeypatch.setattr(ExecutionMixin, "execute", fake_execute)
        monkeypatch.setattr(backend, "_reconnect", lambda: reconnects.append(True) or True)

        result = backend.execute("SELECT 1")

        assert result is expected
        assert attempts == ["SELECT 1", "SELECT 1"]
        assert reconnects == [True]

    def test_non_transient_error_is_not_retried(self, backend, monkeypatch):
        error = OperationalError("The MySQL server is running with the --read-only option")
        error.transient = False
        attempts = []

        def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            raise error

        reconnects = []
        monkeypatch.setattr(ExecutionMixin, "execute", fake_execute)
        monkeypatch.setattr(backend, "_reconnect", lambda: reconnects.append(True) or True)

        with pytest.raises(OperationalError) as info:
            backend.execute("INSERT INTO t VALUES (1)")

        assert info.value is error
        assert attempts == ["INSERT INTO t VALUES (1)"]
        assert reconnects == []

    def test_commit_failure_raises_transaction_error(self, backend, monkeypatch):
        commit_error = RuntimeError("commit failed")
        connection = _FakeConnection(commit_error=commit_error)
        backend._connection = connection
        backend.config.autocommit = False
        monkeypatch.setattr(backend, "_get_cursor", lambda: _FakeCursor())

        with pytest.raises(TransactionError) as info:
            backend.execute(
                "INSERT INTO t VALUES (1)",
                options=ExecutionOptions(stmt_type=StatementType.DML),
            )

        assert info.value.__cause__ is commit_error
        assert connection.commit_calls == 1

    def test_execute_many_deadlock_maps_to_deadlock_error(self, backend, monkeypatch):
        deadlock = mysql_errors.OperationalError(
            msg="Deadlock found when trying to get lock; try restarting transaction",
            errno=1213,
        )
        cursor = _FakeCursor(execute_error=deadlock)
        backend._connection = _FakeConnection()
        backend.config.autocommit = False
        monkeypatch.setattr(backend, "_get_cursor", lambda: cursor)

        with pytest.raises(DeadlockError) as info:
            backend.execute_many("UPDATE t SET x = 1 WHERE id = %s", [(1,)])

        assert info.value.driver_code == 1213
        assert info.value.transient is True

    def test_execute_many_commits_after_success(self, backend, monkeypatch):
        connection = _FakeConnection()
        backend._connection = connection
        backend.config.autocommit = False
        cursor = _FakeCursor(rowcount=2)
        monkeypatch.setattr(backend, "_get_cursor", lambda: cursor)

        result = backend.execute_many("UPDATE t SET x = 1", [(1,), (2,)])

        assert result.affected_rows == 4
        assert connection.commit_calls == 1

    def test_execute_many_close_failure_keeps_original_error(self, backend, monkeypatch):
        duplicate = mysql_errors.IntegrityError(
            msg="Duplicate entry '1' for key 'PRIMARY'", errno=1062
        )
        cursor = _FakeCursor(
            execute_error=duplicate,
            close_error=RuntimeError("close failed"),
        )
        backend._connection = _FakeConnection()
        monkeypatch.setattr(backend, "_get_cursor", lambda: cursor)

        with pytest.raises(IntegrityError) as info:
            backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

        assert "Duplicate entry" in str(info.value)


class TestAsyncExecuteErrorPhases:
    @pytest.mark.asyncio
    async def test_transient_error_reconnects_and_retries(self, async_backend, monkeypatch):
        error = _transient_operational_error()
        expected = QueryResult(data=None, affected_rows=1, duration=0.0)
        attempts = []

        async def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            if len(attempts) == 1:
                raise error
            return expected

        async def fake_reconnect():
            reconnects.append(True)
            return True

        reconnects = []
        monkeypatch.setattr(AsyncExecutionMixin, "execute", fake_execute)
        monkeypatch.setattr(async_backend, "_reconnect", fake_reconnect)

        result = await async_backend.execute("SELECT 1")

        assert result is expected
        assert attempts == ["SELECT 1", "SELECT 1"]
        assert reconnects == [True]

    @pytest.mark.asyncio
    async def test_non_transient_error_is_not_retried(self, async_backend, monkeypatch):
        error = OperationalError("The MySQL server is running with the --read-only option")
        error.transient = False
        attempts = []

        async def fake_execute(self, sql, params=None, *, options=None):
            attempts.append(sql)
            raise error

        async def fake_reconnect():
            reconnects.append(True)
            return True

        reconnects = []
        monkeypatch.setattr(AsyncExecutionMixin, "execute", fake_execute)
        monkeypatch.setattr(async_backend, "_reconnect", fake_reconnect)

        with pytest.raises(OperationalError) as info:
            await async_backend.execute("INSERT INTO t VALUES (1)")

        assert info.value is error
        assert attempts == ["INSERT INTO t VALUES (1)"]
        assert reconnects == []

    @pytest.mark.asyncio
    async def test_commit_failure_raises_transaction_error(self, async_backend, monkeypatch):
        commit_error = RuntimeError("commit failed")
        connection = _FakeAsyncConnection(commit_error=commit_error)
        async_backend._connection = connection
        async_backend.config.autocommit = False

        async def fake_get_cursor():
            return _FakeAsyncCursor()

        monkeypatch.setattr(async_backend, "_get_cursor", fake_get_cursor)

        with pytest.raises(TransactionError) as info:
            await async_backend.execute(
                "INSERT INTO t VALUES (1)",
                options=ExecutionOptions(stmt_type=StatementType.DML),
            )

        assert info.value.__cause__ is commit_error
        assert connection.commit_calls == 1

    @pytest.mark.asyncio
    async def test_execute_many_deadlock_maps_to_deadlock_error(
        self, async_backend, monkeypatch
    ):
        deadlock = mysql_errors.OperationalError(
            msg="Deadlock found when trying to get lock; try restarting transaction",
            errno=1213,
        )
        cursor = _FakeAsyncCursor(execute_error=deadlock)
        async_backend._connection = _FakeAsyncConnection()
        async_backend.config.autocommit = False

        async def fake_get_cursor():
            return cursor

        monkeypatch.setattr(async_backend, "_get_cursor", fake_get_cursor)

        with pytest.raises(DeadlockError) as info:
            await async_backend.execute_many("UPDATE t SET x = 1 WHERE id = %s", [(1,)])

        assert info.value.driver_code == 1213
        assert info.value.transient is True

    @pytest.mark.asyncio
    async def test_execute_many_commits_after_success(self, async_backend, monkeypatch):
        connection = _FakeAsyncConnection()
        async_backend._connection = connection
        async_backend.config.autocommit = False
        cursor = _FakeAsyncCursor(rowcount=2)

        async def fake_get_cursor():
            return cursor

        monkeypatch.setattr(async_backend, "_get_cursor", fake_get_cursor)

        result = await async_backend.execute_many("UPDATE t SET x = 1", [(1,), (2,)])

        assert result.affected_rows == 4
        assert connection.commit_calls == 1

    @pytest.mark.asyncio
    async def test_execute_many_close_failure_keeps_original_error(
        self, async_backend, monkeypatch
    ):
        duplicate = mysql_errors.IntegrityError(
            msg="Duplicate entry '1' for key 'PRIMARY'", errno=1062
        )
        cursor = _FakeAsyncCursor(
            execute_error=duplicate,
            close_error=RuntimeError("close failed"),
        )
        async_backend._connection = _FakeAsyncConnection()

        async def fake_get_cursor():
            return cursor

        monkeypatch.setattr(async_backend, "_get_cursor", fake_get_cursor)

        with pytest.raises(IntegrityError) as info:
            await async_backend.execute_many("INSERT INTO t VALUES (%s)", [(1,)])

        assert "Duplicate entry" in str(info.value)
