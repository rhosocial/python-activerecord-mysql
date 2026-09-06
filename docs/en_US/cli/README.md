# Command-Line Interface

## Overview

The MySQL backend includes a command-line interface for database operations. The CLI provides commands for querying, introspecting, and managing your MySQL database without writing Python code.

CLI commands fall into two categories:

1. **MySQL-specific commands** — MySQL-unique operations (query, introspect, info, status)
2. **Core inherited commands** — shared across all backends (named-expression, named-procedure, named-migration, named-connection)

## Invocation

The CLI is installed as `rhosocial-activerecord-mysql` when you install the package:

```bash
pip install rhosocial-activerecord-mysql
```

Then invoke commands directly:

```bash
rhosocial-activerecord-mysql <command> [options]
```

This command is registered in `pyproject.toml` and is equivalent to `python -m rhosocial.activerecord.backend.impl.mysql`.

## Output Formats

The CLI supports multiple output formats via the `-o` / `--output` option:

| Format | Description | Rich Required |
|--------|-------------|---------------|
| `table` | Human-readable table with borders (default) | Yes |
| `json` | JSON array of objects | No |
| `csv` | Comma-separated values | No |
| `tsv` | Tab-separated values | No |

When Rich is installed, the `table` format provides beautified output with colored borders. When Rich is not available, the CLI automatically falls back to `json` format.

### Rich Integration

