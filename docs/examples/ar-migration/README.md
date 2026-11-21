# ActiveRecord-layer migration examples — MySQL (offline)

Backend-specific examples for the MySQL backend of
`rhosocial-activerecord`. They show how the *same* migration intent is rendered
into MySQL's own DDL: inline `PARTITION BY`, `ADD`/`DROP`/`REORGANIZE PARTITION`,
`REMOVE PARTITIONING`/`COALESCE PARTITION`, and `DROP TABLE`.

All examples are **offline**: no server, no connection, no `ctx.apply()`. A
dialect is constructed with a version, a plan is assembled from real expression
nodes, a `suggest_partition_*` method returns a chain of expression objects, and
each SQL line is printed from `expr.to_sql()` (never a hand-written SQL string).

## Running

From the repository root with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python docs/examples/ar-migration/01_partition_build.py
PYTHONPATH=src python docs/examples/ar-migration/02_partition_lifecycle.py
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH='src'
python docs/examples/ar-migration/01_partition_build.py
python docs/examples/ar-migration/02_partition_lifecycle.py
```

Use the worktree's own interpreter, e.g.
`.venv3.14\Scripts\python.exe`.

## Scripts

| Script | Scenarios |
|---|---|
| `01_partition_build.py` | All 8 build strategies: `RANGE`, `RANGE COLUMNS`, `LIST`, `LIST COLUMNS`, `HASH`, `LINEAR HASH`, `KEY`, `LINEAR KEY`; plus two declined paths (unknown strategy, missing definitions) |
| `02_partition_lifecycle.py` | `ADD PARTITION` (append) and `REORGANIZE PARTITION` (via add + `into`), `DROP PARTITION`, retention (cutoff keeps newest, all-old keeps newest, nothing-old no-op), `REORGANIZE` split, `REMOVE PARTITIONING`, `COALESCE PARTITION`, `DROP TABLE`, `MERGE` always declined, and drop/add declined/no-op tri-states |

## MySQL specifics worth noting

- **Plan shape**: a `dict` (or attribute object). Build uses
  `{"keys": [Column(d, "id")], "definitions": [...]}`; HASH/KEY use
  `"partitions_count"` instead of definitions. Lifecycle plans use `"table"` plus
  `"definitions"` / `"names"` / `"cutoff"` / `"partition"` + `"into"`.
- **Strategy enum**: `MySQLPartitionStrategy` has 8 members —
  `RANGE`, `RANGE COLUMNS`, `LIST`, `LIST COLUMNS`, `HASH`, `LINEAR HASH`,
  `KEY`, `LINEAR KEY`.
- **Definitions**: `MySQLPartitionDefinition(name=..., less_than=[MySQLPartitionValue(d, bound)])`
  for RANGE, or `in_values=[...]` for LIST.
- **Tri-state**: `suggestion.operations` is a tuple of expression nodes when a
  real chain exists, `False` when MySQL has no such mechanism for that
  strategy/plan, and `None` when nothing needs doing (e.g. retention with no
  eligible partitions).
- **No MERGE PARTITION**: `suggest_partition_merge` always returns `False`;
  COALESCE only shrinks HASH/KEY by count.
- **Retention never drops the last partition**: when all partitions qualify, the
  newest one is kept (MySQL refuses to drop the last partition of a table).
- **Dialect version**: `MySQLDialect(version=(8, 0, 0))` is used so rendering is
  deterministic and independent of any installed server.

These are the AR-layer migration *suggestions* (`suggest_partition_*`), distinct
from the backend `migrate` command demonstrated in `docs/examples/migration/`.

> Part of the cross-backend `ar-migration` example set; see the core examples in
> `python-activerecord/docs/examples/ar-migration/`.
