# $\mathcal{B}_{\text{mysql}}^{\rho}$ - MySQL Backend Quick Execution Tool

This `__main__.py` script provides a command-line interface to quickly execute SQL queries against a MySQL database using the `rhosocial-activerecord` MySQL backend implementation. It supports both synchronous and asynchronous execution modes.

## Purpose

This tool is designed for:
*   Rapid testing of MySQL backend connectivity and query execution.
*   Debugging specific SQL queries or backend behaviors.
*   Performing quick database operations (DDL/DML) directly from the command line.

## Usage

To run the script, navigate to the root directory of the `python-activerecord` project (where the `src` folder is located). Then, execute the module using `python -m` followed by the module path.

The SQL query is now a **positional argument** and should be the last argument after all optional flags.

```bash
python -m src.rhosocial.activerecord.backend.impl.mysql [OPTIONAL_FLAGS] "YOUR_SQL_QUERY;"
```

### Arguments

| Argument         | Default                                           | Description                                                                                                                                                             |
| :--------------- | :------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--host`         | `MYSQL_HOST` env var or `localhost`               | Database host.                                                                                                                                          |
| `--port`         | `MYSQL_PORT` env var or `3306`                    | Database port.                                                                                                                                          |
| `--database`     | `MYSQL_DATABASE` env var or _None_                | Database name to connect to (optional). If not provided, the connection will be established without selecting a default database. Useful for `CREATE DATABASE` or `SHOW DATABASES` commands. |
| `--user`         | `MYSQL_USER` env var or `root`                    | Database user.                                                                                                                                          |
| `--password`     | `MYSQL_PASSWORD` env var or _empty string_        | Database password.                                                                                                                                      |
| `--charset`      | `MYSQL_CHARSET` env var or `utf8mb4`              | Connection character set.                                                                                                                               |
| `query`          | _Required_ (positional)                           | **SQL query to execute.** Must be enclosed in quotes.                                                                                                   |
| `--use-async`    | _False_                                           | Use the asynchronous backend (`AsyncMySQLBackend`). If omitted, the synchronous backend (`MySQLBackend`) will be used.                                    |
| `--log-level`    | `INFO`                                            | Set the logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).                                                                        |
| `--rich-ascii`   | _False_                                           | Use ASCII characters for table borders. Recommended for terminals that have trouble rendering Unicode box characters.                                |

## Pretty Output with `rich`

This tool integrates with the [rich](https://github.com/Textualize/rich) library to provide beautified, color-coded output and logging. This is an optional feature.

### Activation

To enable this feature, simply install `rich` in your Python environment:
```bash
pip install rich
```
The script will automatically detect its presence and enhance the output. If `rich` is not found, the script will fall back to standard plain text output.

### Rendering Issues in Terminals

Some terminals (especially on Windows) may not correctly render the box-drawing characters used in tables by default, leading to garbled output. To fix this, you can use the `--rich-ascii` flag.

```bash
python -m rhosocial.activerecord.backend.impl.mysql ... --rich-ascii "SELECT 1;"
```
This forces the table borders to be rendered using only ASCII characters, which is compatible with all terminals.

## Using Environment Variables for Connection Parameters

To simplify command-line execution and avoid repetitive arguments, you can set connection parameters as environment variables. Command-line arguments will always take precedence over environment variables.

**Supported Environment Variables:**
*   `MYSQL_HOST`
*   `MYSQL_PORT`
*   `MYSQL_DATABASE`
*   `MYSQL_USER`
*   `MYSQL_PASSWORD`
*   `MYSQL_CHARSET`

**Examples for setting environment variables and running commands:**

### Bash (Linux/macOS)

```bash
# Set environment variables for the current session
export MYSQL_HOST="your_mysql_host"
export MYSQL_PORT="your_mysql_port" # e.g., "3306" or your custom port
export MYSQL_USER="your_mysql_user" # e.g., "root"
export MYSQL_PASSWORD="your_secure_password"
# export MYSQL_DATABASE="your_default_db" # Optional, if you often work with one database

# Run a query using environment variables
python -m src.rhosocial.activerecord.backend.impl.mysql "SELECT NOW();" --use-async

# Override user via command-line
python -m src.rhosocial.activerecord.backend.impl.mysql "SELECT * FROM your_table;" --user guest
```

### PowerShell (Windows)

```powershell
# Set environment variables for the current session
$env:MYSQL_HOST="your_mysql_host"
$env:MYSQL_PORT="your_mysql_port" # e.g., "3306" or your custom port
$env:MYSQL_USER="your_mysql_user" # e.g., "root"
$env:MYSQL_PASSWORD="your_secure_password"
# $env:MYSQL_DATABASE="your_default_db" # Optional, if you often work with one database

