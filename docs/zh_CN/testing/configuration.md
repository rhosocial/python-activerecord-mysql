# 测试配置

## 概述

本节介绍如何配置 MySQL 后端的测试环境。

## 使用 Dummy 后端进行单元测试

推荐使用 `dummy` 后端进行单元测试，它不需要实际的数据库连接：

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


# 配置 Dummy 后端
config = DummyConnectionConfig()
User.configure(config, DummyBackend)
```

## 使用 SQLite 后端进行集成测试

对于需要真实数据库行为的测试，可以使用 SQLite 后端：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig


class User(ActiveRecord):
    name: str
    email: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# 配置 SQLite 内存数据库
config = SQLiteConnectionConfig(database=':memory:')
User.configure(config, SQLiteBackend)
```

## 使用 MySQL 后端进行端到端测试

对于完整的 MySQL 行为测试，使用 MySQL 后端：

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


# 从环境变量读取配置
config = MySQLConnectionConfig(
    host=os.environ.get('MYSQL_HOST', 'localhost'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    database=os.environ.get('MYSQL_DATABASE', 'test'),
    username=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
)
User.configure(config, MySQLBackend)
```

## 测试夹具 (Fixtures)

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

💡 *AI 提示词：* "单元测试、集成测试和端到端测试有什么区别？"
