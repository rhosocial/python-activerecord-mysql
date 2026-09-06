# Installation and Configuration

This section covers how to install and configure the MySQL backend for rhosocial-activerecord.

## Contents

- [Installation Guide](installation.md): pip installation and driver setup
- [Connection Configuration](configuration.md): Host, port, database, credentials, and advanced options
- [SSL/TLS Configuration](ssl.md): Secure connection settings
- [Connection Management](pool.md): Connect-on-use lifecycle and async pool roadmap
- [Character Set / Encoding](charset.md): utf8mb4 configuration and best practices

## Quick Setup

Install the core library and MySQL backend:

```bash
pip install rhosocial-activerecord
pip install rhosocial-activerecord-mysql
```

The MySQL backend depends on `mysql-connector-python` (>=8.0.0). This is the only supported driver -- alternatives like mysqlclient or PyMySQL are not compatible.

## Basic Configuration

```python
from rhosocial.activerecord.backend.impl.mysql import (
    MySQLBackend,
    AsyncMySQLBackend,
    MySQLConnectionConfig,
)

# Synchronous
config = MySQLConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
)
MySQLBackend(config).connect()

# Asynchronous
AsyncMySQLBackend(config).connect()
```

## Connection Model

The MySQL backend uses a **connect-on-use** pattern. There is no built-in connection pool -- each ActiveRecord class binds to a single connection via `configure()`. For multi-process scenarios, `configure()` must be called inside each child process.

## SSL/TLS

For secure connections:

```python
config = MySQLConnectionConfig(
    host='db.example.com',
    port=3306,
    database='myapp',
    username='secure_user',
    password='secret',
    ssl_ca='/path/to/ca.pem',
    ssl_cert='/path/to/client-cert.pem',
    ssl_key='/path/to/client-key.pem',
)
```

## Character Set

Always use `utf8mb4` for full Unicode support (including emoji):

```python
config = MySQLConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
    charset='utf8mb4',
)
```

Using `utf8` (without `mb4`) limits storage to 3-byte characters and will lose 4-byte Unicode data.

AI Prompt: "What is the difference between utf8 and utf8mb4 in MySQL?"
