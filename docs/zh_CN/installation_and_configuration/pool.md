# 连接管理

## 概述

本后端**暂不支持连接池**。推荐采用「随用随连，用完即释放」的模式管理数据库连接。

⚠️ **重要提示**：

- 不推荐自行开发连接池方案
- 不推荐借用第三方连接池库
- 请保持简单的连接管理策略：每次操作时建立连接，操作完成后立即释放

## 基本用法

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

## 异步用法

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

## 连接超时配置

可以通过以下参数配置连接行为：

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| connect_timeout | int | 10 | 连接超时时间（秒）|
| read_timeout | int | 30 | 读取超时时间（秒）|
| write_timeout | int | 30 | 写入超时时间（秒）|

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

💡 *AI 提示词：* "数据库连接池的原理是什么？为什么有些场景不推荐使用连接池？"
