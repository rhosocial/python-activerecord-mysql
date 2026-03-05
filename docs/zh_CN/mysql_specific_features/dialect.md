# MySQL Dialect 表达式

## 概述

MySQL 有一些特定的 SQL 语法和函数，本节介绍常用的 MySQL 特有表达式。

## DDL 语句

### CREATE TABLE ... LIKE

MySQL 支持使用 `LIKE` 子句复制表结构。这对于创建具有相同结构的表备份或测试表非常有用。

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

# 基本用法 - 复制表结构
create_expr = CreateTableExpression(
    dialect=MySQLDialect(),
    table_name="users_copy",
    columns=[],
    dialect_options={'like_table': 'users'}
)
# 生成: CREATE TABLE `users_copy` LIKE `users`

# 带模式限定的源表
create_expr = CreateTableExpression(
    dialect=MySQLDialect(),
    table_name="users_copy",
    columns=[],
    dialect_options={'like_table': ('production', 'users')}
)
# 生成: CREATE TABLE `users_copy` LIKE `production`.`users`

# 带临时表和 IF NOT EXISTS
create_expr = CreateTableExpression(
    dialect=MySQLDialect(),
    table_name="temp_users",
    columns=[],
    temporary=True,
    if_not_exists=True,
    dialect_options={'like_table': 'users'}
)
# 生成: CREATE TABLE TEMPORARY IF NOT EXISTS `temp_users` LIKE `users`
```

**重要说明：**
- 当 `dialect_options` 中指定 `like_table` 时，具有最高优先级
- 所有其他参数（columns、indexes、constraints 等）都会被忽略
- 只有 `temporary` 和 `if_not_exists` 标志会被考虑
- MySQL 的 LIKE 会复制：列、索引、约束、默认值、auto_increment 设置

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
