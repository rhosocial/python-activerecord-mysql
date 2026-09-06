# 简介

## MySQL 后端概述

`rhosocial-activerecord-mysql` 是 rhosocial-activerecord 核心库的 MySQL 数据库后端实现。它提供完整的 ActiveRecord 模式支持，专门针对 MySQL 数据库特性进行了优化。

该后端主要负责三项核心任务：

- **SQL 方言生成** -- 将通用查询构建器转换为 MySQL 特定的 SQL 语句
- **数据类型映射** -- 处理 MySQL 类型，包括 TINYINT 到 BIGINT、CHAR/VARCHAR/TEXT 变体、DATE/TIME/DATETIME/TIMESTAMP、BINARY/VARBINARY/BLOB、JSON、ENUM 和 SET
- **连接和事务管理** -- 建立 TCP 连接、执行 BEGIN/COMMIT/ROLLBACK，以及管理 MySQL 特定行为（如自增和保存点）

## 同步和异步

MySQL 后端提供功能等价的同步和异步 API。文档中使用同步示例，但异步 API 的用法完全相同 -- 只需将方法调用替换为异步等效方法即可。

### 命名约定

| 组件 | 同步 | 异步 |
|------|------|------|
| 后端类 | `MySQLBackend` | `AsyncMySQLBackend` |
| 事务管理器 | `MySQLTransactionManager` | `AsyncMySQLTransactionManager` |
| 连接配置 | `MySQLConnectionConfig` | `MySQLConnectionConfig`（共享） |
| 方言 | `MySQLDialect` | `MySQLDialect`（共享） |

连接配置和方言在同步和异步之间共享 -- 它们是纯数据对象，不是活动连接。

### 模型层

| 操作 | `ActiveRecord`（同步） | `AsyncActiveRecord`（异步） |
|------|----------------------|----------------------------|
| 查找一个 | `find_one()` | `async find_one()` |
| 查找全部 | `find_all()` | `async find_all()` |
| 保存 | `save()` | `async save()` |
| 删除 | `delete()` | `async delete()` |
| 查询构建器 | `.query()` -> `ActiveQuery` | `.query()` -> `AsyncActiveQuery` |

方法名在同步和异步之间完全一致 -- 区别在于类级别，而不是方法级别。

### 异步驱动

MySQL 使用相同的包进行同步和异步：

| 后端 | 同步驱动 | 异步驱动 | 备注 |
|------|---------|---------|------|
| MySQL | `mysql-connector-python` | `mysql.connector.aio` | 同一包，子模块 |

如果导入 `AsyncMySQLBackend` 而异步驱动未安装，将在导入时收到 `ImportError`。

## 快速开始

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

# 同步
config = MySQLConnectionConfig(
    host='localhost', port=3306,
    database='myapp', username='user', password='password',
)
User.configure(config, MySQLBackend)

user = User(username='tom', email='tom@example.com')
user.save()
found = User.query().where(User.c.username == 'tom').one()

# 异步
User.configure(config, AsyncMySQLBackend)
user = await User(username='tom', email='tom@example.com').save()
```

## 与核心库的关系

rhosocial-activerecord 采用模块化设计，核心库提供与数据库无关的 ActiveRecord 实现，而数据库后端作为独立的扩展包存在。MySQL 后端的命名空间是 `rhosocial.activerecord.backend.impl.mysql`，与其他后端处于同一级别。

```
rhosocial.activerecord
├── backend.impl.sqlite   # SQLite 后端
├── backend.impl.dummy    # 测试用的虚拟后端
└── backend.impl.mysql    # MySQL 后端（本包）
    ├── MySQLBackend
    ├── AsyncMySQLBackend
    └── ...
```

后端不参与 ActiveRecord 层变更 -- 它们严格遵循后端接口协议。后端更新与核心库的 ActiveRecord 功能解耦。

## 已知限制和怪异行为

每个数据库都有与 SQL 标准不同的行为。本节记录 MySQL 特有的怪异行为，可能会让您感到意外。

| 怪异行为 | 描述 |
|---------|------|
| 无 RETURNING 子句 | MySQL 不支持 RETURNING。使用 `ON DUPLICATE KEY UPDATE` 进行 upsert。 |
| 无 MERGE 语句 | 使用 `INSERT ... ON DUPLICATE KEY UPDATE` 或 `REPLACE INTO` 替代。 |
| upsert 的 affected_rows | `ON DUPLICATE KEY UPDATE` 在更新发生时返回 affected_rows=2（插入时为 1）。 |
| 无更改的 UPDATE | 将列设置为当前值的 UPDATE 返回 affected_rows=0（而不是 1）。 |
| NO_BACKSLASH_ESCAPES | 当此 SQL 模式激活时，反斜杠被视为普通字符。 |
| 批量插入的 lastrowid | `lastrowid` 仅对单行自增插入可靠。 |

> **MariaDB**: 仅通过 MySQL 兼容功能部分支持。未经完整测试。建议在生产环境中使用 MySQL。

AI 提示: "什么是 ActiveRecord 模式？它与 DataMapper 模式有什么不同？"
