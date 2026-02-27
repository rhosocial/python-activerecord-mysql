# MySQL Dialect 表达式

## 概述

MySQL 有一些特定的 SQL 语法和函数，本节介绍常用的 MySQL 特有表达式。

## 特有的运算符

### LIKE 表达式

```python
# 搜索以指定字符开头的记录
User.query().where(User.c.name.like('%test%'))

# REGEXP 正则表达式
User.query().where(User.c.name.regexp('^A.*'))
```

## 特有的函数

### GROUP_CONCAT

```python
# 连接分组中的字符串
# SELECT GROUP_CONCAT(name SEPARATOR ',') FROM users GROUP BY role
from rhosocial.activerecord.backend.expression import FunctionExpression


class GroupConcat(FunctionExpression):
    def __init__(self, column, separator=','):
        super().__init__(
            'GROUP_CONCAT',
            column,
            separator=f"SEPARATOR '{separator}'"
        )
```

### ON DUPLICATE KEY UPDATE

```python
# 插入或更新
# INSERT INTO users (id, name) VALUES (1, 'Tom') ON DUPLICATE KEY UPDATE name = 'Tom'
```

### REPLACE INTO

```python
# 替换插入（先删除再插入）
# REPLACE INTO users (id, name) VALUES (1, 'Tom')
```

💡 *AI 提示词：* "MySQL 的 REPLACE INTO 和 INSERT ... ON DUPLICATE KEY UPDATE 有什么区别？"
