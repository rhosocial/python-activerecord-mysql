# Installation Guide

## System Requirements

- Python 3.8+
- MySQL 5.6 ~ 9.6 or MariaDB (only supports MySQL-compatible features)
- pip or poetry

## Installation Steps

### 1. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Core Library and MySQL Backend

```bash
# Install core library
pip install rhosocial-activerecord

# Install MySQL backend
pip install rhosocial-activerecord-mysql
```

### 3. Install MySQL Driver

This backend only supports mysql-connector-python driver:

```bash
pip install mysql-connector-python
```

⚠️ **Note**: This backend does not support other MySQL drivers (such as mysqlclient, PyMySQL, etc.). Please ensure you use mysql-connector-python.

## Verify Installation

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

backend = MySQLBackend(
    host='localhost',
    port=3306,
    database='test_db',
    username='root',
    password='password'
)
backend.connect()
print(f"MySQL version: {backend.get_server_version()}")
backend.disconnect()
```

💡 *AI Prompt:* "What are the advantages and disadvantages of mysql-connector-python?"
