# Introduction

## MySQL Backend Overview

`rhosocial-activerecord-mysql` is the MySQL database backend implementation for the rhosocial-activerecord core library. It provides complete ActiveRecord pattern support, optimized specifically for MySQL database features.

The backend is responsible for three primary tasks:

- **SQL Dialect Generation** -- converting generic query builders into MySQL-specific SQL statements
- **Data Type Mapping** -- handling MySQL types including TINYINT through BIGINT, CHAR/VARCHAR/TEXT variants, DATE/TIME/DATETIME/TIMESTAMP, BINARY/VARBINARY/BLOB, JSON, ENUM, and SET
- **Connection and Transaction Management** -- establishing TCP connections, executing BEGIN/COMMIT/ROLLBACK, and managing MySQL-specific behaviors like auto-increment and savepoints

## Synchronous and Asynchronous

The MySQL backend provides both synchronous and asynchronous APIs that are functionally equivalent. The documentation uses synchronous examples throughout, but the asynchronous API usage is identical -- just replace method calls with their async equivalents.

### Naming Convention

| Component | Sync | Async |
|-----------|------|-------|
| Backend class | `MySQLBackend` | `AsyncMySQLBackend` |
| Transaction manager | `MySQLTransactionManager` | `AsyncMySQLTransactionManager` |
| Connection config | `MySQLConnectionConfig` | `MySQLConnectionConfig` (shared) |
| Dialect | `MySQLDialect` | `MySQLDialect` (shared) |

The connection config and dialect are shared between sync and async -- they are pure data objects, not active connections.

### Model Layer

| Operation | `ActiveRecord` (sync) | `AsyncActiveRecord` (async) |
|-----------|----------------------|----------------------------|
| Find one | `find_one()` | `async find_one()` |
| Find all | `find_all()` | `async find_all()` |
| Save | `save()` | `async save()` |
| Delete | `delete()` | `async delete()` |
| Query builder | `.query()` -> `ActiveQuery` | `.query()` -> `AsyncActiveQuery` |

The method names are identical across sync and async -- the distinction is at the class level, not the method level.

### Async Driver

MySQL uses the same package for both sync and async:

| Backend | Sync Driver | Async Driver | Notes |
|---------|-------------|--------------|-------|
| MySQL | `mysql-connector-python` | `mysql.connector.aio` | Same package, sub-module |

If you import `AsyncMySQLBackend` and the async driver is not installed, you will get an `ImportError` at import time.

## Quick Start

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from rhosocial.activerecord.backend.impl.mysql import (
    MySQLBackend, AsyncMySQLBackend, MySQLConnectionConfig,
)

class User(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str
    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Synchronous
config = MySQLConnectionConfig(
    host='localhost', port=3306,
    database='myapp', username='user', password='password',
)
User.configure(config, MySQLBackend)

user = User(username='tom', email='tom@example.com')
user.save()
found = User.query().where(User.c.username == 'tom').one()

# Asynchronous
User.configure(config, AsyncMySQLBackend)
user = await User(username='tom', email='tom@example.com').save()
```

## Relationship with Core Library

rhosocial-activerecord uses a modular design where the core library provides database-agnostic ActiveRecord implementations, and database backends exist as separate extension packages. The MySQL backend's namespace is `rhosocial.activerecord.backend.impl.mysql`, at the same level as other backends.

```
rhosocial.activerecord
├── backend.impl.sqlite   # SQLite backend
├── backend.impl.dummy    # Dummy backend for testing
└── backend.impl.mysql    # MySQL backend (this package)
    ├── MySQLBackend
    ├── AsyncMySQLBackend
    └── ...
```

Backends do not participate in ActiveRecord layer changes -- they strictly follow backend interface protocols. Backend updates are decoupled from the core library's ActiveRecord functionality.

## Known Limitations and Quirks

Every database has behavior that differs from the SQL standard. This section documents MySQL-specific quirks that may surprise you.

| Quirk | Description |
|-------|-------------|
| No RETURNING clause | MySQL does not support RETURNING. Use `ON DUPLICATE KEY UPDATE` for upserts. |
| No MERGE statement | Use `INSERT ... ON DUPLICATE KEY UPDATE` or `REPLACE INTO` instead. |
| affected_rows for upserts | `ON DUPLICATE KEY UPDATE` returns affected_rows=2 when an update occurs (1 for insert). |
| UPDATE with no change | UPDATE that sets a column to its current value returns affected_rows=0 (not 1). |
| NO_BACKSLASH_ESCAPES | When this SQL mode is active, backslash is treated as a literal character. |
| lastrowid for batch inserts | `lastrowid` is only reliable for single-row inserts with auto-increment. |

> **MariaDB**: Partial support via MySQL-compatible features only. Not fully tested. MySQL is recommended for production.

AI Prompt: "What is the ActiveRecord pattern? How does it differ from DataMapper pattern?"
