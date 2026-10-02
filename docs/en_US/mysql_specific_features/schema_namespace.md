# docs/en_US/mysql_specific_features/schema_namespace.md

# MySQL Schema Namespaces

> This page covers what is specific to this backend: that a `schema_name` names
> a database rather than a namespace inside one, how a qualified name is
> rendered, why a column reference never carries the database, what the DDL
> statements do with the value, and how identifier case is treated.
>
> The model-level API — declaring `__schema_name__`, when the schema reaches
> the SQL, the DDL boundary, the cross-backend support matrix — is documented in
> the core library guide `docs/modeling/schema_namespace.md`, which lives in the
> `python-activerecord` repository
> ([`docs/en_US/modeling/schema_namespace.md`][core-en]). A summary of the same
> points appears under *Schema Names* in [dialect.md](dialect.md).

[core-en]: https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/schema_namespace.md

## How this page was verified

SQL fragments were rendered by the expression layer through
`MySQLDialect()` with no server involved:

```
PYTHONPATH=src .venv3.14-ubuntu26.04/bin/python
```

Statements that describe the server rather than the renderer were executed
against every instance declared in `tests/config/mysql_scenarios.yaml` — MySQL
5.6.51, 5.7.44, 8.0.46, 8.4.11, 9.2.0, 9.4.0 and 26.7.0. All seven returned the
same result for everything reported below: the `SHOW SCHEMAS` / `SHOW DATABASES`
comparison, the `DATABASE()` / `SCHEMA()` equivalence, the three-part column
reference, the unknown-alias error, the index-name syntax error, and the case
behaviour of database and table names.

## A `schema_name` here names a database

Settle this first, because it decides what every other example in this page
means.

**MySQL has no namespace layer inside a database. `schema` and `database` are
one word with two spellings.** `CREATE SCHEMA app` creates a database, and the
database it creates is what `SHOW DATABASES` and `SHOW SCHEMAS` both list:

```sql
CREATE SCHEMA app;
SHOW SCHEMAS;        -- lists app
SHOW DATABASES;      -- lists app, and the same list
```

Measured on all seven instances above, the two listings are identical element for
element. A database created with `CREATE DATABASE` shows up in `SHOW SCHEMAS`
just the same.

`MySQLDialect` implements the core `SchemaSupport` protocol, so a `schema_name`
is accepted everywhere the core expects one:

```python
dialect.supports_schema()                # True
dialect.supports_create_schema()         # True
dialect.supports_drop_schema()           # True
dialect.supports_schema_if_not_exists()  # True
dialect.supports_schema_if_exists()      # True
dialect.supports_schema_cascade()        # False
dialect.supports_schema_authorization()  # False
```

The two `False` values are MySQL's own, and they are refused while the statement
renders rather than being ignored:

```
UnsupportedFeatureError: 'MySQL' dialect does not support CREATE SCHEMA
AUTHORIZATION. Suggestion: MySQL does not support CREATE SCHEMA AUTHORIZATION.
```

```
UnsupportedFeatureError: 'MySQL' dialect does not support DROP SCHEMA CASCADE.
Suggestion: MySQL does not support DROP SCHEMA CASCADE.
```

### How this differs from PostgreSQL

On PostgreSQL a `schema_name` names a namespace **inside** the current database,
so one connection sees `app.orders` and `public.orders` as two unrelated tables.
The value is one level of a three-part name.

Here the value *is* the whole database. There is no third level, so:

| | PostgreSQL | MySQL |
|---|---|---|
| `schema_name="app"` names | a schema inside the current database | the current database itself, or another one |
| Fully qualified name | `app.orders`, one of three levels | `app`.`orders`, all of them |
| Two schemas side by side | `app.orders` and `crm.orders` in one connection | two separate connections, one per database |
| What a second level would need | a real namespace | nothing — there is nowhere to put it |

The practical consequence is that a cross-database join is a single statement
here (`FROM shop.orders JOIN crm.users`), while the same two tables on
PostgreSQL are two schemas inside one database and need no separate connection.
The other consequence is that `__schema_name__` on a MySQL model selects which
**server database** the statement lands in — switching schemas switches the
database, which is a heavier operation than switching a namespace on
PostgreSQL.

The connection's own database is set by `MySQLConnectionConfig(database=...)`,
and it is what an unqualified name resolves against.

## Declaring one on a model

```python
from typing import ClassVar, Optional

from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord

class Order(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = "ar_shop"        # a database, not a namespace
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    user_id: Optional[int] = None
```

`__schema_name__` is optional and defaults to `None`, which means unqualified.
When it is set, every statement the model builds carries the database, and only
the `FROM` range shows it:

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT `orders`.`id` FROM `ar_shop`.`orders`

