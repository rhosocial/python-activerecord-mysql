# Migrations on MySQL

> **Scope**: this chapter covers **only the MySQL-specific parts** of running migrations — how to
> configure the MySQL backend, what MySQL's DDL semantics mean for UP/DOWN, version-gated features,
> and how the `named-migration` CLI is wired here. It deliberately does **not** re-explain the
> migration system itself (decorators, ordering and dependencies, version records, dry-run internals,
> the exception hierarchy). Read the authoritative
> [Migration System chapter](https://github.com/rhosocial/python-activerecord/blob/feature/activerecord-ddl/docs/en_US/migration/README.md)
> in the core library first; everything there applies unchanged on MySQL.

## Contents

1. [Two entry points, one system](#1-two-entry-points-one-system)
2. [Configuring a MySQL backend for migrations](#2-configuring-a-mysql-backend-for-migrations)
3. [Function-style migrations on MySQL](#3-function-style-migrations-on-mysql)
4. [DDL is not transactional on MySQL](#4-ddl-is-not-transactional-on-mysql)
5. [Version-gated DDL features](#5-version-gated-ddl-features)
6. [Class-style migrations and the named-migration CLI](#6-class-style-migrations-and-the-named-migration-cli)
7. [Further reading](#7-further-reading)

## 1. Two entry points, one system

| | Function style (recommended) | Class style (legacy-compatible) |
|---|---|---|
| Authoring unit | `@migration`-decorated function | `NamedMigration` subclass with `up()`/`down()` |
| Runner | `run_migration_group()` | `MigrationRunner` / `BatchMigrationRunner` |
| CLI | core model CLI's `migrate` command | MySQL backend CLI's `named-migration` command |

Both paths run against the same `MySQLBackend` instance you construct (§2). The migration system's
semantics are identical to the core chapter; only configuration, DDL behaviour and CLI wiring are
MySQL-specific and documented below.

## 2. Configuring a MySQL backend for migrations

Use this repository's backend and configuration classes, then **introspect and adapt** before
running any migration:

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

Why `introspect_and_adapt()` matters here:

- It queries the live server with `get_server_version()` and rebuilds the dialect/type adapters for
  that version. The MySQL dialect gates many DDL capabilities on the server version (§5), so without
  this call the gates may reflect the config default instead of the server you will actually migrate.
- The CLI's `named-migration` handler calls it automatically after connecting (§6); code that builds
  a backend by hand, or passes one to `run_migration_group()`, must call it itself.
- `MySQLConnectionConfig.version` (from `VersionMixin`) can pin a version for offline work, but a
  live `introspect_and_adapt()` overrides it once connected.
- `autocommit=True` is the config default. It does **not** make DDL transactional — see §4.

## 3. Function-style migrations on MySQL

A migration function emits model DDL statements via `ctx.apply(...)`; the group is executed with the
MySQL backend:

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

MySQL-specific guidance:

- **Always dry-run first.** Because DDL auto-commits (§4), a dry run is the only no-write way to see
  the exact SQL that will be executed. Use `preview.dry_run_sql` / `preview.dry_run_total` to review
  it.
- After every group run, `run_migration_group()` calls `backend.introspector.clear_cache()`, so
  subsequent introspection sees the new schema — important on MySQL, where table metadata is cached.
- If the dialect cannot render a construct on the connected server, the failure surfaces as
  `MigrationDialectError` (§5); on a mid-group failure, inspect the error's `executed` list and
  `transactional_ddl` flag (§4).

A complete runnable script is at
[`docs/examples/migration/01_mysql_first_migration.py`](../../examples/migration/01_mysql_first_migration.py).

## 4. DDL is not transactional on MySQL

**This is the most important MySQL-specific fact about migrations.** `MySQLDialect.supports_transactional_ddl()`
returns `False` on every supported MySQL version: MySQL implicitly commits around each DDL statement,
and DDL cannot be rolled back.

Consequences you must design around:

1. **DOWN is a compensating operation, not an undo.** `DROP TABLE` in a DOWN function commits just as
   `CREATE TABLE` in UP did. Treat DOWN as forward DDL that needs the same care as UP.
2. **A group is not atomic.** If the second of three migrations fails, the first has already
   committed. On failure `run_migration_group()` raises `MigrationFunctionExecutionError` whose
   `executed` list names the versions that ran and whose `transactional_ddl` attribute is `False`.
   No version record is written for the failed migration, so you must reconcile the schema with the
   record store yourself.
3. **Transactions and `transaction_mode` do not help DDL.** Wrapping a migration in an explicit
   transaction, or choosing a `TransactionMode`, cannot make DDL atomic on MySQL.
4. **`--single-transaction` is not a safety net for DDL.** The class-style batch runner can defer
   version-record writes until the end, but its DDL statements still auto-commit individually. Never
   rely on it to undo a partially applied batch.

Mitigations:

- Dry-run both UP and DOWN and read the rendered SQL before applying.
- Keep each migration to a single DDL statement where practical, and make DOWN statements explicit
  and re-runnable-friendly (`IF EXISTS` / `IF NOT EXISTS`) where the dialect supports it.
- Verify the result with introspection after a run, and keep UP/DOWN pairs close together in review.

## 5. Version-gated DDL features

The MySQL dialect decides many capabilities from the server version via `version_at_least((major, minor, patch))`.
A migration that emits DDL using a feature the live server lacks gets an `UnsupportedFeatureError`
from the dialect, which the migration system surfaces as `MigrationDialectError` (see the core
chapter's exception hierarchy).

Examples relevant to schema migrations:

| Feature | Minimum MySQL version |
|---|---|
| JSON column type / JSON functions | 5.7.8 |
| Generated columns | 5.7.0 |
| Invisible, descending and functional (expression) indexes | 8.0.0 |
| Window functions / Common Table Expressions | 8.0.0 |
| `LATERAL` joins | 8.0.14 |
| Multi-value table value constructor / `ALGORITHM=INSTANT` | 8.0.19 |
| Spatial indexes / GeoJSON functions | 5.7 / 5.7.5 |
| `VECTOR` type / vector indexes | 9.0.0 / 9.0.1 |
| JSON duality views | 9.7.0 |

The "no transactional DDL" rule (§4) is **not** version-gated — it holds on all of them. For the full
support matrix, see [Supported Versions](../introduction/supported_versions.md) and the
[MySQL DDL overview](../ddl/README.md).

Practical rule: if a migration uses a version-gated construct, either guarantee the deployment server
is new enough, or check the dialect capability when authoring. Runtime correctness depends on
`introspect_and_adapt()` (§2) keeping those gates tied to the real server.

## 6. Class-style migrations and the named-migration CLI

The MySQL backend CLI wires the `named-migration` subcommand to the shared CLI helper. Its handler
constructs `MySQLBackend` from the connection arguments, connects and calls `introspect_and_adapt()`
before dispatching, so the version gates are live.

```bash
python -m rhosocial.activerecord.backend.impl.mysql named-migration \
  rhosocial.activerecord.backend.impl.mysql.examples.named_migrations.migrations.V001CreateUsers \
  --host localhost --database test --direction up \
  --record-store ./migrations.json
```

Common flags: `--direction up|down`, `--dry-run`, `--record-store PATH`, `--describe`, `--list`,
`--all`, `--param KEY=VALUE` and `--single-transaction`. The `--single-transaction` caveat in §4
applies here too. Connection options come from the MySQL CLI's parent parser (`--host`, `--port`,
`--database`, `--user`, `--password`, etc.).

Runnable end-to-end demos (class-style, with UP/DOWN verification) live in
[`src/rhosocial/activerecord/backend/impl/mysql/examples/named_migrations/`](../../../src/rhosocial/activerecord/backend/impl/mysql/examples/named_migrations/).
A programmatic counterpart using this repo's backend/config classes is at
[`docs/examples/migration/02_named_migration.py`](../../examples/migration/02_named_migration.py).

## 7. Further reading

- [Core migration system (authoritative)](https://github.com/rhosocial/python-activerecord/blob/feature/activerecord-ddl/docs/en_US/migration/README.md)
- [Core migration examples](https://github.com/rhosocial/python-activerecord/tree/feature/activerecord-ddl/docs/examples/migration)
- [Local runnable examples](../../examples/migration/README.md)
- [MySQL DDL operations](../ddl/README.md)
- [Supported MySQL versions](../introduction/supported_versions.md)
