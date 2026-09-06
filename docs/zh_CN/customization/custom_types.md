# 自定义数据类型

## 概述

MySQL 后端提供类型系统，用于在 Python 类型和 MySQL 列类型之间进行转换。您可以通过创建自定义 DataType 子类来添加对新 Python 类型的支持。

## 类型系统架构

类型系统有两层：

1. **核心 DataType 层次结构** -- 类型转换的基类
2. **后端特定 DataType** -- MySQL 特定的类型处理

## 创建自定义数据类型

### 步骤 1：定义 DataType 子类

```python
from rhosocial.activerecord.backend.impl.mysql.types import MySQLDataType

class PointDataType(MySQLDataType):
    """用于地理点的自定义数据类型。"""

    @staticmethod
    def to_sql(value, dialect):
        """将 Python Point 转换为 MySQL POINT 字面量。"""
        if value is None:
            return None
        return f"ST_GeomFromText('POINT({value.x} {value.y})')"

    @staticmethod
    def from_sql(value, dialect):
        """将 MySQL POINT 转换为 Python Point。"""
        if value is None:
            return None
        # 解析 WKT 格式
        coords = value.replace("POINT(", "").replace(")", "").split()
        return Point(float(coords[0]), float(coords[1]))
```

### 步骤 2：使用 @handles 装饰器注册

```python
from rhosocial.activerecord.backend.impl.mysql.types import MySQLDataType

@MySQLDataType.handles(Point)
class PointAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return f"ST_GeomFromText('POINT({value.x} {value.y})')"

    @staticmethod
    def from_sql(value, dialect):
        coords = value.replace("POINT(", "").replace(")", "").split()
        return Point(float(coords[0]), float(coords[1]))
```

### 步骤 3：在模型中使用

```python
from rhosocial.activerecord import Model

class Location(Model):
    __tablename__ = "locations"
    id: int
    name: str
    coordinates: Point  # 使用自定义类型
```

## 类型参数

定义自定义类型时，考虑以下参数：

| 参数 | 描述 | 示例 |
|------|------|------|
| `precision` | 数字类型的总位数 | `DECIMAL(10, 2)` |
| `scale` | 小数点后的位数 | `DECIMAL(10, 2)` |
| `length` | 字符串类型的最大长度 | `VARCHAR(255)` |
| `unsigned` | 无符号整数标志 | `INT UNSIGNED` |

## MySQL 特定类型

MySQL 后端提供以下内置类型：

| MySQL 类型 | Python 类型 | 备注 |
|-----------|-------------|------|
| `SET` | `set` | 逗号分隔的值 |
| `ENUM` | `str` | 限于定义的值 |
| `JSON` | `dict/list` | 原生 JSON 支持 |
| `TINYINT(1)` | `bool` | 布尔表示 |
| `GEOMETRY` | `bytes` | 空间数据 |

## 另请参阅

- [MySQL 字段类型](../backend_specific_features/field_types.md) -- MySQL 特定的数据类型
- [类型映射](../type_adapters/mapping.md) -- MySQL 到 Python 类型转换表
- [核心自定义类型指南](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/backend/template/customization/custom_types.md) -- 通用自定义模式

💡 *AI 提示:* "如何在 MySQL 中添加对自定义 Python 类型的支持？"
