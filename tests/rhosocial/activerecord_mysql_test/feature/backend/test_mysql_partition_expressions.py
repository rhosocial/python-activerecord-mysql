"""MySQL partition expression construction and safety tests."""

from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLAddPartitionExpression,
    MySQLDropPartitionExpression,
    MySQLExchangePartitionExpression,
    MySQLRemovePartitioningExpression,
    MySQLCoalescePartitionExpression,
    MySQLAnalyzePartitionExpression,
    MySQLCheckPartitionExpression,
    MySQLOptimizePartitionExpression,
    MySQLRebuildPartitionExpression,
    MySQLRepairPartitionExpression,
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByRange,
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
    MySQLTruncatePartitionExpression,
)


@pytest.fixture
def dialect():
    """Create a MySQL dialect for expression tests."""
    return MySQLDialect()


def _partition_value(dialect, value):
    return MySQLPartitionValue(dialect, value)


def test_partition_by_range_expression(dialect):
    """PARTITION BY RANGE should format expression keys and bounds."""
    expr = MySQLPartitionByRange(
        dialect=dialect,
        keys=[Column(dialect, "created_year")],
        partitions=[
            MySQLPartitionDefinition(
                name="p2026",
                less_than=[_partition_value(dialect, 2027)],
            )
        ],
    )

    sql, params = expr.to_sql()

    assert "PARTITION BY RANGE" in sql
    assert "created_year" in sql
    assert "PARTITION" in sql
    assert "p2026" in sql
    assert "VALUES LESS THAN (2027)" in sql
    assert params == ()


@pytest.mark.parametrize(
    "expr_factory, expected",
    [
        (
            lambda dialect: MySQLPartitionByList(
                dialect=dialect,
                keys=[Column(dialect, "tenant_id")],
                partitions=[
                    MySQLPartitionDefinition(
                        name="p_tenant_10_20",
                        in_values=[_partition_value(dialect, 10), _partition_value(dialect, 20)],
                    )
                ],
            ),
            "PARTITION BY LIST",
        ),
        (
            lambda dialect: MySQLPartitionByListColumns(
                dialect=dialect,
                keys=[Column(dialect, "status")],
                partitions=[
                    MySQLPartitionDefinition(
                        name="p_active",
                        in_values=[_partition_value(dialect, "active"), _partition_value(dialect, "pending")],
                    )
                ],
            ),
            "PARTITION BY LIST COLUMNS",
        ),
    ],
)
def test_values_in_partition_definitions(dialect, expr_factory, expected):
    """LIST and LIST COLUMNS should render VALUES IN definitions."""
    sql, params = expr_factory(dialect).to_sql()

    assert expected in sql
    assert "VALUES IN" in sql
    assert "p_" in sql
    assert params == ()


def test_hash_and_key_partition_counts(dialect):
    """HASH and KEY partition expressions should support PARTITIONS count."""
    hash_sql, hash_params = MySQLPartitionByHash(
        dialect=dialect,
        keys=[Column(dialect, "id")],
        partitions_count=4,
    ).to_sql()
    key_sql, key_params = MySQLPartitionByKey(
        dialect=dialect,
        keys=[Column(dialect, "id")],
        partitions_count=4,
    ).to_sql()

    assert "PARTITION BY HASH" in hash_sql
    assert "PARTITIONS 4" in hash_sql
    assert hash_params == ()
    assert "PARTITION BY KEY" in key_sql
    assert "PARTITIONS 4" in key_sql
    assert key_params == ()


def test_linear_hash_and_key_partition_counts(dialect):
    """LINEAR HASH and LINEAR KEY should be expressible."""
    hash_sql, _ = MySQLPartitionByHash(
        dialect=dialect,
        keys=[Column(dialect, "id")],
        partitions_count=4,
        linear=True,
    ).to_sql()
    key_sql, _ = MySQLPartitionByKey(
        dialect=dialect,
        keys=[Column(dialect, "id")],
        partitions_count=4,
        linear=True,
    ).to_sql()

    assert "PARTITION BY LINEAR HASH" in hash_sql
    assert "PARTITION BY LINEAR KEY" in key_sql


def test_multiple_partition_maintenance_statements(dialect):
    """ADD, DROP, and TRUNCATE should format multiple partitions."""
    partitions = [
        MySQLPartitionDefinition(name="p2026_03", less_than=[_partition_value(dialect, "2026-04-01")]),
        MySQLPartitionDefinition(name="p2026_04", less_than=[_partition_value(dialect, "2026-05-01")]),
    ]

    add_sql, add_params = MySQLAddPartitionExpression(dialect, "events", partitions).to_sql()
    drop_sql, drop_params = MySQLDropPartitionExpression(dialect, "events", ["p2026_03", "p2026_04"]).to_sql()
    truncate_sql, truncate_params = MySQLTruncatePartitionExpression(
        dialect,
        "events",
        ["p2026_03", "p2026_04"],
    ).to_sql()

    assert "ADD PARTITION" in add_sql
    assert "p2026_03" in add_sql and "p2026_04" in add_sql
    assert add_params == ()
    assert "DROP PARTITION" in drop_sql
    assert "p2026_03" in drop_sql and "p2026_04" in drop_sql
    assert drop_params == ()
    assert "TRUNCATE PARTITION" in truncate_sql
    assert "p2026_03" in truncate_sql and "p2026_04" in truncate_sql
    assert truncate_params == ()


