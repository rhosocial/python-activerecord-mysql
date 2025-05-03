import logging
import re
import time
from typing import Optional, Tuple, List, Dict, Union

import mysql.connector
from mysql.connector.errors import (
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
    ProgrammingError,
    OperationalError as MySQLOperationalError,
    DatabaseError as MySQLDatabaseError,
)

from .dialect import MySQLDialect, SQLDialectBase, MySQLSQLBuilder
from .type_converters import MySQLGeometryConverter, MySQLEnumConverter, MySQLUUIDConverter, MySQLDateTimeConverter
from ...dialect import ReturningOptions
from .transaction import MySQLTransactionManager
from ...base import StorageBackend, ColumnTypes
from ...errors import (
    ConnectionError,
    IntegrityError,
    OperationalError,
    QueryError,
    DeadlockError,
    DatabaseError,
    ReturningNotSupportedError
)
from ...typing import QueryResult, ConnectionConfig, DatabaseType


class MySQLBackend(StorageBackend):
    """MySQL storage backend implementation"""

    def __init__(self, **kwargs):
        """Initialize MySQL backend

        Args:
            **kwargs: Connection configuration
                - pool_size: Connection pool size
                - pool_name: Pool name for identification
                - Other standard MySQL connection parameters
        """
        super().__init__(**kwargs)
        self._cursor = None
        self._pool = None
        self._transaction_manager = None
        self._server_version_cache = None

        # Configure MySQL specific settings
        if isinstance(self.config, ConnectionConfig):
            self._connection_args = self._prepare_connection_args(self.config)
        else:
            self._connection_args = kwargs

        # Initialize dialect with a temporary version
        # The actual version will be obtained and updated after connecting to the database
        self._dialect = MySQLDialect(self.config)

        # Register MySQL-specific converters
        self._register_mysql_converters()

        # If version is already provided in config, use it (but will still update with actual version after connection)
        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            self._update_dialect_version(self.config.version)

    def _register_mysql_converters(self):
        """Register MySQL-specific type converters"""
        # Register MySQL geometry converter
        self.dialect.register_converter(MySQLGeometryConverter(),
                                        names=["POINT", "POLYGON", "GEOMETRY", "LINESTRING"],
                                        types=[DatabaseType.POINT, DatabaseType.POLYGON,
                                               DatabaseType.GEOMETRY])

        # Register MySQL enum/set converter
        self.dialect.register_converter(MySQLEnumConverter(),
                                        names=["ENUM", "SET"],
                                        types=[DatabaseType.ENUM, DatabaseType.SET])

        # Register MySQL UUID converter (string mode)
        self.dialect.register_converter(MySQLUUIDConverter(binary_mode=False),
                                        names=["UUID", "CHAR"],
                                        types=[DatabaseType.UUID])

        # Register MySQL UUID binary converter
        self.dialect.register_converter(MySQLUUIDConverter(binary_mode=True),
                                        names=["BINARY"],
                                        types=[])
        
        # Register MySQL DateTime converter
        self.dialect.register_converter(MySQLDateTimeConverter(),
                                        names=["DATETIME", "DATE", "TIME", "TIMESTAMP"],
                                        types=[DatabaseType.DATETIME, DatabaseType.DATE, DatabaseType.TIME, DatabaseType.TIMESTAMP])
        

    def _prepare_connection_args(self, config: ConnectionConfig) -> Dict:
        """Prepare MySQL connection arguments

        Args:
            config: Connection configuration

        Returns:
            Dict: MySQL connection arguments
        """
        args = config.to_dict()

        # Map config parameters to MySQL connector parameters
        param_mapping = {
            'database': 'database',
            'username': 'user',
            'password': 'password',
            'host': 'host',
            'port': 'port',
            'charset': 'charset',
            'ssl_ca': 'ssl_ca',
            'ssl_cert': 'ssl_cert',
            'ssl_key': 'ssl_key',
            'ssl_mode': 'ssl_mode',
            'pool_size': 'pool_size',
            'pool_name': 'pool_name',
            'auth_plugin': 'auth_plugin'
        }

        connection_args = {}
        for config_key, mysql_key in param_mapping.items():
            if config_key in args:
                connection_args[mysql_key] = args[config_key]

        # Add additional options
        connection_args.update({
            'use_pure': True,  # Use pure Python implementation
            'get_warnings': True,  # Enable warning support
            'raise_on_warnings': False,  # Don't raise on warnings
            'connection_timeout': self.config.pool_timeout,
            'time_zone': self.config.timezone or '+00:00'
        })

        # Add pooling configuration if enabled
        if config.pool_size > 0:
            connection_args['pool_name'] = config.pool_name or 'mysql_pool'
            connection_args['pool_size'] = config.pool_size

        return connection_args

    @property
    def dialect(self) -> SQLDialectBase:
        """Get MySQL dialect"""
        return self._dialect

    def connect(self) -> None:
        """Establish connection to MySQL server

        Creates a connection pool if pool_size > 0

        Raises:
            ConnectionError: If connection fails
        """
        # Clear version cache on new connection
        self._server_version_cache = None

        try:
            self.log(logging.INFO, f"Connecting to MySQL server: {self.config.host}:{self.config.port}")

            if self.config.pool_size > 0:
                # Create connection pool
                if not self._pool:
                    self.log(logging.DEBUG, f"Creating connection pool (size: {self.config.pool_size})")
                    self._pool = mysql.connector.pooling.MySQLConnectionPool(
                        **self._connection_args
                    )
                self._connection = self._pool.get_connection()
                self.log(logging.DEBUG, "Got connection from pool")
            else:
                # Create single connection
                self._connection = mysql.connector.connect(
                    **self._connection_args
                )
                self.log(logging.DEBUG, "Created direct connection")

            # Configure session
            cursor = self._connection.cursor()
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cursor.execute("SET SESSION sql_mode = 'STRICT_ALL_TABLES'")
            if self.config.timezone:
                cursor.execute(f"SET time_zone = '{self.config.timezone}'")
            cursor.close()
            self.log(logging.INFO, "Connected to MySQL successfully")

            # Get server version immediately after connecting and update dialect
            self.get_server_version()

        except MySQLError as e:
            error_msg = f"Failed to connect: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise ConnectionError(error_msg)

    def disconnect(self) -> None:
        """Close database connection"""
        # Clear version cache on disconnect
        self._server_version_cache = None

        if self._connection:
            try:
                self.log(logging.INFO, "Disconnecting from MySQL")
                if self._cursor:
                    self._cursor.close()
                    self._cursor = None

                # Rollback any active transaction before closing
                if self._transaction_manager and self._transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    self._transaction_manager.rollback()

                try:
                    self._connection.close()
                    self.log(logging.INFO, "Disconnected from MySQL successfully")
                except MySQLError as e:
                    # Only log errors, don't raise exceptions
                    error_msg = f"Warning during disconnect: {str(e)}"
                    self.log(logging.WARNING, error_msg)
            finally:
                self._connection = None
                self._transaction_manager = None

    def ping(self, reconnect: bool = True) -> bool:
        """Test database connection

        Args:
            reconnect: Whether to attempt reconnection if connection is lost

        Returns:
            bool: True if connection is alive
        """
        if not self._connection:
            self.log(logging.DEBUG, "No active connection during ping")
            if reconnect:
                self.log(logging.INFO, "Reconnecting during ping")
                self.connect()
                return True
            return False

        try:
            self.log(logging.DEBUG, "Pinging MySQL connection")
            self._connection.ping(reconnect=reconnect)
            return True
        except MySQLError as e:
            self.log(logging.WARNING, f"Ping failed: {str(e)}")
            if reconnect:
                self.log(logging.INFO, "Reconnecting after failed ping")
                self.connect()
                return True
            return False

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters for MySQL

        Uses MySQLSQLBuilder to handle MySQL-specific parameter placeholders (%s)

        Args:
            sql: Raw SQL with %s placeholders
            params: SQL parameters

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)
        """
        builder = MySQLSQLBuilder(self.dialect)
        return builder.build(sql, params)

    @property
    def is_mysql(self) -> bool:
        """Flag to identify MySQL backend for compatibility checks"""
        return True

    def _is_select_statement(self, stmt_type: str) -> bool:
        """
        Check if statement is a SELECT-like query.

        MySQL includes additional read-only statements and WITH queries
        that are actually SELECT statements.

        Args:
            stmt_type: Statement type

        Returns:
            bool: True if statement is a read-only query
        """
        return stmt_type in ("SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE", "DESC", "ANALYZE")

    def _get_statement_type(self, sql: str) -> str:
        """
        Parse the SQL statement type from the query.

        MySQL supports special statements and CTEs with WITH (in MySQL 8.0+).

        Args:
            sql: SQL statement

        Returns:
            str: Statement type in uppercase
        """
        # Strip comments and whitespace for better detection
        clean_sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE).strip()

        # Check if SQL is empty after cleaning
        if not clean_sql:
            return ""

        upper_sql = clean_sql.upper()

        # Check for MySQL specific statements
        if upper_sql.startswith('SHOW'):
            return 'SHOW'
        if upper_sql.startswith('SET'):
            return 'SET'
        if upper_sql.startswith('USE'):
            return 'USE'

        # Check for CTE queries (WITH ... SELECT/INSERT/UPDATE/DELETE)
        if upper_sql.startswith('WITH'):
            # Find the main statement type after WITH clause
            for main_type in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                if main_type in upper_sql:
                    # This is a simple approach that works for most cases
                    # More complex cases might need a SQL parser
                    return main_type
            # If no main type found, default to SELECT (most common)
            return 'SELECT'

        # Default to base implementation for other statement types
        return super()._get_statement_type(clean_sql)

    def _prepare_returning_clause(self, sql: str, options: ReturningOptions, stmt_type: str) -> str:
        """
        Prepare RETURNING clause for MySQL - not natively supported.

        This method implements alternative approaches when force=True:
        1. For INSERT, use LAST_INSERT_ID() to emulate basic RETURNING
        2. For UPDATE/DELETE, use user variables to track changes

        Args:
            sql: SQL statement
            options: RETURNING options
            stmt_type: Statement type

        Returns:
            str: SQL statement (without actual RETURNING clause)

        Raises:
            ReturningNotSupportedError: If not forced
        """
        # MySQL doesn't support RETURNING natively
        if not options.force:
            error_msg = (
                "RETURNING clause is not supported by MySQL. "
                "This is a fundamental limitation of the database engine, not a driver issue. "
                "Use force=True to attempt emulation if you understand the limitations."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

        # When force=True, implement alternatives based on statement type
        if stmt_type == "INSERT":
            # For INSERT, we'll use LAST_INSERT_ID() later in _process_result_set
            self._returning_emulation = {
                "type": "insert",
                "options": options,
                "statement": sql
            }

            # Get table name for later use
            match = re.search(r"INSERT\s+INTO\s+`?(\w+)`?", sql, re.IGNORECASE)
            if match:
                self._returning_emulation["table"] = match.group(1)

            # Log warning about limitations
            self.log(logging.WARNING,
                     "MySQL doesn't support RETURNING. Will attempt to emulate using "
                     "LAST_INSERT_ID() which only works reliably for single row inserts "
                     "with auto-increment primary keys.")

        elif stmt_type in ("UPDATE", "DELETE"):
            # For UPDATE/DELETE, we can use session variables to track affected IDs
            # This requires modifying the original query to save affected IDs

            # Extract table name
            table_match = None
            if stmt_type == "UPDATE":
                table_match = re.search(r"UPDATE\s+`?(\w+)`?", sql, re.IGNORECASE)
            else:  # DELETE
                table_match = re.search(r"DELETE\s+FROM\s+`?(\w+)`?", sql, re.IGNORECASE)

            if table_match:
                table_name = table_match.group(1)

                # For simplicity, we'll only support emulation with a primary key named 'id'
                # A more robust implementation would determine the actual primary key column

                # Store information for result processing
                self._returning_emulation = {
                    "type": stmt_type.lower(),
                    "options": options,
                    "table": table_name,
                    "statement": sql
                }

                # Log significant warning
                self.log(logging.WARNING,
                         f"MySQL doesn't support RETURNING for {stmt_type}. Emulation is very "
                         f"limited and requires separate queries. Results may be incomplete.")
            else:
                self.log(logging.ERROR, f"Could not parse table name from {stmt_type} query")

        # Return SQL unchanged - no actual RETURNING clause added
        return sql

    def _get_cursor(self):
        """
        Get or create cursor for MySQL.

        MySQL supports dictionary cursors.

        Returns:
            mysql.connector.cursor: MySQL cursor
        """
        if self._cursor:
            return self._cursor

        # Create cursor with dictionary=True for dict-like access
        cursor = self._connection.cursor(dictionary=True)
        return cursor

    def _process_result_set(self, cursor, is_select: bool, need_returning: bool, column_types: Optional[ColumnTypes]) -> \
    Optional[List[Dict]]:
        """
        Process query result set for MySQL.

        Handle emulated RETURNING functionality when forced.

        Args:
            cursor: MySQL cursor with executed query
            is_select: Whether this is a SELECT query
            need_returning: Whether RETURNING was requested
            column_types: Column type mapping for conversion

        Returns:
            Optional[List[Dict]]: Processed result rows or None
        """
        # For standard SELECT queries, use default processing
        if is_select:
            return super()._process_result_set(cursor, is_select, need_returning, column_types)

        # Handle emulated RETURNING if requested and set up
        if need_returning and hasattr(self, "_returning_emulation"):
            emulation = self._returning_emulation
            emulation_type = emulation.get("type")

            if emulation_type == "insert" and hasattr(cursor, "lastrowid") and cursor.lastrowid:
                # Use LAST_INSERT_ID() to fetch the inserted row
                last_id = cursor.lastrowid
                table = emulation.get("table")

                if table:
                    # Determine columns to fetch
                    options = emulation.get("options")
                    if options and options.columns:
                        column_list = ", ".join([f"`{col}`" for col in options.columns])
                    else:
                        column_list = "*"

                    # Create a new cursor for fetching
                    fetch_cursor = self._connection.cursor(dictionary=True)

                    try:
                        # Fetch the inserted row
                        fetch_sql = f"SELECT {column_list} FROM `{table}` WHERE id = %s"
                        fetch_cursor.execute(fetch_sql, (last_id,))
                        rows = fetch_cursor.fetchall()

                        # Apply type conversions if needed
                        if column_types and rows:
                            result = []
                            for row in rows:
                                converted_row = {}
                                for key, value in row.items():
                                    db_type = column_types.get(key)
                                    if db_type is not None:
                                        converted_row[key] = self.dialect.from_database(value, db_type)
                                    else:
                                        converted_row[key] = value
                                result.append(converted_row)
                            return result

                        return rows or []
                    except Exception as e:
                        self.log(logging.ERROR, f"Error during RETURNING emulation: {str(e)}")
                        # Fall back to empty result set on error
                        return []
                    finally:
                        fetch_cursor.close()
                        return None

            elif emulation_type in ("update", "delete"):
                # For UPDATE/DELETE, emulation is much more complex and limited
                # We would need to have fetched the rows *before* the operation
                # This is just a placeholder for potential implementation
                self.log(logging.WARNING,
                         f"RETURNING emulation for {emulation_type.upper()} "
                         f"is not fully implemented. Returning empty result set.")
                return []

        # No results for non-SELECT without RETURNING
        return None

    def _build_query_result(self, cursor, data: Optional[List[Dict]], duration: float) -> QueryResult:
        """
        Build QueryResult object from execution results.

        Handles MySQL-specific result attributes.

        Args:
            cursor: MySQL cursor
            data: Processed result data
            duration: Query execution duration

        Returns:
            QueryResult: Query result object
        """
        return QueryResult(
            data=data,
            affected_rows=getattr(cursor, 'rowcount', 0),
            last_insert_id=getattr(cursor, 'lastrowid', None),
            duration=duration
        )

    def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit for MySQL.

        MySQL may have autocommit enabled at connection level.
        """
        try:
            # Check if connection exists
            if not self._connection:
                return

            # Check if autocommit is disabled and no active transaction
            if hasattr(self._connection, 'autocommit') and not self._connection.autocommit:
                # Check if we're not in an active transaction
                if not self._transaction_manager or not self._transaction_manager.is_active:
                    self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def _handle_execution_error(self, error: Exception):
        """
        Handle MySQL-specific errors during execution.

        Args:
            error: Exception raised during execution

        Raises:
            Appropriate database exception
        """
        if hasattr(error, 'errno'):
            # Handle MySQL error codes
            code = getattr(error, 'errno', None)
            msg = str(error)

            # Handle common error codes
            if code == 1062:  # Duplicate entry
                self.log(logging.ERROR, f"Unique constraint violation: {msg}")
                raise IntegrityError(f"Unique constraint violation: {msg}")
            elif code == 1452:  # Foreign key constraint fails
                self.log(logging.ERROR, f"Foreign key constraint violation: {msg}")
                raise IntegrityError(f"Foreign key constraint violation: {msg}")
            elif code in (1205, 1213):  # Lock wait timeout, deadlock
                self.log(logging.ERROR, f"Deadlock or lock wait timeout: {msg}")
                raise DeadlockError(msg)

        # Call parent handler for common error processing
        super()._handle_execution_error(error)

    def _handle_error(self, error: Exception) -> None:
        """Handle MySQL specific errors

        Args:
            error: MySQL exception

        Raises:
            Appropriate exception type for the error
        """
        if isinstance(error, MySQLError):
            if isinstance(error, MySQLIntegrityError):
                msg = str(error)
                if "Duplicate entry" in msg:
                    raise IntegrityError(f"Unique constraint violation: {msg}")
                elif "foreign key constraint fails" in msg.lower():
                    raise IntegrityError(f"Foreign key constraint violation: {msg}")
                raise IntegrityError(msg)

            elif isinstance(error, MySQLOperationalError):
                msg = str(error)
                if "Lock wait timeout exceeded" in msg:
                    raise DeadlockError(msg)
                elif "deadlock" in msg.lower():
                    raise DeadlockError(msg)
                raise OperationalError(msg)

            elif isinstance(error, ProgrammingError):
                raise QueryError(str(error))

            elif isinstance(error, MySQLDatabaseError):
                raise DatabaseError(str(error))

        raise error

    def execute_many(
            self,
            sql: str,
            params_list: List[Tuple]
    ) -> Optional[QueryResult]:
        """Execute batch operations

        Args:
            sql: SQL statement
            params_list: List of parameter tuples

        Returns:
            QueryResult: Execution results
        """
        start_time = time.perf_counter()
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._connection.cursor()

            # Convert parameters
            converted_params = []
            for params in params_list:
                if params:
                    converted = tuple(
                        self.dialect.to_database(value, None)
                        for value in params
                    )
                    converted_params.append(converted)

            cursor.executemany(sql, converted_params)
            duration = time.perf_counter() - start_time

            self.log(logging.INFO,
                     f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s"
                     )

            # 同样移除批量操作中的自动提交逻辑
            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )

        except MySQLError as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)
            return None

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on MySQL connection and transaction state.

        This method will commit the current connection if:
        1. Autocommit is disabled for the connection
        2. There is no active transaction managed by transaction_manager

        It's used by insert/update/delete operations to ensure changes are
        persisted immediately when auto_commit=True is specified.
        """
        try:
            # Check if connection exists and has autocommit attribute
            if not self._connection:
                return

            # Check if autocommit is disabled and no active transaction
            if hasattr(self._connection, 'autocommit') and not self._connection.autocommit:
                # Check if we're not in an active transaction
                if not self._transaction_manager or not self._transaction_manager.is_active:
                    self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise - this is a convenience feature
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def insert(self,
               table: str,
               data: Dict,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_types: Optional[ColumnTypes] = None,
               auto_commit: Optional[bool] = True,
               primary_key: Optional[str] = 'id') -> QueryResult:
        """
        Insert record with enhanced RETURNING support.

        Args:
            table: Table name
            data: Data to insert
            returning: Controls RETURNING clause behavior:
                - None: No RETURNING clause
                - bool: Simple RETURNING * if True
                - List[str]: Return specific columns
                - ReturningOptions: Full control over RETURNING options
            column_types: Column type mapping for result type conversion
            auto_commit: If True and not in transaction, auto commit
            primary_key: Primary key column name (optional, not used by this backend)

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING is not supported by MySQL
        """
        # Clean field names by stripping quotes - maintaining MySQL's backtick style
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        # Use dialect's format_identifier to ensure correct MySQL backtick quoting
        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = list(cleaned_data.values())
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        # Execute query and get result
        result = self.execute(sql, tuple(values), returning, column_types)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit_if_needed()

        # If we have returning data, ensure the column names are consistently without quotes
        if returning and result.data:
            cleaned_data = []
            for row in result.data:
                cleaned_row = {
                    k.strip('"').strip('`'): v
                    for k, v in row.items()
                }
                cleaned_data.append(cleaned_row)
            result.data = cleaned_data

        return result

    def update(self,
               table: str,
               data: Dict,
               where: str,
               params: Tuple,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_types: Optional[ColumnTypes] = None,
               auto_commit: bool = True) -> QueryResult:
        """
        Update record with enhanced RETURNING support.

        Args:
            table: Table name
            data: Data to update
            where: WHERE condition
            params: WHERE condition parameters
            returning: Controls RETURNING clause behavior:
                - None: No RETURNING clause
                - bool: Simple RETURNING * if True
                - List[str]: Return specific columns
                - ReturningOptions: Full control over RETURNING options
            column_types: Column type mapping for result type conversion
            auto_commit: If True and not in transaction, auto commit

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING is not supported by MySQL
        """
        # Clean field names and use correct MySQL backtick quoting
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        # Use dialect's format_identifier to ensure correct quoting for column names
        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in cleaned_data.keys()]

        values = [self.dialect.to_database(v, column_types.get(k.strip('"').strip('`')) if column_types else None)
                  for k, v in data.items()]

        sql = f"UPDATE {table} SET {', '.join(set_items)} WHERE {where}"

        # Execute query and get result
        result = self.execute(sql, tuple(values) + params, returning, column_types)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    @property
    def transaction_manager(self) -> MySQLTransactionManager:
        """Get transaction manager

        Returns:
            MySQLTransactionManager: Transaction manager instance
        """
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = MySQLTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    @property
    def supports_returning(self) -> bool:
        """Check if RETURNING is supported

        Returns:
            bool: True if RETURNING clause is supported
        """
        supported = self.dialect.returning_handler.is_supported
        self.log(logging.DEBUG, f"RETURNING clause support: {supported}")
        return supported

    def _update_dialect_version(self, version: tuple) -> None:
        """Update the dialect's version information

        Args:
            version: Database server version tuple (major, minor, patch)
        """
        self._dialect._version = version

        # Also update version information in dialect's handlers
        if hasattr(self._dialect, '_returning_handler'):
            self._dialect._returning_handler._version = version

        if hasattr(self._dialect, '_aggregate_handler'):
            self._dialect._aggregate_handler._version = version

        if hasattr(self._dialect, '_json_operation_handler'):
            self._dialect._json_operation_handler._version = version

    def get_server_version(self, fallback_to_default: bool = False) -> tuple:
        """Get MySQL server version

        Returns version tuple (major, minor, patch) with caching
        to avoid repeated queries. Version is cached per connection.

        Args:
            fallback_to_default: If True, use default version when query fails

        Returns:
            tuple: Server version as (major, minor, patch)

        Raises:
            Exception: If version determination fails and fallback_to_default is False
        """
        # Return cached version if available
        if self._server_version_cache:
            return self._server_version_cache

        # If we have connection config version, use it
        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            # Update dialect's version information
            self._update_dialect_version(self._server_version_cache)
            return self._server_version_cache

        # Otherwise query the server
        try:
            if not self._connection:
                self.connect()

            self.log(logging.DEBUG, "Querying MySQL server version")
            cursor = self._connection.cursor()
            cursor.execute("SELECT VERSION()")
            version_str = cursor.fetchone()[0]
            cursor.close()

            # Parse version string (e.g. "8.0.26" into (8, 0, 26))
            # Handle also strings like "8.0.26-community" or "5.7.36-log"
            version_parts = version_str.split('-')[0].split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            patch = int(version_parts[2]) if len(version_parts) > 2 else 0

            # Cache the result
            self._server_version_cache = (major, minor, patch)

            # Update dialect's version information
            self._update_dialect_version(self._server_version_cache)

            self.log(logging.INFO, f"Detected MySQL version: {major}.{minor}.{patch}")
            return self._server_version_cache

        except Exception as e:
            # Log the error
            error_msg = f"Failed to determine MySQL version: {str(e)}"
            self.log(logging.ERROR, error_msg)

            if fallback_to_default:
                # Use default version while logging a warning
                default_version = (8, 0, 0)
                self.log(logging.WARNING,
                         f"Using default MySQL version {default_version} instead of actual version"
                         )
                self._server_version_cache = default_version

                # Update dialect's version information
                self._update_dialect_version(default_version)

                return default_version
            else:
                # Raise the exception
                raise Exception(error_msg)