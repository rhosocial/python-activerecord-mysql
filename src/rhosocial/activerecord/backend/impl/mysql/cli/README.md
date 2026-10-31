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
| `views` | `information_schema.views` | Views, with their definitions. `NAME` narrows it to one view. |
| `columns` | `information_schema.columns` | One table's columns: name, type, nullability, default. |
| `indexes` | `information_schema.statistics` | One table's indexes, including the primary key. |
| `foreign-keys` | `information_schema.key_column_usage` | One table's constraints and the columns each side names. |
| `triggers` | `information_schema.triggers` | Triggers, optionally narrowed to one table. |
| `table-options` | `information_schema.tables` | The storage facts about a table: engine, row format, collation, auto-increment, comment, and the byte sizes `information_schema` reports. `NAME` narrows it to one table. |
| `partitions` | `information_schema.partitions` | One table's partitions and subpartitions, in the engine's own order. An empty answer means the table is not partitioned. |
| `database` | `information_schema.schemata`, `variables` | Server version, charset, and the databases visible to this role. |

### What `NAME` means

`NAME` is one argument with three possible meanings, decided by the type:

| Meaning | Types |
| :--- | :--- |
| A **table**, required | `columns`, `indexes`, `foreign-keys`, `partitions` |
| The **object itself**, optional — given, it answers for that one object and exits 1 if there is no such object | `views`, `triggers`, `table-options` |
| **Refused** — the type answers for the whole database | `tables`, `database` |

A `NAME` a type cannot use is an error (exit 2), never a silently ignored
argument: a run that prints the whole catalogue while the caller believes it
asked about one object is the worst of the possible answers.


## Options

| Option | Default | Description |
| :--- | :--- | :--- |
| `-o, --output` | `table` | `table` (rich), `json`, `csv`, `tsv`. |
| `--database` | required (env: `MYSQL_DATABASE`) | The database to connect to **and** the database to read. MySQL has one namespace level and calls it a database, so there is no second flag: the run connects to a database and asks about that database. |
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
*   **There is no namespace flag, and that is deliberate.** MySQL has one
    namespace level and calls it a database — `CREATE SCHEMA` is a synonym for
    `CREATE DATABASE`, and nothing sits inside a database under a further name.
    So `--database` is the whole answer: the run connects to a database and
    asks about that database. There is no `--schema`, and it has not been left
    as an alias, so a caller cannot end up asking about a level that does not
    exist here.
*   **`data_length` and `index_length` are estimates.** InnoDB reports
    approximate byte sizes for the clustered index, not exact file sizes. They
    are printed as reported; the caveat travels with the number.
*   **One question per invocation.** A CLI process is one connection that
    opens, answers, and closes — there is no cache carried between runs, so
    the answer reflects the server as it is *now*.
*   **`introspector.show` is reachable from the library only, not from here.**
    Its nineteen methods (`create_table`, `variables`, `status`, `processlist`,
    `grants`, `engines`, …) are the raw `SHOW` verbs. Most of them are not
    catalogue metadata at all — `variables` is server configuration, `status`
    is running counters, `processlist` is current activity, `warnings` and
    `errors` are this session's leftovers — and the `create_*` ones return DDL
    text where `columns`, `views` and `triggers` already give the structured
    answer to the same question. `introspect` asks *what the database holds*;
    a second door onto the same facts would only raise the question of which
    one is authoritative.

## Examples

```bash
# Storage facts and partitions for the order tables
python -m rhosocial.activerecord.backend.impl.mysql introspect table-options --database shop
python -m rhosocial.activerecord.backend.impl.mysql introspect table-options orders --database shop
python -m rhosocial.activerecord.backend.impl.mysql introspect partitions orders --database shop -o json

# One view, with its definition
python -m rhosocial.activerecord.backend.impl.mysql introspect views orders_v --database shop

# A script asks the question and reads the answer
export MYSQL_HOST=localhost MYSQL_DATABASE=shop MYSQL_USER=root MYSQL_PASSWORD=secret
python -m rhosocial.activerecord.backend.impl.mysql introspect tables -o json | jq '.[].name'
```
