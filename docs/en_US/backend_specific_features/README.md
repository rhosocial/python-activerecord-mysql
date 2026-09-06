# MySQL Specific Features

This section covers MySQL-specific features that extend the core ActiveRecord functionality.

## Contents

- [Field Types](field_types.md): SET, ENUM, JSON, TEXT vs VARCHAR
- [Dialect Expressions](dialect.md): MySQL-specific SQL syntax and functions
- [Storage Engines](storage_engine.md): InnoDB, MyISAM selection
- [Indexing](indexing.md): Index types and optimization strategies
- [EXPLAIN](explain.md): Query execution plan analysis
- [Introspection](introspection.md): Database metadata queries
- [Partitioning](partition.md): Table partitioning strategies

## Overview

MySQL offers several features not available in other backends. The backend leverages these through dedicated expression classes and dialect extensions.

### Field Types

MySQL supports rich column types beyond the SQL standard:

| Type | Description | Use Case |
|------|-------------|----------|
| ENUM | Fixed set of allowed values (string) | Status fields, categories |
| SET | Combination of allowed values | Multi-select flags |
| JSON | Structured document storage | Flexible attributes |
| TEXT variants | TINYTEXT, TEXT, MEDIUMTEXT, LONGTEXT | Varying text length needs |
| Spatial types | POINT, LINESTRING, POLYGON, GEOMETRY | Geographic data |

### Storage Engines

MySQL allows per-table storage engine selection. The backend supports specifying the engine via DDL options:

```python
create_table = CreateTableExpression(
    dialect,
    table_name='logs',
    columns=[...],
    dialect_options={'engine': 'InnoDB'}
)
```

InnoDB is the default and recommended engine. MyISAM may be used for read-heavy workloads where transactional guarantees are not required.

### Dialect Expressions

MySQL provides specific SQL functions and syntax extensions. The dialect layer generates MySQL-compatible SQL for operations like JSON queries, string manipulation, and date arithmetic.

### Partitioning

MySQL supports RANGE, LIST, HASH, and KEY partitioning strategies. The backend provides dedicated expression classes for each strategy, enabling type-safe partition management through DDL operations.

AI Prompt: "When should I use ENUM vs a lookup table in MySQL?"
