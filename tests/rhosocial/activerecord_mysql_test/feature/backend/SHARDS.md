# Directory-bound database shards (MySQL backend)

Every **leaf** directory under `execute/` binds exactly one database. The
directory is the unit of isolation: tests in one directory run serially against
that database, while different directories run in parallel. `construct/` uses no
database at all.

Resolution order is **directory shard first**, then the existing worker-slot
pool (`providers/pooling.py::resolve_database_name`). Because the directory wins
in a serial run too, a directory's tests always see the same database regardless
of `PYTEST_XDIST_WORKER`.

At session start `tests/conftest.py::_prepare_directory_shards` creates and
clears every registered database on every scenario's server (scenarios still
choose the host/port; the shard only chooses the database name). The databases
are left in place after the session.

Each directory declares its shard in its own `conftest.py`:

```python
from pathlib import Path

from providers.shards import register

register(Path(__file__).parent, "test_db_7")
```

`tests/conftest.py` tags every item of a registered directory with
`pytest.mark.xdist_group("db:<name>")`, so run with `--dist=loadgroup` to get
directory-serial / directory-parallel scheduling.

## Shared feature leaves (test_db_1 … test_db_23)

| Leaf directory | Database |
|---|---|
| `execute/connection` | `test_db_1` |
| `execute/crud` | `test_db_2` |
| `execute/query` | `test_db_3` |
| `execute/join` | `test_db_4` |
| `execute/transaction` | `test_db_5` |
| `execute/ddl_table` | `test_db_6` |
| `execute/ddl_column` | `test_db_7` |
| `execute/ddl_constraint` | `test_db_8` |
| `execute/ddl_index` | `test_db_9` |
| `execute/ddl_view` | `test_db_10` |
| `execute/dml_insert` | `test_db_11` |
| `execute/dml_update_delete` | `test_db_12` |
| `execute/json` | `test_db_13` |
| `execute/partition` | `test_db_14` |
| `execute/introspection` | `test_db_15` |
| `execute/errors` | `test_db_16` |
| `execute/concurrency` | `test_db_17` |
| `execute/cli` | `test_db_18` |
| `execute/functions` | `test_db_19` |
| `execute/sequence_identity` | `test_db_20` |
| `execute/fulltext_spatial` | `test_db_21` |
| `execute/show_admin` | `test_db_22` |
| `execute/routine_domain` | `test_db_23` |

`test_db_24` is retired: it belonged to the former generic backend-only grab
bag, which is replaced by the backend namespace below.

## MySQL-only leaves (test_db_25 …)

`execute/mysql/` is a namespace: it holds no test files. Each leaf below is a
backend-unique capability and owns its own database.

| Leaf directory | Database |
|---|---|
| `execute/mysql/dialect` | `test_db_25` |
| `execute/mysql/enum` | `test_db_26` |
| `execute/mysql/set` | `test_db_27` |
| `execute/mysql/uuid` | `test_db_28` |
| `execute/mysql/literals` | `test_db_29` |

Add a new MySQL-only capability as a new leaf with the next number; keep
`execute/mysql/` itself free of test files.

## Construct layer

`construct/` has no shard and no database: dialect, expression, functions,
statements, ddl, types, mixins, errors, connection, cli, introspection all run
without IO. `construct/mysql/introspection/` is the namespace for MySQL-only
introspection construction/parsing (also no database).
