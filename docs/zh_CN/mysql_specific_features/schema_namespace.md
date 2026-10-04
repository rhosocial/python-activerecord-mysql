# docs/zh_CN/mysql_specific_features/schema_namespace.md

# MySQL Schema 命名空间

> 本文只讲本后端特有的部分：`schema_name` 在这里指向的是 database 而不是一层命名空间、
> 限定名如何渲染、列引用为什么永远不带 database、DDL 语句各自怎么使用这个值，以及标识符
> 的大小写如何处理。
>
> 模型层的通用部分——怎么在模型上声明 `__schema_name__`、schema 何时进入 SQL、
> DDL 的边界、各后端支持矩阵——由核心库（`python-activerecord` 仓库）的
> `docs/modeling/schema_namespace.md` 讲，见
> [`docs/zh_CN/modeling/schema_namespace.md`][core-zh]。同样的要点在
> [dialect.md](dialect.md) 的「schema 名称」一节里有摘要。

[core-zh]: https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/modeling/schema_namespace.md

## 本文结论的验证方式

文中的 SQL 由表达式层配合 `MySQLDialect()` 渲染得出，过程中没有连接服务端；涉及版本门控的
能力（只有下面 CTE 那个例子）改用 `MySQLDialect(version=(8, 0, 46))`。两者都是在**本分支**
的核心库上运行的：

```
PYTHONPATH=/mnt/i/GitHubRepositories/rhosocial/.worktrees/core-schema-name/src \
  .venv3.14-ubuntu26.04/bin/python
```

描述服务端而非渲染器的部分，则在 `tests/config/mysql_scenarios.yaml` 声明的每一个实例上
实际执行过——MySQL 5.6.51、5.7.44、8.0.46、8.4.11、9.2.0、9.4.0、26.7.0。下面报告的每一项
服务端行为，七者返回的结果都相同：`SHOW SCHEMAS` 与 `SHOW DATABASES` 的对比、`DATABASE()`
与 `SCHEMA()` 的等价关系、三段列引用、别名不存在的报错、索引名的语法错误，以及 database
名与表名的大小写行为。

## `schema_name` 在这里指向 database

这一点要先讲清楚，因为本页其余所有示例的含义都取决于它。

**MySQL 在 database 内部没有命名空间层。`schema` 与 `database` 是同一个词，只是有两种
写法。** `CREATE SCHEMA app` 建出来的是 database，而这个 database 正是 `SHOW DATABASES`
与 `SHOW SCHEMAS` 都会列出来的东西：

```sql
CREATE SCHEMA app;
SHOW SCHEMAS;        -- 列出 app
SHOW DATABASES;      -- 同样列出 app，两者结果完全一致
```

在上述七个实例上实测，两个列表逐项相同。用 `CREATE DATABASE` 建出来的 database，在
`SHOW SCHEMAS` 里同样查得到。

`MySQLDialect` 实现了核心库的 `SchemaSupport` 协议，因此凡是核心库期待出现 `schema_name`
的地方都能接受：

```python
dialect.supports_schema()                # True
dialect.supports_create_schema()         # True
dialect.supports_drop_schema()           # True
dialect.supports_schema_if_not_exists()  # True
dialect.supports_schema_if_exists()      # True
dialect.supports_schema_cascade()        # False
dialect.supports_schema_authorization()  # False
```

两个 `False` 来自 MySQL 自身，且是在渲染阶段直接拒绝，而不是当作没看见：

```
UnsupportedFeatureError: 'MySQL' dialect does not support CREATE SCHEMA
AUTHORIZATION. Suggestion: MySQL does not support CREATE SCHEMA AUTHORIZATION.
```

```
UnsupportedFeatureError: 'MySQL' dialect does not support DROP SCHEMA CASCADE.
Suggestion: MySQL does not support DROP SCHEMA CASCADE.
```

### 与 PostgreSQL 的差别

在 PostgreSQL 上，`schema_name` 指向当前 database **内部**的一个命名空间，所以同一条
连接里 `app.orders` 与 `public.orders` 是两张互不相干的表；这个值是三段式名字里的
一层。

