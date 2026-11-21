# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/ddl/partition_syntax_fixtures.py
"""Fixture-driven MySQL partition syntax matrix.

Each case describes one MySQL partition syntax family: how to build it, which
fragments its rendered SQL must contain, which must not appear, and which
unsupported feature it must refuse by name. ``partition_syntax_case`` turns that
description into a pytest parameter, so the test module stays free of per-family
branches.

The matrix is offline. ``live_setup`` and ``live_check`` are reserved for a
server-backed extension; every case leaves them unset today.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

import pytest

from rhosocial.activerecord.backend.expression.statements import (
    PartitionDefinitionExpression,
    PartitionOptionsExpression,
)
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLAddPartitionExpression,
    MySQLAnalyzePartitionExpression,
    MySQLCheckPartitionExpression,
    MySQLCoalescePartitionExpression,
    MySQLDropPartitionExpression,
    MySQLExchangePartitionExpression,
    MySQLOptimizePartitionExpression,
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
    MySQLRebuildPartitionExpression,
    MySQLRemovePartitioningExpression,
    MySQLReorganizePartitionExpression,
    MySQLRepairPartitionExpression,
    MySQLSubpartitionClause,
    MySQLSubpartitionStrategy,
    MySQLTruncatePartitionExpression,
)

Builder = Callable[[MySQLDialect], Any]


@dataclass(frozen=True)
class PartitionSyntaxCase:
    """One row of the MySQL partition syntax matrix.

    Attributes:
        name: Stable pytest id and syntax-family name.
        description: Human-readable note shown in test output.
        builder: Callable rendering the case's expression or expressions.
        expected_fragments: Substrings the rendered SQL must contain.
        forbidden_fragments: Substrings the rendered SQL must not contain.
        ordered_fragments: Substrings that must appear in this order.
        refusal_feature: When set, the builder must raise
            ``UnsupportedFeatureError`` whose ``feature_name`` contains it.
        live_setup: Optional hook for a server-backed extension.
        live_check: Optional hook for a server-backed extension.
    """

    name: str
    description: str
    builder: Optional[Builder] = None
    expected_fragments: Tuple[str, ...] = ()
    forbidden_fragments: Tuple[str, ...] = ()
    ordered_fragments: Tuple[str, ...] = ()
    refusal_feature: Optional[str] = None
    live_setup: Optional[Callable[..., Any]] = None
    live_check: Optional[Callable[..., Any]] = None


def _value(dialect: MySQLDialect, value: Any) -> MySQLPartitionValue:
    """Build a MySQL partition boundary literal."""
    return MySQLPartitionValue(dialect, value)


def _range_definition(
    dialect: MySQLDialect,
    name: str,
    upper_bound: Any,
) -> PartitionDefinitionExpression:
    """Build a RANGE definition, using MAXVALUE when ``upper_bound`` is None."""
    if upper_bound is None:
        return PartitionDefinitionExpression(
            dialect,
            name,
            less_than=[MySQLPartitionMaxValue(dialect)],
        )
    return PartitionDefinitionExpression(
        dialect,
        name,
        less_than=[_value(dialect, upper_bound)],
    )


def _list_definition(
    dialect: MySQLDialect,
    name: str,
    values: Any,
) -> PartitionDefinitionExpression:
    """Build a LIST definition with one boundary row of literal values."""
    return PartitionDefinitionExpression(
        dialect,
        name,
        in_values=[_value(dialect, value) for value in values],
    )


# --- Expression builders ---------------------------------------------------


def _range_builder(dialect: MySQLDialect) -> MySQLPartitionByRange:
    return MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            _range_definition(dialect, "p2026", "2026-01-01"),
            _range_definition(dialect, "p2027", "2027-01-01"),
        ],
    )


def _range_columns_builder(dialect: MySQLDialect) -> MySQLPartitionByRangeColumns:
    return MySQLPartitionByRangeColumns(
        dialect,
        [Column(dialect, "created_year"), Column(dialect, "created_month")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p2026",
                less_than=[_value(dialect, 2026), _value(dialect, 6)],
            ),
        ],
    )


def _list_builder(dialect: MySQLDialect) -> MySQLPartitionByList:
    return MySQLPartitionByList(
        dialect,
        [Column(dialect, "status")],
        partitions=[
            _list_definition(dialect, "p_active", ["active", "pending"]),
        ],
    )


def _list_columns_builder(dialect: MySQLDialect) -> MySQLPartitionByListColumns:
    return MySQLPartitionByListColumns(
        dialect,
        [Column(dialect, "region"), Column(dialect, "status")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p_us",
                in_values=[
                    [_value(dialect, "us"), _value(dialect, "active")],
                    [_value(dialect, "eu"), _value(dialect, "active")],
                ],
            ),
        ],
    )


def _hash_builder(dialect: MySQLDialect) -> MySQLPartitionByHash:
    return MySQLPartitionByHash(
        dialect,
        [Column(dialect, "id")],
        partitions_count=4,
    )


def _key_builder(dialect: MySQLDialect) -> MySQLPartitionByKey:
    return MySQLPartitionByKey(
        dialect,
        [Column(dialect, "id")],
        partitions_count=4,
    )


def _linear_hash_builder(dialect: MySQLDialect) -> MySQLPartitionByHash:
    return MySQLPartitionByHash(
        dialect,
        [Column(dialect, "id")],
        partitions_count=4,
        linear=True,
    )


def _linear_key_builder(dialect: MySQLDialect) -> MySQLPartitionByKey:
    return MySQLPartitionByKey(
        dialect,
        [Column(dialect, "id")],
        partitions_count=4,
        linear=True,
    )


def _range_maxvalue_builder(dialect: MySQLDialect) -> MySQLPartitionByRange:
    return MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            _range_definition(dialect, "p2026", "2027-01-01"),
            _range_definition(dialect, "pmax", None),
        ],
    )


def _hash_subpartition_builder(dialect: MySQLDialect) -> MySQLPartitionByRange:
    return MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[_range_definition(dialect, "p2026", "2027-01-01")],
        subpartition_by=MySQLSubpartitionClause(
            dialect,
            strategy=MySQLSubpartitionStrategy.HASH,
            expression=Column(dialect, "id"),
            count=4,
        ),
    )


def _key_subpartition_builder(dialect: MySQLDialect) -> MySQLPartitionByRange:
    return MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[_range_definition(dialect, "p2026", "2027-01-01")],
        subpartition_by=MySQLSubpartitionClause(
            dialect,
            strategy=MySQLSubpartitionStrategy.KEY,
            expression=Column(dialect, "id"),
            count=4,
        ),
    )


def _range_subpartition_refused(dialect: MySQLDialect) -> MySQLSubpartitionClause:
    return MySQLSubpartitionClause(
        dialect,
        strategy="RANGE",  # type: ignore[arg-type]
        count=2,
    )


def _list_subpartition_refused(dialect: MySQLDialect) -> MySQLSubpartitionClause:
    return MySQLSubpartitionClause(
        dialect,
        strategy="LIST",  # type: ignore[arg-type]
        count=2,
    )


def _partition_options_builder(dialect: MySQLDialect) -> MySQLPartitionByRange:
    return MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p2026",
                less_than=[_value(dialect, 2027)],
                options=PartitionOptionsExpression(
                    dialect,
                    {
                        "engine": "InnoDB",
                        "comment": "hot tenant",
                        "max_rows": 1000,
                        "tablespace": "ts_hot",
                    },
                ),
            ),
        ],
    )


def _lifecycle_add_drop(
    dialect: MySQLDialect,
) -> Tuple[MySQLAddPartitionExpression, MySQLDropPartitionExpression]:
    return (
        MySQLAddPartitionExpression(
            dialect,
            Table(dialect, "events"),
            [
                _range_definition(dialect, "p2026", 2026),
                _range_definition(dialect, "p2027", 2027),
            ],
        ),
        MySQLDropPartitionExpression(
            dialect,
            Table(dialect, "events"),
            ["p2026"],
        ),
    )


def _lifecycle_reorganize(dialect: MySQLDialect) -> MySQLReorganizePartitionExpression:
    return MySQLReorganizePartitionExpression(
        dialect,
        Table(dialect, "events"),
        "p2026",
        [
            _range_definition(dialect, "p2026_a", 2026),
            _range_definition(dialect, "p2026_b", 2027),
        ],
    )


def _lifecycle_exchange(dialect: MySQLDialect) -> MySQLExchangePartitionExpression:
    return MySQLExchangePartitionExpression(
        dialect,
        Table(dialect, "events"),
        "p2026",
        Table(dialect, "events_archive"),
        without_validation=True,
    )


def _lifecycle_coalesce(dialect: MySQLDialect) -> MySQLCoalescePartitionExpression:
    return MySQLCoalescePartitionExpression(
        dialect,
        Table(dialect, "events"),
        2,
    )


def _lifecycle_truncate(dialect: MySQLDialect) -> MySQLTruncatePartitionExpression:
    return MySQLTruncatePartitionExpression(
        dialect,
        Table(dialect, "events"),
        ["p2026", "p2027"],
    )


def _lifecycle_remove(dialect: MySQLDialect) -> MySQLRemovePartitioningExpression:
    return MySQLRemovePartitioningExpression(
        dialect,
        Table(dialect, "events"),
    )


def _maintenance_statements(
    dialect: MySQLDialect,
) -> Tuple[Any, ...]:
    names = ["p2026", "p2027"]
    return (
        MySQLAnalyzePartitionExpression(dialect, Table(dialect, "events"), names),
        MySQLCheckPartitionExpression(dialect, Table(dialect, "events"), names),
        MySQLOptimizePartitionExpression(dialect, Table(dialect, "events"), names),
        MySQLRebuildPartitionExpression(dialect, Table(dialect, "events"), names),
        MySQLRepairPartitionExpression(dialect, Table(dialect, "events"), names),
    )


CASES: List[PartitionSyntaxCase] = [
    PartitionSyntaxCase(
        name="range",
        description="RANGE partitioning with a MAXVALUE terminator",
        builder=_range_builder,
        expected_fragments=(
            "PARTITION BY RANGE (`created_at`)",
            "PARTITION `p2026` VALUES LESS THAN ('2026-01-01')",
            "PARTITION `p2027` VALUES LESS THAN ('2027-01-01')",
        ),
        forbidden_fragments=("MAXVALUE",),
    ),
    PartitionSyntaxCase(
        name="range_columns",
        description="RANGE COLUMNS partitioning over two columns",
        builder=_range_columns_builder,
        expected_fragments=(
            "PARTITION BY RANGE COLUMNS (`created_year`, `created_month`)",
            "PARTITION `p2026` VALUES LESS THAN (2026, 6)",
        ),
        forbidden_fragments=("PARTITION BY RANGE (",),
    ),
    PartitionSyntaxCase(
        name="list",
        description="LIST partitioning with independent value sets",
        builder=_list_builder,
        expected_fragments=(
            "PARTITION BY LIST (`status`)",
            "PARTITION `p_active` VALUES IN ('active', 'pending')",
        ),
        forbidden_fragments=("PARTITION BY LIST COLUMNS",),
    ),
    PartitionSyntaxCase(
        name="list_columns",
        description="LIST COLUMNS partitioning with row tuples",
        builder=_list_columns_builder,
        expected_fragments=(
            "PARTITION BY LIST COLUMNS (`region`, `status`)",
            "PARTITION `p_us` VALUES IN (('us', 'active'), ('eu', 'active'))",
        ),
        forbidden_fragments=("PARTITION BY LIST (`",),
    ),
    PartitionSyntaxCase(
        name="hash",
        description="HASH partitioning with an explicit partition count",
        builder=_hash_builder,
        expected_fragments=(
            "PARTITION BY HASH (`id`)",
            "PARTITIONS 4",
        ),
        forbidden_fragments=("LINEAR HASH",),
    ),
    PartitionSyntaxCase(
        name="key",
        description="KEY partitioning with an explicit partition count",
        builder=_key_builder,
        expected_fragments=(
            "PARTITION BY KEY (`id`)",
            "PARTITIONS 4",
        ),
        forbidden_fragments=("LINEAR KEY",),
    ),
    PartitionSyntaxCase(
        name="linear_hash",
        description="LINEAR HASH partitioning",
        builder=_linear_hash_builder,
        expected_fragments=(
            "PARTITION BY LINEAR HASH (`id`)",
            "PARTITIONS 4",
        ),
        forbidden_fragments=("PARTITION BY HASH (`",),
    ),
    PartitionSyntaxCase(
        name="linear_key",
        description="LINEAR KEY partitioning",
        builder=_linear_key_builder,
        expected_fragments=(
            "PARTITION BY LINEAR KEY (`id`)",
            "PARTITIONS 4",
        ),
        forbidden_fragments=("PARTITION BY KEY (`",),
    ),
    PartitionSyntaxCase(
        name="range_maxvalue",
        description="MAXVALUE must terminate the RANGE definition list",
        builder=_range_maxvalue_builder,
        expected_fragments=(
            "PARTITION `p2026` VALUES LESS THAN ('2027-01-01')",
            "PARTITION `pmax` VALUES LESS THAN (MAXVALUE)",
        ),
        forbidden_fragments=("VALUES LESS THAN (MAXVALUE),",),
        ordered_fragments=(
            "PARTITION `p2026`",
            "PARTITION `pmax`",
            "MAXVALUE",
        ),
    ),
    PartitionSyntaxCase(
        name="hash_subpartition",
        description="SUBPARTITION BY HASH is accepted under RANGE",
        builder=_hash_subpartition_builder,
        expected_fragments=(
            "PARTITION BY RANGE (`created_at`)",
            "SUBPARTITION BY HASH (`id`) SUBPARTITIONS 4",
            "PARTITION `p2026` VALUES LESS THAN ('2027-01-01')",
        ),
        forbidden_fragments=("SUBPARTITION BY RANGE",),
    ),
    PartitionSyntaxCase(
        name="key_subpartition",
        description="SUBPARTITION BY KEY is accepted under RANGE",
        builder=_key_subpartition_builder,
        expected_fragments=(
            "PARTITION BY RANGE (`created_at`)",
            "SUBPARTITION BY KEY (`id`) SUBPARTITIONS 4",
        ),
        forbidden_fragments=(
            "SUBPARTITION BY HASH",
            "SUBPARTITION BY RANGE",
            "SUBPARTITION BY LIST",
        ),
    ),
    PartitionSyntaxCase(
        name="range_subpartition_refused",
        description="SUBPARTITION BY RANGE is refused by name, not downgraded",
        builder=_range_subpartition_refused,
        refusal_feature="SUBPARTITION BY RANGE",
    ),
    PartitionSyntaxCase(
        name="list_subpartition_refused",
        description="SUBPARTITION BY LIST is refused by name, not downgraded",
        builder=_list_subpartition_refused,
        refusal_feature="SUBPARTITION BY LIST",
    ),
    PartitionSyntaxCase(
        name="partition_options",
        description="MySQL partition definition storage options",
        builder=_partition_options_builder,
        expected_fragments=(
            "ENGINE `InnoDB`",
            "COMMENT 'hot tenant'",
            "MAX_ROWS 1000",
            "TABLESPACE `ts_hot`",
        ),
        forbidden_fragments=("MIN_ROWS",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_add_drop",
        description="ADD PARTITION and DROP PARTITION lifecycle pair",
        builder=_lifecycle_add_drop,
        expected_fragments=(
            "ALTER TABLE `events` ADD PARTITION",
            "PARTITION `p2026` VALUES LESS THAN (2026)",
            "ALTER TABLE `events` DROP PARTITION `p2026`",
        ),
        forbidden_fragments=("TRUNCATE PARTITION",),
        ordered_fragments=(
            "ALTER TABLE `events` ADD PARTITION",
            "ALTER TABLE `events` DROP PARTITION",
        ),
    ),
    PartitionSyntaxCase(
        name="lifecycle_reorganize",
        description="REORGANIZE PARTITION splits one partition into many",
        builder=_lifecycle_reorganize,
        expected_fragments=(
            "ALTER TABLE `events` REORGANIZE PARTITION `p2026` INTO (",
            "PARTITION `p2026_a` VALUES LESS THAN (2026)",
            "PARTITION `p2026_b` VALUES LESS THAN (2027)",
        ),
        forbidden_fragments=("REORGANIZE PARTITION `p2026` INTO ()",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_exchange",
        description="EXCHANGE PARTITION targets another table",
        builder=_lifecycle_exchange,
        expected_fragments=(
            "EXCHANGE PARTITION `p2026` WITH TABLE `events_archive`",
            "WITHOUT VALIDATION",
        ),
        forbidden_fragments=("WITH VALIDATION",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_coalesce",
        description="COALESCE PARTITION reduces the partition count",
        builder=_lifecycle_coalesce,
        expected_fragments=("ALTER TABLE `events` COALESCE PARTITION 2",),
        forbidden_fragments=("COALESCE PARTITION 0",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_truncate",
        description="TRUNCATE PARTITION empties named partitions",
        builder=_lifecycle_truncate,
        expected_fragments=("ALTER TABLE `events` TRUNCATE PARTITION `p2026`, `p2027`",),
    ),
    PartitionSyntaxCase(
        name="lifecycle_remove",
        description="REMOVE PARTITIONING drops the partitioning scheme",
        builder=_lifecycle_remove,
        expected_fragments=("ALTER TABLE `events` REMOVE PARTITIONING",),
        forbidden_fragments=("REMOVE PARTITIONING (",),
    ),
    PartitionSyntaxCase(
        name="maintenance_analyze_check_optimize_rebuild_repair",
        description="Per-partition maintenance statements stay one per action",
        builder=_maintenance_statements,
        expected_fragments=(
            "ALTER TABLE `events` ANALYZE PARTITION `p2026`, `p2027`",
            "ALTER TABLE `events` CHECK PARTITION `p2026`, `p2027`",
            "ALTER TABLE `events` OPTIMIZE PARTITION `p2026`, `p2027`",
            "ALTER TABLE `events` REBUILD PARTITION `p2026`, `p2027`",
            "ALTER TABLE `events` REPAIR PARTITION `p2026`, `p2027`",
        ),
        ordered_fragments=(
            "ANALYZE PARTITION",
            "CHECK PARTITION",
            "OPTIMIZE PARTITION",
            "REBUILD PARTITION",
            "REPAIR PARTITION",
        ),
    ),
]


@pytest.fixture(params=CASES, ids=[case.name for case in CASES])
def partition_syntax_case(request: pytest.FixtureRequest) -> PartitionSyntaxCase:
    """Yield one MySQL partition syntax case per pytest parameter."""
    return request.param
