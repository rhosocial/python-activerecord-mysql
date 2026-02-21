# Connection Management

## Overview

This backend **does not support connection pools**. It is recommended to use a "connect on use, disconnect after use" pattern for database connection management.

⚠️ **Important Notes**:

- Not recommended to develop your own connection pool solutions
- Not recommended to use third-party connection pool libraries
- Please keep a simple connection management strategy: establish connection on each operation, release immediately after operation completes

## Basic Usage

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

def get_user(user_id):
    backend = MySQLBackend(
        host='localhost',
        port=3306,
        database='myapp',
        username='user',
        password='password'
    )
    try:
        backend.connect()
        user = backend.find('User', user_id)
        return user
    finally:
        backend.disconnect()
```

## Asynchronous Usage

```python
import asyncio
from rhosocial.activerecord.backend.impl.mysql import AsyncMySQLBackend

async def get_user(user_id):
    backend = AsyncMySQLBackend(
        host='localhost',
        port=3306,
        database='myapp',
        username='user',
        password='password'
    )
    try:
        await backend.connect()
        user = await backend.find('User', user_id)
        return user
    finally:
        await backend.disconnect()
```

## Connection Timeout Configuration

You can configure connection behavior with the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| connect_timeout | int | 10 | Connection timeout in seconds |
| read_timeout | int | 30 | Read timeout in seconds |
| write_timeout | int | 30 | Write timeout in seconds |

```python
backend = MySQLBackend(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
    connect_timeout=10,
    read_timeout=30,
    write_timeout=30,
)
```

💡 *AI Prompt:* "What is the principle of database connection pools? Why are they not recommended in some scenarios?"
