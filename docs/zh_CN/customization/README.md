# 自定义

## 概述

MySQL 后端提供用于自定义 SQL 生成、类型处理和数据转换的扩展点。

## 内容

- [自定义表达式](custom_expressions.md)：创建 MySQL 特定 SQL 的新表达式类
- [自定义数据类型](custom_types.md)：定义新的 DataType 子类以支持自定义列类型
- [自定义类型适配器](custom_adapters.md)：注册 Python 和 MySQL 之间的自定义转换器

## 快速参考

### 自定义表达式

扩展表达式系统以添加 MySQL 特定的 SQL 语法：

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class MySQLOpenTableExpression(BaseExpression):
    def to_sql(self, dialect):
        return "OPEN TABLE ..."
```

### 自定义数据类型

在 MySQL 列中添加对新 Python 类型的支持：

```python
from rhosocial.activerecord.backend.impl.mysql.types import MySQLDataType

@MySQLDataType.handles(MyClass)
class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        return json.dumps(value.__dict__)

    @staticmethod
    def from_sql(value, dialect):
        return MyClass(**json.loads(value))
```

### 自定义类型适配器

注册自定义类型转换器：

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

backend = MySQLBackend(...)
backend.type_registry.register(MyClass, MyAdapter)
```

## 另请参阅

- [核心自定义指南](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/backend/template/customization) -- 通用自定义模式
- [MySQL 字段类型](../backend_specific_features/field_types.md) -- MySQL 特定的数据类型

AI 提示: "如何为 MySQL 特定的 SQL 语法创建自定义表达式类？"
