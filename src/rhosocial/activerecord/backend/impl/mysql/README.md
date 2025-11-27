# $\mathcal{B}_{\text{mysql}}^{\rho}$ - MySQL Backend Quick Execution Tool

This `__main__.py` script provides a command-line interface to quickly execute a single SQL query against a MySQL database using the `rhosocial-activerecord` MySQL backend implementation.

## Purpose

This tool is designed for:
*   Rapid testing of MySQL backend connectivity and query execution.
*   Debugging specific SQL queries or backend behaviors.
*   Performing quick, single-statement database operations (DDL/DML) directly from the command line.

## Usage

To run the script, navigate to the root directory of the project (where the `src` folder is located). Then, execute the module using `python -m` followed by the module path.

SQL queries can be provided as a positional argument, from a file using the `--file` flag, or piped via standard input (stdin).

```bash
python -m rhosocial.activerecord.backend.impl.mysql [OPTIONAL_FLAGS] [YOUR_SQL_QUERY]
```

## Arguments

| Argument          | Default                                            | Description                                                                                                                                                             |
| :---------------- | :------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `query`           | _None_                                             | **SQL query to execute.** If not provided, reads from `--file` or stdin.                                                                                                |
| `-f, --file`      | _None_                                             | Path to a file containing a **single** SQL query to execute.                                                                                                           |
| `--host`          | `MYSQL_HOST` env var or `localhost`                | Database host.                                                                                                                                                          |
| `--port`          | `MYSQL_PORT` env var or `3306`                     | Database port.                                                                                                                                                          |
| `--database`      | `MYSQL_DATABASE` env var or _None_                 | Database name to connect to.                                                                                                                                            |
| `--user`          | `MYSQL_USER` env var or `root`                     | Database user.                                                                                                                                                          |
| `--password`      | `MYSQL_PASSWORD` env var or _empty string_         | Database password.                                                                                                                                                      |
| `--charset`       | `MYSQL_CHARSET` env var or `utf8mb4`               | Connection character set.                                                                                                                                               |
| `--use-async`     | _False_                                            | Use the asynchronous backend.                                                                                                                                           |
| `--output`        | `table` (if rich available) or `json` (fallback)    | Output format. Choices are `table` (rich formatted), `json`, `csv`, `tsv`.                                                                                             |
| `--log-level`     | `INFO`                                             | Set the logging level (e.g., `DEBUG`, `INFO`).                                                                                                                        |
| `--rich-ascii`    | _False_                                            | Use ASCII characters for table borders.                                                                                                                                 |

## Important Notes

*   **Single Statement Only**: This tool does not support multi-statement execution. Any input provided (via argument, file, or stdin) **must contain only a single SQL statement**.
*   **Project Root Execution**: Ensure you execute these commands from the root directory of your project for module path resolution.
*   **Environment Variables**: Connection parameters can be set via environment variables (e.g., `MYSQL_HOST`). Command-line arguments will override them.

## Examples

#### 1. Execute Query from Argument

```bash
# Set PYTHONPATH to include both this project's and the core project's src
export PYTHONPATH="src:../python-activerecord/src"

# Run a query with credentials
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_host --user your_user --password "your_pass" --database "your_db" \
    "SELECT NOW();"
```

#### 2. Execute Query from Stdin with CSV Output

```bash
echo "SELECT user, host FROM mysql.user WHERE user = 'root';" | \
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_host --user your_user --password "your_pass" --output csv
```
**Expected Output (to stdout):**
```csv
user,host
root,%
```

#### 3. Execute Query from File with JSON Output

Create a file `get_version.sql` with the content:
```sql
SELECT VERSION();
```

Then run the command:
```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_host --user your_user --password "your_pass" \
    --file get_version.sql --output json
```
**Expected Output (to stdout):**
```json
[
  {
    "VERSION()": "8.0.43"
  }
]
```