# 自定义表达式

## 概述

MySQL 后端通过 MySQL 特定的 SQL 语法扩展核心表达式类。您可以创建新的表达式类型来添加对 MySQL 独有 SQL 构造的支持。

## 表达式设计原则

表达式是**声明式的** -- 它们收集所有参数并将 SQL 生成委托给方言：

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, **params):
        self.dialect = dialect
        self.params = params

    def to_sql(self, dialect):
        # 委托给方言进行 SQL 生成
        return dialect.format_my_expression(**self.params)
```

## 创建自定义表达式

### 步骤 1：定义表达式类

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class MySQLJSONExpression(BaseExpression):
    """用于 JSON_EXTRACT 的 MySQL JSON 表达式。"""

    def __init__(self, dialect, column, path):
        self.dialect = dialect
        self.column = column
        self.path = path

    def to_sql(self, dialect):
        return f"JSON_EXTRACT({self.column.to_sql(dialect)}, '{self.path}')"
```

### 步骤 2：注册到方言

```python
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

class CustomMySQLDialect(MySQLDialect):
    def format_json_extract(self, column, path):
        return f"JSON_EXTRACT({column}, '{path}')"
```

### 步骤 3：在代码中使用

```python
expr = MySQLJSONExpression(dialect, Column(dialect, "data"), "$.name")
sql = expr.to_sql(dialect)
# 输出: JSON_EXTRACT(`data`, '$.name')
```

## 运算符混入

使用运算符混入进行常见的比较和算术运算：

```python
from rhosocial.activerecord.backend.expression.operators import ComparisonMixin, ArithmeticMixin

class MyExpression(ComparisonMixin, ArithmeticMixin, BaseExpression):
    pass

# 现在支持 ==、!=、<、>、+、-、*、/ 等
expr = MyExpression(dialect, Column(dialect, "amount")) > 100
```

## 序列化

表达式支持序列化/反序列化，用于缓存和日志记录：

```python
# 序列化
data = expr.serialize()

# 反序列化
expr = BaseExpression.deserialize(data)
```

## 另请参阅

- [核心表达式系统](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/expression) -- 表达式基类和运算符
- [MySQL 方言](../backend_specific_features/dialect.md) -- MySQL 特定的 SQL 函数

💡 *AI 提示:* "如何为 MySQL JSON 函数创建自定义表达式？"
