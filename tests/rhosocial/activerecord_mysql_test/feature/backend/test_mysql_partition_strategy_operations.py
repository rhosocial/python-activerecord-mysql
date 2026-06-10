"""Real MySQL tests for partition strategies beyond RANGE COLUMNS."""

from typing import Sequence

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    FunctionCall,
    InsertExpression,
    Literal,
    LogicalPredicate,
    OrderByClause,
    QueryExpression,
    TableExpression,
    ValuesSource,
    WildcardExpression,
)
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLAddPartitionExpression,
    MySQLDropPartitionExpression,
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByRange,
    MySQLPartitionDefinition,
    MySQLPartitionValue,
    MySQLTruncatePartitionExpression,
)


RANGE_TABLE = "ar_mysql_partition_strategy_range"
LIST_TABLE = "ar_mysql_partition_strategy_list"
LIST_COLUMNS_TABLE = "ar_mysql_partition_strategy_list_columns"
HASH_TABLE = "ar_mysql_partition_strategy_hash"
KEY_TABLE = "ar_mysql_partition_strategy_key"
LINEAR_HASH_TABLE = "ar_mysql_partition_strategy_linear_hash"
LINEAR_KEY_TABLE = "ar_mysql_partition_strategy_linear_key"
STRATEGY_TABLES = (
    RANGE_TABLE,
    LIST_TABLE,
    LIST_COLUMNS_TABLE,
    HASH_TABLE,
    KEY_TABLE,
    LINEAR_HASH_TABLE,
    LINEAR_KEY_TABLE,
)


def _drop_named_table_expression(dialect, table_name: str):
    return DropTableExpression(dialect=dialect, table=table_name, if_exists=True)


def _base_columns():
    return [
        ColumnDefinition("id", "BIGINT NOT NULL"),
        ColumnDefinition("shard_id", "BIGINT NOT NULL"),
        ColumnDefinition("category", "VARCHAR(32) NOT NULL"),
        ColumnDefinition("payload", "VARCHAR(255) NOT NULL"),
    ]


def _partition_value(dialect, value):
    return MySQLPartitionValue(dialect, value)


def _create_range_table_expression(dialect):
    return CreateTableExpression(
        dialect=dialect,
        table=RANGE_TABLE,
        columns=_base_columns(),
        partition=MySQLPartitionByRange(
            dialect=dialect,
            keys=[Column(dialect, "shard_id")],
            partitions=[
                MySQLPartitionDefinition("p_low", less_than=[_partition_value(dialect, 100)]),
                MySQLPartitionDefinition("p_mid", less_than=[_partition_value(dialect, 200)]),
            ],
        ),
    )


def _create_list_table_expression(dialect):
    return CreateTableExpression(
        dialect=dialect,
        table=LIST_TABLE,
        columns=_base_columns(),
        partition=MySQLPartitionByList(
            dialect=dialect,
            keys=[Column(dialect, "shard_id")],
            partitions=[
                MySQLPartitionDefinition(
                    "p_small",
                    in_values=[_partition_value(dialect, 1), _partition_value(dialect, 2)],
                ),
                MySQLPartitionDefinition(
                    "p_large",
                    in_values=[_partition_value(dialect, 3), _partition_value(dialect, 4)],
                ),
            ],
        ),
    )


def _create_list_columns_table_expression(dialect):
    return CreateTableExpression(
        dialect=dialect,
        table=LIST_COLUMNS_TABLE,
        columns=_base_columns(),
        partition=MySQLPartitionByListColumns(
            dialect=dialect,
            keys=[Column(dialect, "category")],
            partitions=[
                MySQLPartitionDefinition(
                    "p_active",
                    in_values=[_partition_value(dialect, "active"), _partition_value(dialect, "pending")],
                ),
                MySQLPartitionDefinition(
                    "p_closed",
                    in_values=[_partition_value(dialect, "closed"), _partition_value(dialect, "archived")],
                ),
            ],
        ),
    )


def _create_hash_table_expression(dialect, table_name: str, *, linear: bool = False):
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        columns=_base_columns(),
        partition=MySQLPartitionByHash(
            dialect=dialect,
            keys=[Column(dialect, "shard_id")],
            partitions_count=4,
            linear=linear,
        ),
    )


