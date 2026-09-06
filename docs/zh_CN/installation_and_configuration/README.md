# 安装与配置

本节介绍如何安装和配置 rhosocial-activerecord 的 MySQL 后端。

## 内容

- [安装指南](installation.md)：pip 安装和驱动程序设置
- [连接配置](configuration.md)：主机、端口、数据库、凭据和高级选项
- [SSL/TLS 配置](ssl.md)：安全连接设置
- [连接管理](pool.md)：按需连接生命周期和异步池路线图
- [字符集/编码](charset.md)：utf8mb4 配置和最佳实践

## 快速设置

安装核心库和 MySQL 后端：

```bash
pip install rhosocial-activerecord
pip install rhosocial-activerecord-mysql
```

MySQL 后端依赖于 `mysql-connector-python`（>=8.0.0）。这是唯一支持的驱动程序 -- mysqlclient 或 PyMySQL 等替代品不兼容。

## 基本配置

```python
from rhosocial.activerecord.backend.impl.mysql import (
    MySQLBackend,
    AsyncMySQLBackend,
    MySQLConnectionConfig,
)

# 同步
config = MySQLConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
)
MySQLBackend(config).connect()

# 异步
AsyncMySQLBackend(config).connect()
```

## 连接模型

MySQL 后端使用**按需连接**模式。没有内置连接池 -- 每个 ActiveRecord 类通过 `configure()` 绑定到单个连接。对于多进程场景，必须在每个子进程中调用 `configure()`。

## SSL/TLS

对于安全连接：

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

## 字符集

始终使用 `utf8mb4` 以获得完整的 Unicode 支持（包括表情符号）：

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

使用 `utf8`（不带 `mb4`）将存储限制为 3 字节字符，并会丢失 4 字节 Unicode 数据。

AI 提示: "MySQL 中 utf8 和 utf8mb4 有什么区别？"
