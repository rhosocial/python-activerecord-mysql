# tests/rhosocial/activerecord_mysql_test/feature/partition/test_partition_subpartition_syntax.py
"""Offline MySQL subpartition syntax and capability-limit tests.

These tests never connect to a server.  They only render subpartition expression
nodes through the dialect's own formatters, so they verify that HASH/KEY
subpartitioning is accepted, RANGE/LIST is refused by name, and explicit
per-partition subpartition definitions still render.  The former maintenance
planner tests that shared this module were retired with the partition
maintenance protocol; suggestion behaviour is covered by test_partition_suggestions.py.
"""

import pytest

from rhosocial.activerecord.backend.expression.statements import (
    PartitionDefinitionExpression,
    SubpartitionDefinitionExpression,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
    MySQLPartitionValue,
    MySQLSubpartitionClause,
    MySQLSubpartitionStrategy,
)


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


def _value(dialect, value):
    return MySQLPartitionValue(dialect, value)


# --- subpartition capability limits ----------------------------------------


def test_subpartition_hash_and_key_are_accepted(dialect):
    for strategy in (
        MySQLSubpartitionStrategy.HASH,
        MySQLSubpartitionStrategy.KEY,
        MySQLSubpartitionStrategy.LINEAR_HASH,
        MySQLSubpartitionStrategy.LINEAR_KEY,
    ):
        clause = MySQLSubpartitionClause(
            dialect,
            strategy=strategy,
            expression=Column(dialect, "id"),
            count=2,
        )
        sql, params = clause.to_sql()
        assert f"SUBPARTITION BY {strategy.value}" in sql
        assert "`id`" in sql
        assert "SUBPARTITIONS 2" in sql
        assert params == ()


@pytest.mark.parametrize("strategy", ["RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"])
def test_subpartition_range_and_list_are_refused_by_name(dialect, strategy):
    with pytest.raises(UnsupportedFeatureError, match="SUBPARTITION BY"):
        MySQLSubpartitionClause(dialect, strategy=strategy)


def test_subpartition_range_is_not_silently_downgraded(dialect):
    with pytest.raises(UnsupportedFeatureError) as caught:
        MySQLSubpartitionClause(dialect, strategy="RANGE")
    assert "RANGE" in caught.value.feature_name
    assert "HASH" in (caught.value.suggestion or "")


def test_explicit_per_partition_subpartition_definitions(dialect):
    expression = MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p2026",
                less_than=[_value(dialect, "2027-01-01")],
                subpartitions=[
                    SubpartitionDefinitionExpression(dialect, "p2026_s0"),
                    SubpartitionDefinitionExpression(dialect, "p2026_s1"),
                ],
            ),
            PartitionDefinitionExpression(
                dialect,
                "p2027",
                less_than=[_value(dialect, "2028-01-01")],
                subpartitions=[
                    SubpartitionDefinitionExpression(dialect, "p2027_s0"),
                ],
            ),
        ],
        subpartition_by=MySQLSubpartitionClause(
            dialect,
            strategy=MySQLSubpartitionStrategy.HASH,
            expression=Column(dialect, "tenant_id"),
            count=2,
        ),
    )

    sql, params = expression.to_sql()

    assert sql.index("SUBPARTITION BY HASH") < sql.index("PARTITION `p2026`")
    assert "`p2026_s0`" in sql and "`p2026_s1`" in sql
    assert "`p2027_s0`" in sql
    assert params == ()


def test_subpartition_definition_options_still_render_after_rejection(dialect):
    expression = MySQLPartitionByRangeColumns(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            PartitionDefinitionExpression(
                dialect,
                "p0",
                less_than=[_value(dialect, "2026-01-01")],
                subpartitions=[SubpartitionDefinitionExpression(dialect, "s0")],
            )
        ],
        subpartition_by=MySQLSubpartitionClause(
            dialect,
            strategy=MySQLSubpartitionStrategy.KEY,
            expression=Column(dialect, "id"),
            count=1,
        ),
    )
    sql, _ = expression.to_sql()
    assert "SUBPARTITION BY KEY" in sql
    assert "`id`" in sql
    assert "`s0`" in sql
