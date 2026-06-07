# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_partition_operations.py
"""Real MySQL partition operation tests."""

from datetime import datetime

import pytest


PARTITION_TABLE = "ar_mysql_partition_events"


def _drop_table(backend):
    backend.execute(f"DROP TABLE IF EXISTS `{PARTITION_TABLE}`")


async def _async_drop_table(backend):
    await backend.execute(f"DROP TABLE IF EXISTS `{PARTITION_TABLE}`")


def _create_partitioned_table(backend):
    _drop_table(backend)
    backend.execute(f"""
        CREATE TABLE `{PARTITION_TABLE}` (
            id BIGINT NOT NULL,
            created_at DATETIME NOT NULL,
            payload VARCHAR(255),
            KEY idx_created_at (created_at),
            KEY idx_id (id)
        )
        PARTITION BY RANGE COLUMNS (created_at) (
            PARTITION p2026_01 VALUES LESS THAN ('2026-02-01'),
            PARTITION p2026_02 VALUES LESS THAN ('2026-03-01')
        )
    """)


async def _async_create_partitioned_table(backend):
    await _async_drop_table(backend)
    await backend.execute(f"""
        CREATE TABLE `{PARTITION_TABLE}` (
            id BIGINT NOT NULL,
            created_at DATETIME NOT NULL,
            payload VARCHAR(255),
            KEY idx_created_at (created_at),
            KEY idx_id (id)
        )
        PARTITION BY RANGE COLUMNS (created_at) (
            PARTITION p2026_01 VALUES LESS THAN ('2026-02-01'),
            PARTITION p2026_02 VALUES LESS THAN ('2026-03-01')
        )
    """)


def _partition_names(backend):
    rows = backend.fetch_all(
        """
        SELECT PARTITION_NAME AS name
        FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND PARTITION_NAME IS NOT NULL
        ORDER BY PARTITION_NAME
        """,
        (PARTITION_TABLE,),
    )
    return [row["name"] for row in rows]


async def _async_partition_names(backend):
    rows = await backend.fetch_all(
        """
        SELECT PARTITION_NAME AS name
        FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND PARTITION_NAME IS NOT NULL
        ORDER BY PARTITION_NAME
        """,
        (PARTITION_TABLE,),
    )
    return [row["name"] for row in rows]


def _partition_metadata(backend):
    return backend.fetch_all(
        """
        SELECT PARTITION_NAME AS name,
               PARTITION_METHOD AS method,
               PARTITION_EXPRESSION AS expression,
               PARTITION_DESCRIPTION AS description,
               TABLE_ROWS AS table_rows,
               DATA_LENGTH AS data_length,
               INDEX_LENGTH AS index_length
        FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND PARTITION_NAME IS NOT NULL
        ORDER BY PARTITION_NAME
        """,
        (PARTITION_TABLE,),
    )


async def _async_partition_metadata(backend):
    return await backend.fetch_all(
        """
        SELECT PARTITION_NAME AS name,
               PARTITION_METHOD AS method,
               PARTITION_EXPRESSION AS expression,
               PARTITION_DESCRIPTION AS description,
               TABLE_ROWS AS table_rows,
               DATA_LENGTH AS data_length,
               INDEX_LENGTH AS index_length
        FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND PARTITION_NAME IS NOT NULL
        ORDER BY PARTITION_NAME
        """,
        (PARTITION_TABLE,),
    )


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
    row = backend.fetch_one(f"SHOW CREATE TABLE `{PARTITION_TABLE}`")
    return row.get("Create Table") or row.get("create table")


