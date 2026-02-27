# Test Configuration

## Overview

This section describes how to configure the testing environment for the MySQL backend.

## Unit Testing with Dummy Backend

The `dummy` backend is recommended for unit tests as it does not require a real database connection:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.dummy import DummyBackend, DummyConnectionConfig


class User(ActiveRecord):
    name: str
    email: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Configure Dummy backend
config = DummyConnectionConfig()
User.configure(config, DummyBackend)
```

## Integration Testing with SQLite Backend

For tests requiring real database behavior, use the SQLite backend:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig


class User(ActiveRecord):
    name: str
    email: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Configure SQLite in-memory database
config = SQLiteConnectionConfig(database=':memory:')
User.configure(config, SQLiteBackend)
```

## End-to-End Testing with MySQL Backend

For complete MySQL behavior testing, use the MySQL backend:

```python
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig


class User(ActiveRecord):
    name: str
    email: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Read configuration from environment variables
config = MySQLConnectionConfig(
    host=os.environ.get('MYSQL_HOST', 'localhost'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    database=os.environ.get('MYSQL_DATABASE', 'test'),
    username=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
)
User.configure(config, MySQLBackend)
```

## Test Fixtures

```python
import pytest
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig


@pytest.fixture
def mysql_config():
    return MySQLConnectionConfig(
        host='localhost',
        port=3306,
        database='test',
        username='root',
        password='password',
    )


@pytest.fixture
def mysql_backend(mysql_config):
    backend = MySQLBackend(connection_config=mysql_config)
    backend.connect()
    yield backend
    backend.disconnect()


def test_connection(mysql_backend):
    version = mysql_backend.get_server_version()
    assert version is not None
```

💡 *AI Prompt:* "What is the difference between unit tests, integration tests, and end-to-end tests?"
