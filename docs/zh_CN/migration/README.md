# MySQL 中的迁移

> **范围**：本章 **只** 介绍运行迁移时与 MySQL 相关的部分 —— 如何配置 MySQL 后端、MySQL 的 DDL 语义对 UP/DOWN 意味着什么、按版本开放的特性，以及 `named-migration` CLI 在本仓库中如何接线。本章有意 **不** 重复讲解迁移系统本身（装饰器、排序与依赖、版本记录、dry-run 内部机制、异常层次）。请先阅读核心库中权威的 [迁移系统章节](https://github.com/rhosocial/python-activerecord/blob/feature/activerecord-ddl/docs/en_US/migration/README.md)；其中所有内容在 MySQL 上均原样适用。

## 目录

1. [两种入口，同一套系统](#1-两种入口同一套系统)
2. [为迁移配置 MySQL 后端](#2-为迁移配置-mysql-后端)
3. [MySQL 上的函数式迁移](#3-mysql-上的函数式迁移)
4. [MySQL 上的 DDL 不是事务性的](#4-mysql-上的-ddl-不是事务性的)
5. [按版本开放的 DDL 特性](#5-按版本开放的-ddl-特性)
6. [类式迁移与 named-migration CLI](#6-类式迁移与-named-migration-cli)
7. [延伸阅读](#7-延伸阅读)

## 1. 两种入口，同一套系统

| | 函数式（推荐） | 类式（兼容旧版） |
|---|---|---|
| 编写单元 | 用 `@migration` 装饰的函数 | 带 `up()`/`down()` 的 `NamedMigration` 子类 |
| 运行器 | `run_migration_group()` | `MigrationRunner` / `BatchMigrationRunner` |
| CLI | 核心模型 CLI 的 `migrate` 命令 | MySQL 后端 CLI 的 `named-migration` 命令 |

两条路径都作用于你构造的同一个 `MySQLBackend` 实例（§2）。迁移系统的语义与核心章节完全一致；只有配置、DDL 行为和 CLI 接线是 MySQL 特有的，如下所述。

## 2. 为迁移配置 MySQL 后端

使用本仓库的后端与配置类，并在运行任何迁移之前 **内省并适配**：

```python
import os

from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

config = MySQLConnectionConfig(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE", "test"),
    username=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    charset="utf8mb4",
)
backend = MySQLBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()  # reads the live server version — see below
```

为什么 `introspect_and_adapt()` 在这里如此重要：

- 它通过 `get_server_version()` 查询实际服务器，并针对该版本重建方言/类型适配器。MySQL 方言的许多 DDL 能力由服务器版本决定（§5）；若不调用它，这些能力判断可能反映的是配置默认值，而不是你真正要迁移的服务器。
- CLI 的 `named-migration` 处理器会在连接后自动调用它（§6）；手工构造后端或把后端传给 `run_migration_group()` 的代码必须自己调用。
- `MySQLConnectionConfig.version`（来自 `VersionMixin`）可以在离线时固定一个版本，但连接后实际的 `introspect_and_adapt()` 会覆盖它。
- `autocommit=True` 是配置默认值。它 **不会** 让 DDL 变成事务性的 —— 见 §4。

## 3. MySQL 上的函数式迁移

迁移函数通过 `ctx.apply(...)` 发出模型 DDL 语句；迁移组使用 MySQL 后端执行：

```python
from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    migration,
    run_migration_group,
)


@migration("v001_create_users", description="create the users table")
def create_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(User.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))


fqn = f"{__name__}:create_users"
preview = run_migration_group(backend, [fqn], dry_run=True)   # renders SQL, writes nothing
result = run_migration_group(backend, [fqn], record_store=store)
```

MySQL 特有的注意事项：

- **务必先 dry-run。** 由于 DDL 会自动提交（§4），dry-run 是唯一一种不写入任何内容就能看到实际将执行 SQL 的方式。可用 `preview.dry_run_sql` / `preview.dry_run_total` 检查。
- 每次运行迁移组后，`run_migration_group()` 都会调用 `backend.introspector.clear_cache()`，使后续内省看到新 schema —— 在会缓存表元数据的 MySQL 上这很重要。
- 如果方言无法在所连接的服务器上渲染某个构造，失败会表现为 `MigrationDialectError`（§5）；若迁移组执行到一半失败，请检查异常的 `executed` 列表和 `transactional_ddl` 标记（§4）。

完整可运行脚本见
[`docs/examples/migration/01_mysql_first_migration.py`](../../examples/migration/01_mysql_first_migration.py)。

## 4. MySQL 上的 DDL 不是事务性的

**这是 MySQL 迁移中最重要的事实。** `MySQLDialect.supports_transactional_ddl()` 在所有受支持的 MySQL 版本上都返回 `False`：MySQL 会在每条 DDL 语句前后隐式提交，DDL 无法回滚。

必须围绕以下事实设计：

1. **DOWN 是补偿操作，不是撤销。** DOWN 函数中的 `DROP TABLE` 与 UP 中的 `CREATE TABLE` 一样会提交。请把 DOWN 当作与 UP 同样需要谨慎对待的前向 DDL。
2. **迁移组不是原子的。** 如果三个迁移中的第二个失败，第一个已经提交。失败时 `run_migration_group()` 抛出 `MigrationFunctionExecutionError`，其 `executed` 列出已运行的版本，`transactional_ddl` 属性为 `False`。失败的迁移不会写入版本记录，因此你必须自行核对 schema 与记录存储的一致性。
3. **事务和 `transaction_mode` 对 DDL 无效。** 把迁移包在显式事务里，或选择某个 `TransactionMode`，都无法让 MySQL 上的 DDL 具备原子性。
4. **`--single-transaction` 不是 DDL 的安全网。** 类式批量运行器可以把版本记录写入推迟到最后，但其 DDL 语句仍会逐条自动提交。绝不要指望它撤销部分已应用的批次。

缓解措施：

- 对 UP 和 DOWN 都先 dry-run，并在应用前阅读渲染出的 SQL。
- 在可行的情况下让每个迁移只包含一条 DDL 语句；在方言支持的前提下，让 DOWN 语句显式且便于重跑（`IF EXISTS` / `IF NOT EXISTS`）。
- 运行后用内省验证结果，并在评审时把 UP/DOWN 成对放在一起检查。

## 5. 按版本开放的 DDL 特性

MySQL 方言通过 `version_at_least((major, minor, patch))` 根据服务器版本决定许多能力。若某个迁移发出的 DDL 使用了实际服务器不支持的特性，方言会抛出 `UnsupportedFeatureError`，迁移系统将其表现为 `MigrationDialectError`（参见核心章节的异常层次）。

与 schema 迁移相关的例子：

| 特性 | 最低 MySQL 版本 |
|---|---|
| JSON 列类型 / JSON 函数 | 5.7.8 |
| 生成列 | 5.7.0 |
| 不可见、降序与函数（表达式）索引 | 8.0.0 |
| 窗口函数 / 公共表表达式 | 8.0.0 |
| `LATERAL` 连接 | 8.0.14 |
| 多值表值构造器 / `ALGORITHM=INSTANT` | 8.0.19 |
| 空间索引 / GeoJSON 函数 | 5.7 / 5.7.5 |
| `VECTOR` 类型 / 向量索引 | 9.0.0 / 9.0.1 |
| JSON 对偶视图 | 9.7.0 |

“不支持事务性 DDL” 这条规则（§4） **不受** 版本限制 —— 上述所有版本都如此。完整支持矩阵见 [Supported Versions](../introduction/supported_versions.md) 和
[MySQL DDL 概览](../ddl/README.md)。

实用准则：如果迁移使用了按版本开放的结构，要么确保部署服务器足够新，要么在编写时检查方言能力。运行时的正确性依赖于 `introspect_and_adapt()`（§2）把这些能力判断与真实服务器绑定。

## 6. 类式迁移与 named-migration CLI

MySQL 后端 CLI 将 `named-migration` 子命令接到共享的 CLI 辅助模块。其处理器根据连接参数构造 `MySQLBackend`、建立连接，并在分发前调用 `introspect_and_adapt()`，因此版本能力判断是实时的。

```bash
python -m rhosocial.activerecord.backend.impl.mysql named-migration \
  rhosocial.activerecord.backend.impl.mysql.examples.named_migrations.migrations.V001CreateUsers \
  --host localhost --database test --direction up \
  --record-store ./migrations.json
```

常用参数：`--direction up|down`、`--dry-run`、`--record-store PATH`、`--describe`、`--list`、`--all`、`--param KEY=VALUE` 和 `--single-transaction`。§4 中关于 `--single-transaction` 的注意事项在此同样适用。连接参数来自 MySQL CLI 的父解析器（`--host`、`--port`、`--database`、`--user`、`--password` 等）。

可运行的端到端示例（类式，含 UP/DOWN 验证）在
[`src/rhosocial/activerecord/backend/impl/mysql/examples/named_migrations/`](../../../src/rhosocial/activerecord/backend/impl/mysql/examples/named_migrations/)。
使用本仓库后端/配置类的编程方式对照示例见
[`docs/examples/migration/02_named_migration.py`](../../examples/migration/02_named_migration.py)。

## 7. 延伸阅读

- [核心迁移系统（权威）](https://github.com/rhosocial/python-activerecord/blob/feature/activerecord-ddl/docs/en_US/migration/README.md)
- [核心迁移示例](https://github.com/rhosocial/python-activerecord/tree/feature/activerecord-ddl/docs/examples/migration)
- [本地可运行示例](../../examples/migration/README.md)
- [MySQL DDL 操作](../ddl/README.md)
- [支持的 MySQL 版本](../introduction/supported_versions.md)
