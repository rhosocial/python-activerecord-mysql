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
