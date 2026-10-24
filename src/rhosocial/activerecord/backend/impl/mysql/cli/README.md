# `introspect` — MySQL metadata, from the command line

The `introspect` subcommand asks a live MySQL server what it holds, and prints
the answer. Every question runs through the backend's introspector, so what the
CLI reports is what the library sees — the same objects, the same types, the
same parsing — rather than a second implementation that can drift from it.

```bash
python -m rhosocial.activerecord.backend.impl.mysql introspect <TYPE> [NAME] [OPTIONS]
```

## What it can ask about

| Type | Reads | Notes |
| :--- | :--- | :--- |
| `tables` | `information_schema.tables` | Base tables. `--include-system` adds MySQL's own metadata databases. |
| `views` | `information_schema.views` | Views, with their definitions. |
| `table` | several | One table by name, with its columns, indexes and foreign keys filled in. |
| `columns` | `information_schema.columns` | One table's columns: name, type, nullability, default. |
| `indexes` | `information_schema.statistics` | One table's indexes, including the primary key. |
| `foreign-keys` | `information_schema.key_column_usage` | One table's constraints and the columns each side names. |
| `triggers` | `information_schema.triggers` | Triggers, optionally narrowed to one table. |
| `table-options` | `information_schema.tables` | The storage facts about a table: engine, row format, collation, auto-increment, comment, and the byte sizes `information_schema` reports. |
| `partitions` | `information_schema.partitions` | One table's partitions and subpartitions, in the engine's own order. An empty answer means the table is not partitioned. |
| `database` | `information_schema.schemata`, `variables` | Server version, charset, and the databases visible to this role. |

`NAME` is required for `table`, `columns`, `indexes`, `foreign-keys` and
`partitions`. The list types take no name.

## Options

| Option | Default | Description |
| :--- | :--- | :--- |
| `-o, --output` | `table` | `table` (rich), `json`, `csv`, `tsv`. |
| `--schema` | the connected database | The database to read. MySQL's only namespace level above a table. |
| `--include-system` | off | Include system tables. |
| `--host`, `--port`, `--database`, `--user`, `--password` | env or defaults | Connection. `MYSQL_*` env vars are honoured, and arguments override them. |
| `--charset` | _None_ | Connection charset. |
| `--ssl` | off | Use SSL for the connection. |
| `--async` | off | Drive the asynchronous backend. |
| `--named-connection` | _None_ | A connection saved by the `named-connection` subcommand. |
| `--conn-param` | _None_ | Extra `key=value` connection parameters; repeatable. |
| `--rich-ascii` | off | ASCII characters for table borders. |

## Notes

*   **Read-only.** `introspect` never writes. It does not create, drop, or
    alter anything, so it is safe to run against a database whose schema
    matters.
*   **The database is explicit.** `--schema` names the database to read, rather
    than relying on the connection's default — which differs between clients
    and is the usual reason two tools disagree about what a table looks like.
*   **`data_length` and `index_length` are estimates.** InnoDB reports
    approximate byte sizes for the clustered index, not exact file sizes. They
    are printed as reported; the caveat travels with the number.
*   **One question per invocation.** A CLI process is one connection that
    opens, answers, and closes — there is no cache carried between runs, so
    the answer reflects the server as it is *now*.

## Examples

```bash
# Storage facts and partitions for the order tables
python -m rhosocial.activerecord.backend.impl.mysql introspect table-options --database shop
python -m rhosocial.activerecord.backend.impl.mysql introspect partitions orders --database shop -o json

# One table in full
python -m rhosocial.activerecord.backend.impl.mysql introspect table orders --database shop

# A script asks the question and reads the answer
export MYSQL_HOST=localhost MYSQL_DATABASE=shop MYSQL_USER=root MYSQL_PASSWORD=secret
python -m rhosocial.activerecord.backend.impl.mysql introspect tables -o json | jq '.[].name'
```
