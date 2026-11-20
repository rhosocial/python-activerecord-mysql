# MySQL Partitioning

MySQL supports table partitioning to improve management and query performance for large tables.

## Partitioning Strategies

| Strategy | Expression Class | Description |
|----------|-----------------|-------------|
| RANGE | `MySQLPartitionByRange` | Range-based partitioning, e.g. `PARTITION BY RANGE (id)` |
| RANGE COLUMNS | `MySQLPartitionByRangeColumns` | Multi-column range partitioning |
| LIST | `MySQLPartitionByList` | Value list partitioning |
| LIST COLUMNS | `MySQLPartitionByListColumns` | Multi-column value list partitioning |
| HASH | `MySQLPartitionByHash` | Hash partitioning, supports LINEAR |
| KEY | `MySQLPartitionByKey` | Like HASH, uses MySQL built-in hash function |

### Creating a Partitioned Table

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionByRange, MySQLPartitionDefinition, MySQLPartitionValue,
    MySQLPartitionMaxValue,
)

partition_by = MySQLPartitionByRange(
    dialect,
    keys=["created_at"],
    partitions=[
        MySQLPartitionDefinition("p_old", less_than=MySQLPartitionValue("2024-01-01")),
        MySQLPartitionDefinition("p_current", less_than=MySQLPartitionMaxValue()),
    ]
)
# sql: 'PARTITION BY RANGE (created_at) (PARTITION p_old VALUES LESS THAN ("2024-01-01"), PARTITION p_current VALUES LESS THAN MAXVALUE)'
```

## Partition Lifecycle Management

### ADD PARTITION

```python
add_part = MySQLAddPartitionExpression(
    dialect, table="orders",
    partitions=[MySQLPartitionDefinition("p_new", less_than=MySQLPartitionValue("2025-01-01"))],
)
```

### DROP PARTITION

```python
drop_part = MySQLDropPartitionExpression(dialect, table="orders", partitions=["p_old"])
```

### EXCHANGE PARTITION

```python
exchange = MySQLExchangePartitionExpression(
    dialect, table="orders", partition="p_current",
    exchange_table="orders_staging", with_validation=True,
)
```

## Partition Capabilities: Suggestions and Introspection

MySQL does not ship a separate partition-maintenance helper.  Partition DDL is
offered through the backend's **partition-suggestion** protocol, and the
catalogue side through the engine's own **partition introspection** family.
Together they are the single source for how this backend handles partitions.

A caller describes the target layout as an opaque plan -- a mapping or an object
with attributes such as `table`, `keys`, `definitions`, `partitions_count`,
`partition`, `into`, `names` and `cutoff`.  The dialect turns that plan into real
MySQL statement chains:

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionDefinition, MySQLPartitionStrategy, MySQLPartitionValue,
)

plan = {
    "table": "orders",
    "definitions": [
        MySQLPartitionDefinition("p2026", less_than=[MySQLPartitionValue(dialect, "2027-01-01")]),
        MySQLPartitionDefinition("p2027", less_than=[MySQLPartitionValue(dialect, "2028-01-01")]),
    ],
}

build = dialect.suggest_partition_build(MySQLPartitionStrategy.RANGE, plan)
add = dialect.suggest_partition_add(MySQLPartitionStrategy.RANGE, plan)
retention = dialect.suggest_partition_retention(
    MySQLPartitionStrategy.RANGE, {**plan, "cutoff": "2027-01-01"}
)
```

Each suggestion is a frozen value whose `operations` is one of three things: a
tuple of real MySQL expression nodes the dialect can render and the caller can
execute, `False` when this backend has no such mechanism for the strategy/plan,
or `None` when nothing needs doing.  The eight methods cover `build`, `add`,
`drop`, `retention`, `split`, `merge`, `table_alter` and `table_drop`; the dialect
formatter owns the exact SQL spelling.  For RANGE retention, a partition whose
upper bound is less than or equal to the cutoff is considered old, and the last
partition of a table is never dropped.

The catalogue side is answered by introspection:

```python
if dialect.supports_partition_introspection():
    partitions = backend.introspector.list_partitions("orders")
    for part in partitions:
        print(part.name, part.description)
```

`list_partitions()` returns this backend's `MySQLPartitionInfo` records (an
empty result means the table is not partitioned).  Core's partition-info probe
stays `False` because MySQL answers through its own switch; see
[Database Introspection](introspection.md) for the full probe table.

## Subpartitioning

MySQL supports subpartitioning only with `HASH` and `KEY` (and their `LINEAR`
variants).  `SUBPARTITION BY RANGE` or `LIST` raises `UnsupportedFeatureError`
instead of being silently downgraded.

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLSubpartitionClause, MySQLSubpartitionStrategy,
)

subpartition_by = MySQLSubpartitionClause(
    dialect,
    strategy=MySQLSubpartitionStrategy.HASH,
    expression=Column(dialect, "tenant_id"),
    count=4,
)
```

A partition definition may carry explicit `subpartition_definitions`; those
names override the template for that parent partition.

## Dialect Feature Detection

```python
if dialect.supports_table_partitioning():
    pass
if dialect.supports_exchange_partition():
    pass
```
