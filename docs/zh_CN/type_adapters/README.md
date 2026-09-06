# 类型适配器

本节介绍 MySQL 数据类型和 Python 类型之间的转换。

## 内容

- [类型映射](mapping.md)：MySQL 到 Python 类型转换表
- [自定义适配器](custom.md)：使用自定义适配器扩展类型支持
- [时区处理](timezone.md)：时间戳和时区配置

## 概述

MySQL 后端自动将 MySQL 列类型映射到 Python 类型：

| MySQL 类型 | Python 类型 | 备注 |
|-----------|-------------|------|
| TINYINT、SMALLINT、MEDIUMINT、INT、BIGINT | int | |
| FLOAT、DOUBLE | float | |
| DECIMAL | Decimal | 来自 `decimal` 模块 |
| CHAR、VARCHAR | str | |
| TEXT、TINYTEXT、MEDIUMTEXT、LONGTEXT | str | |
| BINARY、VARBINARY | bytes | |
| BLOB、TINYBLOB、MEDIUMBLOB、LONGBLOB | bytes | |
| DATE | date | 来自 `datetime` 模块 |
| TIME | time | 来自 `datetime` 模块 |
| DATETIME | datetime | |
| TIMESTAMP | datetime | 带时区转换 |
| YEAR | int | |
| ENUM | str | |
| SET | str | 逗号分隔的值 |
| JSON | dict/list | 从 JSON 字符串解析 |

## 自定义适配器

您可以为应用特定类型注册自定义类型适配器：

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class MyClass:
    def __init__(self, value):
        self.value = value

class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return json.dumps({"value": value.value})

    @staticmethod
    def from_sql(value, dialect):
        data = json.loads(value)
        return MyClass(data["value"])

backend = MySQLBackend(config)
backend.type_registry.register(MyClass, MyClassAdapter)
```

## 时区处理

MySQL TIMESTAMP 列以 UTC 存储值，并在检索时转换为会话时区。后端自动处理此转换。对于 DATETIME 列（没有时区感知），如果需要请显式配置会话时区。

详细的配置请参阅[时区处理](timezone.md)。

AI 提示: "MySQL 如何处理 TIMESTAMP 列的时区转换？"
