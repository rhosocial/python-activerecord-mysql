# tests/rhosocial/activerecord_mysql_test/feature/partition/test_partition_suggestions.py
"""Offline contract tests for the 8 MySQL partition suggestion methods.

No server is needed: the dialect's own formatters render each suggestion's
expression chain, so these tests verify both the tri-state shape and that the
returned nodes are real MySQL statements/clauses rather than hand-built SQL.
"""

import dataclasses

import pytest

from rhosocial.activerecord.backend.dialect.protocols import (
    PartitionAddSuggestionSupport,
    PartitionBuildSuggestionSupport,
    PartitionDropSuggestionSupport,
    PartitionMergeSuggestionSupport,
    PartitionRetentionSuggestionSupport,
    PartitionSplitSuggestionSupport,
    PartitionTableAlterSuggestionSupport,
    PartitionTableDropSuggestionSupport,
)
from rhosocial.activerecord.backend.expression import Column, DropTableStatement
from rhosocial.activerecord.backend.suggestion import (
    PartitionAddSuggestion,
    PartitionBuildSuggestion,
    PartitionDropSuggestion,
    PartitionMergeSuggestion,
    PartitionRetentionSuggestion,
    PartitionSplitSuggestion,
    PartitionTableAlterSuggestion,
    PartitionTableDropSuggestion,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLAddPartitionExpression,
    MySQLCoalescePartitionExpression,
    MySQLDropPartitionExpression,
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
    MySQLPartitionDefinition,
    MySQLPartitionStrategy,
    MySQLPartitionValue,
    MySQLRemovePartitioningExpression,
    MySQLReorganizePartitionExpression,
)

PROTOCOLS = (
    ("build", PartitionBuildSuggestionSupport, PartitionBuildSuggestion),
    ("add", PartitionAddSuggestionSupport, PartitionAddSuggestion),
    ("drop", PartitionDropSuggestionSupport, PartitionDropSuggestion),
    ("retention", PartitionRetentionSuggestionSupport, PartitionRetentionSuggestion),
    ("table_drop", PartitionTableDropSuggestionSupport, PartitionTableDropSuggestion),
    ("table_alter", PartitionTableAlterSuggestionSupport, PartitionTableAlterSuggestion),
    ("split", PartitionSplitSuggestionSupport, PartitionSplitSuggestion),
    ("merge", PartitionMergeSuggestionSupport, PartitionMergeSuggestion),
)


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


def _range(dialect, name, bound):
    return MySQLPartitionDefinition(name=name, less_than=[MySQLPartitionValue(dialect, bound)])


def _list(dialect, name, value):
    return MySQLPartitionDefinition(name=name, in_values=[MySQLPartitionValue(dialect, value)])


def _sql(operations):
    return " ".join(expr.to_sql()[0] for expr in operations)


def test_dialect_satisfies_all_eight_protocols(dialect):
    for _name, protocol, _dataclass in PROTOCOLS:
        assert isinstance(dialect, protocol)


def test_suggestion_values_are_frozen_dataclasses(dialect):
    for name, _protocol, cls in PROTOCOLS:
        suggestion = getattr(dialect, f"suggest_partition_{name}")(
            MySQLPartitionStrategy.RANGE, None
        )
        assert isinstance(suggestion, cls)
        assert dataclasses.is_dataclass(suggestion)
        with pytest.raises(dataclasses.FrozenInstanceError):
            suggestion.operations = False


def test_build_returns_real_partition_by_clauses(dialect):
    definitions = [_range(dialect, "p0", 100), _range(dialect, "p1", 200)]
    list_definitions = [_list(dialect, "p0", "a"), _list(dialect, "p1", "b")]
    cases = (
        (MySQLPartitionStrategy.RANGE, {"definitions": definitions}, MySQLPartitionByRange),
        (
            MySQLPartitionStrategy.RANGE_COLUMNS,
            {"definitions": definitions},
            MySQLPartitionByRangeColumns,
        ),
        (MySQLPartitionStrategy.LIST, {"definitions": list_definitions}, MySQLPartitionByList),
        (
            MySQLPartitionStrategy.LIST_COLUMNS,
            {"definitions": list_definitions},
            MySQLPartitionByListColumns,
        ),
        (MySQLPartitionStrategy.HASH, {"partitions_count": 4}, MySQLPartitionByHash),
        (MySQLPartitionStrategy.LINEAR_HASH, {"partitions_count": 4}, MySQLPartitionByHash),
        (MySQLPartitionStrategy.KEY, {"partitions_count": 4}, MySQLPartitionByKey),
        (MySQLPartitionStrategy.LINEAR_KEY, {"partitions_count": 4}, MySQLPartitionByKey),
    )
    for strategy, extra, clause_class in cases:
        plan = {"keys": [Column(dialect, "id")], **extra}
        suggestion = dialect.suggest_partition_build(strategy, plan)
        assert len(suggestion.operations) == 1
        assert isinstance(suggestion.operations[0], clause_class)
        assert "PARTITION BY" in _sql(suggestion.operations)
    assert "LINEAR HASH" in _sql(
        dialect.suggest_partition_build(
            MySQLPartitionStrategy.LINEAR_HASH,
            {"keys": [Column(dialect, "id")], "partitions_count": 4},
        ).operations
    )


def test_build_declines_unknown_strategy(dialect):
    suggestion = dialect.suggest_partition_build("SPATIAL", {"keys": [Column(dialect, "id")]})
    assert suggestion.operations is False
    assert dialect.suggest_partition_build(MySQLPartitionStrategy.RANGE, {}).operations is False


