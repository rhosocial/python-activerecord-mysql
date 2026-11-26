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
from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionByRange, MySQLPartitionValue, MySQLPartitionMaxValue,
)

# RANGE 分区
partition_by = MySQLPartitionByRange(
    dialect,
    keys=["created_at"],
    partitions=[
        PartitionDefinitionExpression(dialect, "p_old", less_than=[MySQLPartitionValue(dialect, "2024-01-01")]),
        PartitionDefinitionExpression(dialect, "p_current", less_than=[MySQLPartitionMaxValue(dialect)]),
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
        PartitionDefinitionExpression(dialect, "p_new", less_than=[MySQLPartitionValue(dialect, "2025-01-01")]),
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

## 分区能力：建议与内省

MySQL 不提供独立的分区维护辅助类。分区 DDL 通过后端的**分区建议**协议提供，
目录侧由引擎自身的**分区内省**家族回答；二者共同构成本后端处理分区的唯一来源。

调用方把目标布局描述为一个不透明的 plan —— 可以是映射，也可以是带 `table`、
`keys`、`definitions`、`partitions_count`、`partition`、`into`、`names`、`cutoff`
等属性的对象。dialect 把该 plan 转成真实的 MySQL 语句链：

```python
from rhosocial.activerecord.backend.expression import Column, PartitionByRangeClause
from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression
from rhosocial.activerecord.backend.impl.mysql.expression.partition import MySQLPartitionValue

strategy = PartitionByRangeClause(dialect, [Column(dialect, "id")])
plan = {
    "table": "orders",
    "definitions": [
        PartitionDefinitionExpression(dialect, "p2026", less_than=[MySQLPartitionValue(dialect, "2027-01-01")]),
        PartitionDefinitionExpression(dialect, "p2027", less_than=[MySQLPartitionValue(dialect, "2028-01-01")]),
    ],
}

build = dialect.suggest_partition_build(strategy, plan)
add = dialect.suggest_partition_add(strategy, plan)
retention = dialect.suggest_partition_retention(
    strategy, {**plan, "cutoff": "2027-01-01"}
)
```

每个建议都是冻结值，其 `operations` 有三种可能：可由 dialect 渲染、由调用方执行的
真实 MySQL 表达式节点元组；本后端对该策略/plan 没有相应机制时的 `False`；
以及无需操作时返回的 `None`。八个方法覆盖 `build`、`add`、`drop`、`retention`、
`split`、`merge`、`table_alter` 与 `table_drop`，SQL 的具体拼写由 方言格式化函数负责。
对 RANGE 保留策略，上界小于等于截止时间的分区视为过期，且始终保留表的最后一个分区。

目录侧通过内省回答：

```python
if dialect.supports_partition_metadata_introspection():
    state = backend.introspector.get_partition_state("orders")
    if state.scheme is None:
        print("未分区")
    for bound in state.bounds:
        print(bound.name, bound.upper, bound.is_maxvalue)
```

`get_partition_state()` 返回核心库的中立 `PartitionState`：`scheme is None`
表示该表未分区，`upper` 携带 `PARTITION_DESCRIPTION`，`MAXVALUE` 会设置
`is_maxvalue`，而每个分区的 `row_count` / `size_bytes` 仅在
`include_stats=True` 时填充。上面这个探针来自核心库，也是本后端分区家族
唯一的探针；完整的探针表见 [数据库内省](introspection.md)。

## 子分区

MySQL 只支持 `HASH` 与 `KEY`（及其 `LINEAR` 变体）子分区。
`SUBPARTITION BY RANGE` 或 `LIST` 会抛出 `UnsupportedFeatureError`，不会静默降级。

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

分区定义可携带显式 `subpartition_definitions`，这些名称会覆盖父分区的模板。

## 方言检查

```python
if dialect.supports_table_partitioning():
    # 支持表分区

if dialect.supports_range_columns_partitioning():
    # 支持 RANGE COLUMNS 分区

if dialect.supports_exchange_partition():
    # 支持 EXCHANGE PARTITION
```
