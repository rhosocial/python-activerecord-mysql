# MySQL Dialect Expressions

## Overview

MySQL has some specific SQL syntax and functions. This section covers commonly used MySQL-specific expressions.

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