Order.query().where(Order.c.id > 1).to_sql()[0]
# SELECT * FROM `ar_shop`.`orders` WHERE `orders`.`id` > %s

Order.query().order_by(Order.c.id).to_sql()[0]
# SELECT * FROM `ar_shop`.`orders` ORDER BY `orders`.`id` ASC
```

A model without `__schema_name__` renders unqualified and lets the connection
decide:

```python
PlainOrder.query().select(PlainOrder.c.id).to_sql()[0]
# SELECT `orders`.`id` FROM `orders`
```

The value is read once, through `schema_name()`, and reaches each column
expression as it is built. Changing `__schema_name__` afterwards therefore does
not rewrite an expression that already exists — rebuild the condition, or build
it after the change.

## How a qualified name is rendered

Each part is quoted on its own, with a backtick. MySQL uses backticks for
identifiers; no other quoting character is produced by the dialect.

| Expression | SQL |
|---|---|
| `TableExpression(dialect, "orders", schema_name="app")` | `` `app`.`orders` `` |
| `TableExpression(dialect, "orders")` | `` `orders` `` |
| `TableExpression(dialect, "orders", schema_name="app", alias="o")` | `` `app`.`orders` AS `o` `` |

A backtick inside the value is escaped by doubling it, so a value cannot break
out of its own quoting:

```python
TableExpression(dialect, "orders", schema_name="a`b").to_sql()[0]
# `a``b`.`orders`
```

Nothing is case-folded at render time. `schema_name="App"` renders `` `App`.`orders` ``
exactly as written — see [Identifier case](#identifier-case-and-quoting) for what
the server then does with it.

## A column reference has two parts, never three

**The database appears on the table in `FROM` and nowhere else.** Every column
reference this backend renders has at most two parts:

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT `orders`.`id` FROM `ar_shop`.`orders`
```

A `schema_name` reaching a column expression is dropped, and the column renders
with its table qualifier alone:

```python
Column(dialect, "id", table="orders", schema_name="app").to_sql()[0]
# `orders`.`id`
```

The MySQL dialect overrides the core `format_column` to do this. The core
renders a three-part reference for an unaliased schema-bound range, which is
what PostgreSQL wants; here the two-part form is emitted instead.

This is a choice of this backend rather than a limit of the server. MySQL itself
accepts the three-part spelling:

```sql
SELECT `ar_shop`.`orders`.`id` FROM `ar_shop`.`orders`;   -- accepted
SELECT * FROM `ar_shop`.`orders`.`id`;                    -- syntax error
```

A qualified column without a table in `FROM` is what the server rejects. Nothing
in this backend generates it, because the range always carries the database.

### A `schema_name` on a bare column raises a warning rather than an error

A column expression with a `schema_name` but no `table` cannot be qualified at
all. The core dialect raises here; this backend warns and renders the bare
column, so that one model definition can still target both MySQL and a backend
that has a schema layer:

```python
Column(dialect, "id", schema_name="app").to_sql()[0]
# `id`
# UserWarning: MySQL: dropping schema_name='app' from column 'id' because no
# table was given; a column reference needs a table to be qualified
```

### What a table alias leaves to address a range by

An alias replaces the range's name, so once a range is aliased the alias is all
that is left to address it by. The range keeps its database; the column
reference becomes one part:

```python
aliased = Order.c.with_table_alias("o")

CrmUser.query().join(Order, on=aliased.user_id == CrmUser.c.id, alias="o") \
    .select(CrmUser.c.name, aliased.total).to_sql()[0]
# SELECT `users`.`name`, `o`.`total` FROM `ar_crm`.`users`
#   JOIN `ar_shop`.`orders` AS `o` ON `o`.`user_id` = `users`.`id`
```

Aliasing only the column side leaves the range unaliased, and the server rejects
the statement rather than the framework:

```python
Order.query().select(Order.c.with_table_alias("o").id).to_sql()[0]
# SELECT `o`.`id` FROM `ar_shop`.`orders`
```

```
1054 (42S22): Unknown column 'o.id' in 'field list'
```

### Cross-database joins

Each side qualifies its own range, so one statement can span two databases with
no extra configuration:

```python
Order.query().join(CrmUser, on=Order.c.user_id == CrmUser.c.id) \
    .select(Order.c.id, CrmUser.c.name).to_sql()[0]
# SELECT `orders`.`id`, `users`.`name` FROM `ar_shop`.`orders`
#   JOIN `ar_crm`.`users` ON `orders`.`user_id` = `users`.`id`
```

### Set operations

`UNION`, `INTERSECT` and `EXCEPT` name no object of their own, so there is
nothing for them to qualify. Each branch keeps its own database:

```python
Order.query().select(Order.c.id).union(
    CrmUser.query().select(CrmUser.c.id)).to_sql()[0]
# SELECT `orders`.`id` FROM `ar_shop`.`orders`
#   UNION SELECT `users`.`id` FROM `ar_crm`.`users`
```

