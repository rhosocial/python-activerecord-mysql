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

### 语句级常量与 DEFAULT 值

MySQL DDL 中的 `DEFAULT` 子句经常需要使用 SQL 语句级常量（statement-level constants），如 `CURRENT_TIMESTAMP`、`NOW()`、`CURRENT_DATE` 等。这些是 SQL 关键字或函数调用，**不是字符串字面量**，因此必须使用 `FunctionCall` 传入，而非 Python 字符串。

```python
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition, ColumnConstraint, ColumnConstraintType,
)

# 正确：使用 FunctionCall 传递 SQL 语句级常量
ColumnDefinition(
    name='created_at',
    data_type='TIMESTAMP',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT,
                         default_value=FunctionCall(dialect, 'CURRENT_TIMESTAMP')),
        # 生成: `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    ],
)

# 正确：使用 NOW() 函数
ColumnDefinition(
    name='updated_at',
    data_type='DATETIME',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT,
                         default_value=FunctionCall(dialect, 'NOW')),
        # 生成: `updated_at` DATETIME DEFAULT NOW()
    ],
)

# 正确：数字字面量直接传入 Python 原生类型
ColumnDefinition(
    name='is_active',
    data_type='TINYINT(1)',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
        # 生成: `is_active` TINYINT(1) DEFAULT 1
    ],
)

# 正确：字符串字面量传入 Python 字符串（会自动加引号）
ColumnDefinition(
    name='status',
    data_type='VARCHAR(20)',
    constraints=[
        ColumnConstraint(ColumnConstraintType.DEFAULT, default_value='active'),
        # 生成: `status` VARCHAR(20) DEFAULT 'active'
    ],
)
```

**错误做法：**

```python
# 错误：将 SQL 关键字作为 Python 字符串传入
# 这会导致生成 DEFAULT 'CURRENT_TIMESTAMP'（被引号包裹，变成字符串字面量）
ColumnConstraint(ColumnConstraintType.DEFAULT, default_value='CURRENT_TIMESTAMP')
```

**常见语句级常量对照表：**

| SQL 常量 | Expression API | 说明 |
| ---------- | ---------------------------------------------- | ------ |
| `CURRENT_TIMESTAMP` | `FunctionCall(dialect, 'CURRENT_TIMESTAMP')` | 当前时间戳 |
| `CURRENT_TIMESTAMP(6)` | `FunctionCall(dialect, 'CURRENT_TIMESTAMP', Literal(dialect, 6))` | 带精度的时间戳 |
| `NOW()` | `FunctionCall(dialect, 'NOW')` | 当前日期时间 |
| `CURRENT_DATE` | `FunctionCall(dialect, 'CURRENT_DATE')` | 当前日期 |
| `CURRENT_TIME` | `FunctionCall(dialect, 'CURRENT_TIME')` | 当前时间 |
| `UUID()` | `FunctionCall(dialect, 'UUID')` | 生成 UUID（MySQL 8.0+） |

> **核心规则**：凡是 SQL 中的关键字、函数、常量（不需要引号包裹的），一律使用 `FunctionCall`；凡是需要引号包裹的字面量值，使用 Python 原生类型（字符串、数字、布尔值）。

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

## 查询运行时函数与常量

MySQL 支持不涉及数据源的纯函数查询，如 `SELECT CURRENT_TIMESTAMP`、`SELECT NOW()`、`SELECT VERSION()` 等。使用 `QueryExpression` 不指定 `from_` 子句即可实现。

```python
from rhosocial.activerecord.backend.expression import QueryExpression
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal

# SELECT CURRENT_TIMESTAMP()
query = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'CURRENT_TIMESTAMP')],
)
sql, params = query.to_sql()
# 生成: SELECT CURRENT_TIMESTAMP()

# SELECT NOW()
query = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'NOW')],
)
# 生成: SELECT NOW()

# SELECT CURRENT_DATE, CURRENT_TIME
query = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'CURRENT_DATE'),
        FunctionCall(dialect, 'CURRENT_TIME'),
    ],
)
# 生成: SELECT CURRENT_DATE(), CURRENT_TIME()

# 带别名的多函数查询
query = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'NOW').as_('current_time'),
        FunctionCall(dialect, 'DATABASE').as_('db_name'),
        FunctionCall(dialect, 'VERSION').as_('db_version'),
    ],
)
# 生成: SELECT NOW() AS `current_time`, DATABASE() AS `db_name`, VERSION() AS `db_version`

# 带参数的函数调用
query = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'DATE_FORMAT',
                     FunctionCall(dialect, 'NOW'),
                     Literal(dialect, '%Y-%m-%d')).as_('formatted_date'),
    ],
)
# 生成: SELECT DATE_FORMAT(NOW(), %s) AS `formatted_date`
```

**常用 MySQL 信息函数：**

| 函数 | Expression API | 返回值 |
| ------ | ---------------------------------------------- | ------ |
| `CURRENT_TIMESTAMP()` | `FunctionCall(dialect, 'CURRENT_TIMESTAMP')` | 当前时间戳 |
| `NOW()` | `FunctionCall(dialect, 'NOW')` | 当前日期时间 |
| `CURRENT_DATE` | `FunctionCall(dialect, 'CURRENT_DATE')` | 当前日期 |
| `CURRENT_TIME` | `FunctionCall(dialect, 'CURRENT_TIME')` | 当前时间 |
| `DATABASE()` | `FunctionCall(dialect, 'DATABASE')` | 当前数据库名 |
| `VERSION()` | `FunctionCall(dialect, 'VERSION')` | MySQL 版本号 |
| `USER()` | `FunctionCall(dialect, 'USER')` | 当前用户 |
| `UUID()` | `FunctionCall(dialect, 'UUID')` | 生成 UUID（8.0+） |
| `CONNECTION_ID()` | `FunctionCall(dialect, 'CONNECTION_ID')` | 连接 ID |

> **注意**：`FunctionCall` 生成的函数调用始终带括号。MySQL 中 `CURRENT_TIMESTAMP` 和 `CURRENT_TIMESTAMP()` 在 DDL DEFAULT 上下文中均合法，在 SELECT 上下文中也均合法。
