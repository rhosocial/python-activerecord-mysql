# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/ddl/partition_syntax_fixtures.py
"""Fixture-driven MySQL partition syntax matrix.

Each case describes one MySQL partition syntax family: how to build it,
which fragments its rendered SQL must contain, which must not appear, and
which planning, refusal or maintenance contract it exercises.
``partition_syntax_case`` turns that description into a pytest parameter, so
the test module stays free of per-family branches.

The matrix is offline.  ``live_setup`` and ``live_check`` are reserved for a
server-backed extension; every case leaves them unset today.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

import pytest

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
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLPartitionOptions,
    MySQLPartitionValue,
    MySQLRebuildPartitionExpression,
    MySQLRemovePartitioningExpression,
    MySQLReorganizePartitionExpression,
    MySQLRepairPartitionExpression,
    MySQLSubpartitionClause,
    MySQLSubpartitionStrategy,
    MySQLTruncatePartitionExpression,
)
from rhosocial.activerecord.backend.impl.mysql.partition_maintenance import (
    MySQLPartitionPlan,
)

Builder = Callable[[MySQLDialect], Any]


@dataclass(frozen=True)
class MaintenanceScenario:
    """Offline expectation for ``ensure`` / ``list`` / ``drop_before``.

    Attributes:
        rows: Callable returning ``information_schema.PARTITIONS``-shaped rows.
        plan: Callable building the caller-owned plan for the fake backend.
        cutoff: Inclusive retention cutoff passed to ``drop_before``.
        expected_existing: Top-level names the fake table currently has.
        expected_missing: Names ``ensure`` must report missing.
        expected_added: Names ``ensure`` must add in its one DDL statement.
        expected_skipped: Names the planner must report as skipped.
        expected_dropped: Names ``drop_before`` must report as dropped.
        expected_ensure_fragments: Fragments the ADD statement must contain.
        expected_drop_fragments: Fragments the DROP statement must contain.
    """

    rows: Callable[[], Sequence[Mapping[str, Any]]]
    plan: Callable[[MySQLDialect], MySQLPartitionPlan]
    cutoff: Any
    expected_existing: Tuple[str, ...]
    expected_missing: Tuple[str, ...]
    expected_added: Tuple[str, ...]
    expected_skipped: Tuple[str, ...]
    expected_dropped: Tuple[str, ...]
    expected_ensure_fragments: Tuple[str, ...]
    expected_drop_fragments: Tuple[str, ...]


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
        plan: Optional valid :class:`MySQLPartitionPlan` factory.
        invalid_plan: Optional factory that must raise ``ValueError``.
        invalid_plan_match: ``ValueError`` message fragment for ``invalid_plan``.
        maintenance: Optional offline maintenance scenario.
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
    plan: Optional[Callable[[MySQLDialect], MySQLPartitionPlan]] = None
    invalid_plan: Optional[Callable[[MySQLDialect], MySQLPartitionPlan]] = None
    invalid_plan_match: str = ""
    maintenance: Optional[MaintenanceScenario] = None
    live_setup: Optional[Callable[..., Any]] = None
    live_check: Optional[Callable[..., Any]] = None


def _value(dialect: MySQLDialect, value: Any) -> MySQLPartitionValue:
    """Build a MySQL partition boundary literal."""
    return MySQLPartitionValue(dialect, value)


def _range_definition(
    dialect: MySQLDialect,
    name: str,
    upper_bound: Any,
) -> MySQLPartitionDefinition:
    """Build a RANGE definition, using MAXVALUE when ``upper_bound`` is None."""
    if upper_bound is None:
        return MySQLPartitionDefinition(
            name,
            less_than=[MySQLPartitionMaxValue(dialect)],
        )
    return MySQLPartitionDefinition(
        name,
        less_than=[_value(dialect, upper_bound)],
    )


def _list_definition(
    dialect: MySQLDialect,
    name: str,
    values: Sequence[Any],
) -> MySQLPartitionDefinition:
    """Build a LIST definition with one boundary row of literal values."""
    return MySQLPartitionDefinition(
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
            MySQLPartitionDefinition(
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
            MySQLPartitionDefinition(
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
            MySQLPartitionDefinition(
                "p2026",
                less_than=[_value(dialect, 2027)],
                partition_options=MySQLPartitionOptions(
                    engine="InnoDB",
                    comment="hot tenant",
                    max_rows=1000,
                    tablespace="ts_hot",
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


# --- Plan factories --------------------------------------------------------


def _range_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026", "2026-01-01"),
            _range_definition(dialect, "p2027", "2027-01-01"),
        ),
    )


def _range_columns_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            MySQLPartitionDefinition(
                "p2026",
                less_than=[_value(dialect, 2026), _value(dialect, 6)],
            ),
            MySQLPartitionDefinition(
                "p2027",
                less_than=[_value(dialect, 2027), _value(dialect, 6)],
            ),
        ),
    )


def _list_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _list_definition(dialect, "p_active", ["active"]),
            _list_definition(dialect, "p_pending", ["pending"]),
        ),
    )


def _list_columns_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            MySQLPartitionDefinition(
                "p_us",
                in_values=[[_value(dialect, "us"), _value(dialect, "active")]],
            ),
            MySQLPartitionDefinition(
                "p_eu",
                in_values=[[_value(dialect, "eu"), _value(dialect, "active")]],
            ),
        ),
    )


def _maxvalue_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026", "2027-01-01"),
            _range_definition(dialect, "pmax", None),
        ),
    )


def _maintenance_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026_01", "2026-02-01"),
            _range_definition(dialect, "p2026_02", "2026-03-01"),
            _range_definition(dialect, "p2026_03", "2026-04-01"),
            _range_definition(dialect, "p2026_04", "2026-05-01"),
        ),
    )


def _unsorted_range_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2027", "2027-01-01"),
            _range_definition(dialect, "p2026", "2026-01-01"),
        ),
    )


def _duplicate_name_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026", "2027-01-01"),
            _range_definition(dialect, "p2026", "2028-01-01"),
        ),
    )


def _mixed_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "p2026", "2027-01-01"),
            _list_definition(dialect, "p_active", ["active"]),
        ),
    )


def _maxvalue_not_last_plan(dialect: MySQLDialect) -> MySQLPartitionPlan:
    return MySQLPartitionPlan(
        "events",
        (
            _range_definition(dialect, "pmax", None),
            _range_definition(dialect, "p2026", "2027-01-01"),
        ),
    )


# --- Maintenance rows ------------------------------------------------------


def _row(name: str, description: str) -> Mapping[str, Any]:
    """Build one ``information_schema.PARTITIONS`` row for the fake backend."""
    return {
        "name": name,
        "subname": None,
        "method": "RANGE",
        "submethod": None,
        "description": description,
        "table_rows": 1,
        "data_length": 2,
        "index_length": 3,
    }


def _existing_rows() -> Tuple[Mapping[str, Any], ...]:
    return (
        _row("p2026_01", "2026-02-01"),
        _row("p2026_02", "2026-03-01"),
        _row("p2026_03", "2026-04-01"),
    )


_MAINTENANCE_SCENARIO = MaintenanceScenario(
    rows=_existing_rows,
    plan=_maintenance_plan,
    cutoff="2026-02-01",
    expected_existing=("p2026_01", "p2026_02", "p2026_03"),
    expected_missing=("p2026_04",),
    expected_added=("p2026_04",),
    expected_skipped=(),
    expected_dropped=("p2026_01",),
    expected_ensure_fragments=(
        "ALTER TABLE `events` ADD PARTITION",
        "PARTITION `p2026_04` VALUES LESS THAN ('2026-05-01')",
    ),
    expected_drop_fragments=(
        "ALTER TABLE `events` DROP PARTITION `p2026_01`",
    ),
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
        plan=_range_plan,
        invalid_plan=_unsorted_range_plan,
        invalid_plan_match="ascending order",
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
        plan=_range_columns_plan,
        invalid_plan=_duplicate_name_plan,
        invalid_plan_match="must be unique",
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
        plan=_list_plan,
        invalid_plan=_mixed_plan,
        invalid_plan_match="not both",
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
        plan=_list_columns_plan,
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
        plan=_maxvalue_plan,
        invalid_plan=_maxvalue_not_last_plan,
        invalid_plan_match="MAXVALUE partition must be the last",
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
    PartitionSyntaxCase(
        name="maintenance_ensure_list_drop_before",
        description="Plan-driven ensure, list and drop_before with a fake backend",
        maintenance=_MAINTENANCE_SCENARIO,
    ),
]


@pytest.fixture(params=CASES, ids=[case.name for case in CASES])
def partition_syntax_case(request: pytest.FixtureRequest) -> PartitionSyntaxCase:
    """Yield one MySQL partition syntax case per pytest parameter."""
    return request.param