### CTEs

A CTE is named for the rest of the query, not for the database, so its own name
is never qualified. The query inside it still carries the model's database:

```python
cte = CTEQuery(backend)
cte.with_cte("recent_orders", Order.query().select(Order.c.id))
cte.from_cte("recent_orders").select("*").to_sql()[0]
# WITH `recent_orders` AS (SELECT `orders`.`id` FROM `ar_shop`.`orders`)
#   SELECT `*` FROM `recent_orders`
```

`CTEQuery` requires a dialect that reports CTE support, which this backend
gates on MySQL 8.0 and later.

## DDL statements name a database of their own

`__schema_name__` selects the database that reads and writes go to. It is not
consulted when DDL is built — a migration has to name the database it means —
and every statement that names a schema-bearing object accepts a `schema_name` of
its own, so qualification no longer has to be assembled by hand.

```python
TruncateExpression(dialect, "users", schema_name="app").to_sql()[0]
# TRUNCATE TABLE `app`.`users`

CreateViewExpression(dialect, "v_users", query, schema_name="app").to_sql()[0]
# CREATE VIEW `app`.`v_users` AS ...

DropViewExpression(dialect, "v_users", schema_name="app", if_exists=True).to_sql()[0]
# DROP VIEW IF EXISTS `app`.`v_users`

DropTableExpression(dialect, TableExpression(dialect, "users", schema_name="app"),
                    if_exists=True).to_sql()[0]
# DROP TABLE IF EXISTS `app`.`users`
```

Each of these was executed against all seven instances.

`CREATE TABLE` and `DROP TABLE` are the two plain forms that take a qualified
`TableExpression` rather than a `schema_name` of their own — they have no
`schema_name` parameter.

`CREATE SCHEMA` and `DROP SCHEMA` are the statements where the value is not a
qualifier but the object itself. Both spellings work here and both create or
drop a database:

```python
CreateSchemaExpression(dialect, "app").to_sql()[0]                  # CREATE SCHEMA `app`
CreateSchemaExpression(dialect, "app", if_not_exists=True).to_sql()[0]
# CREATE SCHEMA IF NOT EXISTS `app`
DropSchemaExpression(dialect, "app").to_sql()[0]                    # DROP SCHEMA `app`
DropSchemaExpression(dialect, "app", if_exists=True).to_sql()[0]
# DROP SCHEMA IF EXISTS `app`
```

`CreateDatabaseExpression` and `DropDatabaseExpression` render the `DATABASE`
spelling and behave identically:

```python
CreateDatabaseExpression(dialect, "app").to_sql()[0]                # CREATE DATABASE `app`
DropDatabaseExpression(dialect, "app", if_exists=True).to_sql()[0]  # DROP DATABASE IF EXISTS `app`
```

On MySQL, `CreateDatabaseExpression` is the more descriptive spelling to reach
for in a migration, because it says what the statement actually does.

### `CREATE INDEX` and `DROP INDEX` do not take one

MySQL does not accept a qualified index name. An index belongs to the table it
is defined on, and `CREATE INDEX db.name` is a syntax error:

```
1064 (42000): You have an error in your SQL syntax; check the manual that
corresponds to your MySQL server version for the right syntax to use near
'.`idx_a` ON `ar_shop`.`orders` (`total`)' at line 1
```

Passing `schema_name` to `CreateIndexExpression` or `DropIndexExpression`
qualifies the index name as well as the table, which is what produces that
error. The two statements also take `table_name` as a `str`, not a
`TableExpression`, so a qualified range cannot be supplied there in place of the
value. Both were checked against the instances above.

An unqualified index name against an unqualified table is accepted:

```python
CreateIndexExpression(dialect, "idx_a", "orders", ["total"]).to_sql()[0]
# CREATE INDEX `idx_a` ON `orders` (`total`)
```

So an index is created on the connection's current database. To create one in a
different database, run the statement against a connection configured for that
database, rather than passing `schema_name`.

## Which database an unqualified name resolves against

```python
backend.get_current_schema()          # the current database
await async_backend.get_current_schema()
```

This asks the server through `current_schema()`, which renders as
`SELECT DATABASE()`:

```python
from rhosocial.activerecord.backend.impl.mysql.functions.schema import (
    current_schema,
)

current_schema(dialect).to_sql()[0]   # DATABASE()
```

`SCHEMA()` is a synonym for `DATABASE()` in MySQL and returns the same value;
the dialect uses the `DATABASE()` spelling because that is what the MySQL
function set documents.

The method returns `None` when the connection has no database selected, rather
than raising:

```python
# MySQLConnectionConfig without database=...
backend.get_current_schema()          # None

# MySQLConnectionConfig(database="ar_shop", ...)
backend.get_current_schema()          # 'ar_shop'
```

