# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_partition_operations.py
"""Real MySQL partition operation tests."""

from datetime import datetime
from typing import Any, List, Sequence

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    FunctionCall,
    IndexDefinition,
    InsertExpression,
    Literal,
    LogicalPredicate,
    OrderByClause,
    QueryExpression,
    TableExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql import ShowCreateTableExpression
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLAddPartitionExpression,
    MySQLDropPartitionExpression,
    MySQLPartitionByRangeColumns,
    MySQLPartitionDefinition,
    MySQLPartitionValue,
    MySQLReorganizePartitionExpression,
    MySQLTruncatePartitionExpression,
)


PARTITION_TABLE = "ar_mysql_partition_events"


def _drop_table_expression(dialect):
    return DropTableExpression(dialect=dialect, table=PARTITION_TABLE, if_exists=True)


def _base_partition_definitions(dialect: MySQLDialect) -> List[MySQLPartitionDefinition]:
    return [
        MySQLPartitionDefinition(
            name="p2026_01",
            less_than=[MySQLPartitionValue(dialect, "2026-02-01")],
        ),
        MySQLPartitionDefinition(
            name="p2026_02",
            less_than=[MySQLPartitionValue(dialect, "2026-03-01")],
        ),
    ]


def _create_partitioned_table_expression(dialect):
    return CreateTableExpression(
        dialect=dialect,
        table=PARTITION_TABLE,
        columns=[
            ColumnDefinition("id", "BIGINT NOT NULL"),
            ColumnDefinition("created_at", "DATETIME NOT NULL"),
            ColumnDefinition("payload", "VARCHAR(255)"),
        ],
        indexes=[
            IndexDefinition(name="idx_created_at", columns=["created_at"]),
            IndexDefinition(name="idx_id", columns=["id"]),
        ],
        partition=MySQLPartitionByRangeColumns(
            dialect=dialect,
            keys=[Column(dialect, "created_at")],
            partitions=_base_partition_definitions(dialect),
        ),
    )


def _insert_events_expression(dialect, rows):
    return InsertExpression(
        dialect=dialect,
        into=PARTITION_TABLE,
        columns=["id", "created_at", "payload"],
        source=ValuesSource(
            dialect,
            [[Literal(dialect, value) for value in row] for row in rows],
        ),
    )


def _select_payloads_expression(dialect):
    return QueryExpression(
        dialect,
        select=[Column(dialect, "payload")],
        from_=TableExpression(dialect, PARTITION_TABLE),
        order_by=OrderByClause(dialect, [(Column(dialect, "id"), "ASC")]),
    )


def _select_payload_by_id_expression(dialect, row_id):
    return QueryExpression(
        dialect,
        select=[Column(dialect, "payload")],
        from_=TableExpression(dialect, PARTITION_TABLE),
        where=Column(dialect, "id") == Literal(dialect, row_id),
    )


def _partition_names_expression(dialect):
    partitions = TableExpression(dialect, "PARTITIONS", schema_name="information_schema")
    return QueryExpression(
        dialect,
        select=[Column(dialect, "PARTITION_NAME", alias="name")],
        from_=partitions,
        where=LogicalPredicate(
            dialect,
            "AND",
            Column(dialect, "TABLE_SCHEMA") == FunctionCall(dialect, "DATABASE"),
            Column(dialect, "TABLE_NAME") == Literal(dialect, PARTITION_TABLE),
            Column(dialect, "PARTITION_NAME").is_not_null(),
        ),
        order_by=OrderByClause(dialect, [(Column(dialect, "PARTITION_NAME"), "ASC")]),
    )


def _partition_metadata_expression(dialect):
    partitions = TableExpression(dialect, "PARTITIONS", schema_name="information_schema")
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "PARTITION_NAME", alias="name"),
            Column(dialect, "PARTITION_METHOD", alias="method"),
            Column(dialect, "PARTITION_EXPRESSION", alias="expression"),
            Column(dialect, "PARTITION_DESCRIPTION", alias="description"),
            Column(dialect, "TABLE_ROWS", alias="table_rows"),
            Column(dialect, "DATA_LENGTH", alias="data_length"),
            Column(dialect, "INDEX_LENGTH", alias="index_length"),
        ],
        from_=partitions,
        where=LogicalPredicate(
            dialect,
            "AND",
            Column(dialect, "TABLE_SCHEMA") == FunctionCall(dialect, "DATABASE"),
            Column(dialect, "TABLE_NAME") == Literal(dialect, PARTITION_TABLE),
            Column(dialect, "PARTITION_NAME").is_not_null(),
        ),
        order_by=OrderByClause(dialect, [(Column(dialect, "PARTITION_NAME"), "ASC")]),
    )


