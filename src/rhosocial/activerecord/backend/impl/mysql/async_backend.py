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
from typing import Dict, List, Optional, Tuple, Type, Union

import mysql.connector.aio as mysql_async
from mysql.connector.errors import (
    DatabaseError as MySQLDatabaseError,
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
    OperationalError as MySQLOperationalError,
    ProgrammingError,
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
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.result import QueryResult
from .adapters import (
    MySQLBlobAdapter,
    MySQLBooleanAdapter,
    MySQLDateAdapter,
    MySQLDatetimeAdapter,
    MySQLDecimalAdapter,
    MySQLEnumAdapter,
    MySQLJSONAdapter,
    MySQLTimeAdapter,
    MySQLUUIDAdapter,
)
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect
from .async_transaction import AsyncMySQLTransactionManager


class AsyncMySQLBackend(AsyncStorageBackend):
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

    def _register_mysql_adapters(self):
        """Register MySQL-specific type adapters."""
        mysql_adapters = [
            MySQLBlobAdapter(),
            MySQLBooleanAdapter(),
            MySQLDateAdapter(),
            MySQLDatetimeAdapter(self._version),
            MySQLDecimalAdapter(),
            MySQLEnumAdapter(use_int_storage=False),  # Default to string representation
            MySQLJSONAdapter(),
            MySQLTimeAdapter(),
            MySQLUUIDAdapter(),
        ]

        for adapter in mysql_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    # Use allow_override=True to allow re-registration with updated version
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)

        self.log(logging.DEBUG, "Registered MySQL-specific type adapters")

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

    @property
    def dialect(self):
        """Get the MySQL dialect instance (lazy loads with configured version)."""
        if self._dialect is None:
            self._dialect = MySQLDialect(self._version)
        return self._dialect

    @property
    def transaction_manager(self):
        """Get the async MySQL transaction manager."""
        # Update the transaction manager's connection if needed
        if self._transaction_manager:
            self._transaction_manager._connection = self._connection
        return self._transaction_manager

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
                # Note: Connection pool parameters (pool_name, pool_size, pool_pre_ping, etc.) are not supported by async connector
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

            self.log(logging.INFO, f"Connected to MySQL database: {self.config.host}:{self.config.port}/{self.config.database}")
        except mysql_async.Error as e:
            self.log(logging.ERROR, f"Failed to connect to MySQL database: {str(e)}")
            raise ConnectionError(f"Failed to connect to MySQL: {str(e)}")

    async def disconnect(self):
        """Close async connection to MySQL database."""
        if self._connection:
            try:
                # Rollback any active transaction
                if self.transaction_manager.is_active:
                    await self.transaction_manager.rollback()

                await self._connection.close()
                self._connection = None
                self.log(logging.INFO, "Disconnected from MySQL database")
            except mysql_async.Error as e:
                self.log(logging.ERROR, f"Error during disconnection: {str(e)}")
                raise OperationalError(f"Error during MySQL disconnection: {str(e)}")

    async def _get_cursor(self):
        """Get a database cursor, ensuring connection is active."""
        if not self._connection:
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

            self.log(logging.INFO, f"Batch operation completed, affected {affected_rows} rows, duration={duration:.3f}s")
            return result

        except MySQLIntegrityError as e:
            self.log(logging.ERROR, f"Integrity error in batch: {str(e)}")
            raise IntegrityError(str(e))
        except MySQLError as e:
            self.log(logging.ERROR, f"MySQL error in batch: {str(e)}")
            raise DatabaseError(str(e))
        except Exception as e:
            self.log(logging.ERROR, f"Unexpected error during batch execution: {str(e)}")
            raise QueryError(str(e))
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

    def requires_manual_commit(self) -> bool:
        """Check if manual commit is required for this database."""
        return not getattr(self.config, 'autocommit', True)

    def _check_returning_compatibility(self, returning_clause):
        """Check if RETURNING clause is compatible with this MySQL version."""
        # MySQL does not support RETURNING clause
        if self.dialect.supports_returning_clause():
            return True
        else:
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                "MySQL does not support RETURNING clause. "
                "Consider using LAST_INSERT_ID() or alternative approaches."
            )

    async def ping(self, reconnect: bool = True) -> bool:
        """Ping the MySQL server to check if the connection is alive."""
        try:
            if not self._connection:
                if reconnect:
                    await self.connect()
                    return True
                else:
                    return False

            # Try to execute a simple query to check connection
            cursor = await self._get_cursor()
            await cursor.execute("SELECT 1")
            await cursor.fetchone()
            await cursor.close()

            return True
        except (mysql_async.Error) as e:
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
        elif isinstance(error, mysql_async.Error):
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

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple['SQLTypeAdapter', Type]]:
        """
        [Backend Implementation] Provides default type adapter suggestions for MySQL.

        This method defines a curated set of type adapter suggestions for common Python
        types, mapping them to their typical MySQL-compatible representations as
        demonstrated in test fixtures. It explicitly retrieves necessary `SQLTypeAdapter`
        instances from the backend's `adapter_registry`. If an adapter for a specific
        (Python type, DB driver type) pair is not registered, no suggestion will be
        made for that Python type.

        Returns:
            Dict[Type, Tuple[SQLTypeAdapter, Type]]: A dictionary where keys are
            original Python types (`TypeRegistry`'s `py_type`), and values are
            tuples containing a `SQLTypeAdapter` instance and the target
            Python type (`TypeRegistry`'s `db_type`) expected by the driver.
        """
        suggestions: Dict[Type, Tuple['SQLTypeAdapter', Type]] = {}

        # Define a list of desired Python type to DB driver type mappings.
        # This list reflects types seen in test fixtures and common usage,
        # along with their preferred database-compatible Python types for the driver.
        # Types that are natively compatible with the DB driver (e.g., Python str, int, float)
        # and for which no specific conversion logic is needed are omitted from this list.
        # The consuming layer should assume pass-through behavior for any Python type
        # that does not have an explicit adapter suggestion.
        #
        # Exception: If a user requires specific processing for a natively compatible type
        # (e.g., custom serialization/deserialization for JSON strings beyond basic conversion),
        # they would need to implement and register their own specialized adapter.
        # This backend's default suggestions do not cater to such advanced processing needs.
        from datetime import date, datetime, time
        from decimal import Decimal
        from uuid import UUID
        from enum import Enum

        type_mappings = [
            (bool, int),        # Python bool -> DB driver int (MySQL TINYINT)
            # Why str for date/time?
            # MySQL accepts string representations of dates/times and converts them appropriately.
            (datetime, str),    # Python datetime -> DB driver str (MySQL DATETIME/TIMESTAMP)
            (date, str),        # Python date -> DB driver str (MySQL DATE)
            (time, str),        # Python time -> DB driver str (MySQL TIME)
            (Decimal, float),   # Python Decimal -> DB driver float (MySQL DECIMAL)
            (UUID, str),        # Python UUID -> DB driver str (MySQL CHAR/VARCHAR/BINARY)
            (dict, str),        # Python dict -> DB driver str (MySQL TEXT for JSON)
            (list, str),        # Python list -> DB driver str (MySQL TEXT for JSON)
            (Enum, str),        # Python Enum -> DB driver str (MySQL TEXT/VARCHAR)
        ]

        # Iterate through the defined mappings and retrieve adapters from the registry.
        for py_type, db_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter:
                suggestions[py_type] = (adapter, db_type)
            else:
                # Log a debug message if a specific adapter is expected but not found.
                self.log(logging.DEBUG, f"No adapter found for ({py_type.__name__}, {db_type.__name__}). "
                                      "Suggestion will not be provided for this type.")

        return suggestions

    async def execute(self, sql: str, params: Optional[Tuple] = None, *, options=None, **kwargs) -> QueryResult:
        """Execute a SQL statement with optional parameters asynchronously."""
        from rhosocial.activerecord.backend.options import ExecutionOptions, StatementType
        
        # If no options provided, create default options from kwargs
        if options is None:
            # Determine statement type based on SQL
            sql_upper = sql.strip().upper()
            if sql_upper.startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'PRAGMA')):
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

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, '_logger') and self._logger:
            self._logger.log(level, message)
        else:
            # Fallback logging
            print(f"[{logging.getLevelName(level)}] {message}")