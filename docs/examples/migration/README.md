# MySQL Migration Examples

Runnable examples for running migrations on the MySQL backend. They demonstrate only the
MySQL-specific concerns; the migration system itself is documented in the
[core Migration System chapter](https://github.com/rhosocial/python-activerecord/blob/feature/activerecord-ddl/docs/en_US/migration/README.md)
and summarised for this backend in [Migrations on MySQL](../../en_US/migration/README.md).

> These scripts **need a reachable MySQL server** (unlike the core chapter's SQLite examples), so
> they will not run offline. Connection settings come from `MYSQL_HOST`, `MYSQL_PORT`,
> `MYSQL_DATABASE`, `MYSQL_USER` and `MYSQL_PASSWORD`.

Run from the repository root with `PYTHONPATH=src`:

```bash
python docs/examples/migration/01_mysql_first_migration.py
python docs/examples/migration/02_named_migration.py
```

| Script | Demonstrates |
|---|---|
| `01_mysql_first_migration.py` | `@migration` function + `ctx.apply()`; MySQL backend/config with `introspect_and_adapt()`; `run_migration_group` dry-run → UP → DOWN with a `JSONFileMigrationRecordStore` |
| `02_named_migration.py` | class-style `NamedMigration` via `MigrationRunner` with this repo's backend/config, plus the equivalent `named-migration` CLI invocation |

Both scripts are deliberately safe to re-run: the DOWN step drops the demo table and each script
uses a temporary record store. Remember that MySQL DDL auto-commits — review the dry-run output
before applying. For the longer class-style end-to-end demos shipped with the backend, see
[`src/.../named_migrations/`](../../../src/rhosocial/activerecord/backend/impl/mysql/examples/named_migrations/).