async def _async_show_create_table_sql(backend):
    row = await backend.fetch_one(f"SHOW CREATE TABLE `{PARTITION_TABLE}`")
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
        mysql_backend.execute(
            f"INSERT INTO `{PARTITION_TABLE}` (id, created_at, payload) VALUES (%s, %s, %s), (%s, %s, %s)",
            (1, datetime(2026, 1, 15), "jan", 2, datetime(2026, 2, 15), "feb"),
        )

        rows = mysql_backend.fetch_all(f"SELECT payload FROM `{PARTITION_TABLE}` ORDER BY id")
        assert [row["payload"] for row in rows] == ["jan", "feb"]

    def test_add_partition_for_future_range(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE ADD PARTITION should allow future range inserts."""
        mysql_backend.execute(
            f"ALTER TABLE `{PARTITION_TABLE}` ADD PARTITION (PARTITION p2026_03 VALUES LESS THAN ('2026-04-01'))"
        )
        mysql_backend.execute(
            f"INSERT INTO `{PARTITION_TABLE}` (id, created_at, payload) VALUES (%s, %s, %s)",
            (3, datetime(2026, 3, 15), "mar"),
        )

        assert _partition_names(mysql_backend) == ["p2026_01", "p2026_02", "p2026_03"]
        row = mysql_backend.fetch_one(f"SELECT payload FROM `{PARTITION_TABLE}` WHERE id = %s", (3,))
        assert row["payload"] == "mar"

    def test_truncate_partition(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE TRUNCATE PARTITION should clear one range only."""
        mysql_backend.execute(
            f"INSERT INTO `{PARTITION_TABLE}` (id, created_at, payload) VALUES (%s, %s, %s), (%s, %s, %s)",
            (1, datetime(2026, 1, 15), "jan", 2, datetime(2026, 2, 15), "feb"),
        )
        mysql_backend.execute(f"ALTER TABLE `{PARTITION_TABLE}` TRUNCATE PARTITION p2026_01")

        rows = mysql_backend.fetch_all(f"SELECT payload FROM `{PARTITION_TABLE}` ORDER BY id")
        assert [row["payload"] for row in rows] == ["feb"]

    def test_reorganize_partition(self, mysql_backend, mysql_partitioned_table):
        """ALTER TABLE REORGANIZE PARTITION should split an existing range."""
        mysql_backend.execute(
            f"ALTER TABLE `{PARTITION_TABLE}` REORGANIZE PARTITION p2026_02 INTO ("
            "PARTITION p2026_02a VALUES LESS THAN ('2026-02-15'), "
            "PARTITION p2026_02b VALUES LESS THAN ('2026-03-01'))"
        )

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
        await async_mysql_backend.execute(
            f"INSERT INTO `{PARTITION_TABLE}` (id, created_at, payload) VALUES (%s, %s, %s), (%s, %s, %s)",
            (1, datetime(2026, 1, 15), "jan", 2, datetime(2026, 2, 15), "feb"),
        )

        rows = await async_mysql_backend.fetch_all(f"SELECT payload FROM `{PARTITION_TABLE}` ORDER BY id")
        assert [row["payload"] for row in rows] == ["jan", "feb"]

    @pytest.mark.asyncio
    async def test_add_partition_for_future_range(
        self,
        async_mysql_backend,
        async_mysql_partitioned_table,
    ):
        """ALTER TABLE ADD PARTITION should allow future range inserts."""
        await async_mysql_backend.execute(
            f"ALTER TABLE `{PARTITION_TABLE}` ADD PARTITION (PARTITION p2026_03 VALUES LESS THAN ('2026-04-01'))"
        )
        await async_mysql_backend.execute(
            f"INSERT INTO `{PARTITION_TABLE}` (id, created_at, payload) VALUES (%s, %s, %s)",
            (3, datetime(2026, 3, 15), "mar"),
        )

        assert await _async_partition_names(async_mysql_backend) == [
            "p2026_01",
            "p2026_02",
            "p2026_03",
        ]
        row = await async_mysql_backend.fetch_one(
            f"SELECT payload FROM `{PARTITION_TABLE}` WHERE id = %s",
            (3,),
        )
        assert row["payload"] == "mar"

    @pytest.mark.asyncio
    async def test_truncate_partition(self, async_mysql_backend, async_mysql_partitioned_table):
        """ALTER TABLE TRUNCATE PARTITION should clear one range only."""
        await async_mysql_backend.execute(
            f"INSERT INTO `{PARTITION_TABLE}` (id, created_at, payload) VALUES (%s, %s, %s), (%s, %s, %s)",
            (1, datetime(2026, 1, 15), "jan", 2, datetime(2026, 2, 15), "feb"),
        )
        await async_mysql_backend.execute(f"ALTER TABLE `{PARTITION_TABLE}` TRUNCATE PARTITION p2026_01")

        rows = await async_mysql_backend.fetch_all(f"SELECT payload FROM `{PARTITION_TABLE}` ORDER BY id")
        assert [row["payload"] for row in rows] == ["feb"]

    @pytest.mark.asyncio
    async def test_reorganize_partition(self, async_mysql_backend, async_mysql_partitioned_table):
        """ALTER TABLE REORGANIZE PARTITION should split an existing range."""
        await async_mysql_backend.execute(
            f"ALTER TABLE `{PARTITION_TABLE}` REORGANIZE PARTITION p2026_02 INTO ("
            "PARTITION p2026_02a VALUES LESS THAN ('2026-02-15'), "
            "PARTITION p2026_02b VALUES LESS THAN ('2026-03-01'))"
        )

        assert await _async_partition_names(async_mysql_backend) == [
            "p2026_01",
            "p2026_02a",
            "p2026_02b",
        ]
