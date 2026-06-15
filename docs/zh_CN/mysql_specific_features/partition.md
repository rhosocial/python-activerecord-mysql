# MySQL 分区

MySQL 支持表分区以改善大表的管理和查询性能。

## 分区策略

MySQL 支持以下分区策略：

| 策略 | 表达式类 | 说明 |
|------|---------|------|
| RANGE | `MySQLPartitionByRange` | 按范围分区，如 `PARTITION BY RANGE (id)` |
| RANGE COLUMNS | `MySQLPartitionByRangeColumns` | 按多列范围分区 |
| LIST | `MySQLPartitionByList` | 按值列表分区 |
| LIST COLUMNS | `MySQLPartitionByListColumns` | 按多列值列表分区 |
| HASH | `MySQLPartitionByHash` | 哈希分区，支持 LINEAR |
| KEY | `MySQLPartitionByKey` | 类似 HASH，使用 MySQL 内置哈希函数 |

### 创建分区表

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionByRange, MySQLPartitionDefinition, MySQLPartitionValue,
    MySQLPartitionMaxValue,
)

# RANGE 分区
partition_by = MySQLPartitionByRange(
    dialect,
    keys=["created_at"],
    partitions=[
        MySQLPartitionDefinition("p_old", less_than=MySQLPartitionValue("2024-01-01")),
        MySQLPartitionDefinition("p_current", less_than=MySQLPartitionMaxValue()),
    ]
)

# 在 CREATE TABLE 中使用
# sql: 'PARTITION BY RANGE (created_at) (PARTITION p_old VALUES LESS THAN ("2024-01-01"), PARTITION p_current VALUES LESS THAN MAXVALUE)'
```

## 分区生命周期管理

### ADD PARTITION

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLAddPartitionExpression,
)

add_part = MySQLAddPartitionExpression(
    dialect,
    table="orders",
    partitions=[
        MySQLPartitionDefinition("p_new", less_than=MySQLPartitionValue("2025-01-01")),
    ]
)
# sql: 'ALTER TABLE orders ADD PARTITION (PARTITION p_new VALUES LESS THAN ("2025-01-01"))'
```

### DROP PARTITION

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import MySQLDropPartitionExpression

drop_part = MySQLDropPartitionExpression(dialect, table="orders", partitions=["p_old"])
# sql: 'ALTER TABLE orders DROP PARTITION p_old'
```

### EXCHANGE PARTITION

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import MySQLExchangePartitionExpression

exchange = MySQLExchangePartitionExpression(
    dialect, table="orders", partition="p_current",
    exchange_table="orders_staging", with_validation=True
)
# sql: 'ALTER TABLE orders EXCHANGE PARTITION p_current WITH TABLE orders_staging WITH VALIDATION'
```

## 辅助工具

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition_lifecycle import (
    MySQLAddPartitionHelper, MySQLDropOldestPartitionHelper,
)

# 批量添加分区（自动命名）
helper = MySQLAddPartitionHelper(dialect, "orders", [less_than_value1, less_than_value2])
for expr in helper:
    # 执行每个 ADD PARTITION
    pass

# 删除最旧分区
helper = MySQLDropOldestPartitionHelper(dialect, "orders")
for expr in helper:
    pass
```

## 分区维护

| 操作 | 表达式 | 说明 |
|------|--------|------|
| 分析 | `MySQLAnalyzePartitionExpression` | 更新索引统计 |
| 检查 | `MySQLCheckPartitionExpression` | 检查数据一致性 |
| 优化 | `MySQLOptimizePartitionExpression` | 回收空间 |
| 重建 | `MySQLRebuildPartitionExpression` | 重建分区 |
| 修复 | `MySQLRepairPartitionExpression` | 修复损坏 |

## 方言检查

```python
if dialect.supports_table_partitioning():
    # 支持表分区

if dialect.supports_range_columns_partitioning():
    # 支持 RANGE COLUMNS 分区

if dialect.supports_exchange_partition():
    # 支持 EXCHANGE PARTITION
```