def _create_key_table_expression(dialect, table_name: str, *, linear: bool = False):
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        columns=_base_columns(),
        partition=MySQLPartitionByKey(
            dialect=dialect,
            keys=[Column(dialect, "id")],
            partitions_count=4,
            linear=linear,
        ),
    )


def _insert_rows_expression(dialect, table_name: str, rows: Sequence[Sequence[object]]):
    return InsertExpression(
        dialect=dialect,
        into=table_name,
        columns=["id", "shard_id", "category", "payload"],
        source=ValuesSource(
            dialect,
            [[Literal(dialect, value) for value in row] for row in rows],
        ),
    )


def _select_payloads_expression(dialect, table_name: str):
    return QueryExpression(
        dialect,
        select=[Column(dialect, "payload")],
        from_=TableExpression(dialect, table_name),
        order_by=OrderByClause(dialect, [(Column(dialect, "id"), "ASC")]),
    )


def _select_count_expression(dialect, table_name: str):
    return QueryExpression(
        dialect,
        select=[FunctionCall(dialect, "COUNT", WildcardExpression(dialect)).as_("count")],
        from_=TableExpression(dialect, table_name),
    )


def _partition_metadata_expression(dialect, table_name: str):
    partitions = TableExpression(dialect, "PARTITIONS", schema_name="information_schema")
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "PARTITION_NAME", alias="name"),
            Column(dialect, "PARTITION_METHOD", alias="method"),
            Column(dialect, "PARTITION_EXPRESSION", alias="expression"),
            Column(dialect, "PARTITION_DESCRIPTION", alias="description"),
        ],
        from_=partitions,
        where=LogicalPredicate(
            dialect,
            "AND",
            Column(dialect, "TABLE_SCHEMA") == FunctionCall(dialect, "DATABASE"),
            Column(dialect, "TABLE_NAME") == Literal(dialect, table_name),
            Column(dialect, "PARTITION_NAME").is_not_null(),
        ),
        order_by=OrderByClause(dialect, [(Column(dialect, "PARTITION_NAME"), "ASC")]),
    )


def _create_table(backend, table_name: str, expression_factory):
    backend.execute(*_drop_named_table_expression(backend.dialect, table_name).to_sql())
    backend.execute(*expression_factory(backend.dialect).to_sql())


def _drop_tables(backend):
    for table_name in STRATEGY_TABLES:
        backend.execute(*_drop_named_table_expression(backend.dialect, table_name).to_sql())


async def _async_create_table(backend, table_name: str, expression_factory):
    await backend.execute(*_drop_named_table_expression(backend.dialect, table_name).to_sql())
    await backend.execute(*expression_factory(backend.dialect).to_sql())


async def _async_drop_tables(backend):
    for table_name in STRATEGY_TABLES:
        await backend.execute(*_drop_named_table_expression(backend.dialect, table_name).to_sql())


def _metadata(backend, table_name: str):
    return backend.fetch_all(*_partition_metadata_expression(backend.dialect, table_name).to_sql())


async def _async_metadata(backend, table_name: str):
    return await backend.fetch_all(*_partition_metadata_expression(backend.dialect, table_name).to_sql())


def _assert_partition_method(rows, method: str):
    assert rows
    assert all(method in str(row["method"]).upper() for row in rows)


