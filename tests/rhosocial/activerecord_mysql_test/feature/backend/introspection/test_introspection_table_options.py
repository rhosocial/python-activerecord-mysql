# tests/rhosocial/activerecord_mysql_test/feature/backend/introspection/test_introspection_table_options.py
"""Tests for MySQL table storage-options introspection.

``list_table_options`` / ``get_table_options`` answer from
``information_schema.TABLES``: engine, row format, collation, the
self-managed auto-increment counter, comment, extra create options and the
server's data/index byte accounting. These are MySQL-only questions with
no cross-backend type, so the results are the typed
:class:`MySQLTableOptions` records rather than plain dicts.
"""

from dataclasses import FrozenInstanceError
from typing import Any, Dict, List, Tuple

import pytest

from rhosocial.activerecord.backend.impl.mysql.introspection.types import (
    MySQLTableOptions,
)
from rhosocial.activerecord.backend.introspection.executor import (
    AsyncIntrospectorExecutor,
    SyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

from mysql_live_server import mysql_server_available

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)


class CountingExecutor(SyncIntrospectorExecutor):
    """An executor that reports how many questions it was asked."""

    def __init__(self, backend: Any) -> None:
        super().__init__(backend)
        self.calls = 0

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        return super().execute(sql, params)


class AsyncCountingExecutor(AsyncIntrospectorExecutor):
    """The async counterpart of :class:`CountingExecutor`."""

    def __init__(self, backend: Any) -> None:
        super().__init__(backend)
        self.calls = 0

    async def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        return await super().execute(sql, params)


class TestListTableOptions:
    """Tests for list_table_options against a live server."""

    def test_returns_typed_non_empty_results(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()

        assert options
        assert all(isinstance(option, MySQLTableOptions) for option in options)
        names = {option.table_name for option in options}
        assert "users" in names

    def test_reports_storage_fields_for_users(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()
        users = next(option for option in options if option.table_name == "users")

        assert users.schema == backend_with_tables.config.database
        assert users.engine == "InnoDB"
        assert users.row_format
        assert users.table_collation
        assert users.table_comment is not None
        assert isinstance(users.data_length, int)
        assert isinstance(users.index_length, int)
        assert users.total_length == users.data_length + users.index_length

    def test_result_is_frozen(self, backend_with_tables):
        options = backend_with_tables.introspector.list_table_options()
        with pytest.raises(FrozenInstanceError):
            options[0].engine = "MyISAM"  # type: ignore[misc]

    def test_cache_returns_the_same_list(self, backend_with_tables):
        first = backend_with_tables.introspector.list_table_options()
        second = backend_with_tables.introspector.list_table_options()

        assert first is second

    def test_warm_cache_asks_the_server_nothing(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.list_table_options()
        cold = executor.calls
        introspector.list_table_options()

        assert cold > 0
        assert executor.calls == cold


class TestGetTableOptions:
    """Tests for get_table_options against a live server."""

    def test_returns_typed_result(self, backend_with_tables):
        options = backend_with_tables.introspector.get_table_options("users")

        assert isinstance(options, MySQLTableOptions)
        assert options.table_name == "users"
        assert options.engine == "InnoDB"

    def test_missing_table_returns_none(self, backend_with_tables):
        assert (
            backend_with_tables.introspector.get_table_options(
                "table_options_does_not_exist"
            )
            is None
        )

    def test_cache_returns_the_same_record(self, backend_with_tables):
        first = backend_with_tables.introspector.get_table_options("users")
        second = backend_with_tables.introspector.get_table_options("users")

        assert first is second

    def test_warm_cache_asks_the_server_nothing(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.get_table_options("users")
        cold = executor.calls
        introspector.get_table_options("users")

        assert cold > 0
        assert executor.calls == cold

    def test_invalidating_the_table_drops_the_record(self, backend_with_tables):
        introspector = backend_with_tables.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_tables)
        introspector._executor = executor

        introspector.get_table_options("users")
        cold = executor.calls
        introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")
        introspector.get_table_options("users")

        assert executor.calls > cold


class TestAsyncTableOptions:
    """Async tests for table storage-options introspection."""

    @pytest.mark.asyncio
    async def test_returns_typed_non_empty_results(self, async_backend_with_tables):
        options = await async_backend_with_tables.introspector.list_table_options()

        assert options
        assert all(isinstance(option, MySQLTableOptions) for option in options)
        assert "users" in {option.table_name for option in options}

    @pytest.mark.asyncio
    async def test_returns_typed_record(self, async_backend_with_tables):
        options = await async_backend_with_tables.introspector.get_table_options("users")

        assert isinstance(options, MySQLTableOptions)
        assert options.engine == "InnoDB"

    @pytest.mark.asyncio
    async def test_missing_table_returns_none(self, async_backend_with_tables):
        options = await async_backend_with_tables.introspector.get_table_options(
            "table_options_does_not_exist"
        )

        assert options is None

    @pytest.mark.asyncio
    async def test_warm_cache_asks_the_server_nothing(self, async_backend_with_tables):
        introspector = async_backend_with_tables.introspector
        introspector.clear_cache()
        executor = AsyncCountingExecutor(async_backend_with_tables)
        introspector._executor = executor

        await introspector.list_table_options()
        await introspector.get_table_options("users")
        cold = executor.calls
        await introspector.list_table_options()
        await introspector.get_table_options("users")

        assert cold > 0
        assert executor.calls == cold