在这里，这个值**就是**整个 database。没有第三层，于是：

| | PostgreSQL | MySQL |
|---|---|---|
| `schema_name="app"` 指向 | 当前 database 内的 schema | 当前 database 自身，或另一个 database |
| 完整限定名 | `app.orders`，三段中的一段 | `app`.`orders`，全部 |
| 两个 schema 并存 | 一条连接里的 `app.orders` 与 `crm.orders` | 两条连接，每个 database 一条 |
| 若要再加一层 | 有真正的命名空间可用 | 无处安放 |

实际影响有两点。一是跨 database 的 join 在这里是**一条**语句
（`FROM shop.orders JOIN crm.users`），而同样两张表在 PostgreSQL 上是同一个 database 里的
两个 schema，不需要另开连接。二是 MySQL 模型上的 `__schema_name__` 决定语句落在服务端
**哪个 database**；切换 schema 就是切换 database，比在 PostgreSQL 上切换命名空间更重。

连接自身的 database 由 `MySQLConnectionConfig(database=...)` 指定，也正是不加限定的名字
所解析到的目标。

## 在模型上声明

```python
from typing import ClassVar, Optional

from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord

class Order(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = "ar_shop"        # 这是一个 database，不是一层命名空间
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    user_id: Optional[int] = None
    total: Optional[int] = None
```

`__schema_name__` 是可选的，默认 `None`，也就是不加限定。设置之后，模型生成的每一条语句
都带上这个 database，而它**只出现在 `FROM` 的表上**：

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT `orders`.`id` FROM `ar_shop`.`orders`

Order.query().where(Order.c.id > 1).to_sql()[0]
# SELECT * FROM `ar_shop`.`orders` WHERE `orders`.`id` > %s

Order.query().order_by(Order.c.id).to_sql()[0]
# SELECT * FROM `ar_shop`.`orders` ORDER BY `orders`.`id` ASC
```

没有设 `__schema_name__` 的模型渲染成不带限定的形式，交给连接去决定：

```python
PlainOrder.query().select(PlainOrder.c.id).to_sql()[0]
# SELECT `orders`.`id` FROM `orders`
```

这个值只经由 `schema_name()` 读取一次，并在各个列表达式构造时传下去。因此事后修改
`__schema_name__` 不会改写已经存在的表达式——条件要重新构造，或者在改动之后再构造。

## 限定名如何渲染

每一段各自加引号，引号是反引号。MySQL 用反引号标识符，方言不会产出别的引号字符。

| 表达式 | SQL |
|---|---|
| `TableExpression(dialect, "orders", schema_name="app")` | `` `app`.`orders` `` |
| `TableExpression(dialect, "orders")` | `` `orders` `` |
| `TableExpression(dialect, "orders", schema_name="app", alias="o")` | `` `app`.`orders` AS `o` `` |

值里的反引号按双写转义，因此值本身无法提前结束它所在的引号：

```python
TableExpression(dialect, "orders", schema_name="a`b").to_sql()[0]
# `a``b`.`orders`
```

渲染阶段不做任何大小写折叠：`schema_name="App"` 渲染成 `` `App`.`orders` ``，与写下来的
一模一样。服务端随后如何匹配，见[标识符的大小写与引号](#标识符的大小写与引号)。

## 列引用只有两段，绝不三段

**database 落在 `FROM` 的表上，此外任何地方都不出现。** 本后端渲染出的列引用最多两段：

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT `orders`.`id` FROM `ar_shop`.`orders`
```

带 `schema_name` 的列表达式会丢掉这个值，只留表限定：

```python
Column(dialect, "id", table="orders", schema_name="app").to_sql()[0]
# `orders`.`id`
```

MySQL 方言覆写了核心库的 `format_column` 来实现这一点。核心库对一个未取别名的、带 schema
的范围渲染三段引用，那是 PostgreSQL 需要的形状；这里改为输出两段。

这是本后端的选择，而不是服务端的限制。MySQL 自身接受三段写法：

