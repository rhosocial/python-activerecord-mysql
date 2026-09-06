# MySQL 到 Python 类型映射

## 概述

MySQL 后端负责将 MySQL 数据库中的数据类型转换为 Python 对象，以及将 Python 对象转换回 MySQL 可识别的格式。

## 类型映射表

### 数值类型

| MySQL 类型 | Python 类型 | 说明 |
|-----------|-------------|------|
| TINYINT | int | 8 位整数 |
| SMALLINT | int | 16 位整数 |
| MEDIUMINT | int | 24 位整数 |
| INT | int | 32 位整数 |
| BIGINT | int | 64 位整数 |
| FLOAT | float | 单精度浮点数 |
| DOUBLE | float | 双精度浮点数 |
| DECIMAL | Decimal | 精确小数 |

### 字符串类型

| MySQL 类型 | Python 类型 | 说明 |
|-----------|-------------|------|
| CHAR | str | 固定长度字符串 |
| VARCHAR | str | 可变长度字符串 |
| TINYTEXT | str | 最多 255 字节 |
| TEXT | str | 最多 65535 字节 |
| MEDIUMTEXT | str | 最多 16777215 字节 |
| LONGTEXT | str | 最多 4294967295 字节 |
| JSON | dict/list | JSON 文档 (MySQL 5.7+) |

### 日期时间类型

| MySQL 类型 | Python 类型 | 说明 |
|-----------|-------------|------|
| DATE | date | 日期 |
| TIME | time | 时间 |
| DATETIME | datetime | 日期时间 |
| TIMESTAMP | datetime | 时间戳 |
| YEAR | int | 年份 |

### 二进制类型

| MySQL 类型 | Python 类型 | 说明 |
|-----------|-------------|------|
| BINARY | bytes | 固定长度二进制 |
| VARBINARY | bytes | 可变长度二进制 |
| TINYBLOB | bytes | 最多 255 字节 |
| BLOB | bytes | 最多 65535 字节 |
| MEDIUMBLOB | bytes | 最多 16777215 字节 |
| LONGBLOB | bytes | 最多 4294967295 字节 |

### 特殊类型

| MySQL 类型 | Python 类型 | 说明 |
|-----------|-------------|------|
| ENUM | str | 枚举值 |
| SET | str | 集合值 |
| BIT | int | 位字段 |
| BOOLEAN | bool | 布尔值 |

## 使用示例

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, DefaultTimestampMixin
from typing import ClassVar
from decimal import Decimal


class Product(UUIDMixin, DefaultTimestampMixin, ActiveRecord):
    name: str
    price: Decimal  # 自动映射为 DECIMAL
    description: str  # 自动映射为 TEXT
    metadata: dict  # 自动映射为 JSON (MySQL 5.7+) 或 TEXT (MySQL 5.6)
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def table_name(cls) -> str:
        return 'products'
```

## dict/list 类型处理（MySQL 5.6 vs 5.7+）

`MySQLJSONAdapter` 负责处理 Python `dict` 和 `list` 类型。不同 MySQL 版本的存储行为有显著差异：

| 特性 | MySQL 5.6 | MySQL 5.7+ |
|------|-----------|------------|
| 列类型 | TEXT | JSON |
| 存储格式 | JSON 字符串 | 二进制 JSON |
| 验证 | 无 | 自动验证 |
| JSON 函数 | 不可用 | JSON_EXTRACT、JSON_SET 等 |
| 索引 | 不支持 | 通过生成列 |
| 最大大小 | 65,535 字节 | 1 GB |
| 查询语法 | 字符串比较 | 原生 JSON 操作符 |

### MySQL 5.6 行为

```python
# MySQL 5.6: dict/list 存储为 TEXT
# 无验证、无 JSON 函数、查询能力有限

data = {"name": "Tom", "tags": ["admin", "user"]}

# 存储: TEXT 列，存储 JSON 字符串
# '{"name": "Tom", "tags": ["admin", "user"]}'

# 查询: 只能使用字符串比较
User.query().where(User.c.metadata.like('%admin%')).all()
```

### MySQL 5.7+ 行为

```python
# MySQL 5.7+: dict/list 存储为原生 JSON 类型
# 自动验证，完整 JSON 函数支持

data = {"name": "Tom", "tags": ["admin", "user"]}

# 存储: 二进制 JSON 格式（更高效）
# 自动验证确保 JSON 有效性

# 查询: 原生 JSON 操作符
User.query().where(User.c.metadata['$.name'] == 'Tom').all()
User.query().where(User.c.metadata['$.tags'].contains('admin')).all()
```

### 版本检测

适配器自动处理版本差异：

```python
from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLJSONAdapter

adapter = MySQLJSONAdapter()

# 两个版本产生相同的 Python 结果
db_value = adapter.to_database(data, dict)  # JSON 字符串
python_value = adapter.from_database(db_value, dict)  # Python dict
```

💡 *AI 提示：* "为什么推荐使用 DECIMAL 而不是 FLOAT 来存储金额？"