# Run a query using environment variables
python -m src.rhosocial.activerecord.backend.impl.mysql "SELECT NOW();" --use-async

# Override user via command-line
python -m src.rhosocial.activerecord.backend.impl.mysql "SELECT * FROM your_table;" --user guest
```

### Command Prompt (CMD) (Windows)

```cmd
REM Set environment variables for the current session
set MYSQL_HOST="your_mysql_host"
set MYSQL_PORT="your_mysql_port" REM e.g., "3306" or your custom port
set MYSQL_USER="your_mysql_user" REM e.g., "root"
set MYSQL_PASSWORD="your_secure_password"
REM set MYSQL_DATABASE="your_default_db" REM Optional, if you often work with one database

REM Run a query using environment variables
python -m src.rhosocial.activerecord.backend.impl.mysql "SELECT NOW();" --use-async

REM Override user via command-line
python -m src.rhosocial.activerecord.backend.impl.mysql "SELECT * FROM your_table;" --user guest
```

## Examples

This section provides a complete lifecycle example of database operations, from creating a database to cleaning it up.

**Note**:
*   The following examples assume you are running the commands from the root of the `python-activerecord-mysql` project.
*   For a multi-repository setup (with `python-activerecord` and `python-activerecord-mysql` in separate folders), you must set your `PYTHONPATH` to include the `src` directories of both projects.
    *   **PowerShell**: `$env:PYTHONPATH="src;..\python-activerecord\src"`
    *   **Bash**: `export PYTHONPATH="src:../python-activerecord/src"`
*   Replace placeholder credentials (`your_mysql_host`, etc.) with your actual MySQL server credentials, or set the corresponding environment variables (`MYSQL_HOST`, etc.).

---

### Step 1: Create a Database

First, we'll create a new database named `test_db`. Note that we don't use the `--database` flag here.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    "CREATE DATABASE test_db;"
```

### Step 2: Create a Table

Now, let's create a `users` table within our new database. We'll specify `--database test_db` for this and all subsequent table-level commands.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), email VARCHAR(100));"
```

### Step 3: Insert Records

Let's add two users, 'Alice' and 'Bob', to our `users` table.

```bash
# Insert Alice
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');"

# Insert Bob
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com');"
```

### Step 4: Query Records

Retrieve all records from the `users` table to verify the insertions.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "SELECT * FROM users;"
```
*Expected Output:*
```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
{
  "id": 2,
  "name": "Bob",
  "email": "bob@example.com"
}
```

### Step 5: Update a Record

Let's update Alice's email address.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "UPDATE users SET email = 'alice_updated@example.com' WHERE name = 'Alice';"
```

### Step 6: Delete a Record

Now, let's remove Bob from the table.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "DELETE FROM users WHERE name = 'Bob';"
```

### Step 7: Clean Up by Dropping the Table

After our operations are complete, we can clean up by dropping the `users` table.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    --database test_db \
    "DROP TABLE users;"
```

### Step 8: Final Cleanup by Dropping the Database

Finally, we remove the test database itself.

```bash
python -m rhosocial.activerecord.backend.impl.mysql \
    --host your_mysql_host --user your_mysql_user --password your_secure_password \
    "DROP DATABASE test_db;"
```

## Important Notes

*   **Project Root Execution**: Ensure you execute these commands from the root directory of your `python-activerecord` project (the directory containing the `src` folder) for module path resolution.
*   **Optional Database**: The `--database` argument is optional. If you need to perform operations like `CREATE DATABASE` or `SHOW DATABASES` that don't target a specific existing database, you can omit `--database` or specify a system database like `mysql`.
*   **Environment Variables**: Connection parameters can be set via environment variables (e.g., `MYSQL_HOST`). Command-line arguments will override environment variables if both are provided. Refer to the "Using Environment Variables for Connection Parameters" section for platform-specific instructions.
*   **Error Handling**: The script includes basic error handling for connection and query issues.
*   **Logging**: Adjust the `--log-level` to `DEBUG` for more verbose output during execution.
*   **Query Parameter**: The SQL query is now a **positional argument** and should be placed at the end of the command after all optional flags. Always wrap your SQL query in quotes to ensure it's passed as a single argument.