```sql
SELECT `ar_shop`.`orders`.`id` FROM `ar_shop`.`orders`;   -- 接受
SELECT * FROM `ar_shop`.`orders`.`id`;                    -- 语法错误
```

被服务端拒绝的是 `FROM` 里没有对应表时的限定列引用。本后端不会生成这种语句，因为范围上
一定带着 database。

### 裸列上的 `schema_name` 报警告而不是报错

一个带 `schema_name` 却没有 `table` 的列表达式根本无法限定。核心方言在这里抛异常；本后端
改为发出警告并渲染裸列，这样同一份模型定义既能指向 MySQL，也能指向真正有 schema 层的
后端：

```python
Column(dialect, "id", schema_name="app").to_sql()[0]
# `id`
# UserWarning: MySQL: dropping schema_name='app' from column 'id' because no
# table was given; a column reference needs a table to be qualified
```

### 取了表别名之后用什么标识一个范围

别名会顶替范围的名字，所以取过别名之后，能标识这个范围的只剩别名。范围仍带着 database，
列引用则变成一段：

```python
aliased = Order.c.with_table_alias("o")

CrmUser.query().join(Order, on=aliased.user_id == CrmUser.c.id, alias="o") \
    .select(CrmUser.c.name, aliased.total).to_sql()[0]
# SELECT `users`.`name`, `o`.`total` FROM `ar_crm`.`users`
#   JOIN `ar_shop`.`orders` AS `o` ON `o`.`user_id` = `users`.`id`
```

只在列这一侧取别名而范围没取，框架不会拒绝，是服务端报错：

```python
Order.query().select(Order.c.with_table_alias("o").id).to_sql()[0]
# SELECT `o`.`id` FROM `ar_shop`.`orders`
```

```
1054 (42S22): Unknown column 'o.id' in 'field list'
```

### 跨 database 的 join

两侧各自限定自己的范围，所以一条语句可以横跨两个 database，无需额外配置：

```python
Order.query().join(CrmUser, on=Order.c.user_id == CrmUser.c.id) \
    .select(Order.c.id, CrmUser.c.name).to_sql()[0]
# SELECT `orders`.`id`, `users`.`name` FROM `ar_shop`.`orders`
#   JOIN `ar_crm`.`users` ON `orders`.`user_id` = `users`.`id`
```

### 集合操作

`UNION`、`INTERSECT`、`EXCEPT` 本身不指称任何对象，因此没有可限定的东西。每个分支各自
保留自己的 database：

```python
Order.query().select(Order.c.id).union(
    CrmUser.query().select(CrmUser.c.id)).to_sql()[0]
# SELECT `orders`.`id` FROM `ar_shop`.`orders`
#   UNION SELECT `users`.`id` FROM `ar_crm`.`users`
```

### CTE

CTE 是给查询其余部分用的名字，不是 database 的名字，因此它自身的名字永远不加限定。CTE
内部的查询仍然带着模型的 database：

```python
cte = CTEQuery(backend)
cte.with_cte("recent_orders", Order.query().select(Order.c.id))
cte.from_cte("recent_orders").select("*").to_sql()[0]
# WITH `recent_orders` AS (SELECT `orders`.`id` FROM `ar_shop`.`orders`)
#   SELECT `*` FROM `recent_orders`
```

`CTEQuery` 要求方言报告支持 CTE，本后端把它限定在 MySQL 8.0 及以后。

## DDL 语句要各自写明 database

`__schema_name__` 决定读写的 database。构造 DDL 时并不读取它——迁移必须自己写明它要的
database——但也不必再手工拼限定名。

**凡是目标是一个表的语句，收的都是 `TableExpression`，不是表名字符串。** 传裸字符串一律在
**构造期**报错：

```
TypeError: table must be a TableExpression, got str
```

收 `TableExpression` 的语句有 `CreateTableExpression`、`DropTableExpression`、
`TruncateExpression`、`AlterTableExpression`、`CreateIndexExpression`、
`DropIndexExpression`、`CreateFulltextIndexExpression`、
`DropFulltextIndexExpression`、`CreateTriggerExpression` 与
`DropTriggerExpression`。它们之中，限定表的都不是 `schema_name`，而是那个
`TableExpression`。`CREATE TABLE`、`DROP TABLE`、`TRUNCATE`、`ALTER TABLE` 干脆没有
`schema_name` 参数；索引类与触发器类语句则保留了一个，但那里它限定的是索引名或触发器名
——正是下面两小节要讲的事。