The CLI integrates with the [Rich](https://github.com/Textualize/rich) library for enhanced terminal output:

- **Colored borders**: Unicode box-drawing characters for table borders
- **ASCII fallback**: Use `--rich-ascii` to force ASCII borders (`+`, `-`, `|`)
- **Auto-detection**: If Rich is not installed, falls back to JSON output automatically

```bash
# Default table output (Unicode borders)
rhosocial-activerecord-mysql query --host localhost --database mydb "SELECT * FROM users;"

# ASCII borders (for terminals without Unicode support)
rhosocial-activerecord-mysql query --host localhost --database mydb --rich-ascii "SELECT * FROM users;"

# Force JSON output
rhosocial-activerecord-mysql query --host localhost --database mydb -o json "SELECT * FROM users;"
```

### Output Examples

**Table format (default):**
```
┌─────┬─────────┬───────┐
│ id  │ name    │ email │
├─────┼─────────┼───────┤
│ 1   │ Alice   │ a@x   │
│ 2   │ Bob     │ b@x   │
└─────┴─────────┴───────┘
```

**JSON format:**
```json
[
  {"id": 1, "name": "Alice", "email": "a@x"},
  {"id": 2, "name": "Bob", "email": "b@x"}
]
```

**CSV format:**
```csv
id,name,email
1,Alice,a@x
2,Bob,b@x
```

**TSV format:**
```tsv
id	name	email
1	Alice	a@x
2	Bob	b@x
```

## MySQL-Specific Commands

### info

Display environment information without requiring a database connection:

```bash
rhosocial-activerecord-mysql info
```

Output includes:
- MySQL version information
- Protocol support status
- Feature availability

### query

Execute SQL queries directly:

```bash
# Simple query
rhosocial-activerecord-mysql query \
    --host localhost --port 3306 --database mydb \
    --user root --password secret \
    "SELECT * FROM users LIMIT 10"

# JSON output
rhosocial-activerecord-mysql query \
    --host localhost --port 3306 --database mydb \
    --user root --password secret \
    -o json "SELECT * FROM users LIMIT 10"
```

### introspect

Inspect database metadata:

```bash
# List all tables
rhosocial-activerecord-mysql introspect tables \
    --host localhost --port 3306 --database mydb

# List all views
rhosocial-activerecord-mysql introspect views \
    --host localhost --port 3306 --database mydb

# Get database information
rhosocial-activerecord-mysql introspect database \
    --host localhost --port 3306 --database mydb

# Get complete table info (columns, indexes, foreign keys)
rhosocial-activerecord-mysql introspect table users \
    --host localhost --port 3306 --database mydb

# Query specific details
rhosocial-activerecord-mysql introspect columns users \
    --host localhost --port 3306 --database mydb
rhosocial-activerecord-mysql introspect indexes users \
    --host localhost --port 3306 --database mydb
```

#### Introspection Types

| Type | Description |
|------|-------------|
| `tables` | List all tables |
| `views` | List all views |
| `table` | Describe a specific table |
| `columns` | List columns for a table |
| `indexes` | List indexes for a table |
| `foreign-keys` | List foreign keys for a table |
| `triggers` | List triggers |
| `database` | Database information |

### status

Display server status:

```bash
rhosocial-activerecord-mysql status \
    --host localhost --port 3306 --database mydb
```

## Core Inherited Commands

These commands are **inherited from the core `python-activerecord` library** and work identically across all backends:

| Command | Source Module | Description |
|---------|--------------|-------------|
| `named-expression` | `backend.named_expression` | Execute type-safe parameterized SQL defined in Python |
| `named-procedure` | `backend.named_expression.procedure` | Execute multi-query orchestration with transaction support |
| `named-procedure-graph` | `backend.named_expression.procedure` | Execute procedure graphs (DAG workflows) |
| `named-migration` | `backend.migration` | Execute versioned schema changes with dependency tracking |
| `named-connection` | `backend.named_connection` | Manage and test named connection configurations |

### Why Named Features?

Named features let you **encode complex configurations as a single name**, avoiding verbose command-line arguments and enabling parameter combinations that cannot be expressed through CLI flags alone.

**Named Connection** — encapsulates all connection parameters:

```bash
# Without named connection: long argument list
rhosocial-activerecord-mysql query \
    --host prod-db.example.com --port 3306 --database myapp \
    --user readonly --password secret --charset utf8mb4 \
    --conn-param ssl-ca=/path/to/ca.pem \
    --conn-param ssl-cert=/path/to/client-cert.pem \
    --conn-param ssl-key=/path/to/client-key.pem \
    "SELECT * FROM users"

# With named connection: one name holds everything
rhosocial-activerecord-mysql query \
    --named-connection myapp.connections.prod_readonly \
    "SELECT * FROM users"
```

**Named Expression** — encapsulates complex query logic:

```bash
# Without named expression: complex SQL that's hard to shell-escape
rhosocial-activerecord-mysql query \
    "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.created_at >= '2026-01-01' GROUP BY u.id HAVING COUNT(o.id) > 5 ORDER BY order_count DESC LIMIT 20"

# With named expression: one name, typed parameters
rhosocial-activerecord-mysql named-expression \
    myapp.queries.high_value_customers \
    --param since=2026-01-01 --param min_orders=5
```

**Named Procedure** — encapsulates multi-step workflows:

```bash
# Without named procedure: multiple sequential commands
rhosocial-activerecord-mysql query "BEGIN TRANSACTION; ..."
rhosocial-activerecord-mysql query "UPDATE inventory ..."
rhosocial-activerecord-mysql query "INSERT INTO orders ..."
rhosocial-activerecord-mysql query "COMMIT;"

# With named procedure: one command, transaction managed
rhosocial-activerecord-mysql named-procedure \
    myapp.workflows.place_order \
    --param user_id=42 --param product_id=100 --param quantity=3
```

| Feature | Benefit |
|---------|---------|
| Named Connection | Store connection config in versionable Python code; share across scripts |
| Named Expression | Encapsulate complex SQL; type-safe parameters; reuse across tools |
| Named Procedure | Multi-query workflows with transaction management; parallel execution |
| Named Migration | Versioned schema changes with dependency tracking; up/down support |

### named-expression

Execute named expressions (parameterized SQL defined in Python modules):

```bash
rhosocial-activerecord-mysql named-expression \
    myapp.queries.orders_by_status \
    --host localhost --port 3306 --database mydb \
    --user root --password secret \
    --param status=pending
```

### named-procedure

Execute named procedures:

```bash
rhosocial-activerecord-mysql named-procedure \
    myapp.procedures.sync_users \
    --host localhost --port 3306 --database mydb \
    --user root --password secret
```

### named-migration

Execute named migrations:

```bash
# Run migration up
rhosocial-activerecord-mysql named-migration up add_users_table \
    --host localhost --port 3306 --database mydb \
    --user root --password secret

# Run migration down
rhosocial-activerecord-mysql named-migration down add_users_table \
    --host localhost --port 3306 --database mydb \
    --user root --password secret
```

### named-connection

Manage and test named connection configurations:

```bash
rhosocial-activerecord-mysql named-connection my_connection \
    --params host=localhost port=3306 database=mydb user=root password=secret
```

## Connection Arguments

All commands that require a database connection accept these common arguments:

| Argument | Description |
|----------|-------------|
| `--host` | Database server hostname |
| `--port` | Database server port |
| `--database` | Database name |
| `--user` | Authentication username |
| `--password` | Authentication password |
| `--charset` | Character set (MySQL-specific) |
| `--async` | Use async backend |
| `--named-connection` | Use a named connection configuration |
| `--conn-param` | Additional connection parameters |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

## Global Options

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help message and exit |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) |

## Architecture

The CLI follows a consistent architecture:

```
backend/impl/mysql/
├── __main__.py          # Entry point, builds parser, dispatches to handlers
└── cli/
    ├── __init__.py      # COMMAND_NAMES list, register_commands()
    ├── connection.py    # Connection argument parsing and backend creation
    ├── output.py        # Output format providers (Rich/JSON/CSV/TSV)
    │
    │   # MySQL-specific commands
    ├── info.py          # 'info' command handler
    ├── query.py         # 'query' command handler
    ├── introspect.py    # 'introspect' command handler
    ├── status.py        # 'status' command handler
    │
    │   # Core inherited commands (thin adapters)
    ├── named_expression.py      # Delegates to core named_expression.cli
    ├── named_procedure.py       # Delegates to core named_expression.procedure.cli
    ├── named_procedure_graph.py # Delegates to core named_expression.procedure.cli
    ├── named_migration.py       # Delegates to core migration.cli
    └── named_connection.py      # Delegates to core named_connection.cli
```

## See Also

- [Installation Guide](../installation_and_configuration/installation.md) — setup instructions
- [Connection Management](../installation_and_configuration/pool.md) — connection configuration
- [Core Named Features](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US) — named connection, expression, procedure, migration documentation

💡 *AI Prompt:* "How do I list all tables in my MySQL database from the command line?"
