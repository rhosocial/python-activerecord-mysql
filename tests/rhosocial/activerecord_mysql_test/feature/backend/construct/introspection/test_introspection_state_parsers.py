# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/introspection/test_introspection_state_parsers.py
"""Parser-level tests for the neutral object-state answers.

The rows ``information_schema.PARTITIONS`` would return are supplied directly,
so these tests run without a server and fail on the mapping rather than on a
missing database: scheme, bounds, MAXVALUE and the statistics gate.
"""

from types import SimpleNamespace

from rhosocial.activerecord.backend.introspection.types import (
    PartitionScheme,
    TableType,
)

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.introspection import MySQLIntrospector
from rhosocial.activerecord.backend.impl.mysql.introspection.types import (
    MySQLTableOptions,
)


class _NoServerBackend:
    """The parts of a MySQL backend an introspector reads, and nothing else."""

    def __init__(self) -> None:
        self.config = SimpleNamespace(database="shop")
        self.dialect = MySQLDialect((8, 0, 0))
        self._cached_version = (8, 0, 0)

    def get_cached_server_version(self):
        return self._cached_version


class _UnusedExecutor:
    """An executor that fails loudly if a parser-level test asks for SQL."""

    def execute(self, sql, params=()):
        raise AssertionError("a parser-level test must not execute SQL")


def _introspector() -> MySQLIntrospector:
    return MySQLIntrospector(_NoServerBackend(), _UnusedExecutor())


def _range_row(description, name, ordinal, **extra):
    row = {
        "TABLE_SCHEMA": "shop",
        "TABLE_NAME": "events",
        "PARTITION_NAME": name,
        "PARTITION_METHOD": "RANGE",
        "PARTITION_EXPRESSION": "YEAR(`created_at`)",
        "PARTITION_DESCRIPTION": description,
        "PARTITION_ORDINAL_POSITION": ordinal,
    }
    row.update(extra)
    return row


class TestParsePartitionState:
    def test_no_rows_is_scheme_none(self):
        state = _introspector().parse_partition_state([], "events", "shop")

        assert state.scheme is None
        assert state.bounds == ()

    def test_range_rows_map_to_bounds_and_maxvalue(self):
        rows = [
            _range_row("2021", "p2020", 1),
            _range_row("2022", "p2021", 2),
            _range_row("MAXVALUE", "p_max", 3),
        ]

        state = _introspector().parse_partition_state(rows, "events", "shop")

        assert state.scheme is PartitionScheme.RANGE
        assert state.key_expression == "YEAR(`created_at`)"
        assert [bound.name for bound in state.bounds] == ["p2020", "p2021", "p_max"]
        assert [bound.upper for bound in state.bounds] == ["2021", "2022", "MAXVALUE"]
        assert [bound.is_maxvalue for bound in state.bounds] == [False, False, True]
        assert all(not bound.is_default for bound in state.bounds)

    def test_statistics_are_ignored_when_not_requested(self):
        rows = [
            _range_row("2021", "p2020", 1, TABLE_ROWS=10, DATA_LENGTH=4096),
        ]

        state = _introspector().parse_partition_state(rows, "events", "shop")

        assert state.bounds[0].row_count is None
        assert state.bounds[0].size_bytes is None

    def test_statistics_are_sums_across_subpartition_rows(self):
        rows = [
            _range_row(
                "2021",
                "p2020",
                1,
                SUBPARTITION_NAME="p2020_0",
                SUBPARTITION_METHOD="HASH",
                TABLE_ROWS=10,
                DATA_LENGTH=4096,
            ),
            _range_row(
                "2021",
                "p2020",
                1,
                SUBPARTITION_NAME="p2020_1",
                SUBPARTITION_METHOD="HASH",
                TABLE_ROWS=20,
                DATA_LENGTH=8192,
            ),
        ]

        state = _introspector().parse_partition_state(rows, "events", "shop", include_stats=True)

        assert state.scheme is PartitionScheme.COMPOSITE
        assert len(state.bounds) == 1
        assert state.bounds[0].subpartition_count == 2
        assert state.bounds[0].row_count == 30
        assert state.bounds[0].size_bytes == 4096 + 8192

    def test_key_partition_carries_its_column_list(self):
        rows = [
            {
                "TABLE_SCHEMA": "shop",
                "TABLE_NAME": "events",
                "PARTITION_NAME": "p0",
                "PARTITION_METHOD": "KEY",
                "PARTITION_EXPRESSION": "`id`,`tenant_id`",
                "PARTITION_DESCRIPTION": None,
            }
        ]

        state = _introspector().parse_partition_state(rows, "events", "shop")

        assert state.scheme is PartitionScheme.KEY
        assert state.key_columns == ("id", "tenant_id")

    def test_list_columns_is_the_list_scheme(self):
        row = _range_row("1,2,3", "p_low", 1)
        row["PARTITION_METHOD"] = "LIST COLUMNS"

        state = _introspector().parse_partition_state([row], "events", "shop")

        assert state.scheme is PartitionScheme.LIST
        assert state.bounds[0].upper == "1,2,3"

    def test_an_unrecognised_method_still_says_partitioned(self):
        row = _range_row(None, "p0", 1)
        row["PARTITION_METHOD"] = "SOMETHING_NEW"

        state = _introspector().parse_partition_state([row], "events", "shop")

        assert state.scheme is PartitionScheme.EXPRESSION


class TestStorageOptionsState:
    def test_engine_collation_and_derived_charset(self):
        options = MySQLTableOptions(
            schema="shop",
            table_name="users",
            engine="InnoDB",
            table_collation="utf8mb4_0900_ai_ci",
            table_comment="accounts",
            row_format="Dynamic",
            data_length=16384,
            index_length=0,
        )

        state = _introspector().parse_storage_options_state(options)

        assert state.engine == "InnoDB"
        assert state.collation == "utf8mb4_0900_ai_ci"
        assert state.charset == "utf8mb4"
        assert state.raw["row_format"] == "Dynamic"
        assert state.raw["data_length"] == 16384

    def test_no_options_is_an_empty_state(self):
        state = _introspector().parse_storage_options_state(None)

        assert state.engine is None
        assert state.collation is None
        assert state.charset is None

    def test_binary_collation_is_its_own_charset(self):
        assert _introspector().charset_from_collation("binary") == "binary"


class TestTableStateKind:
    def test_catalogue_kinds_map_to_neutral_spellings(self):
        introspector = _introspector()

        assert introspector.table_state_kind(TableType.BASE_TABLE) == "regular"
        assert introspector.table_state_kind(TableType.VIEW) == "view"
        assert introspector.table_state_kind(TableType.SYSTEM_TABLE) == "system_view"
        assert introspector.table_state_kind(TableType.PARTITIONED_TABLE) == "regular"