def _add_future_partition_expression(dialect):
    return MySQLAddPartitionExpression(
        dialect=dialect,
        table=PARTITION_TABLE,
        partitions=[
            MySQLPartitionDefinition(
                name="p2026_03",
                less_than=[MySQLPartitionValue(dialect, "2026-04-01")],
            )
        ],
    )


def _drop_partition_expression(dialect, partition):
    return MySQLDropPartitionExpression(dialect, PARTITION_TABLE, [partition])


def _truncate_partition_expression(dialect, partition):
    return MySQLTruncatePartitionExpression(dialect, PARTITION_TABLE, [partition])


def _reorganize_partition_expression(dialect):
    return MySQLReorganizePartitionExpression(
        dialect=dialect,
        table=PARTITION_TABLE,
        partition="p2026_02",
        into=[
            MySQLPartitionDefinition(
                name="p2026_02a",
                less_than=[MySQLPartitionValue(dialect, "2026-02-15")],
            ),
            MySQLPartitionDefinition(
                name="p2026_02b",
                less_than=[MySQLPartitionValue(dialect, "2026-03-01")],
            ),
        ],
    )


def _drop_table(backend):
    backend.execute(*_drop_table_expression(backend.dialect).to_sql())


async def _async_drop_table(backend):
    await backend.execute(*_drop_table_expression(backend.dialect).to_sql())


def _create_partitioned_table(backend):
    _drop_table(backend)
    backend.execute(*_create_partitioned_table_expression(backend.dialect).to_sql())


async def _async_create_partitioned_table(backend):
    await _async_drop_table(backend)
    await backend.execute(*_create_partitioned_table_expression(backend.dialect).to_sql())


def _partition_names(backend):
    rows = backend.fetch_all(*_partition_names_expression(backend.dialect).to_sql())
    return [row["name"] for row in rows]


async def _async_partition_names(backend):
    rows = await backend.fetch_all(*_partition_names_expression(backend.dialect).to_sql())
    return [row["name"] for row in rows]


def _partition_metadata(backend):
    return backend.fetch_all(*_partition_metadata_expression(backend.dialect).to_sql())


async def _async_partition_metadata(backend):
    return await backend.fetch_all(*_partition_metadata_expression(backend.dialect).to_sql())


def _assert_base_partition_metadata(rows):
    assert [row["name"] for row in rows] == ["p2026_01", "p2026_02"]

    by_name = {row["name"]: row for row in rows}
    for row in rows:
        assert "RANGE" in str(row["method"]).upper()
        assert "created_at" in str(row["expression"]).lower()
        assert "table_rows" in row
        assert "data_length" in row
        assert "index_length" in row

    assert "2026-02-01" in str(by_name["p2026_01"]["description"])
    assert "2026-03-01" in str(by_name["p2026_02"]["description"])


def _show_create_table_sql(backend):
    row = backend.fetch_one(*ShowCreateTableExpression(backend.dialect, PARTITION_TABLE).to_sql())
    return row.get("Create Table") or row.get("create table")


async def _async_show_create_table_sql(backend):
    row = await backend.fetch_one(*ShowCreateTableExpression(backend.dialect, PARTITION_TABLE).to_sql())
    return row.get("Create Table") or row.get("create table")


def _assert_show_create_table_includes_partition_definition(create_sql):
    assert create_sql
    upper_sql = create_sql.upper()
    lower_sql = create_sql.lower()

    assert "PARTITION BY RANGE" in upper_sql
    assert "created_at" in lower_sql
    assert "p2026_01" in create_sql
    assert "p2026_02" in create_sql
    assert "VALUES LESS THAN" in upper_sql
    assert "2026-02-01" in create_sql
    assert "2026-03-01" in create_sql


@pytest.fixture
def mysql_partitioned_table(mysql_backend):
    """Create a real RANGE-partitioned MySQL table."""
    _create_partitioned_table(mysql_backend)
    yield PARTITION_TABLE
    _drop_table(mysql_backend)


@pytest.fixture
async def async_mysql_partitioned_table(async_mysql_backend):
    """Create a real RANGE-partitioned MySQL table asynchronously."""
    await _async_create_partitioned_table(async_mysql_backend)
    yield PARTITION_TABLE
    await _async_drop_table(async_mysql_backend)


