# src/rhosocial/activerecord/backend/impl/mysql/async_backend.py
"""
Asynchronous MySQL-specific implementation of the AsyncStorageBackend.

This module provides the concrete async implementation for interacting with MySQL databases,
handling connections, queries, transactions, and type adaptations tailored for MySQL's
specific behaviors and SQL dialect. The async backend mirrors the functionality of
the synchronous backend but uses async/await for I/O operations.
"""
import datetime
import logging
from typing import List, Optional, Tuple

import mysql.connector.aio as mysql_async
from mysql.connector.errors import (
    DatabaseError as MySQLDatabaseError,
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
    OperationalError as MySQLOperationalError,
)

from rhosocial.activerecord.backend.base import AsyncStorageBackend
from rhosocial.activerecord.backend.errors import (
    ConnectionError,
    DatabaseError,
    DeadlockError,
    IntegrityError,
    OperationalError,
    QueryError,
)
from rhosocial.activerecord.backend.result import QueryResult
from rhosocial.activerecord.backend.introspection.backend_mixin import IntrospectorBackendMixin
from rhosocial.activerecord.backend.explain import AsyncExplainBackendMixin
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect
from .async_transaction import AsyncMySQLTransactionManager
from .mixins import MySQLBackendMixin


class AsyncMySQLBackend(AsyncExplainBackendMixin, IntrospectorBackendMixin, MySQLBackendMixin, AsyncStorageBackend):
    """Asynchronous MySQL-specific backend implementation."""

    def __init__(self, **kwargs):
        """Initialize async MySQL backend with connection configuration.

        Args:
            version: Expected MySQL server version tuple (major, minor, patch).
                    Used for dialect and type adapter initialization.
                    Defaults to (8, 0, 0). Can be passed as 'version' in kwargs.
        """
        # Extract version from kwargs if provided
        version = kwargs.pop('version', None) or (8, 0, 0)

        # Ensure we have proper MySQL configuration
        connection_config = kwargs.get('connection_config')

        if connection_config is None:
            # Extract MySQL-specific parameters from kwargs
            config_params = {}
            mysql_specific_params = [
                'host', 'port', 'database', 'username', 'password',
                'charset', 'collation', 'timezone', 'version',
                'pool_size', 'pool_timeout', 'pool_name', 'pool_reset_session', 'pool_pre_ping',
                'ssl_ca', 'ssl_cert', 'ssl_key', 'ssl_verify_cert', 'ssl_verify_identity',
                'log_queries', 'log_level',
                'auth_plugin', 'autocommit', 'init_command', 'connect_timeout',
                'read_timeout', 'write_timeout', 'use_pure', 'get_warnings',
                'raise_on_warnings', 'buffered', 'raw', 'consume_results',
                'force_ipv6', 'option_files', 'option_groups', 'use_unicode',
                'sql_mode', 'time_zone', 'sql_log_off',
                'compress', 'allow_local_infile', 'conn_attrs', 'client_flags',
                'unix_socket', 'auth_plugin', 'allow_local_infile_in_path', 'dsn'
            ]

            for param in mysql_specific_params:
                if param in kwargs:
                    config_params[param] = kwargs[param]

            # Set defaults if not provided
            if 'charset' not in config_params:
                config_params['charset'] = 'utf8mb4'
            if 'autocommit' not in config_params:
                config_params['autocommit'] = True
            if 'host' not in config_params:
                config_params['host'] = 'localhost'
            if 'port' not in config_params:
                config_params['port'] = 3306

            kwargs['connection_config'] = MySQLConnectionConfig(**config_params)

        super().__init__(**kwargs)

        # Store the expected MySQL server version
        self._version = version
        # Initialize MySQL-specific components (lazy load dialect)
        self._dialect = None
        # Initialize transaction manager with connection (will be set when connected)
        # Pass None for connection initially, it will be updated later
        self._transaction_manager = AsyncMySQLTransactionManager(None, self.logger)

        # Register MySQL-specific type adapters (uses self._version)
        self._register_mysql_adapters()

        self.log(logging.INFO, "AsyncMySQLBackend initialized")

    def _create_introspector(self):
        """Create an AsyncMySQLIntrospector backed by an AsyncIntrospectorExecutor."""
        from rhosocial.activerecord.backend.introspection.executor import AsyncIntrospectorExecutor
        from .introspection import AsyncMySQLIntrospector
        return AsyncMySQLIntrospector(self, AsyncIntrospectorExecutor(self))

    async def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt backend instance to actual server capabilities.

        This method ensures a connection exists, queries the actual MySQL server version,
        and updates the backend's internal state (version, dialect, type adapters) accordingly.
        """
        # Ensure connection exists
        if not self._connection:
            await self.connect()
        actual_version = await self.get_server_version()
        if self._version != actual_version:
            self._version = actual_version
            self._dialect = MySQLDialect(actual_version)
            self._register_mysql_adapters()
            self.log(logging.INFO, f"Adapted to MySQL server version {actual_version}")

    async def connect(self):
        """Establish async connection to MySQL database."""
        try:
            # Prepare connection parameters from config
            conn_params = {
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'user': self.config.username,
                'password': self.config.password,
                'charset': getattr(self.config, 'charset', 'utf8mb4'),
                'autocommit': getattr(self.config, 'autocommit', True),
                'use_unicode': getattr(self.config, 'use_unicode', True),
                'raise_on_warnings': getattr(self.config, 'raise_on_warnings', False),
                'connection_timeout': getattr(self.config, 'connect_timeout', 10),
                'sql_mode': getattr(self.config, 'sql_mode', 'STRICT_TRANS_TABLES'),
            }

            # Add SSL parameters if provided
            if hasattr(self.config, 'ssl_ca'):
                conn_params['ssl_ca'] = self.config.ssl_ca
            if hasattr(self.config, 'ssl_cert'):
                conn_params['ssl_cert'] = self.config.ssl_cert
            if hasattr(self.config, 'ssl_key'):
                conn_params['ssl_key'] = self.config.ssl_key
            if hasattr(self.config, 'ssl_verify_cert'):
                conn_params['ssl_verify_cert'] = self.config.ssl_verify_cert
            if hasattr(self.config, 'ssl_verify_identity'):
                conn_params['ssl_verify_identity'] = self.config.ssl_verify_identity

            # Add additional parameters if they exist in config
            # Only include parameters that are supported by mysql-connector-python aio
            additional_params = [
                'auth_plugin', 'init_command', 'connect_timeout',
                'read_timeout', 'write_timeout', 'use_pure', 'get_warnings',
                'buffered', 'raw', 'compress', 'allow_local_infile', 'conn_attrs',
                'client_flags', 'unix_socket', 'ssl_disabled'
                # Note: Connection pool parameters (pool_name, pool_size,
                # pool_pre_ping, etc.) are not supported by async connector
            ]

            for param in additional_params:
                if hasattr(self.config, param):
                    # Skip pool-related parameters as they're not supported by async connector
                    if param.startswith('pool_'):
                        continue
                    value = getattr(self.config, param)
                    # Only add the parameter if it's not None
                    if value is not None:
                        conn_params[param] = value

            self._connection = await mysql_async.connect(**conn_params)

            # Set additional session settings if specified
            init_command = getattr(self.config, 'init_command', None)
            if init_command:
                cursor = await self._connection.cursor()
                await cursor.execute(init_command)
                await cursor.close()

            self.log(
                logging.INFO,
                f"Connected to MySQL database: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )
        except MySQLError as e:
            self.log(logging.ERROR, f"Failed to connect to MySQL database: {str(e)}")
            raise ConnectionError(f"Failed to connect to MySQL: {str(e)}") from e

    async def disconnect(self):
        """Close async connection to MySQL database."""
        if self._connection:
            conn = self._connection
            self._connection = None  # Clear reference first to prevent recursion
            try:
                # Rollback any active transaction
                if self.transaction_manager.is_active:
                    try:
                        await self.transaction_manager.rollback()
                    except Exception:
                        pass  # Ignore rollback failure during disconnect

                await conn.close()
                self.log(logging.INFO, "Disconnected from MySQL database")
            except (MySQLError, BrokenPipeError, OSError) as e:
                # MySQL 5.6 may raise BrokenPipeError when closing a dead connection
                # after KILL CONNECTION. We treat disconnect as always successful
                # since the reference is already cleared.
                self.log(logging.WARNING, f"Error during disconnection (ignored): {str(e)}")
            except RuntimeError as e:
                # Python 3.8 + mysql-connector-python has a known issue where
                # closing a connection raises RuntimeError during cursor set iteration:
                # "Set changed size during iteration" in mysql/connector/aio/connection.py:672
                # This happens because the cursor set is modified during close().
                # We only catch this specific error to avoid masking other RuntimeError.
                # See: https://bugs.mysql.com/?id=114095
                if "Set changed size during iteration" in str(e):
                    self.log(logging.WARNING, f"Python 3.8 mysql-connector cursor cleanup issue (ignored): {str(e)}")
                else:
                    # Re-raise other RuntimeError instances
                    raise

    async def _get_cursor(self):
        """Get a database cursor, ensuring connection is active.

        This method implements automatic connection health checking (Plan A):
        - Checks if connection object exists
        - Checks if connection is still valid using is_connected()
        - Automatically reconnects if connection was lost
        """
        if not self._connection:
            self.log(logging.DEBUG, "No connection, connecting...")
            await self.connect()
        else:
            # Protect is_connected() call - may raise BrokenPipeError in MySQL 5.6
            try:
                is_connected = await self._connection.is_connected()
            except (BrokenPipeError, OSError):
                is_connected = False

            if not is_connected:
                self.log(logging.DEBUG, "Connection lost, reconnecting...")
                await self.disconnect()
                await self.connect()

        return await self._connection.cursor()


    async def execute_many(self, sql: str, params_list: List[Tuple]) -> QueryResult:
        """Execute the same SQL statement multiple times with different parameters asynchronously."""
        if not self._connection:
            await self.connect()

        cursor = None
        start_time = datetime.datetime.now()

        try:
            cursor = await self._get_cursor()

            # Log the batch operation if logging is enabled
            if getattr(self.config, 'log_queries', False):
                self.log(logging.DEBUG, f"Executing batch operation: {sql}")
                self.log(logging.DEBUG, f"With {len(params_list)} parameter sets")

            # Execute multiple statements
            affected_rows = 0
            for params in params_list:
                # Convert '?' placeholders to '%s' for MySQL
                mysql_sql = sql.replace('?', '%s')
                await cursor.execute(mysql_sql, params)
                affected_rows += cursor.rowcount

            duration = (datetime.datetime.now() - start_time).total_seconds()

            result = QueryResult(
                affected_rows=affected_rows,
                data=None,
                duration=duration
            )

            self.log(
                logging.INFO,
                f"Batch operation completed, affected {affected_rows} rows, "
                f"duration={duration:.3f}s"
            )
            return result

        except MySQLIntegrityError as e:
            self.log(logging.ERROR, f"Integrity error in batch: {str(e)}")
            raise IntegrityError(str(e)) from e
        except MySQLError as e:
            self.log(logging.ERROR, f"MySQL error in batch: {str(e)}")
            raise DatabaseError(str(e)) from e
        except Exception as e:
            self.log(logging.ERROR, f"Unexpected error during batch execution: {str(e)}")
            raise QueryError(str(e)) from e
        finally:
            if cursor:
                await cursor.close()

    async def get_server_version(self) -> tuple:
        """Get MySQL server version asynchronously."""
        if not self._connection:
            await self.connect()

        cursor = None
        try:
            cursor = await self._get_cursor()
            await cursor.execute("SELECT VERSION()")
            version_row = await cursor.fetchone()
            version_str = version_row[0] if version_row else "8.0.0"

            # Parse version string (e.g., "8.0.26" or "8.0.26-log")
            version_clean = version_str.split('-')[0]  # Remove suffix like "-log"
            version_parts = version_clean.split('.')

            major = int(version_parts[0]) if len(version_parts) > 0 else 0
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            patch = int(version_parts[2]) if len(version_parts) > 2 else 0

            version_tuple = (major, minor, patch)

            self.log(logging.INFO, f"MySQL server version: {major}.{minor}.{patch}")
            return version_tuple
        except Exception as e:
            self.log(logging.WARNING, f"Could not determine MySQL version: {str(e)}, defaulting to 8.0.0")
            return (8, 0, 0)  # Default to a recent version
        finally:
            if cursor:
                await cursor.close()

    async def ping(self, reconnect: bool = True) -> bool:
        """
        Ping the MySQL server to check if the connection is alive.

        Args:
            reconnect: If True, attempt to reconnect if the connection is dead.
                      If False, just return the current connection status.

        Returns:
            True if the connection is alive (or was successfully reconnected),
            False if the connection is dead and reconnect is False or reconnection failed.
        """
        try:
            if not self._connection:
                if reconnect:
                    await self.connect()
                    return True
                else:
                    return False

            # Check connection status without triggering auto-reconnect
            # Note: is_connected() may raise BrokenPipeError/OSError in MySQL 5.6 +
            # mysql-connector-python 9.x when connection has been killed
            try:
                is_connected = await self._connection.is_connected()
            except (BrokenPipeError, OSError):
                is_connected = False

            if not is_connected:
                if reconnect:
                    await self.disconnect()
                    await self.connect()
                    return True
                else:
                    return False

            # When reconnect=False, don't send SELECT 1 to avoid potential
            # BrokenPipeError in MySQL 5.6 RST race condition.
            # Just trust the is_connected() result.
            if not reconnect:
                return True

            # reconnect=True: verify connection with SELECT 1
            try:
                cursor = await self._get_cursor()
                await cursor.execute("SELECT 1")
                await cursor.fetchone()
                await cursor.close()
                return True
            except (BrokenPipeError, OSError):
                # May occur in MySQL 5.6 RST race condition or asyncio transport
                if reconnect:
                    await self.disconnect()
                    await self.connect()
                    return True
                return False

        except (MySQLError, OSError) as e:
            self.log(logging.WARNING, f"MySQL connection ping failed: {str(e)}")
            if reconnect:
                try:
                    await self.disconnect()
                    await self.connect()
                    return True
                except Exception as connect_error:
                    self.log(logging.ERROR, f"Failed to reconnect after ping failure: {str(connect_error)}")
                    return False
            return False

    # MySQL connection error codes that indicate connection loss
    # Reference: https://dev.mysql.com/doc/mysql-errors/8.0/en/server-error-reference.html
    CONNECTION_ERROR_CODES = {
        2003,  # CR_CONN_HOST_ERROR - Can't connect to MySQL server
        2006,  # CR_SERVER_GONE_ERROR - MySQL server has gone away
        2013,  # CR_SERVER_LOST - Lost connection to MySQL server during query
        2048,  # CR_CONN_UNKNOW_PROTOCOL - Invalid connection protocol
        2055,  # CR_SERVER_LOST_EXTENDED - Lost connection to MySQL server
    }

    def _is_connection_error(self, error: Exception) -> bool:
        """
        Check if an error indicates a connection loss.

        This method identifies errors that result from lost or invalid connections,
        which should trigger automatic reconnection attempts.

        Args:
            error: The exception to check

        Returns:
            True if the error indicates a connection problem, False otherwise
        """
        # Check for MySQL error codes
        if hasattr(error, 'errno'):
            if error.errno in self.CONNECTION_ERROR_CODES:
                return True

        # Fallback to string matching for error messages
        error_str = str(error).lower()
        connection_error_patterns = [
            'server has gone away',
            'lost connection',
            "can't connect to mysql server",
            'connection refused',
            'broken pipe',
            'connection reset',
        ]
        return any(pattern in error_str for pattern in connection_error_patterns)

    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect to the MySQL server.

        This method safely disconnects and reconnects, handling any errors
        that might occur during the process.

        Returns:
            True if reconnection was successful, False otherwise
        """
        try:
            self.log(logging.INFO, "Attempting to reconnect...")
            await self.disconnect()
            await self.connect()
            self.log(logging.INFO, "Reconnection successful")
            return True
        except Exception as e:
            self.log(logging.ERROR, f"Reconnection failed: {str(e)}")
            return False

    async def execute(self, sql: str, params: Optional[Tuple] = None, *, options, max_retries: int = 2) -> 'QueryResult':
        """
        Execute a SQL statement with automatic reconnection on connection errors.

        This method extends the parent execute method with retry logic for connection
        errors. If a connection error occurs during execution, it will automatically
        attempt to reconnect and retry the query up to max_retries times.

        This implements Plan B: Error retry mechanism for handling connection loss
        that occurs mid-query (which Plan A's pre-check cannot prevent).

        Args:
            sql: The SQL statement to execute
            params: Optional tuple of parameter values
            options: ExecutionOptions object
            max_retries: Maximum number of retry attempts (default: 2)

        Returns:
            QueryResult object containing execution results

        Raises:
            DatabaseError: If execution fails after all retries
            Other exceptions from parent execute method
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await super().execute(sql, params, options=options)
            except (MySQLOperationalError, MySQLError) as e:
                last_error = e

                # Check if this is a connection error that warrants retry
                if self._is_connection_error(e) and attempt < max_retries:
                    self.log(
                        logging.WARNING,
                        f"Connection error on attempt {attempt + 1}/{max_retries + 1}: {str(e)}"
                    )

                    # Attempt to reconnect
                    if await self._reconnect():
                        # Retry the query
                        continue
                    else:
                        # Reconnection failed, no point in retrying
                        self.log(logging.ERROR, "Reconnection failed, aborting retry")
                        break
                else:
                    # Not a connection error or max retries reached
                    break

        # All retries exhausted or non-connection error
        if last_error:
            await self._handle_error(last_error)

        # This should not be reached, but for type safety
        raise DatabaseError(f"Execution failed after {max_retries + 1} attempts")

    async def _handle_error(self, error: Exception) -> None:
        """Handle MySQL-specific errors asynchronously."""
        error_msg = str(error)

        if isinstance(error, MySQLIntegrityError):
            if "Duplicate entry" in error_msg:
                self.log(logging.ERROR, f"Unique constraint violation: {error_msg}")
                raise IntegrityError(f"Unique constraint violation: {error_msg}")
            elif "Cannot delete or update" in error_msg or "a foreign key constraint fails" in error_msg:
                self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                raise IntegrityError(f"Foreign key constraint violation: {error_msg}")
            self.log(logging.ERROR, f"Integrity error: {error_msg}")
            raise IntegrityError(error_msg)
        elif isinstance(error, MySQLDatabaseError):
            if "Deadlock found" in error_msg:
                self.log(logging.ERROR, f"Deadlock error: {error_msg}")
                raise DeadlockError(error_msg)
            self.log(logging.ERROR, f"Database error: {error_msg}")
            raise DatabaseError(error_msg)
        elif isinstance(error, MySQLOperationalError):
            if "Lock wait timeout exceeded" in error_msg:
                self.log(logging.ERROR, f"Lock timeout error: {error_msg}")
                raise OperationalError(error_msg)
            self.log(logging.ERROR, f"Operational error: {error_msg}")
            raise OperationalError(error_msg)
        elif isinstance(error, MySQLError):
            self.log(logging.ERROR, f"MySQL error: {error_msg}")
            raise DatabaseError(error_msg)
        else:
            self.log(logging.ERROR, f"Unexpected error: {error_msg}")
            raise error

    async def _handle_auto_commit(self) -> None:
        """Handle auto commit based on MySQL connection and transaction state asynchronously.

        This method will commit the current connection if:
        1. The connection exists and is open
        2. There is no active transaction managed by transaction_manager

        It's used by insert/update/delete operations to ensure changes are
        persisted immediately when auto_commit=True is specified.
        """
        try:
            # Check if connection exists
            if not self._connection:
                return

            # Check if we're not in an active transaction
            if not self._transaction_manager or not self._transaction_manager.is_active:
                # For MySQL, if autocommit is disabled, we need to commit explicitly
                if not getattr(self.config, 'autocommit', True):
                    await self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise - this is a convenience feature
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    async def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit for MySQL asynchronously.

        MySQL respects the autocommit setting, but we also need to handle explicit commits.
        """
        if not self.in_transaction and self._connection:
            if not getattr(self.config, 'autocommit', True):
                await self._connection.commit()
                self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")

    async def execute(self, sql: str, params: Optional[Tuple] = None, *, options=None, **kwargs) -> QueryResult:
        """Execute a SQL statement with optional parameters asynchronously."""
        from rhosocial.activerecord.backend.options import ExecutionOptions, StatementType

        # If no options provided, create default options from kwargs
        if options is None:
            # Determine statement type based on SQL
            sql_upper = sql.strip().upper()
            if sql_upper.startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'PRAGMA', 'EXPLAIN')):
                stmt_type = StatementType.DQL
            elif sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE')):
                stmt_type = StatementType.DML
            else:
                stmt_type = StatementType.DDL

            # Extract column_mapping and column_adapters from kwargs if present
            column_mapping = kwargs.get('column_mapping')
            column_adapters = kwargs.get('column_adapters')

            options = ExecutionOptions(
                stmt_type=stmt_type,
                process_result_set=None,  # Let the base logic determine this based on stmt_type
                column_adapters=column_adapters,
                column_mapping=column_mapping
            )
        else:
            # If options is provided but column_mapping or column_adapters are explicitly passed in kwargs,
            # update the options with these values
            if 'column_mapping' in kwargs:
                options.column_mapping = kwargs['column_mapping']
            if 'column_adapters' in kwargs:
                options.column_adapters = kwargs['column_adapters']

        # Convert '?' placeholders to '%s' for MySQL
        if params:
            mysql_sql = sql.replace('?', '%s')
            return await super().execute(mysql_sql, params, options=options)
        else:
            return await super().execute(sql, params, options=options)

    async def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script asynchronously.

        Splits the script on semicolons and executes each non-empty statement
        individually, which is compatible with aiomysql's cursor interface.

        Args:
            sql_script: A string containing one or more SQL statements separated
                       by semicolons.
        """
        import time

        self.log(logging.INFO, "Executing SQL script asynchronously.")
        start_time = time.perf_counter()

        if not self._connection:
            await self.connect()

        cursor = None
        try:
            cursor = await self._connection.cursor()

            # Split on semicolons and execute each statement individually.
            # aiomysql does not support multi=True like mysql-connector-python.
            for stmt in sql_script.split(";"):
                stmt = stmt.strip()
                if stmt:
                    await cursor.execute(stmt)
                    if cursor.description:
                        await cursor.fetchall()

            duration = time.perf_counter() - start_time
            self.log(logging.INFO, f"Async SQL script executed successfully, duration={duration:.3f}s")

        except MySQLError as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            await self._handle_error(e)
        finally:
            if cursor:
                await cursor.close()

    def _parse_explain_result(self, raw_rows, sql, duration):
        """Return a typed :class:`MySQLExplainResult` for MySQL's tabular EXPLAIN output."""
        from .explain import MySQLExplainResult, MySQLExplainRow
        rows = [MySQLExplainRow(**r) for r in raw_rows]
        return MySQLExplainResult(raw_rows=raw_rows, sql=sql, duration=duration, rows=rows)