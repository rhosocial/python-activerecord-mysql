# tests/rhosocial/activerecord_mysql_test/feature/backend/introspection/test_introspection_partitions.py
"""Tests for MySQL partition introspection.

``list_partitions`` answers from ``information_schema.PARTITIONS``. A
partitioned table reports one row per partition (one per partition and
subpartition pair, when subpartitioned); a table that is not partitioned
has only a NULL-named row, which is filtered out so an empty list means
exactly "not partitioned".
"""

from typing import Any, Dict, List, Tuple

import pytest

from rhosocial.activerecord.backend.impl.mysql.introspection.types import (
    MySQLPartitionInfo,
)
from rhosocial.activerecord.backend.introspection.executor import (
    AsyncIntrospectorExecutor,
    SyncIntrospectorExecutor,
)

from mysql_live_server import mysql_server_available

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)

PARTITIONED_TABLE = "partitioned_events"


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


class TestListPartitions:
    """Tests for list_partitions against a live server."""

    def test_returns_typed_partitions(self, backend_with_partitioned_table):
        partitions = backend_with_partitioned_table.introspector.list_partitions(
            PARTITIONED_TABLE
        )

        assert len(partitions) == 3
        assert all(isinstance(partition, MySQLPartitionInfo) for partition in partitions)
        assert [p.partition_name for p in partitions] == ["p2020", "p2021", "p_max"]

    def test_reports_method_expression_and_ordinals(self, backend_with_partitioned_table):
        partitions = backend_with_partitioned_table.introspector.list_partitions(
            PARTITIONED_TABLE
        )

        assert [p.partition_method for p in partitions] == ["RANGE"] * 3
        assert [p.partition_ordinal_position for p in partitions] == [1, 2, 3]
        for partition in partitions:
            assert partition.partition_expression
            assert "YEAR" in partition.partition_expression.upper()
            assert "created_at" in partition.partition_expression
            assert partition.schema == backend_with_partitioned_table.config.database
            assert partition.table_name == PARTITIONED_TABLE

    def test_reports_boundaries_and_sizes(self, backend_with_partitioned_table):
        partitions = backend_with_partitioned_table.introspector.list_partitions(
            PARTITIONED_TABLE
        )

        assert [p.partition_description for p in partitions] == [
            "2021",
            "2022",
            "MAXVALUE",
        ]
        for partition in partitions:
            assert partition.table_rows is None or isinstance(partition.table_rows, int)
            assert partition.data_length is None or isinstance(partition.data_length, int)
            assert partition.index_length is None or isinstance(partition.index_length, int)

    def test_non_partitioned_table_returns_empty(self, backend_with_tables):
        tables = backend_with_tables.introspector.list_tables()
        assert "users" in {table.name for table in tables}

        assert backend_with_tables.introspector.list_partitions("users") == []

    def test_missing_table_returns_empty(self, backend_with_tables):
        assert (
            backend_with_tables.introspector.list_partitions(
                "partitions_does_not_exist"
            )
            == []
        )

    def test_cache_returns_the_same_list(self, backend_with_partitioned_table):
        first = backend_with_partitioned_table.introspector.list_partitions(
            PARTITIONED_TABLE
        )
        second = backend_with_partitioned_table.introspector.list_partitions(
            PARTITIONED_TABLE
        )

        assert first is second

    def test_warm_cache_asks_the_server_nothing(self, backend_with_partitioned_table):
        introspector = backend_with_partitioned_table.introspector
        introspector.clear_cache()
        executor = CountingExecutor(backend_with_partitioned_table)
        introspector._executor = executor

        introspector.list_partitions(PARTITIONED_TABLE)
        cold = executor.calls
        introspector.list_partitions(PARTITIONED_TABLE)

        assert cold > 0
        assert executor.calls == cold


class TestAsyncListPartitions:
    """Async tests for partition introspection."""

    @pytest.mark.asyncio
    async def test_returns_typed_partitions(self, async_backend_with_partitioned_table):
        partitions = await async_backend_with_partitioned_table.introspector.list_partitions(
            PARTITIONED_TABLE
        )

        assert len(partitions) == 3
        assert all(isinstance(partition, MySQLPartitionInfo) for partition in partitions)
        assert [p.partition_name for p in partitions] == ["p2020", "p2021", "p_max"]
        assert [p.partition_ordinal_position for p in partitions] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_non_partitioned_table_returns_empty(self, async_backend_with_tables):
        partitions = await async_backend_with_tables.introspector.list_partitions("users")

        assert partitions == []

    @pytest.mark.asyncio
    async def test_warm_cache_asks_the_server_nothing(self, async_backend_with_partitioned_table):
        introspector = async_backend_with_partitioned_table.introspector
        introspector.clear_cache()
        executor = AsyncCountingExecutor(async_backend_with_partitioned_table)
        introspector._executor = executor

        await introspector.list_partitions(PARTITIONED_TABLE)
        cold = executor.calls
        await introspector.list_partitions(PARTITIONED_TABLE)

        assert cold > 0
        assert executor.calls == cold
