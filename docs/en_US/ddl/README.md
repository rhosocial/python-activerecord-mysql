# MySQL DDL Operations

The MySQL backend supports the same type-safe DDL expressions as the core library.

## Supported Operations

| Operation | MySQL Support | Notes |
|----------|--------------|-------|
| `CreateTableExpression` | ✅ Full | PRIMARY KEY, NOT NULL, UNIQUE, etc. |
| `DropTableExpression` | ✅ Full | IF EXISTS support |
| `AlterTableExpression` | ✅ Full | ADD/DROP COLUMN |
| `CreateIndexExpression` | ✅ Full | Index types (BTREE, HASH) |
| `DropIndexExpression` | ✅ Full | |
| `CreateViewExpression` | ✅ Full | MySQL ALGORITHM options |
| `DropViewExpression` | ✅ Full | |
| `CreateTableExpression` | ✅ Full | Partition support (RANGE, LIST, HASH, KEY) |
| `PartitionByRange` | ✅ Full | RANGE and RANGE COLUMNS partitioning |
| `PartitionByList` | ✅ Full | LIST and LIST COLUMNS partitioning |
| `PartitionByHash` | ✅ Full | HASH and LINEAR HASH partitioning |
| `PartitionByKey` | ✅ Full | KEY and LINEAR KEY partitioning |

## MySQL-Specific Features

### Partition Support

MySQL supports rich table partitioning strategies. See [Partition Documentation](../mysql_specific_features/partition.md).

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

### ALGORITHM Option

MySQL views support ALGORITHM to control execution:

```python
from rhosocial.activerecord.backend.expression import ViewOptions, ViewAlgorithm

create_view = CreateViewExpression(
    dialect,
    view_name="optimized_view",
    query=query,
    options=ViewOptions(algorithm=ViewAlgorithm.MERGE)
)
```

### Storage Engine

MySQL supports specifying storage engine:

```python
create_table = CreateTableExpression(
    dialect,
    table_name="users",
    columns=columns,
    dialect_options={"engine": "InnoDB"}
)
```

## Running the Example

```bash
cd python-activerecord-mysql
source .venv3.8/bin/activate
PYTHONPATH=src python docs/examples/chapter_04_ddl/ddl.py
```

The example tests:
1. Create table with constraints
2. Create table with IF NOT EXISTS
3. Alter table - add column
4. Alter table - drop column
5. Drop table with IF EXISTS
6. Introspection to verify schema changes

> **Note**: MySQL has different ALTER TABLE support than SQLite. For full MySQL DDL capabilities, refer to [MySQL 9.6 Documentation](https://dev.mysql.com/doc/refman/9.6/en/sql-statements.html).