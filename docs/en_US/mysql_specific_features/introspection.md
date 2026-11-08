# Database Introspection

The MySQL backend answers three layers of questions: what the database declares (from `information_schema` and `SHOW`), what it has been doing (six operational families), and what its rows hold (three data families). `backend.introspector` is the entry point for all three, and every answer on this page is MySQL's own: what this engine says, not the shape a cross-dialect consumer can expect.

## Overview

The MySQL introspection system is accessible via `backend.introspector` and provides:

- **Database Information**: Name, version, character set, collation
- **Table Information**: Table list, table details, storage engine, table comments
- **Column Information**: Column name, data type, nullability, default value, character set
- **Index Information**: Index name, columns, uniqueness, index type (BTREE, FULLTEXT, etc.)
- **Foreign Key Information**: Referenced table, column mapping, update/delete actions
- **View Information**: View definition SQL
- **Trigger Information**: Trigger event, execution timing
- **Operational Answers**: unused indexes, I/O counters, runtime facts, dependency edges, the engine's DDL
- **Data Answers**: per-column profiles, value listings, join coverage

## What MySQL Answers

Every question in the introspection contract has a probe on the dialect, and a probe is a question about the server in front of you rather than about the product. This table is MySQL's answer to all twenty-one. Read the `False` rows first: a probe that answers `False` says the question cannot be asked of this server, never that the answer was empty or zero.

| Probe | MySQL answers | The question it gates |
|-------|---------------|-----------------------|
| `supports_introspection()` | `True` | Anything about the schema at all |
| `supports_database_info()` | `True` | The database's name, character set and collation |
| `supports_table_introspection()` | `True` | Tables and their storage slots |
| `supports_column_introspection()` | `True` | Columns and what they declare |
| `supports_index_introspection()` | `True` | Indexes, their columns and types |
| `supports_foreign_key_introspection()` | `True` | Foreign keys and their actions |
| `supports_view_introspection()` | `True` | Views and their definitions |
| `supports_trigger_introspection()` | `True` | Triggers, timing and definition |
| `supports_table_storage_introspection()` | `True` | Per-table data and index bytes |
| `supports_runtime_stats()` | `True` | What the server itself has been doing |
| `supports_table_stats()` | `True` | Per-table I/O counters |
| `supports_index_stats()` | `True` | Per-index usage counters |
| `supports_unused_indexes_detection()` | `True` from 5.7.0, `False` below and before adaptation | Indexes with no recorded access |
| `supports_object_dependencies()` | `True` | The object dependency graph |
| `supports_ddl_extraction()` | `True` | The text that recreates an object |
| `supports_ddl_extraction_native()` | `True` | Whether that text is the engine's own |
| `supports_column_data_profile()` | `True` | What each column of a table holds |
| `supports_column_value_sample()` | `True` | Which values occur, and how often |
| `supports_join_coverage()` | `True` | How much two columns' domains overlap |
| `supports_partition_info()` | `False` | Core's partition family |
| `supports_extensions()` | `False` | Installed add-on components |

`supports_unused_indexes_detection()` is the only probe here whose answer depends on the server's version: `True` from MySQL 5.7.0 and `False` below, because `sys.schema_unused_indexes` is part of the `sys` schema and 5.6 has no `sys` schema. Answering `True` there would turn a definition-time question into an execution error — `1146`, "table does not exist" — so the accessor is asked rather than a bare `True`. A dialect that has not been adapted answers `False` as well, because no version has been confirmed.

`supports_partition_info()` stays `False` by inheritance. MySQL answers a table's partitions through its own `supports_partition_introspection()`, whose result type is `MySQLPartitionInfo` and whose empty answer means "this table is not partitioned". Core's partition family has no method on this backend to oblige, so the probe is left saying it cannot be promised rather than repointed at a family MySQL does not implement. The CLI's `partitions` type reads the engine's own switch.

`supports_extensions()` stays `False` by inheritance, too: MySQL's installable units are plugins, and this backend declares no catalogue for them — nothing maps the extension family onto `information_schema.PLUGINS` or `SHOW PLUGINS`, so there is no answer behind a `True`.

Two switches beyond core's set are this backend's own: `supports_table_options_introspection()` for the `table-options` family and `supports_partition_introspection()` for `partitions`. Both answer `True`, and each CLI type is gated on its own switch. A `True` promises only that the query renders and the server accepts it; it says nothing about the shape of the answer or its price, and the price of every family is stated where the family is described.

