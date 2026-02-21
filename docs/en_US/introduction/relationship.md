# Relationship with Core Library

## Architecture Overview

rhosocial-activerecord uses a modular design where the core library (`rhosocial-activerecord`) provides database-agnostic ActiveRecord implementations, and database backends exist as separate extension packages.

The MySQL backend's namespace is located under `rhosocial.activerecord.backend.impl.mysql`, at the same level as other backends (such as `sqlite`, `dummy`). This means:

- Backends do not participate in ActiveRecord layer changes
- Backends strictly follow backend interface protocols
- Backend updates are decoupled from the core library's ActiveRecord functionality

```
rhosocial.activerecord
├── backend.impl.sqlite   # SQLite backend
├── backend.impl.dummy   # Dummy backend for testing
└── backend.impl.mysql   # MySQL backend (this package)
    ├── MySQLBackend
    ├── AsyncMySQLBackend
    └── ...
```

## Backend Responsibilities

The MySQL backend is responsible for the following:

### 1. SQL Dialect Generation

Converts generic query builders into MySQL-specific SQL statements:

```python
# Core library: generic query building
query = User.query().where(User.c.age >= 18).order_by(User.c.created_at)

# MySQL backend: converted to MySQL SQL
# SELECT * FROM users WHERE age >= 18 ORDER BY created_at
```

### 2. Data Type Mapping

Handles MySQL-specific data types, including:

- TINYINT, SMALLINT, MEDIUMINT, INT, BIGINT
- FLOAT, DOUBLE, DECIMAL
- CHAR, VARCHAR, TEXT, TINYTEXT, MEDIUMTEXT, LONGTEXT
- DATE, TIME, DATETIME, TIMESTAMP, YEAR
- BINARY, VARBINARY, BLOB
- JSON (MySQL 5.7+)
- ENUM, SET

### 3. Connection Management

Provides MySQL connection establishment, disconnection, and other low-level operations.

### 4. Transaction Control

Implements MySQL transaction BEGIN, COMMIT, ROLLBACK logic.

## Quick Start

### 1. Installation

```bash
pip install rhosocial-activerecord
pip install rhosocial-activerecord-mysql
```

### 2. Define Models

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

### 3. Configure Backend

```python
from rhosocial.activerecord.backend.impl.mysql import (
    MySQLBackend,
    MySQLConnectionConfig,
)

# Configure MySQL connection
config = MySQLConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
)

# Configure backend for the model
User.configure(config, MySQLBackend)
```

### 4. CRUD Operations

```python
# Create
user = User(username='tom', email='tom@example.com')
user.save()

# Read
user = User.query().where(User.c.username == 'tom').first()

# Update
user.email = 'tom.new@example.com'
user.save()

# Delete
user.delete()
```

💡 *AI Prompt:* "What is the ActiveRecord pattern? What are its advantages and disadvantages?"
