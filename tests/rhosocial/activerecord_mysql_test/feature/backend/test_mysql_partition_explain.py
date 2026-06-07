# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_partition_explain.py
"""Real MySQL EXPLAIN tests for partitioned tables."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytest

from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.impl.mysql import MySQLExplainResult, MySQLExplainRow


PARTITION_EXPLAIN_TABLE = "ar_mysql_partition_explain_events"


def _drop_partition_explain_table(backend):
    backend.execute(f"DROP TABLE IF EXISTS `{PARTITION_EXPLAIN_TABLE}`")


async def _async_drop_partition_explain_table(backend):
    await backend.execute(f"DROP TABLE IF EXISTS `{PARTITION_EXPLAIN_TABLE}`")


def _create_partition_explain_table(backend):
    _drop_partition_explain_table(backend)
    backend.execute(f"""
        CREATE TABLE `{PARTITION_EXPLAIN_TABLE}` (
            id BIGINT NOT NULL,
            tenant_id BIGINT NOT NULL,
            created_at DATETIME NOT NULL,
            payload VARCHAR(255),
            KEY idx_created_at (created_at),
            KEY idx_tenant_created_at (tenant_id, created_at),
            KEY idx_id (id)
        )
        PARTITION BY RANGE COLUMNS (created_at) (
            PARTITION p2026_01 VALUES LESS THAN ('2026-02-01'),
            PARTITION p2026_02 VALUES LESS THAN ('2026-03-01'),
            PARTITION p2026_03 VALUES LESS THAN ('2026-04-01')
        )
    """)


async def _async_create_partition_explain_table(backend):
    await _async_drop_partition_explain_table(backend)
    await backend.execute(f"""
        CREATE TABLE `{PARTITION_EXPLAIN_TABLE}` (
            id BIGINT NOT NULL,
            tenant_id BIGINT NOT NULL,
            created_at DATETIME NOT NULL,
            payload VARCHAR(255),
            KEY idx_created_at (created_at),
            KEY idx_tenant_created_at (tenant_id, created_at),
            KEY idx_id (id)
        )
        PARTITION BY RANGE COLUMNS (created_at) (
            PARTITION p2026_01 VALUES LESS THAN ('2026-02-01'),
            PARTITION p2026_02 VALUES LESS THAN ('2026-03-01'),
            PARTITION p2026_03 VALUES LESS THAN ('2026-04-01')
        )
    """)


def _seed_partition_explain_rows(backend):
    backend.execute(
        f"""
        INSERT INTO `{PARTITION_EXPLAIN_TABLE}` (id, tenant_id, created_at, payload)
        VALUES (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s)
        """,
        (
            1,
            100,
            datetime(2026, 1, 15),
            "jan",
            2,
            100,
            datetime(2026, 2, 15),
            "feb",
            3,
            200,
            datetime(2026, 3, 15),
            "mar",
        ),
    )


async def _async_seed_partition_explain_rows(backend):
    await backend.execute(
        f"""
        INSERT INTO `{PARTITION_EXPLAIN_TABLE}` (id, tenant_id, created_at, payload)
        VALUES (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s)
        """,
        (
            1,
            100,
            datetime(2026, 1, 15),
            "jan",
            2,
            100,
            datetime(2026, 2, 15),
            "feb",
            3,
            200,
            datetime(2026, 3, 15),
            "mar",
        ),
    )


def _split_partitions(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [partition.strip() for partition in str(value).split(",") if partition.strip()]


def _collect_explain_partitions(result: MySQLExplainResult) -> list[str]:
    partitions: list[str] = []
    for row in result.rows:
        partitions.extend(_split_partitions(row.partitions))
    return partitions


def _assert_explain_result_shape(result: MySQLExplainResult):
    assert isinstance(result, MySQLExplainResult)
    assert result.rows
    assert all(isinstance(row, MySQLExplainRow) for row in result.rows)
    assert all(hasattr(row, "partitions") for row in result.rows)


def _assert_partition_pruning(result: MySQLExplainResult, expected_partition: str):
    _assert_explain_result_shape(result)
    partitions = _collect_explain_partitions(result)
    assert expected_partition in partitions


@pytest.fixture
def mysql_partition_explain_backend(mysql_backend):
    """Create a real partitioned table for EXPLAIN tests."""
    _create_partition_explain_table(mysql_backend)
    _seed_partition_explain_rows(mysql_backend)
    yield mysql_backend
    _drop_partition_explain_table(mysql_backend)


@pytest.fixture
async def async_mysql_partition_explain_backend(async_mysql_backend):
    """Create a real partitioned table for async EXPLAIN tests."""
    await _async_create_partition_explain_table(async_mysql_backend)
    await _async_seed_partition_explain_rows(async_mysql_backend)
    yield async_mysql_backend
    await _async_drop_partition_explain_table(async_mysql_backend)


class TestMySQLPartitionExplain:
    """Synchronous EXPLAIN tests for MySQL partition pruning."""

    def test_explain_partition_pruning_returns_expected_partition(
        self,
        mysql_partition_explain_backend,
    ):
        """Range predicate on partition key should expose the pruned partition."""
        dialect = mysql_partition_explain_backend.dialect
        expr = RawSQLExpression(
            dialect,
            f"""
            SELECT * FROM `{PARTITION_EXPLAIN_TABLE}`
            WHERE created_at >= '2026-02-01' AND created_at < '2026-03-01'
            """,
        )

        result = mysql_partition_explain_backend.explain(expr)

        _assert_partition_pruning(result, "p2026_02")

    def test_explain_full_scan_exposes_partition_scope_when_available(
        self,
        mysql_partition_explain_backend,
    ):
        """Full table scan may report all partitions or NULL depending on MySQL version."""
        dialect = mysql_partition_explain_backend.dialect
        result = mysql_partition_explain_backend.explain(
            RawSQLExpression(dialect, f"SELECT * FROM `{PARTITION_EXPLAIN_TABLE}`")
        )

        _assert_explain_result_shape(result)
        partitions = _collect_explain_partitions(result)
        if partitions:
            assert {"p2026_01", "p2026_02"}.issubset(set(partitions))

    def test_explain_row_exposes_partitions_attribute(self, mysql_partition_explain_backend):
        """MySQLExplainRow should retain the native EXPLAIN partitions field."""
        dialect = mysql_partition_explain_backend.dialect
        result = mysql_partition_explain_backend.explain(
            RawSQLExpression(
                dialect,
                f"""
                SELECT * FROM `{PARTITION_EXPLAIN_TABLE}`
                WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01'
                """,
            )
        )

        _assert_explain_result_shape(result)
        assert all(
            row.partitions is None or isinstance(row.partitions, str)
            for row in result.rows
        )


class TestAsyncMySQLPartitionExplain:
    """Asynchronous EXPLAIN tests for MySQL partition pruning."""

    @pytest.mark.asyncio
    async def test_explain_partition_pruning_returns_expected_partition(
        self,
        async_mysql_partition_explain_backend,
    ):
        """Range predicate on partition key should expose the pruned partition."""
        dialect = async_mysql_partition_explain_backend.dialect
        expr = RawSQLExpression(
            dialect,
            f"""
            SELECT * FROM `{PARTITION_EXPLAIN_TABLE}`
            WHERE created_at >= '2026-02-01' AND created_at < '2026-03-01'
            """,
        )

        result = await async_mysql_partition_explain_backend.explain(expr)

        _assert_partition_pruning(result, "p2026_02")

    @pytest.mark.asyncio
    async def test_explain_full_scan_exposes_partition_scope_when_available(
        self,
        async_mysql_partition_explain_backend,
    ):
        """Full table scan may report all partitions or NULL depending on MySQL version."""
        dialect = async_mysql_partition_explain_backend.dialect
        result = await async_mysql_partition_explain_backend.explain(
            RawSQLExpression(dialect, f"SELECT * FROM `{PARTITION_EXPLAIN_TABLE}`")
        )

        _assert_explain_result_shape(result)
        partitions = _collect_explain_partitions(result)
        if partitions:
            assert {"p2026_01", "p2026_02"}.issubset(set(partitions))

    @pytest.mark.asyncio
    async def test_explain_row_exposes_partitions_attribute(
        self,
        async_mysql_partition_explain_backend,
    ):
        """MySQLExplainRow should retain the native EXPLAIN partitions field."""
        dialect = async_mysql_partition_explain_backend.dialect
        result = await async_mysql_partition_explain_backend.explain(
            RawSQLExpression(
                dialect,
                f"""
                SELECT * FROM `{PARTITION_EXPLAIN_TABLE}`
                WHERE created_at >= '2026-01-01' AND created_at < '2026-02-01'
                """,
            )
        )

        _assert_explain_result_shape(result)
        assert all(
            row.partitions is None or isinstance(row.partitions, str)
            for row in result.rows
        )