def test_exchange_partition_without_validation(dialect):
    """EXCHANGE PARTITION should support WITHOUT VALIDATION."""
    sql, params = MySQLExchangePartitionExpression(
        dialect,
        "events",
        "p2026",
        "events_archive",
        with_validation=False,
    ).to_sql()

    assert "EXCHANGE PARTITION" in sql
    assert "WITHOUT VALIDATION" in sql
    assert params == ()


def test_partition_definition_rejects_invalid_value_mode_combinations(dialect):
    """Partition definitions require exactly one value mode."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        MySQLPartitionDefinition(
            name="p_bad",
            less_than=[_partition_value(dialect, 10)],
            in_values=[_partition_value(dialect, 1)],
        )

    with pytest.raises(ValueError, match="requires less_than or in_values"):
        MySQLPartitionDefinition(name="p_bad")


def test_partition_value_rejects_unsafe_or_invalid_values(dialect):
    """Partition values should reject invalid types and non-finite numbers."""
    with pytest.raises(TypeError, match="must not be bool"):
        MySQLPartitionValue(dialect, True).to_sql()

    with pytest.raises(ValueError, match="float must be finite"):
        MySQLPartitionValue(dialect, float("inf"))

    with pytest.raises(ValueError, match="Decimal must be finite"):
        MySQLPartitionValue(dialect, Decimal("NaN")).to_sql()

    with pytest.raises(TypeError, match="partition value must be"):
        MySQLPartitionValue(dialect, object())


def test_partition_value_escapes_string_literals(dialect):
    """String boundary values should be escaped as SQL literals."""
    sql, params = MySQLPartitionValue(dialect, "x'); DROP TABLE users; --").to_sql()

    assert "DROP TABLE" in sql
    assert "''" in sql
    assert params == ()


def test_maxvalue_uses_capability(dialect):
    """MAXVALUE should format through the partition value formatter."""
    sql, params = MySQLPartitionMaxValue(dialect).to_sql()

    assert sql == "MAXVALUE"
    assert params == ()


def test_partition_definition_options_are_formatted(dialect):
    """Supported partition definition options should render explicitly."""
    definition = MySQLPartitionDefinition(
        name="p2026",
        less_than=[_partition_value(dialect, "2027-01-01")],
        dialect_options={
            "engine": "InnoDB",
            "comment": "tenant's partition",
            "max_rows": 1000,
            "tablespace": "ts_hot",
        },
    )

    sql, params = dialect.format_partition_definition(definition)

    assert "ENGINE" in sql and "InnoDB" in sql
    assert "COMMENT" in sql and "tenant''s partition" in sql
    assert "MAX_ROWS 1000" in sql
    assert "TABLESPACE" in sql and "ts_hot" in sql
    assert params == ()


def test_partition_definition_options_reject_invalid_options(dialect):
    """Unsupported or invalid partition options should fail clearly."""
    with pytest.raises(ValueError, match="Unsupported partition definition option"):
        dialect.format_partition_definition_options({"unknown": "value"})

    with pytest.raises(TypeError, match="max_rows option"):
        dialect.format_partition_definition_options({"max_rows": -1})

def test_extended_partition_maintenance_expressions(dialect):
    """MySQL maintenance expressions should delegate to public formatters."""
    cases = [
        (MySQLRemovePartitioningExpression(dialect, "events"), "REMOVE PARTITIONING"),
        (MySQLCoalescePartitionExpression(dialect, "events", 2), "COALESCE PARTITION 2"),
        (MySQLAnalyzePartitionExpression(dialect, "events", ["p0", "p1"]), "ANALYZE PARTITION"),
        (MySQLCheckPartitionExpression(dialect, "events", ["p0", "p1"]), "CHECK PARTITION"),
        (MySQLOptimizePartitionExpression(dialect, "events", ["p0", "p1"]), "OPTIMIZE PARTITION"),
        (MySQLRebuildPartitionExpression(dialect, "events", ["p0", "p1"]), "REBUILD PARTITION"),
        (MySQLRepairPartitionExpression(dialect, "events", ["p0", "p1"]), "REPAIR PARTITION"),
    ]

    for expr, expected in cases:
        sql, params = expr.to_sql()
        assert expected in sql
        assert params == ()


def test_extended_partition_maintenance_rejects_invalid_arguments(dialect):
    """Maintenance expressions should reject invalid counts and empty lists."""
    with pytest.raises(ValueError, match="positive integer"):
        MySQLCoalescePartitionExpression(dialect, "events", 0)

    with pytest.raises(ValueError, match="partitions must not be empty"):
        MySQLAnalyzePartitionExpression(dialect, "events", []).to_sql()

