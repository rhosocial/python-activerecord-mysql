# rhosocial ActiveRecord MySQL Backend

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord-mysql.svg)](https://badge.fury.io/py/rhosocial-activerecord-mysql)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord-mysql.svg)](https://pypi.org/project/rhosocial-activerecord-mysql/)
[![Tests](https://github.com/rhosocial/python-activerecord-mysql/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord-mysql/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord-mysql/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord-mysql/tree/main)
[![License](https://img.shields.io/github/license/rhosocial/python-activerecord-mysql.svg)](https://github.com/rhosocial/python-activerecord-mysql/blob/main/LICENSE)
[![Powered by vistart](https://img.shields.io/badge/Powered_by-vistart-blue.svg)](https://github.com/vistart)

<div align="center">
    <img src="https://raw.githubusercontent.com/rhosocial/python-activerecord/main/docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <p>MySQL backend implementation for rhosocial-activerecord, providing a robust and optimized MySQL database support.</p>
</div>

## Overview

This package provides MySQL backend support for the [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord) ORM framework. It enables seamless integration with MySQL databases while leveraging all the features of the ActiveRecord pattern implementation.

**Note**: This is a backend implementation only and requires the main [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord) package to function properly.

## Features

> This project is still under development and features are subject to change. Please stay tuned for the latest changes.

- 🚀 Optimized MySQL-specific query generation
- 🔒 Full support for MySQL's unique features
- 📦 Connection pooling support (optional)
- 🔄 Comprehensive transaction management
- 🔍 Advanced query capabilities specific to MySQL
- 🔌 Simple configuration and setup

## Requirements

- Python 3.8+
- rhosocial-activerecord 1.0.0+
- mysql-connector-python 9.2.0+

## Installation

```bash
pip install rhosocial-activerecord-mysql
```

> **Important**: This package is a MySQL backend implementation for [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord) and cannot work independently. You must install and use it together with the main package.

For detailed usage of the main ActiveRecord framework, please refer to the [rhosocial-activerecord documentation](https://github.com/rhosocial/python-activerecord/tree/docs).

## Usage

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    created_at: datetime
    deleted_at: Optional[datetime] = None

# Configure with MySQL backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='myapp',
        user='dbuser',
        password='dbpassword'
    ),
    backend_class=MySQLBackend
)

# Create a table (if not exists)
User.create_table_if_not_exists()

# Create a new user
user = User(name='John Doe', email='john@example.com', created_at=datetime.now())
user.save()

# Query users
active_users = User.query() \
    .where('deleted_at IS NULL') \
    .order_by('created_at DESC') \
    .all()

# Update user
user.name = 'Jane Doe'
user.save()

# Delete user (soft delete if implemented)
user.delete()
```

## Advanced MySQL Features

This backend supports MySQL-specific features and optimizations:

```python
# Using MySQL fulltext search
results = User.query() \
    .where('MATCH(name, email) AGAINST(? IN BOOLEAN MODE)', ('+John -Doe', )) \
    .all()

# Using MySQL JSON operations
results = User.query() \
    .where('settings->>"$.notifications" = ?', ('enabled', )) \
    .all()

# Batch insert with ON DUPLICATE KEY UPDATE
User.batch_insert_or_update([user1, user2, user3])
```

## Documentation

Complete documentation is available at [python-activerecord MySQL Backend](https://docs.python-activerecord.dev.rho.social/backends/mysql.html)

## Contributing

We welcome and value all forms of contributions! For details on how to contribute, please see our [Contributing Guide](https://github.com/rhosocial/python-activerecord-mysql/blob/main/CONTRIBUTING.md).

## License

[![license](https://img.shields.io/github/license/rhosocial/python-activerecord-mysql.svg)](https://github.com/rhosocial/python-activerecord-mysql/blob/main/LICENSE)

Copyright © 2025 [vistart](https://github.com/vistart)