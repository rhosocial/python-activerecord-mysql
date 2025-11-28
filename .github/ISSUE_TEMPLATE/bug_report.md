---
name: Bug Report
about: Report a bug in rhosocial ActiveRecord MySQL Backend
title: '[MYSQL-BUG] '
labels: 'bug, mysql'
assignees: ''
---

## Before Submitting

Please ensure this bug is specific to the MySQL backend implementation. If the issue occurs across all backends (involving ActiveRecord/ActiveQuery functionality), please submit the issue at https://github.com/rhosocial/python-activerecord/issues instead.

## Description

A clear and concise description of the bug in the MySQL backend.

## Environment

- **rhosocial ActiveRecord MySQL Version**: [e.g. 1.0.0.dev13]
- **rhosocial ActiveRecord Core Version**: [e.g. 1.0.0.dev13]
- **Python Version**: [e.g. 3.13]
- **MySQL Version**: [e.g. 8.0, 5.7]
- **MySQL Connector Version**: [e.g. mysql-connector-python 9.0.0]
- **OS**: [e.g. Linux, macOS, Windows]

## Steps to Reproduce

1.
2.
3.

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

What actually happened instead of the expected behavior.

## Database Query

If applicable, provide the generated SQL query that causes the issue:

```sql
-- Your problematic SQL query here
```

## Model Definition

If the issue is related to a specific model, please share your model definition:

```python
# Example model definition
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str
    email: EmailStr
```

## MySQL-Specific Configuration

Any MySQL-specific configuration that might be relevant:

```python
config = MySQLConnectionConfig(
    host='localhost',
    port=3306,
    database='test',
    username='user',
    password='password',
    # Add your specific options here
)
```

## Error Details

If you're getting an error, include the full error message and stack trace:

```
Paste the full error message here
```

## Additional Context

Any other context about the problem here.