def test_table_drop_is_drop_table_statement(dialect):
    suggestion = dialect.suggest_partition_table_drop(MySQLPartitionStrategy.RANGE, {"table": "t"})
    assert len(suggestion.operations) == 1
    assert isinstance(suggestion.operations[0], DropTableStatement)
    assert _sql(suggestion.operations).upper().startswith("DROP TABLE")
    assert (
        dialect.suggest_partition_table_drop(MySQLPartitionStrategy.RANGE, {}).operations is False
    )


def test_table_alter_remove_and_coalesce(dialect):
    remove = dialect.suggest_partition_table_alter(MySQLPartitionStrategy.RANGE, {"table": "t"})
    assert isinstance(remove.operations[0], MySQLRemovePartitioningExpression)
    assert "REMOVE PARTITIONING" in _sql(remove.operations)

    coalesce = dialect.suggest_partition_table_alter(
        MySQLPartitionStrategy.HASH,
        {"table": "t", "mode": "coalesce", "count": 2},
    )
    assert isinstance(coalesce.operations[0], MySQLCoalescePartitionExpression)
    assert "COALESCE PARTITION 2" in _sql(coalesce.operations)

    # COALESCE has no RANGE/LIST meaning, and a missing count is refused.
    assert (
        dialect.suggest_partition_table_alter(
            MySQLPartitionStrategy.RANGE, {"table": "t", "mode": "coalesce", "count": 2}
        ).operations
        is False
    )
    assert (
        dialect.suggest_partition_table_alter(
            MySQLPartitionStrategy.HASH, {"table": "t", "mode": "coalesce"}
        ).operations
        is False
    )


def test_add_append_and_reorganize(dialect):
    append = dialect.suggest_partition_add(
        MySQLPartitionStrategy.RANGE,
        {"table": "t", "definitions": [_range(dialect, "p2", 300)]},
    )
    assert isinstance(append.operations[0], MySQLAddPartitionExpression)
    assert "ADD PARTITION" in _sql(append.operations)

    reorg = dialect.suggest_partition_add(
        MySQLPartitionStrategy.RANGE,
        {
            "table": "t",
            "partition": "p0",
            "into": [_range(dialect, "p0", 50), _range(dialect, "pX", 100)],
        },
    )
    assert isinstance(reorg.operations[0], MySQLReorganizePartitionExpression)
    assert "REORGANIZE PARTITION" in _sql(reorg.operations)

    # HASH/KEY growth is `ADD PARTITION PARTITIONS n`, which has no node here.
    assert (
        dialect.suggest_partition_add(
            MySQLPartitionStrategy.HASH,
            {"table": "t", "definitions": [_range(dialect, "p2", 300)]},
        ).operations
        is False
    )
    assert dialect.suggest_partition_add(MySQLPartitionStrategy.RANGE, {}).operations is False


def test_drop_returns_drop_partition_and_tri_state(dialect):
    dropped = dialect.suggest_partition_drop(
        MySQLPartitionStrategy.RANGE, {"table": "t", "names": ["p0", "p1"]}
    )
    assert isinstance(dropped.operations[0], MySQLDropPartitionExpression)
    assert "DROP PARTITION" in _sql(dropped.operations)
    assert (
        dialect.suggest_partition_drop(MySQLPartitionStrategy.RANGE, {"table": "t"}).operations
        is None
    )
    assert (
        dialect.suggest_partition_drop(
            MySQLPartitionStrategy.HASH, {"table": "t", "names": ["p0"]}
        ).operations
        is False
    )


def test_split_uses_reorganize_partition(dialect):
    suggestion = dialect.suggest_partition_split(
        MySQLPartitionStrategy.RANGE,
        {
            "table": "t",
            "partition": "p0",
            "into": [_range(dialect, "p0", 50), _range(dialect, "pX", 100)],
        },
    )
    assert isinstance(suggestion.operations[0], MySQLReorganizePartitionExpression)
    assert "REORGANIZE PARTITION" in _sql(suggestion.operations)
    assert (
        dialect.suggest_partition_split(MySQLPartitionStrategy.HASH, {"table": "t"}).operations
        is False
    )


def test_merge_is_always_false(dialect):
    for strategy in MySQLPartitionStrategy:
        assert dialect.suggest_partition_merge(strategy, {}).operations is False


def test_retention_drops_old_partitions_and_keeps_last(dialect):
    definitions = [
        _range(dialect, "p0", 100),
        _range(dialect, "p1", 200),
        _range(dialect, "p2", 300),
    ]
    plan = {"table": "t", "definitions": definitions, "cutoff": 250}
    suggestion = dialect.suggest_partition_retention(MySQLPartitionStrategy.RANGE, plan)
    assert isinstance(suggestion.operations[0], MySQLDropPartitionExpression)
    assert suggestion.operations[0].partitions == ["p0", "p1"]
    assert "DROP PARTITION" in _sql(suggestion.operations)

    # When every partition qualifies, the newest one is kept (MySQL cannot drop the last).
    all_old = {**plan, "cutoff": 300}
    kept = dialect.suggest_partition_retention(MySQLPartitionStrategy.RANGE, all_old)
    assert kept.operations[0].partitions == ["p0", "p1"]

    nothing = {**plan, "cutoff": 50}
    assert (
        dialect.suggest_partition_retention(MySQLPartitionStrategy.RANGE, nothing).operations
        is None
    )
    assert (
        dialect.suggest_partition_retention(MySQLPartitionStrategy.LIST, plan).operations is False
    )