## Basic Usage

### Accessing the Introspector

```python
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend

backend = MySQLBackend(
    host="localhost",
    port=3306,
    database="mydb",
    user="root",
    password="password"
)
backend.connect()

# Access via introspector attribute
introspector = backend.introspector
```

### Getting Database Information

```python
# Get basic database information
db_info = backend.introspector.get_database_info()
print(f"Database name: {db_info.name}")
print(f"Version: {db_info.version}")
print(f"Character set: {db_info.encoding}")
print(f"Collation: {db_info.collation}")
```

### Listing Tables

```python
# List all user tables
tables = backend.introspector.list_tables()
for table in tables:
    print(f"Table: {table.name}, Type: {table.table_type.value}")
    if table.comment:
        print(f"  Comment: {table.comment}")

# Include system database tables (usually not needed)
all_tables = backend.introspector.list_tables(include_system=True)

# Filter by specific type
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# Check if table exists
if backend.introspector.table_exists("users"):
    print("users table exists")

# Get table details
table_info = backend.introspector.get_table_info("users")
if table_info:
    print(f"Table name: {table_info.name}")
    print(f"Row estimate: {table_info.row_count}")
    print(f"Data bytes: {table_info.data_size_bytes}")
    print(f"Index bytes: {table_info.index_size_bytes}")
```

