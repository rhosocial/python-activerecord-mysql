# DDL Operations

The MySQL backend supports the same type-safe DDL expressions as the core library, extended with MySQL-specific features.

## Supported Operations

| Operation | MySQL Support | Notes |
|-----------|--------------|-------|
| `CreateTableExpression` | Full | PRIMARY KEY, NOT NULL, UNIQUE, DEFAULT |
| `DropTableExpression` | Full | IF EXISTS support |
| `AlterTableExpression` | Full | ADD/DROP COLUMN |
| `CreateIndexExpression` | Full | BTREE, HASH index types |
| `DropIndexExpression` | Full | |
| `CreateViewExpression` | Full | MySQL ALGORITHM options |
| `DropViewExpression` | Full | |
| Partition support | Full | RANGE, LIST, HASH, KEY partitioning |

## Basic Examples

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

## Partition Support

MySQL supports rich table partitioning. See [Partition Documentation](../backend_specific_features/partition.md):

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

## ALGORITHM Option

MySQL views support ALGORITHM to control execution strategy:

```python
from rhosocial.activerecord.backend.expression import ViewOptions, ViewAlgorithm

create_view = CreateViewExpression(
    dialect,
    view_name="optimized_view",
    query=query,
    options=ViewOptions(algorithm=ViewAlgorithm.MERGE),
)
```

> **Note**: MySQL ALTER TABLE capabilities differ from SQLite. For full DDL capabilities, refer to the [MySQL 9.6 Documentation](https://dev.mysql.com/doc/refman/9.6/en/sql-statements.html).

AI Prompt: "What is the difference between InnoDB and MyISAM for DDL operations?"
