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

## 后端级维护

`MySQLPartitionMaintenance` 把调用方自有的计划变成四个操作：补建缺失分区、
报告分区树、校验目录与计划、按截止时间回收旧分区。它不包含表名、日历词汇或
保留策略默认值。

```python
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

report = maintenance.ensure(plan)                 # 补建缺失分区
report = maintenance.list("orders", plan=plan)    # 分区树 + missing + orphans
report = maintenance.validate(plan)               # 只读校验结果
report = maintenance.drop_before(plan, cutoff, dry_run=True)
```

规则会写进报告，而不是被悄悄绕过：

- 高于当前最大边界的缺失 RANGE 分区用 `ADD PARTITION` 追加；
- 落在已有分区区间内部的缺失分区，通过 `REORGANIZE PARTITION` 拆分该分区；
- 已存在 `MAXVALUE` 分区时，新分区会通过 `REORGANIZE PARTITION` 折叠进去，
  并保留末尾的 `MAXVALUE` 定义；
- 目录边界或分区方式与计划不一致时，所有拆分区间的依据都不再可靠，
  `ensure` 会拒绝执行，并把每个缺失分区写入 `skipped`；它不会把未执行的
  新增报告为成功；
- `drop_before` 认为上界等于截止时间的分区已经完全过期（上界小于等于截止时间），
  与 PostgreSQL、Oracle 一致；始终保留表的最后一个分区；
- `drop_before` 默认 dry-run，只有传入 `dry_run=False` 才执行。

`validate` 比较 `PARTITION_NAME`、`PARTITION_METHOD` 与
`PARTITION_DESCRIPTION`。缺失定义写入 `missing`，计划未命名的目录分区写入
`orphans`，分区方式或边界漂移写入 `issues`。它不发送任何 DDL，也不修复任何
东西。`list("orders", plan=plan)` 也会填好 `missing` 与 `orphans`，供只需要
盘点结果的调用方使用。

`ensure` / `drop_before` 是语句级而非事务级：MySQL 分区 DDL 会隐式提交。
`AsyncMySQLPartitionMaintenance` 提供同名异步方法。

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
