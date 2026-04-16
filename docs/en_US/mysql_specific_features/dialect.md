# MySQL Dialect Expressions

## Overview

MySQL has some specific SQL syntax and functions. This section covers commonly used MySQL-specific expressions.

## DDL Statements

### CREATE TABLE ... LIKE

MySQL supports copying table structure using the `LIKE` clause. This is useful for creating table backups or test tables with identical structure.

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

# Basic usage - copy table structure
create_expr = CreateTableExpression(
    dialect=MySQLDialect(),
    table_name="users_copy",
    columns=[],
    dialect_options={'like_table': 'users'}
)
# Generates: CREATE TABLE `users_copy` LIKE `users`

# With schema-qualified source table
create_expr = CreateTableExpression(
    dialect=MySQLDialect(),
    table_name="users_copy",
    columns=[],
    dialect_options={'like_table': ('production', 'users')}
)
# Generates: CREATE TABLE `users_copy` LIKE `production`.`users`

# With TEMPORARY and IF NOT EXISTS
create_expr = CreateTableExpression(
    dialect=MySQLDialect(),
    table_name="temp_users",
    columns=[],
    temporary=True,
    if_not_exists=True,
    dialect_options={'like_table': 'users'}
)
# Generates: CREATE TABLE TEMPORARY IF NOT EXISTS `temp_users` LIKE `users`
```

**Important Notes:**
- When `like_table` is specified in `dialect_options`, it takes highest priority
- All other parameters (columns, indexes, constraints, etc.) are IGNORED
- Only `temporary` and `if_not_exists` flags are considered
- MySQL's LIKE copies: columns, indexes, constraints, defaults, auto_increment settings

### Statement-Level Constants and DEFAULT Values

MySQL DDL `DEFAULT` clauses frequently require SQL statement-level constants such as `CURRENT_TIMESTAMP`, `NOW()`, `CURRENT_DATE`, etc. These are SQL keywords or function calls, **not string literals**, so they must be passed as `FunctionCall` instances rather than Python strings.

```python
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition, ColumnConstraint, ColumnConstraintType,
)

# Correct: Use FunctionCall for SQL statement-level constants
ColumnDefinition(
    name='created_at',
    data_type='TIMESTAMP',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT,
                         default_value=FunctionCall(dialect, 'CURRENT_TIMESTAMP')),
        # Generates: `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    ],
)

# Correct: Use NOW() function
ColumnDefinition(
    name='updated_at',
    data_type='DATETIME',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT,
                         default_value=FunctionCall(dialect, 'NOW')),
        # Generates: `updated_at` DATETIME DEFAULT NOW()
    ],
)

# Correct: Numeric literals use Python native types
ColumnDefinition(
    name='is_active',
    data_type='TINYINT(1)',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
        # Generates: `is_active` TINYINT(1) DEFAULT 1
    ],
)

# Correct: String literals use Python strings (auto-quoted)
ColumnDefinition(
    name='status',
    data_type='VARCHAR(20)',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT, default_value='active'),
        # Generates: `status` VARCHAR(20) DEFAULT 'active'
    ],
)
```

**Incorrect approach:**

```python
# WRONG: Passing SQL keywords as Python strings
# This would generate DEFAULT 'CURRENT_TIMESTAMP' (quoted, treated as string literal)
ColumnConstraint(ColumnConstraintType.DEFAULT, default_value='CURRENT_TIMESTAMP')
```

**Common statement-level constants reference:**

| SQL Constant | Expression API | Description |
| ------------ | ---------------------------------------------- | ----------- |
| `CURRENT_TIMESTAMP` | `FunctionCall(dialect, 'CURRENT_TIMESTAMP')` | Current timestamp |
| `CURRENT_TIMESTAMP(6)` | `FunctionCall(dialect, 'CURRENT_TIMESTAMP', Literal(dialect, 6))` | Timestamp with precision |
| `NOW()` | `FunctionCall(dialect, 'NOW')` | Current date and time |
| `CURRENT_DATE` | `FunctionCall(dialect, 'CURRENT_DATE')` | Current date |
| `CURRENT_TIME` | `FunctionCall(dialect, 'CURRENT_TIME')` | Current time |
| `UUID()` | `FunctionCall(dialect, 'UUID')` | Generate UUID (MySQL 8.0+) |

> **Core rule**: Anything that is a SQL keyword, function, or constant (i.e., should NOT be quoted in the generated SQL) must use `FunctionCall`. Literal values that need quoting should use Python native types (strings, numbers, booleans).

## Specific Operators

### LIKE Expression

```python
# Search for records starting with specified character
User.query().where(User.c.name.like('%test%'))

