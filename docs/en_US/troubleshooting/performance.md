# Performance Issues

## Overview

This section covers MySQL performance issues and optimization methods.

## Slow Query Analysis

### Enabling Slow Query Log

```sql
-- View slow query configuration
SHOW VARIABLES LIKE 'slow_query_log%';

-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

### Using EXPLAIN to Analyze Queries

The backend provides an `ExplainExpression` class for generating EXPLAIN statements. **Do not execute raw EXPLAIN SQL** — use the expression system instead:

```python
from rhosocial.activerecord.backend.expression.statements.explain import (
    ExplainExpression,
    ExplainOptions,
    ExplainFormat,
)

# Build a query expression
query = User.query().where(User.c.name == "Tom").select(User.c.id, User.c.name)

# Basic EXPLAIN
explain = ExplainExpression(dialect, statement=query)
sql, params = explain.to_sql()
# Output: EXPLAIN SELECT `id`, `name` FROM `users` WHERE `name` = %s

# EXPLAIN with ANALYZE (execute and show actual statistics)
explain_analyze = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(analyze=True),
)

# EXPLAIN with JSON format
explain_json = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(format=ExplainFormat.JSON),
)

# EXPLAIN with TREE format (MySQL 8.0.16+)
explain_tree = ExplainExpression(
    dialect,
    statement=query,
    options=ExplainOptions(format=ExplainFormat.TREE),
)
```

## Common Performance Issues

### 1. Missing Index

```sql
-- Add index
CREATE INDEX idx_name ON users(name);
```

### 2. SELECT *

```python
# Avoid SELECT *, only query required columns
users = User.query().select(User.c.id, User.c.name).all()
```

### 3. N+1 Query Problem

```python
# Use with_() to eagerly load related data and avoid N+1 queries
users = User.query().with_('posts').all()

# Load nested relations
users = User.query().with_('posts.comments').all()

# Load with query modifier
users = User.query().with_(('posts', lambda q: q.limit(5))).all()
```

### 4. JSON Type Performance (MySQL 5.6 vs 5.7+)

When storing `dict` or `list` types, the backend uses the `MySQLJSONAdapter` to serialize data. The storage behavior differs between MySQL versions:

| Feature | MySQL 5.6 | MySQL 5.7+ |
|---------|-----------|------------|
| JSON data type | Not supported | Native JSON type |
| Storage format | TEXT (string) | Binary JSON |
| Validation | None | Automatic |
| JSON functions | Not available | JSON_EXTRACT, etc. |
| Indexing | Not possible | Via generated columns |
| Max size | 65,535 bytes | 1 GB |
| Performance | Slower | Faster |

```python
# The adapter automatically handles version differences
# MySQL 5.6: dict/list stored as TEXT with JSON string
# MySQL 5.7+: dict/list stored as native JSON type

from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLJSONAdapter

adapter = MySQLJSONAdapter()
data = {"name": "Tom", "tags": ["admin"]}

# Convert to database value (same for both versions)
db_value = adapter.to_database(data, dict)
# Output: '{"name": "Tom", "tags": ["admin"]}'

# Convert back to Python (same for both versions)
python_value = adapter.from_database(db_value, dict)
# Output: {'name': 'Tom', 'tags': ['admin']}
```

**Recommendation**: For new projects, use MySQL 8.0+ for full JSON support including `JSON_TABLE` function.

## Connection Timeouts

```python
config = MySQLConnectionConfig(
    connect_timeout=30,
    read_timeout=60,
    write_timeout=60,
)
```

💡 *AI Prompt:* "How to optimize MySQL query performance?"
