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

## Dialect Feature Detection

```python
if dialect.supports_table_partitioning():
    pass
if dialect.supports_exchange_partition():
    pass
```
