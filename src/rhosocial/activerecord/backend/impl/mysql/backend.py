import logging
import time
from typing import Optional, Tuple, List, Dict

import mysql.connector
from mysql.connector.errors import (
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
    ProgrammingError,
    OperationalError as MySQLOperationalError,
    DatabaseError as MySQLDatabaseError,
)

from .dialect import MySQLDialect, SQLDialectBase, MySQLSQLBuilder
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
from ...typing import QueryResult, ConnectionConfig


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

        self._dialect = MySQLDialect(self.config)

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
                    # 仅记录错误，不抛出异常
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

    def execute(self,
                sql: str,
                params: Optional[Tuple] = None,
                returning: bool = False,
                column_types: Optional[ColumnTypes] = None,
                returning_columns: Optional[List[str]] = None,
                force_returning: bool = False) -> Optional[QueryResult]:
        """Execute SQL statement with optional RETURNING clause

        Args:
            sql: SQL statement
            params: Query parameters
            returning: Controls result fetching behavior:
                - For SELECT/EXPLAIN: True to fetch results (default), False to skip fetching
                - For DML: True to use RETURNING clause (not supported in MySQL)
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return. None means all columns.
                Only used when returning=True for DML statements.
            force_returning: Not used in MySQL (always ignored)

        Returns:
            QueryResult: Query result containing:
                - data: Result set if SELECT or query with result
                - affected_rows: Number of affected rows
                - last_insert_id: Last inserted row ID
                - duration: Query execution time

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
            ConnectionError: Database connection error
            QueryError: SQL syntax error
            DatabaseError: Other database errors
        """
        start_time = time.perf_counter()

        # Log query with parameters
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")

        try:
            # Ensure active connection
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            # Parse statement type
            stmt_type = sql.strip().split(None, 1)[0].upper()
            is_query = stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC")
            is_dml = stmt_type in ("INSERT", "UPDATE", "DELETE")
            need_returning = returning and is_dml

            # Check if this is a JOIN query - this is key to handling column name conflicts
            is_join_query = is_query and "JOIN" in sql.upper()

            # Only raise ReturningNotSupportedError for DML statements with returning=True
            if need_returning:
                handler = self.dialect.returning_handler
                if not handler.is_supported:
                    error_msg = (
                        "RETURNING clause is not supported by MySQL. This is a fundamental "
                        "limitation of the database engine, not a driver issue."
                    )
                    self.log(logging.WARNING, error_msg)
                    raise ReturningNotSupportedError(error_msg)

            # Get cursor - for JOIN queries, use regular cursor rather than dictionary
            if is_join_query:
                cursor = self._cursor or self._connection.cursor()
            else:
                cursor = self._cursor or self._connection.cursor(dictionary=True)

            # Process SQL and parameters
            final_sql, final_params = self.build_sql(sql, params)
            self.log(logging.DEBUG, f"Processed SQL: {final_sql}")

            # Convert parameters if needed
            if final_params:
                processed_params = tuple(
                    self.dialect.value_mapper.to_database(value, None)
                    for value in final_params
                )
            else:
                processed_params = None

            # Execute query
            cursor.execute(final_sql, processed_params)

            # Handle result set - for SELECT or other queries with results
            data = None
            if returning and is_query:  # Only fetch data for queries when returning=True
                if is_join_query:
                    # Special handling for JOIN queries to prevent column overwriting
                    # Get column information from cursor description
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    row_count = len(rows) if rows else 0
                    self.log(logging.DEBUG, f"Fetched {row_count} rows")

                    # Create dictionaries with proper handling of same-name columns
                    data = []
                    for row in rows:
                        # Start with empty dictionary for this row
                        row_dict = {}

                        # For each column value, ensure we don't overwrite non-NULL values with NULL
                        for i, value in enumerate(row):
                            col_name = columns[i]

                            # If column name already exists and current value is NULL, don't overwrite
                            if col_name in row_dict and value is None:
                                continue
                            # If column already exists but has NULL and new value is not NULL, replace
                            elif col_name in row_dict and row_dict[col_name] is None and value is not None:
                                row_dict[col_name] = value
                            # If column doesn't exist yet, just add it
                            elif col_name not in row_dict:
                                row_dict[col_name] = value
                            # If both values are non-NULL, keep the first one and add the second with suffix
                            elif col_name in row_dict and row_dict[col_name] is not None and value is not None:
                                # Find a unique suffix
                                suffix = 1
                                new_name = f"{col_name}_{suffix}"
                                while new_name in row_dict:
                                    suffix += 1
                                    new_name = f"{col_name}_{suffix}"
                                row_dict[new_name] = value

                        # Add type conversions if needed
                        if column_types:
                            for key, value in list(row_dict.items()):
                                db_type = column_types.get(key)
                                if db_type is not None and value is not None:
                                    row_dict[key] = self.dialect.value_mapper.from_database(value, db_type)

                        data.append(row_dict)
                else:
                    # Standard handling for non-JOIN queries
                    rows = cursor.fetchall()
                    row_count = len(rows) if rows else 0
                    self.log(logging.DEBUG, f"Fetched {row_count} rows")

                    if column_types:
                        # Apply type conversions
                        self.log(logging.DEBUG, "Applying type conversions")
                        if isinstance(rows[0], dict) if rows else False:
                            # Handle dictionary rows
                            data = []
                            for row in rows:
                                converted_row = {}
                                for key, value in row.items():
                                    db_type = column_types.get(key)
                                    if db_type is not None:
                                        converted_row[key] = (
                                            self.dialect.value_mapper.from_database(
                                                value, db_type
                                            )
                                        )
                                    else:
                                        converted_row[key] = value
                                data.append(converted_row)
                        else:
                            # Handle tuple rows
                            columns = [desc[0] for desc in cursor.description]
                            data = []
                            for row in rows:
                                converted_row = {}
                                for i, value in enumerate(row):
                                    key = columns[i]
                                    db_type = column_types.get(key)
                                    if db_type is not None:
                                        converted_row[key] = (
                                            self.dialect.value_mapper.from_database(
                                                value, db_type
                                            )
                                        )
                                    else:
                                        converted_row[key] = value
                                data.append(converted_row)
                    else:
                        # No type conversion needed
                        if isinstance(rows[0], dict) if rows else False:
                            data = rows
                        else:
                            # Convert tuple rows to dictionaries
                            columns = [desc[0] for desc in cursor.description]
                            data = [dict(zip(columns, row)) for row in rows]

            duration = time.perf_counter() - start_time

            # Log completion metrics
            if is_dml:
                self.log(logging.INFO,
                         f"{stmt_type} affected {cursor.rowcount} rows, "
                         f"last_insert_id={cursor.lastrowid}, duration={duration:.3f}s"
                         )
            elif is_query:
                row_count = len(data) if data is not None else 0
                self.log(logging.INFO, f"{stmt_type} returned {row_count} rows, duration={duration:.3f}s")

            # Build result
            result = QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=duration
            )

            return result

        except MySQLError as e:
            self.log(logging.ERROR, f"MySQL error: {str(e)}")
            self._handle_error(e)

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
                        self.dialect.value_mapper.to_database(value, None)
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
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None,
               force_returning: bool = False,
               auto_commit: bool = True) -> QueryResult:
        """Insert record

        Note on RETURNING support:
        When using SQLite backend with Python <3.10, RETURNING clause has known issues:
        - affected_rows always returns 0
        - last_insert_id may be unreliable
        Use force_returning=True to override this limitation if you understand the consequences.
        This limitation is specific to SQLite backend and does not affect other backends.

        Args:
            table: Table name
            data: Data to insert
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.
            force_returning: If True, allows RETURNING clause in SQLite with Python <3.10
                despite known limitations. Has no effect with other database backends.
            auto_commit: If True and autocommit is disabled and not in active transaction,
                         automatically commit after operation. Default is True.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
                or Python version (SQLite with Python <3.10)
        """
        # Clean field names by stripping quotes - maintaining backward compatibility
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        # Use dialect's format_identifier to ensure correct quoting
        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = [self.value_mapper.to_database(v, column_types.get(k.strip('"').strip('`')) if column_types else None)
                  for k, v in data.items()]
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        # Clean returning columns by stripping quotes if specified
        if returning_columns:
            returning_columns = [col.strip('"').strip('`') for col in returning_columns]

        # Execute query and get result
        result = self.execute(sql, tuple(values), returning, column_types, returning_columns, force_returning)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit()

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
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None,
               force_returning: bool = False,
               auto_commit: bool = True) -> QueryResult:
        """Update record

        Note on RETURNING support:
        When using SQLite backend with Python <3.10, RETURNING clause has known issues:
        - affected_rows always returns 0
        - last_insert_id may be unreliable
        Use force_returning=True to override this limitation if you understand the consequences.
        This limitation is specific to SQLite backend and does not affect other backends.

        Args:
            table: Table name
            data: Data to update
            where: WHERE condition
            params: WHERE condition parameters
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.
            force_returning: If True, allows RETURNING clause in SQLite with Python <3.10
                despite known limitations. Has no effect with other database backends.
            auto_commit: If True and autocommit is disabled and not in active transaction,
                         automatically commit after operation. Default is True.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
                or Python version (SQLite with Python <3.10)
        """
        # Clean field names and use correct dialect formatting
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        # Use dialect's format_identifier to ensure correct quoting for column names
        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in cleaned_data.keys()]

        values = [self.value_mapper.to_database(v, column_types.get(k.strip('"').strip('`')) if column_types else None)
                  for k, v in data.items()]

        sql = f"UPDATE {table} SET {', '.join(set_items)} WHERE {where}"

        result = self.execute(sql, tuple(values) + params, returning, column_types, returning_columns, force_returning)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit()

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
                return default_version
            else:
                # Raise the exception
                raise Exception(error_msg)