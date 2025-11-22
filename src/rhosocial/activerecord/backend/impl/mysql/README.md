# `__main__.py` - MySQL Backend Quick Execution Tool

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

**Note**: Replace `your_mysql_host`, `your_mysql_port`, `your_mysql_user`, `your_secure_password` with your actual MySQL server credentials. If environment variables are set, you can omit these arguments from the examples below.

### 1. Create a Database

To create a new database named `my_new_db`. You can connect without specifying a default database, or to a system database like `mysql`.

*   **Synchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        --database mysql "CREATE DATABASE my_new_db;"
    ```

*   **Asynchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        --database mysql "CREATE DATABASE my_new_db;" --use-async
    ```

### 2. List All Databases

To list all databases accessible by the connected user.

*   **Synchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        "SHOW DATABASES;"
    ```

*   **Asynchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        "SHOW DATABASES;" --use-async
    ```

### 3. Insert Data into a Table

Assuming you have a database named `my_new_db` and a table `users` (`CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255));`).

*   **Synchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        --database my_new_db "INSERT INTO users (name) VALUES ('Alice');"
    ```

*   **Asynchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        --database my_new_db "INSERT INTO users (name) VALUES ('Bob');" --use-async
    ```

### 4. Select Data from a Table

To retrieve data from the `users` table in `my_new_db`.

*   **Synchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        --database my_new_db "SELECT * FROM users;"
    ```

*   **Asynchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        --database my_new_db "SELECT * FROM users WHERE name = 'Alice';" --use-async
    ```

### 5. Delete a Database

To delete the `my_new_db` database.

*   **Synchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        "DROP DATABASE my_new_db;"
    ```

*   **Asynchronous:**
    ```bash
    python -m src.rhosocial.activerecord.backend.impl.mysql \
        --host your_mysql_host --port your_mysql_port --user your_mysql_user --password your_secure_password \
        "DROP DATABASE my_new_db;" --use-async
    ```

## Important Notes

*   **Project Root Execution**: Ensure you execute these commands from the root directory of your `python-activerecord` project (the directory containing the `src` folder) for module path resolution.
*   **Optional Database**: The `--database` argument is optional. If you need to perform operations like `CREATE DATABASE` or `SHOW DATABASES` that don't target a specific existing database, you can omit `--database` or specify a system database like `mysql`.
*   **Environment Variables**: Connection parameters can be set via environment variables (e.g., `MYSQL_HOST`). Command-line arguments will override environment variables if both are provided. Refer to the "Using Environment Variables for Connection Parameters" section for platform-specific instructions.
*   **Error Handling**: The script includes basic error handling for connection and query issues.
*   **Logging**: Adjust the `--log-level` to `DEBUG` for more verbose output during execution.
*   **Query Parameter**: The SQL query is now a **positional argument** and should be placed at the end of the command after all optional flags. Always wrap your SQL query in quotes to ensure it's passed as a single argument.