## The empty string, and when it is caught

`""` is a mistake, not a way of saying "unqualified" — that is what `None` means.
It is rejected, but **not when the expression is built**: an expression only
collects parameters at that point, so strict validation happens while the
statement is rendered, where the statement is known to be whole. The failure
therefore arrives later than expected:

```python
class Bad(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = ""

Bad.schema_name()                        # ''        -- no error
Bad.c.id                                 # Column    -- no error
Bad.query()                              # query     -- no error
Bad.query().select(Bad.c.id)             # query     -- no error
Bad.query().select(Bad.c.id).to_sql()    # ValueError -- here
```

The message names the expression at fault:

```
ValueError: TableExpression.schema_name must be a non-empty string; use None for
an unqualified reference
```

A blank string is rejected the same way as an empty one — the check strips
whitespace first, so `"   "` is refused too. A non-string is rejected the same
way, with its own message:

```
ValueError: TableExpression.schema_name must be a string or None, not int
```

`TruncateExpression` raises the `TableExpression` wording, because it renders
its table through a `TableExpression` internally — the message names the object
that validated the value, not the statement the caller wrote.

## Identifier case and quoting

Identifiers are quoted with backticks, and the renderer does not fold case: a
value is emitted exactly as it was written. Whether the server then matches that
value is a server setting, not something this backend decides.

Measured on all seven instances in `tests/config/mysql_scenarios.yaml`,
`@@lower_case_table_names` was `0` on every one, and database names behaved as
case-sensitive:

```
SHOW DATABASES LIKE 'AR_SHOP';   -- empty, when the database is named ar_shop
USE `AR_SHOP`;                   -- 1049 (42000): Unknown database 'AR_SHOP'
SELECT * FROM `ar_shop`.`ORDERS`;
                                 -- 1146 (42S02): Table 'ar_shop.ORDERS' doesn't exist
```

Table names followed the same setting. With `lower_case_table_names = 0`, a
table created as `MixedCase` is not reachable as `mixedcase`:

```
1146 (42S02): Table 'ar_shop.mixedcase' doesn't exist
```

A different server may be configured differently. `lower_case_table_names` is a
server variable and is not read by this backend, so nothing here adapts to it.
The value to carry forward is that the renderer preserves case and defers the
question to the server.

MySQL has no `lower_case_schema_names` variable; a query for it fails with
`Unknown system variable`.

## Common mistakes

**Expecting a namespace layer.** The value names a database, so a third level
does not exist. `schema_name="app.sales"` renders `` `app.sales`.`orders` `` —
a database whose literal name is `app.sales`:

```python
TableExpression(dialect, "orders", schema_name="app.sales").to_sql()[0]
# `app.sales`.`orders`
```

Each part is quoted separately and a dot inside one part stays inside that part.

**Writing a three-part column reference.** This backend never renders one, and a
hand-built column carrying both a table and a schema loses the schema:

```python
Column(dialect, "id", table="orders", schema_name="app").to_sql()[0]
# `orders`.`id`     -- not `app`.`orders`.`id`
```

**A dot in `__table_name__` is not a database qualifier.** The identifier is
quoted as a single unit, and MySQL creates a table with exactly that name:

```python
TableExpression(dialect, "app.orders").to_sql()[0]
# `app.orders`
```

```
CREATE TABLE `ar_shop`.`app.orders` (id INT);   -- succeeds, named `app.orders`
```

Use `__schema_name__`.

**A schema in a field name is just a column name.** The database qualifies the
range; it has nothing to do with how a column is spelled:

```python
class Report(ActiveRecord):
    __table_name__ = "reports"
    __schema_name__ = "app"
    app_total: Optional[int] = None

Report.query().select(Report.c.app_total).to_sql()[0]
# SELECT `reports`.`app_total` FROM `app`.`reports`
```

**Aliasing only the column side of a range.** The alias has to be set on the
range as well, or the server reports an unknown column. See
[What a table alias leaves to address a range by](#what-a-table-alias-leaves-to-address-a-range-by).

**Expecting construction to raise.** Nothing rejects a bad `schema_name` until
the statement renders, and nothing warns about a wrong database name — a model
pointing at a database the connection cannot reach simply fails at execution.

**Passing `schema_name` to an index statement.** MySQL has no qualified index
name to give. See
[`CREATE INDEX` and `DROP INDEX` do not take one](#create-index-and-drop-index-do-not-take-one).

## Related pages

- [MySQL Dialect Expressions](dialect.md) — the same points in brief, plus the
  MySQL-specific expression surface
- [Database Introspection](introspection.md) — reading metadata through
  `information_schema` and `SHOW`
- Core library guide `docs/modeling/schema_namespace.md` — the model-level API
  and the cross-backend support matrix