class TestMySQLPartitionOperations:
    """Synchronous real backend tests for MySQL partition operations."""

    def test_create_range_partitioned_table(self, mysql_backend, mysql_partitioned_table):
        """information_schema.PARTITIONS should expose created partitions."""
        assert mysql_partitioned_table == PARTITION_TABLE
        assert _partition_names(mysql_backend) == ["p2026_01", "p2026_02"]

    def test_partition_metadata_contains_strategy_key_and_bounds(self, mysql_backend, mysql_partitioned_table):
        """information_schema.PARTITIONS should expose strategy, key, and bounds."""
        _assert_base_partition_metadata(_partition_metadata(mysql_backend))

    def test_show_create_table_includes_partition_definition(self, mysql_backend, mysql_partitioned_table):
        """SHOW CREATE TABLE should include the native partition definition."""
        _assert_show_create_table_includes_partition_definition(_show_create_table_sql(mysql_backend))

    def test_insert_across_partitions_and_query(self, mysql_backend, mysql_partitioned_table):
        """Rows inserted across ranges should remain queryable through parent table."""
        insert = _insert_events_expression(
            mysql_backend.dialect,
            [
                [1, datetime(2026, 1, 15), "jan"],
                [2, datetime(2026, 2, 15), "feb"],
            ],
        )
        mysql_backend.execute(*insert.to_sql())

        rows = mysql_backend.fetch_all(*_select_payloads_expression(mysql_backend.dialect).to_sql())
        assert [row["payload"] for row in rows] == ["jan", "feb"]

    def test_add_partition_for_future_range(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE ADD PARTITION should allow future range inserts."""
        mysql_backend.execute(*_add_future_partition_expression(mysql_backend.dialect).to_sql())
        mysql_backend.execute(
            *_insert_events_expression(
                mysql_backend.dialect,
                [[3, datetime(2026, 3, 15), "mar"]],
            ).to_sql()
        )

        assert _partition_names(mysql_backend) == ["p2026_01", "p2026_02", "p2026_03"]
        row = mysql_backend.fetch_one(*_select_payload_by_id_expression(mysql_backend.dialect, 3).to_sql())
        assert row["payload"] == "mar"

    def test_drop_partition(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE DROP PARTITION should remove the partition and its rows."""
        mysql_backend.execute(
            *_insert_events_expression(
                mysql_backend.dialect,
                [
                    [1, datetime(2026, 1, 15), "jan"],
                    [2, datetime(2026, 2, 15), "feb"],
                ],
            ).to_sql()
        )
        mysql_backend.execute(*_drop_partition_expression(mysql_backend.dialect, "p2026_01").to_sql())

        assert _partition_names(mysql_backend) == ["p2026_02"]
        rows = mysql_backend.fetch_all(*_select_payloads_expression(mysql_backend.dialect).to_sql())
        assert [row["payload"] for row in rows] == ["feb"]

    def test_truncate_partition(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE TRUNCATE PARTITION should clear one range only."""
        mysql_backend.execute(
            *_insert_events_expression(
                mysql_backend.dialect,
                [
                    [1, datetime(2026, 1, 15), "jan"],
                    [2, datetime(2026, 2, 15), "feb"],
                ],
            ).to_sql()
        )
        mysql_backend.execute(*_truncate_partition_expression(mysql_backend.dialect, "p2026_01").to_sql())

        rows = mysql_backend.fetch_all(*_select_payloads_expression(mysql_backend.dialect).to_sql())
        assert [row["payload"] for row in rows] == ["feb"]

    def test_reorganize_partition(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE REORGANIZE PARTITION should split an existing range."""
        mysql_backend.execute(*_reorganize_partition_expression(mysql_backend.dialect).to_sql())

        assert _partition_names(mysql_backend) == ["p2026_01", "p2026_02a", "p2026_02b"]


class TestAsyncMySQLPartitionOperations:
    """Asynchronous real backend tests for MySQL partition operations."""

    @pytest.mark.asyncio
    async def test_create_range_partitioned_table(
        self,
        async_mysql_backend,
        async_mysql_partitioned_table,
    ):
        """information_schema.PARTITIONS should expose created partitions."""
        assert async_mysql_partitioned_table == PARTITION_TABLE
        assert await _async_partition_names(async_mysql_backend) == ["p2026_01", "p2026_02"]

    @pytest.mark.asyncio
    async def test_partition_metadata_contains_strategy_key_and_bounds(
        self,
        async_mysql_backend,
        async_mysql_partitioned_table,
    ):
        """information_schema.PARTITIONS should expose strategy, key, and bounds."""
        _assert_base_partition_metadata(await _async_partition_metadata(async_mysql_backend))

    @pytest.mark.asyncio
    async def test_show_create_table_includes_partition_definition(
        self,
        async_mysql_backend,
        async_mysql_partitioned_table,
    ):
        """SHOW CREATE TABLE should include the native partition definition."""
        create_sql = await _async_show_create_table_sql(async_mysql_backend)
        _assert_show_create_table_includes_partition_definition(create_sql)

    @pytest.mark.asyncio
    async def test_insert_across_partitions_and_query(
        self,
        async_mysql_backend,
        async_mysql_partitioned_table,
    ):
        """Rows inserted across ranges should remain queryable through parent table."""
        insert = _insert_events_expression(
            async_mysql_backend.dialect,
            [
                [1, datetime(2026, 1, 15), "jan"],
                [2, datetime(2026, 2, 15), "feb"],
            ],
        )
        await async_mysql_backend.execute(*insert.to_sql())

        rows = await async_mysql_backend.fetch_all(*_select_payloads_expression(async_mysql_backend.dialect).to_sql())
        assert [row["payload"] for row in rows] == ["jan", "feb"]

    @pytest.mark.asyncio
    async def test_add_partition_for_future_range(
        self,
        async_mysql_backend,
        async_mysql_partitioned_table,
    ):
        """ALTER TABLE ADD PARTITION should allow future range inserts."""
        await async_mysql_backend.execute(*_add_future_partition_expression(async_mysql_backend.dialect).to_sql())
        await async_mysql_backend.execute(
            *_insert_events_expression(
                async_mysql_backend.dialect,
                [[3, datetime(2026, 3, 15), "mar"]],
            ).to_sql()
        )

        assert await _async_partition_names(async_mysql_backend) == [
            "p2026_01",
            "p2026_02",
            "p2026_03",
        ]
        row = await async_mysql_backend.fetch_one(
            *_select_payload_by_id_expression(async_mysql_backend.dialect, 3).to_sql()
        )
        assert row["payload"] == "mar"

    @pytest.mark.asyncio
    async def test_drop_partition(self, async_mysql_backend, async_mysql_partitioned_table):
        """ALTER TABLE DROP PARTITION should remove the partition and its rows."""
        await async_mysql_backend.execute(
            *_insert_events_expression(
                async_mysql_backend.dialect,
                [
                    [1, datetime(2026, 1, 15), "jan"],
                    [2, datetime(2026, 2, 15), "feb"],
                ],
            ).to_sql()
        )
        await async_mysql_backend.execute(
            *_drop_partition_expression(async_mysql_backend.dialect, "p2026_01").to_sql()
        )

        assert await _async_partition_names(async_mysql_backend) == ["p2026_02"]
        rows = await async_mysql_backend.fetch_all(*_select_payloads_expression(async_mysql_backend.dialect).to_sql())
        assert [row["payload"] for row in rows] == ["feb"]

    @pytest.mark.asyncio
    async def test_truncate_partition(self, async_mysql_backend, async_mysql_partitioned_table):
        """ALTER TABLE TRUNCATE PARTITION should clear one range only."""
        await async_mysql_backend.execute(
            *_insert_events_expression(
                async_mysql_backend.dialect,
                [
                    [1, datetime(2026, 1, 15), "jan"],
                    [2, datetime(2026, 2, 15), "feb"],
                ],
            ).to_sql()
        )
        await async_mysql_backend.execute(
            *_truncate_partition_expression(async_mysql_backend.dialect, "p2026_01").to_sql()
        )

        rows = await async_mysql_backend.fetch_all(*_select_payloads_expression(async_mysql_backend.dialect).to_sql())
        assert [row["payload"] for row in rows] == ["feb"]

    @pytest.mark.asyncio
    async def test_reorganize_partition(self, async_mysql_backend, async_mysql_partitioned_table):
        """ALTER TABLE REORGANIZE PARTITION should split an existing range."""
        await async_mysql_backend.execute(*_reorganize_partition_expression(async_mysql_backend.dialect).to_sql())

        assert await _async_partition_names(async_mysql_backend) == [
            "p2026_01",
            "p2026_02a",
            "p2026_02b",
        ]