class TestMySQLPartitionStrategies:
    """Synchronous real backend tests for additional MySQL partition strategies."""

    def test_range_partition_routes_rows(self, mysql_backend):
        """Plain RANGE partitioning should work without COLUMNS mode."""
        _create_table(mysql_backend, RANGE_TABLE, _create_range_table_expression)
        try:
            mysql_backend.execute(
                *_insert_rows_expression(
                    mysql_backend.dialect,
                    RANGE_TABLE,
                    [(1, 10, "active", "low"), (2, 150, "active", "mid")],
                ).to_sql()
            )
            rows = mysql_backend.fetch_all(*_select_payloads_expression(mysql_backend.dialect, RANGE_TABLE).to_sql())
            metadata = _metadata(mysql_backend, RANGE_TABLE)
            assert [row["payload"] for row in rows] == ["low", "mid"]
            _assert_partition_method(metadata, "RANGE")
            assert any("100" in str(row["description"]) for row in metadata)
        finally:
            _drop_tables(mysql_backend)

    def test_list_and_list_columns_route_rows(self, mysql_backend):
        """LIST and LIST COLUMNS should route rows by VALUES IN definitions."""
        _create_table(mysql_backend, LIST_TABLE, _create_list_table_expression)
        _create_table(mysql_backend, LIST_COLUMNS_TABLE, _create_list_columns_table_expression)
        try:
            mysql_backend.execute(
                *_insert_rows_expression(
                    mysql_backend.dialect,
                    LIST_TABLE,
                    [(1, 1, "active", "small"), (2, 4, "active", "large")],
                ).to_sql()
            )
            mysql_backend.execute(
                *_insert_rows_expression(
                    mysql_backend.dialect,
                    LIST_COLUMNS_TABLE,
                    [(3, 10, "active", "active-row"), (4, 20, "closed", "closed-row")],
                ).to_sql()
            )
            list_rows = mysql_backend.fetch_all(*_select_payloads_expression(mysql_backend.dialect, LIST_TABLE).to_sql())
            list_columns_rows = mysql_backend.fetch_all(
                *_select_payloads_expression(mysql_backend.dialect, LIST_COLUMNS_TABLE).to_sql()
            )
            assert [row["payload"] for row in list_rows] == ["small", "large"]
            assert [row["payload"] for row in list_columns_rows] == ["active-row", "closed-row"]
            _assert_partition_method(_metadata(mysql_backend, LIST_TABLE), "LIST")
            _assert_partition_method(_metadata(mysql_backend, LIST_COLUMNS_TABLE), "LIST")
        finally:
            _drop_tables(mysql_backend)

    @pytest.mark.parametrize(
        "table_name,expression_factory,expected_method",
        [
            (HASH_TABLE, lambda dialect: _create_hash_table_expression(dialect, HASH_TABLE), "HASH"),
            (KEY_TABLE, lambda dialect: _create_key_table_expression(dialect, KEY_TABLE), "KEY"),
            (
                LINEAR_HASH_TABLE,
                lambda dialect: _create_hash_table_expression(dialect, LINEAR_HASH_TABLE, linear=True),
                "LINEAR HASH",
            ),
            (
                LINEAR_KEY_TABLE,
                lambda dialect: _create_key_table_expression(dialect, LINEAR_KEY_TABLE, linear=True),
                "LINEAR KEY",
            ),
        ],
    )
    def test_hash_key_and_linear_partition_tables_accept_rows(
        self,
        mysql_backend,
        table_name,
        expression_factory,
        expected_method,
    ):
        """HASH, KEY, and LINEAR variants should create usable partitioned tables."""
        _create_table(mysql_backend, table_name, expression_factory)
        try:
            mysql_backend.execute(
                *_insert_rows_expression(
                    mysql_backend.dialect,
                    table_name,
                    [(1, 10, "active", "one"), (2, 20, "closed", "two")],
                ).to_sql()
            )
            count = mysql_backend.fetch_one(*_select_count_expression(mysql_backend.dialect, table_name).to_sql())["count"]
            metadata = _metadata(mysql_backend, table_name)
            assert count == 2
            _assert_partition_method(metadata, expected_method)
            assert len(metadata) == 4
        finally:
            _drop_tables(mysql_backend)

    def test_multi_partition_add_drop_and_truncate(self, mysql_backend):
        """ADD, DROP, and TRUNCATE should handle multiple partitions in one statement."""
        _create_table(mysql_backend, RANGE_TABLE, _create_range_table_expression)
        try:
            mysql_backend.execute(
                *MySQLAddPartitionExpression(
                    mysql_backend.dialect,
                    RANGE_TABLE,
                    [
                        MySQLPartitionDefinition(
                            "p_high",
                            less_than=[_partition_value(mysql_backend.dialect, 300)],
                        ),
                        MySQLPartitionDefinition(
                            "p_higher",
                            less_than=[_partition_value(mysql_backend.dialect, 400)],
                        ),
                    ],
                ).to_sql()
            )
            assert {row["name"] for row in _metadata(mysql_backend, RANGE_TABLE)} == {
                "p_low",
                "p_mid",
                "p_high",
                "p_higher",
            }
            mysql_backend.execute(
                *_insert_rows_expression(
                    mysql_backend.dialect,
                    RANGE_TABLE,
                    [(1, 250, "active", "high"), (2, 350, "closed", "higher")],
                ).to_sql()
            )
            mysql_backend.execute(
                *MySQLTruncatePartitionExpression(
                    mysql_backend.dialect,
                    RANGE_TABLE,
                    ["p_high", "p_higher"],
                ).to_sql()
            )
            count = mysql_backend.fetch_one(*_select_count_expression(mysql_backend.dialect, RANGE_TABLE).to_sql())["count"]
            assert count == 0
            mysql_backend.execute(
                *MySQLDropPartitionExpression(
                    mysql_backend.dialect,
                    RANGE_TABLE,
                    ["p_high", "p_higher"],
                ).to_sql()
            )
            assert {row["name"] for row in _metadata(mysql_backend, RANGE_TABLE)} == {"p_low", "p_mid"}
        finally:
            _drop_tables(mysql_backend)