The table record answers name, type, comment, row estimate and the data/index byte split; the storage engine is a separate question, answered by `get_table_options()` (see [Storage Engine Information](#storage-engine-information)).

### Querying Column Information

```python
# List all columns of a table
columns = backend.introspector.list_columns("users")
for col in columns:
    nullable = "NOT NULL" if col.nullable.value == "NOT_NULL" else "NULLABLE"
    pk = " [PK]" if col.is_primary_key else ""
    charset = f" ({col.charset})" if col.charset else ""
    print(f"{col.name}: {col.data_type}{charset} {nullable}{pk}")
    if col.comment:
        print(f"  Comment: {col.comment}")

# Get primary key information
pk = backend.introspector.get_primary_key("users")
if pk:
    print(f"Primary key: {[c.name for c in pk.columns]}")

# Get single column information
col_info = backend.introspector.get_column_info("users", "email")
```

### Querying Indexes

```python
# List all indexes of a table
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    idx_type = idx.index_type.value if idx.index_type else "BTREE"
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}Index: {idx.name} ({idx_type})")
    for col in idx.columns:
        print(f"  - {col.name}")
```

### Querying Foreign Keys

```python
# List foreign keys of a table
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"FK: {fk.name}")
    print(f"  Columns: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")
```

### Querying Views

```python
# List all views
views = backend.introspector.list_views()
for view in views:
    print(f"View: {view.name}")

# Get view details
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"Definition: {view_info.definition}")
```

### Querying Triggers

```python
# List all triggers
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"Trigger: {trigger.name} on {trigger.table_name}")

# List triggers for a specific table
table_triggers = backend.introspector.list_triggers("users")
```

## MySQL-Specific: ShowIntrospector

MySQL provides unique `SHOW` command support, accessible via `backend.introspector.show`:

```python
# Access ShowIntrospector
show = backend.introspector.show

# SHOW CREATE TABLE
create_table = show.show_create_table("users")
print(f"Create statement:\n{create_table.create_statement}")

# SHOW CREATE VIEW
create_view = show.show_create_view("user_posts_summary")
print(f"Create view statement:\n{create_view.create_statement}")

# SHOW COLUMNS
columns = show.show_columns("users")
for col in columns:
    print(f"{col.field}: {col.type} {col.null} {col.key} {col.default}")

# SHOW INDEX
indexes = show.show_index("users")
for idx in indexes:
    print(f"Index: {idx.index_name}, Column: {idx.column_name}")

# SHOW TABLE STATUS
table_status = show.show_table_status("users")
print(f"Engine: {table_status.engine}")
print(f"Rows: {table_status.rows}")
print(f"Auto increment: {table_status.auto_increment}")

# SHOW TABLES
tables = show.show_tables()
for table in tables:
    print(f"Table: {table}")

# SHOW DATABASES
databases = show.show_databases()
for db in databases:
    print(f"Database: {db}")

# SHOW TRIGGERS
triggers = show.show_triggers("users")
for trigger in triggers:
    print(f"Trigger: {trigger.trigger}, Event: {trigger.event}")

# SHOW VARIABLES
variables = show.show_variables("character_set_server")
for var in variables:
    print(f"{var.variable_name}: {var.value}")

# SHOW STATUS
status = show.show_status("Threads_connected")
for s in status:
    print(f"{s.variable_name}: {s.value}")

# SHOW PROCESSLIST
processes = show.show_processlist()
for proc in processes:
    print(f"ID: {proc.id}, User: {proc.user}, State: {proc.state}")

# SHOW ENGINES
engines = show.show_engines()
for engine in engines:
    supported = "supported" if engine.support == "YES" else "not supported"
    print(f"{engine.engine}: {supported}")

# SHOW CHARSET
charsets = show.show_charset()
for charset in charsets:
    print(f"{charset.charset}: {charset.description}")

# SHOW COLLATION
collations = show.show_collation("utf8mb4")
for collation in collations:
    print(f"{collation.collation}: {collation.charset}")
```

## Async API

The async backend provides identical introspection methods with the same names as the sync version:

```python
from rhosocial.activerecord.backend.impl.mysql.backend.async_backend import AsyncMySQLBackend

backend = AsyncMySQLBackend(
    host="localhost",
    port=3306,
    database="mydb",
    user="root",
    password="password"
)
await backend.connect()

# Async introspection methods (same names as sync version)
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
columns = await backend.introspector.list_columns("users")

# Async SHOW commands
create_table = await backend.introspector.show.show_create_table("users")
```

## Cache Management

Introspection results are cached by default for performance:

```python
# Clear all introspection cache
backend.introspector.clear_cache()

# Invalidate specific scope
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# Invalidate all table-related cache
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# Invalidate cache for a specific table
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
```

## MySQL-Specific Behaviors

### System Databases

MySQL excludes the following system databases by default:

- `information_schema` — Metadata information
- `performance_schema` — Performance monitoring
- `mysql` — System users and permissions
- `sys` — System views and stored procedures

To include these databases, use `include_system=True` parameter.

### Storage Engine Information

`IntrospectionTableInfo` does not carry the engine — a table record answers its name, type, comment, row estimate and byte split, and `extra` stays empty. Engine, row format, collation, create options and the auto-increment counter are the `table-options` family, answered from the same `information_schema.TABLES` relation:

```python
options = backend.introspector.get_table_options("users")
if options:
    print(f"Engine: {options.engine}")
    print(f"Row format: {options.row_format}")
    print(f"Collation: {options.table_collation}")
    print(f"Auto increment: {options.auto_increment}")
    print(f"Data bytes: {options.data_length}")
    print(f"Index bytes: {options.index_length}")
```

`list_table_options()` answers for every base table at once, and `get_table_options()` returns `None` for a name that is a view or does not exist — a view has no engine, and a half-empty record would be worse than saying nothing. `data_length` and `index_length` are the server's own accounting, which for InnoDB is an estimate from the tablespace rather than an exact byte count; `total_length` sums the two components without recomputing either.

### Character Set and Collation

MySQL column information includes character set and collation:

```python
columns = backend.introspector.list_columns("users")
for col in columns:
    if col.charset:
        print(f"{col.name}: charset={col.charset}, collation={col.collation}")
```

### Index Types

MySQL answers four `INDEX_TYPE` values through `information_schema.STATISTICS`:

| `INDEX_TYPE` | Description |
|--------------|-------------|
| `BTREE` | Default index type |
| `HASH` | Memory engine only |
| `FULLTEXT` | Full-text index |
| `RTREE` | Spatial index (`SPATIAL` is the DDL keyword, not an `INDEX_TYPE` value) |

Both `SPATIAL` and `RTREE` are parsed to `IndexType.SPATIAL`; the other three map to the member of the same name.

```python
from rhosocial.activerecord.backend.introspection.types import IndexType

indexes = backend.introspector.list_indexes("articles")
for idx in indexes:
    if idx.index_type == IndexType.FULLTEXT:
        print(f"Full-text index: {idx.name}")
```

## Operational Families

MySQL implements all six. Each is one catalogue read — or one `SHOW CREATE` for DDL — and none of them scans the user's rows, so a family's price is the price of the view it reads rather than the size of the database.

| Family | Method | MySQL source | Price |
|--------|--------|--------------|-------|
| Unused indexes | `list_unused_indexes()` | `sys.schema_unused_indexes` | One read of a server-wide view |
| Table counters | `list_table_usage_stats()` | `performance_schema.table_io_waits_summary_by_table` | One summary read |
| Runtime metrics | `list_runtime_metrics()` | `performance_schema.setup_instruments` | One server-wide instrument listing |
| Index counters | `list_index_usage_stats()` | `performance_schema.table_io_waits_summary_by_index_usage` | One summary read |
| Dependencies | `list_object_dependencies()` | `information_schema.referential_constraints` | One catalogue read |
| DDL | `get_ddl_statement()` | `SHOW CREATE TABLE` | One statement, engine-side |

The tense is the fact most easily lost. Every counter here is since the statistics were last reset: for the two `performance_schema` summaries the window is the server's uptime — the dialect states that the counters count since the server started, not over a resettable epoch — and for `sys.schema_unused_indexes` it is the last reset of the table's statistics. Nothing in the answer dates the window, so a zero is "none in the stretch the server remembers", never "never". A cached answer also ages faster here than in the declaration layer: a schema cached yesterday is probably still the schema, while the window a counter described has kept running.

### Unused Indexes

The listing is the view's own three columns — object schema, object name, index name — filtered by schema in this backend's formatter, because the view is database-wide and asking about one database should not mean post-filtering the rest. What the view means: an index the performance schema has seen no access for, counting from the last reset of the table's statistics. A table nobody has queried since a restart reports all of its indexes, and the view covers only tables the collector instruments. The answer is "worth reviewing", never "safe to drop". An index that is not listed is absence of evidence, not evidence of use.

The probe is the 5.7 gate described above; below it the type is refused and the listing is never attempted.

### Table Usage Counters

One row per instrumented table from `performance_schema.table_io_waits_summary_by_table`, filtered by `OBJECT_SCHEMA`. The projection renames the view's uppercase address columns onto the common `schema_name` and `table_name`, and carries `count_read`, `count_write`, `count_fetch`, `count_insert`, `count_update` and `count_delete`. The common shape's `sequential_scans`, `indexed_scans`, `inserts`, `updates` and `deletes` stay `None` — MySQL's summary has no counter in those slots — and all six counters arrive in `extra` under the view's own names. `estimated_row_count` stays `None` too: the summary carries no row estimate, and MySQL's estimate lives in `information_schema.TABLES`, a different source with a different refresh schedule, whose figure beside these counters would look more correlated than it is.

A zero on the read side means "no I/O the collector saw", not "cold"; a zero on the write side means the same on the other side of the split. Neither is "no activity at all".

### Runtime Metrics

The listing reads `performance_schema.setup_instruments`, which names what is actually being counted on this server. It projects `NAME` as `name`, `ENABLED` as `value` and `TIMED` as `kind`. The relation has no schema column and is server-wide, so the formatter applies no schema filter — a filter here would refuse a correct query for a nonsensical reason. This answers "what is alive": an instrument that is not enabled produces no rows, so there is no zero that could read as idle. `unit`, `description` and `source` stay `None`, because the relation names none of them.

### Index Usage Counters

From `performance_schema.table_io_waits_summary_by_index_usage`, one row per index of every table in the schema: `COUNT_STAR` is projected as `scans`, `COUNT_FETCH` as `rows_fetched`. `rows_read` stays `None` because the engine keeps no per-index "rows read" counter and a fetch is not a row; `size_bytes` stays `None` because the summary does not carry it. Unlike the unused listing, a zero here is a measurement, and the difference between one scan and a million is what this family exists to show. The schema filter is applied in the formatter, since the summary is server-wide.

### Object Dependencies

`information_schema.referential_constraints` records one edge per foreign key: the constraint, the table that declares it, the table it references and its delete rule. The projection names `TABLE_NAME` as `dependent` and `REFERENCED_TABLE_NAME` as `referenced`, and carries `DELETE_RULE` as `action`. `kind`, `dependent_type` and `referenced_type` stay `None`: the catalogue covers foreign keys only and does not record which view, trigger or routine mentions which table. This is a real graph and a partial one. Naming a table narrows the answer to its dependants; omitting the name returns the whole graph.

### DDL Extraction

`SHOW CREATE TABLE`, read under the engine's own result-column names: `Table` and `Create Table`. The generic parser looks for `ddl`, `sql` or `definition`, and none of those exists in a `SHOW CREATE` row — so MySQL overrides the parser rather than letting a table the engine had just described be reported as having no DDL. `native` is `True`: the text is the engine's retrieval, not an assembly. Only `TABLE` is rendered. Naming `VIEW`, `PROCEDURE`, `FUNCTION` or `TRIGGER` raises `UnsupportedFeatureError`, because each takes a different `SHOW CREATE` statement and result column and this backend has not mapped them. `get_ddl_statement()` returns `None` when the engine reproduces nothing, which is not the same answer as "no such table".

All six answer through the same introspector, sync and async alike:

```python
backend.introspect_and_adapt()

if backend.dialect.supports_unused_indexes_detection():
    for index in backend.introspector.list_unused_indexes():
        print(f"{index.table_name}.{index.index_name}")

for edge in backend.introspector.list_object_dependencies("posts"):
    print(f"{edge.dependent} -> {edge.referenced} ({edge.action})")

ddl = backend.introspector.get_ddl_statement("orders")
if ddl is not None:
    print(ddl.native, ddl.ddl)
```

## Data Families

The three data families measure the rows rather than read a catalogue. MySQL keeps no per-column statistics catalogue: `information_schema` describes what a column *declares*, and `ANALYZE TABLE` refreshes the optimiser's index statistics (`STATISTICS.CARDINALITY` is one estimate per index prefix) without publishing a per-column distribution. Every figure here is therefore computed when asked — exact over the rows the query saw, and paid for in time proportional to the table. The profile projects `source='aggregate'` into every row it returns, rather than stamping the label on afterwards, so a consumer comparing it with another engine's estimate can tell them apart without knowing which engine it asked.

| Family | Method | Price |
|--------|--------|-------|
| Column profiles | `list_column_data_profiles(table)` | One pass over the table per column |
| Value samples | `sample_column_values(table, column, limit=100)` | One grouped pass over the column, plus a sort |
| Join coverage | `estimate_join_coverage(left_table, left_column, right_table, right_column)` | Two sides read for their distinct domains, plus the intersection |

### Column Profiles

One `UNION ALL` arm per column of the table, and each arm reads the table once: the null count is a `SUM` over a `CASE`, the distinct count `COUNT(DISTINCT ...)`, the endpoints the engine's `MIN`/`MAX`, and `COUNT(*)` rides the same scan as the divisor. A table of ten columns is therefore read ten times — the number of round trips stays one, the number of scans does not. `null_fraction` is derived in the parser (`null_count / row_count`), so a row count that may be zero never has to be guarded in SQL. An empty table answers `null_fraction = None` because `SUM` over no rows is NULL — absence of a measurement, not "no nulls" — and `min_value`/`max_value` as `None`; `distinct_count` and `row_count` are `0`, which are measurements rather than absences.

One consequence of the compound statement is visible only in Python types. MySQL resolves one result type per column position across every `UNION ALL` arm, so `min_value` — which holds `code`'s text in one arm and `amount`'s decimal in another — arrives as text: `'1.00'`, not `1.00`. The figures are exact; only the type is the union's. Read a decimal endpoint through `Decimal(str(value))`. A future formatter that cast the column instead would trade text columns' endpoints away to make the numeric ones prettier; one query per column would keep each native type at one round trip per column, which is the loop this family exists to avoid.

### Value Samples

A `GROUP BY` over the column plus a sort of the groups — the same order of cost as the profile, which is why the two are separate calls: a caller wanting only the listing does not pay for the profile's distinct counts and endpoints. `ORDER BY COUNT(*) DESC` is what makes the answer "the most frequent values" rather than "the first values", and ties break by the value so two runs of the same query agree. The limit is bound as a parameter, so the caller's integer is never spliced into statement text. Only `value` and `count` are projected: `frequency` stays `None` because the engine reports a count and the denominator is the row count the profile carries.

`GROUP BY` groups NULLs, so a column that contains NULL has an entry whose `value` is `None`, and it is usually the most frequent one. NULL is a member of the domain in this listing, and the parser does not skip it — unlike address rows elsewhere, which skip a row with no identity. A caller reading the listing as "the values in this column" must not assume every entry is a value; the profile's `null_fraction` is the cross-engine measure of the same fact.

### Join Coverage

Both fractions come from one statement. For each side, the numerator counts the distinct values that also occur on the other side — a `COUNT(*)` over a derived `DISTINCT` — and the denominator counts that side's distinct non-NULL values. NULLs are excluded from both halves explicitly: a `DISTINCT` would otherwise count NULL as one value and credit a match that can never join, while `COUNT(DISTINCT ...)` would skip it silently. `NULLIF(..., 0)` makes a column with nothing to match answer NULL rather than `0.0`, so "nothing matched" and "nothing to match" stay distinct. There is no `* 1.0` here: MySQL's division of two integer counts already answers a fractional `DECIMAL`. Collations are not reconciled, so across mismatched collations the fractions are a lower bound, never an upper one. The price is the two sides read for their distinct domains plus the intersection, with each side's fraction paying a second pass for its denominator — which is why this is a call of its own and never part of a profile.

```python
profiles = backend.introspector.list_column_data_profiles("orders")
for profile in profiles:
    print(profile.column_name, profile.null_fraction, profile.distinct_count,
          profile.row_count, profile.source)

samples = backend.introspector.sample_column_values("orders", "status", limit=20)
for sample in samples:
    print(sample.value, sample.count)    # value is None when NULL is a group

coverage = backend.introspector.estimate_join_coverage(
    "orders", "customer_id",
    "customers", "id",
)
print(coverage.left_coverage, coverage.right_coverage)
```

## Version Compatibility

Introspection behavior differences across MySQL versions:

| Feature | MySQL 5.7 | MySQL 8.0+ |
|---------|-----------|------------|
| `information_schema` | Full support | Full support |
| `sys.schema_unused_indexes` | Supported | Supported |
| Invisible columns | Not supported | Supported from 8.0.23 |
| Generated invisible primary key | Not supported | Supported from 8.0.30 |
| JSON expression extraction | Limited support | Full support |

## Version and Availability Floors

Two limits decide whether an operational or data family can answer at all, and neither is a property of the query text.

| Family | Floor | What a missing floor looks like |
|--------|-------|---------------------------------|
| `unused-indexes` | MySQL 5.7.0, where the `sys` schema arrives | probe `False`; the CLI exits 2 without running the query |
| `table-stats`, `index-stats`, `runtime` | `performance_schema` enabled at install | probe `True`, empty answer |
| every other family | none established here | — |

The `sys` schema floor is the only version gate in this backend. `unused-indexes` reads `sys.schema_unused_indexes`, and before 5.7 the statement renders but the server answers `1146`, "table does not exist" — which is how the gap was found: the CLI was the first caller to reach the family on 5.6 and failed at execution rather than at the capability question. `supports_unused_indexes_detection()` therefore returns `version_at_least((5, 7, 0))` rather than `True`, and below it the CLI refuses the run without reaching the introspector. An unadapted dialect answers `False` too, because a version nobody confirmed is not a capability claimed.

The performance schema is an install-time option, not a version floor. `table-stats`, `index-stats` and `runtime` read its relations, and the collector is enabled when the server is installed (`performance_schema=ON`). The three probes answer `True` unconditionally because a dialect cannot see the server's startup options, and the capability does exist — the data source is a setting. On a server where the collector is off the families return nothing, and that empty answer is not a measurement of idleness; the live tests skip those families there rather than treat the empty answer as a defect.

A probe answering `False` is "the question cannot be asked here", not "nothing was used". It does not say that no index was used, that no table was read, or that the database has no indexes: it says the server cannot be asked. `False` lets a caller take its fallback knowingly; the empty list is reserved for a question that was asked and had nothing to report.

The probes do not test grants. No privilege floor is established here: a probe answers about the server and its settings, not about the account's privileges. If the connected account may not read `sys` or `performance_schema`, the engine's own error arrives at execution; the probe said `True` because the server can answer, not because this account may ask.

## Best Practices

### 1. Use Caching

Introspection operations involve complex `information_schema` queries. Leverage caching:

```python
# First query caches the result
tables = backend.introspector.list_tables()

# Subsequent queries return from cache
tables_again = backend.introspector.list_tables()

# Only clear cache when table structure changes
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")
```

### 2. Use SHOW Commands for Detailed Information

When you need the complete CREATE TABLE statement, use `SHOW CREATE TABLE`:

```python
# Get complete CREATE TABLE statement (including all options)
create_table = backend.introspector.show.show_create_table("users")
print(create_table.create_statement)
```

### 3. Batch Operations

Prefer batch query methods when possible:

```python
# Good: One query for all columns
columns = backend.introspector.list_columns("users")

# Avoid: Multiple single-column queries
for col_name in column_names:
    col = backend.introspector.get_column_info("users", col_name)  # I/O each time
```

## API Reference

### Introspection Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `get_database_info()` | Get database information | None |
| `list_tables()` | List tables | `include_system`, `table_type`, `schema` |
| `get_table_info(name)` | Get table details | `name`, `schema` |
| `table_exists(name)` | Check table exists | `name`, `schema` |
| `list_columns(table_name)` | List columns | `table_name`, `schema` |
| `get_column_info(table_name, column_name)` | Get column details | `table_name`, `column_name`, `schema` |
| `get_primary_key(table_name)` | Get primary key | `table_name`, `schema` |
| `list_indexes(table_name)` | List indexes | `table_name`, `schema` |
| `list_foreign_keys(table_name)` | List foreign keys | `table_name`, `schema` |
| `list_views()` | List views | `schema` |
| `get_view_info(name)` | Get view details | `name`, `schema` |
| `list_triggers(table_name)` | List triggers | `table_name`, `schema` |
| `list_table_options()` | Storage options of every base table | `schema` |
| `get_table_options(name)` | Storage options of one table | `name`, `schema` |
| `list_partitions(table_name)` | One table's partitions | `table_name`, `schema` |
| `list_unused_indexes()` | Indexes with no recorded access | `schema` |
| `list_table_usage_stats()` | Per-table I/O counters | `schema` |
| `list_runtime_metrics()` | Live runtime facts | `schema` |
| `list_index_usage_stats()` | Per-index usage counters | `schema` |
| `list_object_dependencies(object_name)` | Foreign-key dependency edges | `object_name`, `schema` |
| `get_ddl_statement(object_name, object_type)` | The engine's DDL for one table | `object_name`, `object_type`, `schema` |
| `list_column_data_profiles(table_name)` | What each column holds | `table_name`, `schema` |
| `sample_column_values(table_name, column_name, limit)` | Most frequent values | `table_name`, `column_name`, `limit`, `schema` |
| `estimate_join_coverage(left_table, left_column, right_table, right_column)` | Two columns' domain overlap | the four names, `schema` |
| `clear_cache()` | Clear cache | None |
| `invalidate_cache(scope, ...)` | Invalidate cache | `scope`, `name`, `table_name` |

### SHOW Command Methods

| Method | Description |
|--------|-------------|
| `show_create_table(table_name)` | Get CREATE TABLE statement |
| `show_create_view(view_name)` | Get CREATE VIEW statement |
| `show_columns(table_name)` | Show column information |
| `show_index(table_name)` | Show index information |
| `show_tables()` | Show table list |
| `show_databases()` | Show database list |
| `show_table_status(table_name)` | Show table status |
| `show_triggers(table_name)` | Show triggers |
| `show_variables(pattern)` | Show system variables |
| `show_status(pattern)` | Show status variables |
| `show_processlist()` | Show process list |
| `show_engines()` | Show storage engines |
| `show_charset()` | Show character sets |
| `show_collation(pattern)` | Show collations |

## Command Line Introspection

The MySQL backend provides command-line introspection commands to query database metadata without writing code.

### Basic Usage

```bash
# List all tables
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --host localhost --port 3306 --database mydb --user root --password secret

# List all views
python -m rhosocial.activerecord.backend.impl.mysql introspect views \
  --database mydb --user root

# Get database information
python -m rhosocial.activerecord.backend.impl.mysql introspect database \
  --database mydb --user root

# Include system tables
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --include-system
```

### Connection Parameters

Supports configuration via command-line arguments or environment variables:

| Parameter | Environment Variable | Description |
|-----------|---------------------|-------------|
| `--host` | `MYSQL_HOST` | Database host (default: localhost) |
| `--port` | `MYSQL_PORT` | Database port (default: 3306) |
| `--database` | `MYSQL_DATABASE` | Database name (required) |
| `--user` | `MYSQL_USER` | Username (default: root) |
| `--password` | `MYSQL_PASSWORD` | Password |
| `--charset` | `MYSQL_CHARSET` | Character set (default: utf8mb4) |

### Querying Table Details

```bash
# Describe one view
python -m rhosocial.activerecord.backend.impl.mysql introspect views users_v \
  --database mydb --user root

# Query only column information
python -m rhosocial.activerecord.backend.impl.mysql introspect columns users \
  --database mydb --user root

# Query only index information
python -m rhosocial.activerecord.backend.impl.mysql introspect indexes users \
  --database mydb --user root

# Query only foreign key information
python -m rhosocial.activerecord.backend.impl.mysql introspect foreign-keys posts \
  --database mydb --user root

# Query triggers
python -m rhosocial.activerecord.backend.impl.mysql introspect triggers \
  --database mydb --user root

# Query triggers for a specific table
python -m rhosocial.activerecord.backend.impl.mysql introspect triggers users \
  --database mydb --user root
```

### Introspection Types

| Type | Description | Name |
|------|-------------|------|
| `tables` | List all tables | not accepted |
| `views` | List all views, or describe one | optional (view) |
| `database` | Database information | not accepted |
| `columns` | Column information | required (table) |
| `indexes` | Index information | required (table) |
| `foreign-keys` | Foreign key information | required (table) |
| `triggers` | Trigger information | optional (table) |
| `table-options` | Engine, row format, collation and byte sizes of one table | optional (table) |
| `partitions` | One table's partitions | required (table) |
| `unused-indexes` | Indexes with no recorded access | not accepted |
| `table-stats` | Per-table I/O counters | not accepted |
| `runtime` | Live runtime facts | not accepted |
| `index-stats` | Per-index usage counters | not accepted |
| `dependencies` | Foreign-key dependency edges | optional (table) |
| `ddl` | The engine's DDL for one table | required (table) |
| `column-profiles` | What each column of a table holds | required (table) |
| `value-samples` | Most frequent values of one column | required (table) |
| `join-coverage` | Overlap of two columns' value domains | not accepted |

A name the type cannot use is refused (exit 2) rather than ignored.

The nine families added above take a NAME only where one object is the question. `dependencies` narrows to a table's dependants; `table-stats`, `index-stats`, `runtime` and `join-coverage` answer for the whole database and refuse a name (exit 2) rather than print an unnarrowed listing. `ddl`, `column-profiles` and `value-samples` require a table. `value-samples` also requires `--column`, and `join-coverage` requires `--left-table`, `--left-column`, `--right-table` and `--right-column`: a missing required flag is an incomplete invocation (exit 1), and a flag the type does not read is refused (exit 2). `--limit` is forwarded to `sample_column_values()` only when it is given; without it the introspector's own default answers (`VALUE_SAMPLE_LIMIT`, 100), so the number is not written in two places. The `ddl` type prints the engine's text alone in the table format, and the record — schema, object type, object name, `native` and the text — in the formats a caller parses.

### Querying Operational and Data Families

```bash
# Six operational readings
python -m rhosocial.activerecord.backend.impl.mysql introspect unused-indexes \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect table-stats \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect index-stats \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect runtime \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect dependencies \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect dependencies orders \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect ddl orders \
  --database mydb --user root

# Three data readings
python -m rhosocial.activerecord.backend.impl.mysql introspect column-profiles orders \
  --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect value-samples orders \
  --column status --limit 20 --database mydb --user root
python -m rhosocial.activerecord.backend.impl.mysql introspect join-coverage \
  --left-table orders --left-column customer_id \
  --right-table customers --right-column id \
  --database mydb --user root
```

### Output Formats

```bash
# Table format (default, requires rich library)
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root

# JSON format
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --output json

# CSV format
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --output csv

# TSV format
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --output tsv
```

### Using Async Backend

```bash
# Use the --async flag to enable async mode
python -m rhosocial.activerecord.backend.impl.mysql introspect tables \
  --database mydb --user root --async
```

### Environment Variable Configuration

You can set connection parameters in the environment to simplify command-line calls:

```bash
# Set environment variables
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=mydb
export MYSQL_USER=root
export MYSQL_PASSWORD=secret

# Use command directly
python -m rhosocial.activerecord.backend.impl.mysql introspect tables
```
