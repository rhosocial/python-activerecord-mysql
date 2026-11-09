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

## Backend-Level Maintenance

`MySQLPartitionMaintenance` turns a caller-owned plan into the four operations
an application needs: add missing partitions, report the partition tree,
validate the catalogue against the plan, and drop partitions older than a
cutoff.  It carries no table names, calendar vocabulary, or retention defaults.

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionDefinition, MySQLPartitionValue,
)
from rhosocial.activerecord.backend.impl.mysql.partition_maintenance import (
    MySQLPartitionMaintenance, MySQLPartitionPlan,
)

plan = MySQLPartitionPlan(
    "orders",
    (
        MySQLPartitionDefinition("p2026_01", less_than=[MySQLPartitionValue(dialect, "2026-02-01")]),
        MySQLPartitionDefinition("p2026_02", less_than=[MySQLPartitionValue(dialect, "2026-03-01")]),
    ),
)
maintenance = MySQLPartitionMaintenance(backend)

report = maintenance.ensure(plan)                 # add what is missing
report = maintenance.list("orders", plan=plan)    # tree + missing + orphans
report = maintenance.validate(plan)               # read-only findings
report = maintenance.drop_before(plan, cutoff, dry_run=True)
```

Planning rules are reported rather than hidden:

- a missing RANGE partition above the current maximum is appended with
  `ADD PARTITION`;
- a missing RANGE partition inside an existing partition's range is created by
  `REORGANIZE PARTITION` on that partition;
- a new partition after an existing `MAXVALUE` partition is folded into it by
  `REORGANIZE PARTITION`, which keeps a trailing `MAXVALUE` definition;
- a catalogue boundary or method that disagrees with the plan makes every
  split point uncertain, so `ensure` refuses and reports each missing
  definition in `skipped`; it never claims an addition it did not send;
- `drop_before` treats a partition ending exactly at the cutoff as older than
  it (upper bound less than or equal to the cutoff), matching PostgreSQL and
  Oracle, and never drops the last partition of a table;
- `drop_before` is a dry run unless `dry_run=False` is passed.

`validate` compares `PARTITION_NAME`, `PARTITION_METHOD` and
`PARTITION_DESCRIPTION` with the plan.  Missing definitions appear in
`missing`, catalogue partitions the plan does not name appear in `orphans`,
and method or boundary drift appears in `issues`.  It sends no DDL and
repairs nothing.  `list("orders", plan=plan)` fills the same `missing` and
`orphans` collections for callers that only want an inventory.

`ensure` and `drop_before` are statement-level, not transaction-level: MySQL
partition DDL implicitly commits.  A report describes what one statement did.
`AsyncMySQLPartitionMaintenance` offers the same methods with `await`.

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
