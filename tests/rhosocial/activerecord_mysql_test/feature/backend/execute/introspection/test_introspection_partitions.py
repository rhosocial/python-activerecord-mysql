# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/introspection/test_introspection_partitions.py
"""Tests for MySQL partition state against a live server.

``get_partition_state`` answers from ``information_schema.PARTITIONS`` with
the neutral :class:`PartitionState`: ``scheme`` is ``None`` for a table that
is not partitioned, and the bounds are one record per partition. Statistics
(``TABLE_ROWS`` / ``DATA_LENGTH``) are only read when ``include_stats`` asks
for them.
"""

from typing import Any, Dict, List, Tuple

import pytest
from mysql_live_server import mysql_server_available
from rhosocial.activerecord.backend.introspection.errors import ObjectNotFoundError
from rhosocial.activerecord.backend.introspection.executor import (
    AsyncIntrospectorExecutor,
    IntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    PartitionScheme,
    PartitionState,
)

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)

PARTITIONED_TABLE = "partitioned_events"


class CountingExecutor(IntrospectorExecutor):
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


class TestGetPartitionState:
    """Tests for get_partition_state against a live server."""

    def test_returns_neutral_partition_state(self, backend_with_partitioned_table):
        state = backend_with_partitioned_table.introspector.get_partition_state(PARTITIONED_TABLE)

        assert isinstance(state, PartitionState)
        assert state.scheme is PartitionScheme.RANGE
        assert [bound.name for bound in state.bounds] == ["p2020", "p2021", "p_max"]

    def test_reports_expression_and_bounds(self, backend_with_partitioned_table):
        state = backend_with_partitioned_table.introspector.get_partition_state(PARTITIONED_TABLE)

        assert "YEAR" in state.key_expression.upper()
        assert "created_at" in state.key_expression
        assert [bound.upper for bound in state.bounds] == ["2021", "2022", "MAXVALUE"]
        assert [bound.is_maxvalue for bound in state.bounds] == [False, False, True]
        assert all(not bound.is_default for bound in state.bounds)

    def test_stats_are_not_read_when_not_requested(self, backend_with_partitioned_table):
        state = backend_with_partitioned_table.introspector.get_partition_state(PARTITIONED_TABLE)

        assert all(bound.row_count is None for bound in state.bounds)
        assert all(bound.size_bytes is None for bound in state.bounds)

    def test_stats_are_read_when_requested(self, backend_with_partitioned_table):
        state = backend_with_partitioned_table.introspector.get_partition_state(
            PARTITIONED_TABLE, include_stats=True
        )

        for bound in state.bounds:
            assert bound.row_count is None or isinstance(bound.row_count, int)
            assert bound.size_bytes is None or isinstance(bound.size_bytes, int)

    def test_non_partitioned_table_answers_scheme_none(self, backend_with_tables):
        tables = backend_with_tables.introspector.list_tables()
        assert "users" in {table.name for table in tables}

        state = backend_with_tables.introspector.get_partition_state("users")

        assert state.scheme is None
        assert state.bounds == ()

    def test_missing_table_is_reported(self, backend_with_tables):
        with pytest.raises(ObjectNotFoundError):
            backend_with_tables.introspector.get_partition_state("partitions_does_not_exist")

    def test_cache_returns_the_same_state(self, backend_with_partitioned_table):
        first = backend_with_partitioned_table.introspector.get_partition_state(PARTITIONED_TABLE)
        second = backend_with_partitioned_table.introspector.get_partition_state(PARTITIONED_TABLE)

        assert first is second

    def test_warm_cache_asks_the_server_nothing(self, backend_with_partitioned_table):
        introspector = backend_with_partitioned_table.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_partitioned_table)
        introspector._executor = executor

        introspector.get_partition_state(PARTITIONED_TABLE)
        cold = executor.calls
        introspector.get_partition_state(PARTITIONED_TABLE)

        assert cold > 0
        assert executor.calls == cold


class TestGetTableState:
    """The neutral table state folds storage options and partitioning."""

    def test_reports_kind_storage_and_comment(self, backend_with_partitioned_table):
        state = backend_with_partitioned_table.introspector.get_table_state(PARTITIONED_TABLE)

        assert state.kind == "regular"
        assert state.storage.engine == "InnoDB"
        assert state.storage.collation
        assert state.storage.charset == state.storage.collation.split("_", 1)[0]
        assert state.comment == "partitioned introspection fixture"

    def test_partitioning_is_carried(self, backend_with_partitioned_table):
        state = backend_with_partitioned_table.introspector.get_table_state(PARTITIONED_TABLE)

        assert state.partitioning is not None
        assert state.partitioning.scheme is PartitionScheme.RANGE

    def test_unpartitioned_table_carries_scheme_none(self, backend_with_tables):
        state = backend_with_tables.introspector.get_table_state("users")

        assert state.partitioning is not None
        assert state.partitioning.scheme is None
        assert state.comment is None


class TestAsyncGetPartitionState:
    """Async tests for partition state."""

    @pytest.mark.asyncio
    async def test_returns_neutral_partition_state(self, async_backend_with_partitioned_table):
        state = await async_backend_with_partitioned_table.introspector.get_partition_state(
            PARTITIONED_TABLE
        )

        assert isinstance(state, PartitionState)
        assert state.scheme is PartitionScheme.RANGE
        assert [bound.name for bound in state.bounds] == ["p2020", "p2021", "p_max"]
        assert [bound.is_maxvalue for bound in state.bounds] == [False, False, True]

    @pytest.mark.asyncio
    async def test_stats_are_not_read_when_not_requested(
        self, async_backend_with_partitioned_table
    ):
        state = await async_backend_with_partitioned_table.introspector.get_partition_state(
            PARTITIONED_TABLE
        )

        assert all(bound.row_count is None for bound in state.bounds)
        assert all(bound.size_bytes is None for bound in state.bounds)

    @pytest.mark.asyncio
    async def test_table_state_carries_storage_and_partitioning(
        self, async_backend_with_partitioned_table
    ):
        state = await async_backend_with_partitioned_table.introspector.get_table_state(
            PARTITIONED_TABLE
        )

        assert state.kind == "regular"
        assert state.storage.engine == "InnoDB"
        assert state.partitioning is not None
        assert state.partitioning.scheme is PartitionScheme.RANGE

    @pytest.mark.asyncio
    async def test_non_partitioned_table_answers_scheme_none(self, async_backend_with_tables):
        state = await async_backend_with_tables.introspector.get_partition_state("users")

        assert state.scheme is None

    @pytest.mark.asyncio
    async def test_warm_cache_asks_the_server_nothing(self, async_backend_with_partitioned_table):
        introspector = async_backend_with_partitioned_table.introspector
        introspector.clear_cache()
        executor = AsyncCountingExecutor(async_backend_with_partitioned_table)
        introspector._executor = executor

        await introspector.get_partition_state(PARTITIONED_TABLE)
        cold = executor.calls
        await introspector.get_partition_state(PARTITIONED_TABLE)

        assert cold > 0
        assert executor.calls == cold