```python
TruncateExpression(dialect, TableExpression(dialect, "users", schema_name="app")).to_sql()[0]
# TRUNCATE TABLE `app`.`users`

DropTableExpression(dialect, TableExpression(dialect, "users", schema_name="app"),
                    if_exists=True).to_sql()[0]
# DROP TABLE IF EXISTS `app`.`users`
```

**不是表的对象仍然各自带 `schema_name`**——视图、触发器、序列、类型、函数、域，以及语句
要创建或删除的 schema / database 本身：

```python
CreateViewExpression(dialect, "v_users", query, schema_name="app").to_sql()[0]
# CREATE VIEW `app`.`v_users` AS ...

DropViewExpression(dialect, "v_users", schema_name="app", if_exists=True).to_sql()[0]
# DROP VIEW IF EXISTS `app`.`v_users`
```

上面这四条语句——`TRUNCATE`、`DROP TABLE`、`CREATE VIEW`、`DROP VIEW`——同样在七个实例上
实际执行过。

`CREATE SCHEMA` 与 `DROP SCHEMA` 是另两回事：在这两条语句里，这个值不是限定符，**就是**
语句所指的对象本身。两种写法在这里都可用，建的都是 database、删的也都是 database：

```python
CreateSchemaExpression(dialect, "app").to_sql()[0]                  # CREATE SCHEMA `app`
CreateSchemaExpression(dialect, "app", if_not_exists=True).to_sql()[0]
# CREATE SCHEMA IF NOT EXISTS `app`
DropSchemaExpression(dialect, "app").to_sql()[0]                    # DROP SCHEMA `app`
DropSchemaExpression(dialect, "app", if_exists=True).to_sql()[0]
# DROP SCHEMA IF EXISTS `app`
```

`CreateDatabaseExpression` 与 `DropDatabaseExpression` 渲染成 `DATABASE` 写法，行为完全
一致。它们没有从表达式包里再导出，因此要按模块路径导入：

```python
from rhosocial.activerecord.backend.expression.statements.ddl_database import (
    CreateDatabaseExpression,
    DropDatabaseExpression,
)

CreateDatabaseExpression(dialect, "app").to_sql()[0]                # CREATE DATABASE `app`
DropDatabaseExpression(dialect, "app", if_exists=True).to_sql()[0]  # DROP DATABASE IF EXISTS `app`
```

在 MySQL 上，迁移里用 `CreateDatabaseExpression` 更贴切——它直接说明了这条语句实际做的事。

### `CREATE INDEX` 与 `DROP INDEX` 限定的是表，不是索引

索引属于它所依附的表，MySQL 拒绝带 database 的索引名。本后端的
`supports_index_schema_qualification()` 为 `False`，给这两条语句传 `schema_name` 会在
渲染阶段直接被拒：

```
UnsupportedFeatureError: 'MySQL' dialect does not support a namespace-qualified
index name. Suggestion: MySQL places an index in the namespace of its table and
rejects a qualified index name. Qualify the table instead by passing it as a
TableExpression with schema_name set.
```

在这两条语句上，`schema_name` **只**限定索引名，对表已经没有影响——这也正是「限定索引」
如今变成报错、而不是一条交给服务端报语法错误的 SQL 的原因：

```python
CreateIndexExpression(dialect, "idx_a", TableExpression(dialect, "orders", schema_name="app"),
                      ["total"], schema_name="app").to_sql()[0]
# UnsupportedFeatureError（同上）
```

正确做法是只限定表，索引名保持裸名：

```python
CreateIndexExpression(dialect, "idx_a", TableExpression(dialect, "orders", schema_name="app"),
                      ["total"]).to_sql()[0]
# CREATE INDEX `idx_a` ON `app`.`orders` (`total`)

DropIndexExpression(dialect, "idx_a", TableExpression(dialect, "orders", schema_name="app")).to_sql()[0]
# DROP INDEX `idx_a` ON `app`.`orders`
```