# REGEXP regular expression
User.query().where(User.c.name.regexp('^A.*'))
```

## Specific Functions

### GROUP_CONCAT

```python
# Concatenate strings in a group
# SELECT GROUP_CONCAT(name SEPARATOR ',') FROM users GROUP BY role
from rhosocial.activerecord.backend.expression import FunctionExpression


class GroupConcat(FunctionExpression):
    def __init__(self, column, separator=','):
        super().__init__(
            'GROUP_CONCAT',
            column,
            separator=f"SEPARATOR '{separator}'"
        )
```

### ON DUPLICATE KEY UPDATE

```python
# Insert or update
# INSERT INTO users (id, name) VALUES (1, 'Tom') ON DUPLICATE KEY UPDATE name = 'Tom'
```

### REPLACE INTO

```python
# Replace insert (delete then insert)
# REPLACE INTO users (id, name) VALUES (1, 'Tom')
```

💡 *AI Prompt:* "What is the difference between MySQL's REPLACE INTO and INSERT ... ON DUPLICATE KEY UPDATE?"

## Querying Runtime Functions and Constants

MySQL supports querying runtime functions without a data source, such as `SELECT CURRENT_TIMESTAMP`, `SELECT NOW()`, `SELECT VERSION()`. Use `QueryExpression` without specifying `from_` to achieve this.

```python
from rhosocial.activerecord.backend.expression import QueryExpression
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal

# SELECT CURRENT_TIMESTAMP()
query = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'CURRENT_TIMESTAMP')],
)
sql, params = query.to_sql()
# Generates: SELECT CURRENT_TIMESTAMP()

# SELECT NOW()
query = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'NOW')],
)
# Generates: SELECT NOW()

# SELECT CURRENT_DATE, CURRENT_TIME
query = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'CURRENT_DATE'),
        FunctionCall(dialect, 'CURRENT_TIME'),
    ],
)
# Generates: SELECT CURRENT_DATE(), CURRENT_TIME()

# Multi-function query with aliases
query = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'NOW').as_('current_time'),
        FunctionCall(dialect, 'DATABASE').as_('db_name'),
        FunctionCall(dialect, 'VERSION').as_('db_version'),
    ],
)
# Generates: SELECT NOW() AS `current_time`, DATABASE() AS `db_name`, VERSION() AS `db_version`

# Function calls with arguments
query = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'DATE_FORMAT',
                     FunctionCall(dialect, 'NOW'),
                     Literal(dialect, '%Y-%m-%d')).as_('formatted_date'),
    ],
)
# Generates: SELECT DATE_FORMAT(NOW(), %s) AS `formatted_date`
```

**Common MySQL information functions:**

| Function | Expression API | Returns |
| -------- | ---------------------------------------------- | ------- |
| `CURRENT_TIMESTAMP()` | `FunctionCall(dialect, 'CURRENT_TIMESTAMP')` | Current timestamp |
| `NOW()` | `FunctionCall(dialect, 'NOW')` | Current date and time |
| `CURRENT_DATE` | `FunctionCall(dialect, 'CURRENT_DATE')` | Current date |
| `CURRENT_TIME` | `FunctionCall(dialect, 'CURRENT_TIME')` | Current time |
| `DATABASE()` | `FunctionCall(dialect, 'DATABASE')` | Current database name |
| `VERSION()` | `FunctionCall(dialect, 'VERSION')` | MySQL version string |
| `USER()` | `FunctionCall(dialect, 'USER')` | Current user |
| `UUID()` | `FunctionCall(dialect, 'UUID')` | Generate UUID (8.0+) |
| `CONNECTION_ID()` | `FunctionCall(dialect, 'CONNECTION_ID')` | Connection ID |

> **Note**: `FunctionCall` always generates function calls with parentheses. In MySQL, both `CURRENT_TIMESTAMP` and `CURRENT_TIMESTAMP()` are valid in DDL DEFAULT context and SELECT context.