class TestAsyncMySQLPartitionStrategies:
    """Asynchronous real backend tests for additional MySQL partition strategies."""

    @pytest.mark.asyncio
    async def test_range_partition_routes_rows(self, async_mysql_backend):
        """Plain RANGE partitioning should work asynchronously."""
        await _async_create_table(async_mysql_backend, RANGE_TABLE, _create_range_table_expression)
        try:
            await async_mysql_backend.execute(
                *_insert_rows_expression(
                    async_mysql_backend.dialect,
                    RANGE_TABLE,
                    [(1, 10, "active", "low"), (2, 150, "active", "mid")],
                ).to_sql()
            )
            rows = await async_mysql_backend.fetch_all(
                *_select_payloads_expression(async_mysql_backend.dialect, RANGE_TABLE).to_sql()
            )
            metadata = await _async_metadata(async_mysql_backend, RANGE_TABLE)
            assert [row["payload"] for row in rows] == ["low", "mid"]
            _assert_partition_method(metadata, "RANGE")
        finally:
            await _async_drop_tables(async_mysql_backend)

    @pytest.mark.asyncio
    async def test_list_and_list_columns_route_rows(self, async_mysql_backend):
        """LIST and LIST COLUMNS should route rows asynchronously."""
        await _async_create_table(async_mysql_backend, LIST_TABLE, _create_list_table_expression)
        await _async_create_table(
            async_mysql_backend,
            LIST_COLUMNS_TABLE,
            _create_list_columns_table_expression,
        )
        try:
            await async_mysql_backend.execute(
                *_insert_rows_expression(
                    async_mysql_backend.dialect,
                    LIST_TABLE,
                    [(1, 1, "active", "small"), (2, 4, "active", "large")],
                ).to_sql()
            )
            await async_mysql_backend.execute(
                *_insert_rows_expression(
                    async_mysql_backend.dialect,
                    LIST_COLUMNS_TABLE,
                    [(3, 10, "active", "active-row"), (4, 20, "closed", "closed-row")],
                ).to_sql()
            )
            list_rows = await async_mysql_backend.fetch_all(
                *_select_payloads_expression(async_mysql_backend.dialect, LIST_TABLE).to_sql()
            )
            list_columns_rows = await async_mysql_backend.fetch_all(
                *_select_payloads_expression(async_mysql_backend.dialect, LIST_COLUMNS_TABLE).to_sql()
            )
            assert [row["payload"] for row in list_rows] == ["small", "large"]
            assert [row["payload"] for row in list_columns_rows] == ["active-row", "closed-row"]
            _assert_partition_method(await _async_metadata(async_mysql_backend, LIST_TABLE), "LIST")
            _assert_partition_method(await _async_metadata(async_mysql_backend, LIST_COLUMNS_TABLE), "LIST")
        finally:
            await _async_drop_tables(async_mysql_backend)