这两种渲染结果都在上述实例上核对过，服务端都接受；而旧行为手工拼出的那种写法会被拒绝：

```
1064 (42000): You have an error in your SQL syntax; check the manual that
corresponds to your MySQL server version for the right syntax to use near
'.`idx_a` ON `ar_shop`.`orders` (`total`)' at line 1
```

也正因为有这个拒绝，带 `__schema_name__` 的模型用不了 `build_create_index_statement()` 与
`build_drop_index_statement()`：它们把索引的命名空间默认成 `schema_name()`，而传
`index_schema_name=None` 恰恰表示「沿用模型的」，不是「不限定」。所以一个声明了
`__schema_name__ = "ar_shop"` 的模型从工厂拿到的就是 `UnsupportedFeatureError`；要在那个
database 里建索引，就照上面的样子手工构造 `CreateIndexExpression`：

```python
Order.build_create_index_statement(dialect, "idx_a", ["total"]).to_sql()[0]
# UnsupportedFeatureError（同上）
```

## 不加限定的名字落在哪个 database

```python
backend.get_current_schema()          # 当前 database
await async_backend.get_current_schema()
```

它通过 `current_schema()` 询问服务端，渲染出来是 `SELECT DATABASE()`：

```python
from rhosocial.activerecord.backend.impl.mysql.functions.schema import (
    current_schema,
)

current_schema(dialect).to_sql()[0]   # DATABASE()
```

在 MySQL 里 `SCHEMA()` 是 `DATABASE()` 的同义词，返回值相同；方言选 `DATABASE()` 这个
写法，因为 MySQL 的函数文档是这么写的。

连接没有选中 database 时，这个方法返回 `None`，而不抛异常：

```python
# MySQLConnectionConfig 未给 database=...
backend.get_current_schema()          # None

# MySQLConnectionConfig(database="ar_shop", ...)
backend.get_current_schema()          # 'ar_shop'
```

## 空串，以及它在哪一步被拦下

`""` 是一个错误，而不是表达「不加限定」——那件事由 `None` 负责。它会被拒绝，但**不是在
表达式构造时**：那个阶段表达式只是收集参数，严格校验要等到渲染、也就是语句完整之后才
进行。因此这个失败比预想的来得晚。报错信息里指的是**带着这个值的那个表达式**，而不是调用方
写下的那条语句；模型构造出来的列自带这个值，所以查询抛出的是 `Column` 那条措辞：

```python
class Bad(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = ""

Bad.schema_name()                        # ''        -- 不报错
Bad.c.id                                 # Column    -- 不报错
Bad.query()                              # query     -- 不报错
Bad.query().select(Bad.c.id)             # query     -- 不报错
Bad.query().select(Bad.c.id).to_sql()    # ValueError -- 到这里才报错
```

```
ValueError: Column.schema_name must be a non-empty string; use None for an
unqualified reference
```

纯空白串与空串同样被拒——校验前会先 strip，所以 `"   "` 也过不去。非字符串同样被拒，
只是换成另一条信息：

```
ValueError: Column.schema_name must be a string or None, not int
```

直接写出表名的表达式则报 `TableExpression` 那一条：

```python
TableExpression(dialect, "orders", schema_name="").to_sql()[0]
# ValueError: TableExpression.schema_name must be a non-empty string; use None
#             for an unqualified reference

TableExpression(dialect, "orders", schema_name=123).to_sql()[0]
# ValueError: TableExpression.schema_name must be a string or None, not int
```

`TruncateExpression` 抛 `TableExpression` 那条措辞也是同一个原因：它的目标**就是**一个
`TableExpression`，执行校验的正是那个对象。

```python
TruncateExpression(dialect, TableExpression(dialect, "orders", schema_name="")).to_sql()[0]
# ValueError: TableExpression.schema_name must be a non-empty string; use None
#             for an unqualified reference
```

## 标识符的大小写与引号

