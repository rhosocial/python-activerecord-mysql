# DDL 操作

MySQL 后端支持与核心库相同的类型安全 DDL 表达式，并扩展了 MySQL 特有功能。

## 支持的操作

| 操作 | MySQL 支持 | 备注 |
|------|-----------|------|
| `CreateTableExpression` | 完整 | PRIMARY KEY、NOT NULL、UNIQUE、DEFAULT |
| `DropTableExpression` | 完整 | IF EXISTS 支持 |
| `AlterTableExpression` | 完整 | ADD/DROP COLUMN |
| `CreateIndexExpression` | 完整 | BTREE、HASH 索引类型 |
| `DropIndexExpression` | 完整 | |
| `CreateViewExpression` | 完整 | MySQL ALGORITHM 选项 |
| `DropViewExpression` | 完整 | |
| 分区支持 | 完整 | RANGE、LIST、HASH、KEY 分区 |

## 基本示例

### CREATE TABLE

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression, ColumnDefinition

columns = [
    ColumnDefinition(name='id', data_type='INT', auto_increment=True, primary_key=True),
    ColumnDefinition(name='username', data_type='VARCHAR(50)', nullable=False, unique=True),
    ColumnDefinition(name='email', data_type='VARCHAR(255)', nullable=False),
    ColumnDefinition(name='created_at', data_type='DATETIME', default='CURRENT_TIMESTAMP'),
]

create_table = CreateTableExpression(
    dialect,
    table_name='users',
    columns=columns,
    dialect_options={'engine': 'InnoDB'},
)
```

### ALTER TABLE

```python
from rhosocial.activerecord.backend.expression import AlterTableExpression, AddColumnOperation

alter = AlterTableExpression(
    dialect,
    table_name='users',
    operations=[
        AddColumnOperation(ColumnDefinition(name='phone', data_type='VARCHAR(20)')),
    ],
)
```

### DROP TABLE

```python
from rhosocial.activerecord.backend.expression import DropTableExpression

drop = DropTableExpression(dialect, table_name='temp_data', if_exists=True)
```

## 分区支持

MySQL 支持丰富的表分区。参见[分区文档](../backend_specific_features/partition.md)：

```python
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLPartitionByRange, MySQLPartitionDefinition, MySQLPartitionValue,
)

partition = MySQLPartitionByRange(
    dialect,
    keys=["created_at"],
    partitions=[
        MySQLPartitionDefinition("p1", less_than=MySQLPartitionValue("2024-01-01")),
        MySQLPartitionDefinition("p2", less_than=MySQLPartitionMaxValue()),
    ],
)

create_table = CreateTableExpression(
    dialect,
    table_name="orders",
    columns=[...],
    partition_clause=partition,
)
```

## ALGORITHM 选项

MySQL 视图支持 ALGORITHM 来控制执行策略：

```python
from rhosocial.activerecord.backend.expression import ViewOptions, ViewAlgorithm

create_view = CreateViewExpression(
    dialect,
    view_name="optimized_view",
    query=query,
    options=ViewOptions(algorithm=ViewAlgorithm.MERGE),
)
```

> **注意**: MySQL ALTER TABLE 的功能与 SQLite 不同。完整的 DDL 功能请参阅 [MySQL 9.6 文档](https://dev.mysql.com/doc/refman/9.6/en/sql-statements.html)。

AI 提示: "InnoDB 和 MyISAM 在 DDL 操作上有什么区别？"