标识符用反引号引起来，渲染器不折叠大小写：值按写下来的样子原样输出。之后服务端是否匹配
得上，是服务端的设置，本后端不做决定。

在 `tests/config/mysql_scenarios.yaml` 的七个实例上实测，`@@lower_case_table_names`
每一个都是 `0`，database 名也表现为大小写敏感：

```
SHOW DATABASES LIKE 'AR_SHOP';   -- 空，当 database 名为 ar_shop 时
USE `AR_SHOP`;                   -- 1049 (42000): Unknown database 'AR_SHOP'
```

表名遵循同一设置。在 `lower_case_table_names = 0` 下，以 `MixedCase` 建出来的表无法用
`mixedcase` 访问：

```
1146 (42S02): Table 'ar_shop.mixedcase' doesn't exist
```

换个服务端可能配置不同。`lower_case_table_names` 是服务端变量，本后端不读取它，因此这里
不会有什么自动适配。需要记住的是：渲染器保留大小写，把这个判断交给服务端。

MySQL 没有 `lower_case_schema_names` 这个变量，查询它会失败并报
`Unknown system variable`。

## 常见错误

**以为有一层命名空间。** 这个值指向的是 database，因此不存在第三层。
`schema_name="app.sales"` 渲染成 `` `app.sales`.`orders` ``——名字里带着点号的
database：

```python
TableExpression(dialect, "orders", schema_name="app.sales").to_sql()[0]
# `app.sales`.`orders`
```

每段各自加引号，段内的点号就留在这一段里。

**写三段列引用。** 本后端从不渲染三段引用；手工构造的列即使同时带表和 schema，也会丢掉
schema：

```python
Column(dialect, "id", table="orders", schema_name="app").to_sql()[0]
# `orders`.`id`     -- 不是 `app`.`orders`.`id`
```

**`__table_name__` 里的点号不是 database 限定符。** 该标识符整体加引号，MySQL 就照这个
名字建表：

```python
TableExpression(dialect, "app.orders").to_sql()[0]
# `app.orders`
```

```
CREATE TABLE `ar_shop`.`app.orders` (id INT);   -- 成功，表名就是 `app.orders`
```

请改用 `__schema_name__`。

**字段名里的 schema 只是列名。** database 限定的是范围，与列名怎么拼写无关：

```python
class Report(ActiveRecord):
    __table_name__ = "reports"
    __schema_name__ = "app"
    app_total: Optional[int] = None

Report.query().select(Report.c.app_total).to_sql()[0]
# SELECT `reports`.`app_total` FROM `app`.`reports`
```

**只给列那一侧取别名。** 别名必须同时设在范围上，否则服务端会报未知列。参见
[取了表别名之后用什么标识一个范围](#取了表别名之后用什么标识一个范围)。

**以为构造阶段就会报错。** 在语句渲染之前，没有任何东西拒绝一个不合法的 `schema_name`；
写错的 database 名也不会有警告——模型指向一个连接够不到的 database，结果就是在执行时
失败。

**把表名字符串传给 DDL 语句。** `TRUNCATE`、`CREATE TABLE`、`DROP TABLE`、
`ALTER TABLE`、索引类语句与触发器语句收的都是 `TableExpression`，因此传裸字符串是在
**构造期**就抛 `TypeError`，而不是被悄悄当成不带限定的名字：

```python
TruncateExpression(dialect, "users")
# TypeError: table must be a TableExpression, got str
```

**给索引语句传 `schema_name`。** MySQL 上没有可限定的索引名，因此这个值会被直接拒绝，
而不是渲染出来。要限定的是表，请改用表自己的 `TableExpression`。参见
[`CREATE INDEX` 与 `DROP INDEX` 限定的是表，不是索引](#create-index-与-drop-index-限定的是表不是索引)。

## 相关页面

- [MySQL Dialect 表达式](dialect.md)——同样的要点摘要，以及 MySQL 特有的表达式接口
- [数据库内省](introspection.md)——通过 `information_schema` 与 `SHOW` 读取元数据
- 核心库指南 `docs/modeling/schema_namespace.md`——模型层 API 与各后端支持矩阵
