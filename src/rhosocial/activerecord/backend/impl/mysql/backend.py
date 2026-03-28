# src/rhosocial/activerecord/backend/impl/mysql/backend.py
"""
MySQL-specific implementation of the StorageBackend.

This module provides the concrete implementation for interacting with MySQL databases,
handling connections, queries, transactions, and type adaptations tailored for MySQL's
specific behaviors and SQL dialect.
"""
import datetime
import logging
from typing import List, Optional, Tuple

import mysql.connector
from mysql.connector.errors import (
    DatabaseError as MySQLDatabaseError,
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
    OperationalError as MySQLOperationalError,
)

from rhosocial.activerecord.backend.base import StorageBackend
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
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect
from .transaction import MySQLTransactionManager
from .mixins import MySQLBackendMixin


class MySQLBackend(IntrospectorBackendMixin, MySQLBackendMixin, StorageBackend):
    """MySQL-specific backend implementation."""

    def __init__(self, **kwargs):
        """Initialize MySQL backend with connection configuration.

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
                'sql_mode', 'time_zone', 'sql_log_off', 'get_warnings',
                'raise_on_warnings', 'buffered', 'raw', 'consume_results',
                'compress', 'allow_local_infile', 'conn_attrs', 'autocommit',
                'client_flags', 'unix_socket', 'auth_plugin',
                'allow_local_infile_in_path', 'dsn'
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
        self._version = version or (8, 0, 0)
        # Initialize MySQL-specific components (lazy load dialect)
        self._dialect = None
        # Initialize transaction manager with connection (will be set when connected)
        # Pass None for connection initially, it will be updated later
        self._transaction_manager = MySQLTransactionManager(None, self.logger)

        # Register MySQL-specific type adapters (uses self._version)
        self._register_mysql_adapters()

        self.log(logging.INFO, "MySQLBackend initialized")

    def _create_introspector(self):
        """Create a SyncMySQLIntrospector backed by a SyncIntrospectorExecutor."""
        from rhosocial.activerecord.backend.introspection.executor import SyncIntrospectorExecutor
        from .introspection import SyncMySQLIntrospector
        return SyncMySQLIntrospector(self, SyncIntrospectorExecutor(self))

    def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt backend instance to actual server capabilities.

        This method ensures a connection exists, queries the actual MySQL server version,
        and updates the backend's internal state (version, dialect, type adapters) accordingly.
        """
        # Ensure connection exists
        if not self._connection:
            self.connect()
        actual_version = self.get_server_version()
        if self._version != actual_version:
            self._version = actual_version
            self._dialect = MySQLDialect(actual_version)
            self._register_mysql_adapters()
            self.log(logging.INFO, f"Adapted to MySQL server version {actual_version}")

    def connect(self):
        """Establish connection to MySQL database."""
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
                'get_warnings': getattr(self.config, 'get_warnings', False),
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
            # Only include parameters that are supported by mysql.connector
            additional_params = [
                'auth_plugin', 'init_command', 'connect_timeout',
                'read_timeout', 'write_timeout', 'use_pure', 'get_warnings',
                'buffered', 'raw', 'compress', 'allow_local_infile', 'conn_attrs',
                'client_flags', 'unix_socket', 'ssl_disabled'
                # Note: pool_pre_ping is not supported by mysql.connector
            ]

            for param in additional_params:
                if hasattr(self.config, param):
                    # Skip pool-related parameters as they're not supported by mysql.connector
                    if param.startswith('pool_'):
                        continue
                    value = getattr(self.config, param)
                    # Only add the parameter if it's not None
                    if value is not None:
                        conn_params[param] = value

            self._connection = mysql.connector.connect(**conn_params)

            # Set additional session settings if specified
            init_command = getattr(self.config, 'init_command', None)
            if init_command:
                cursor = self._connection.cursor()
                cursor.execute(init_command)
                cursor.close()

            self.log(
                logging.INFO,
                f"Connected to MySQL database: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )
        except MySQLError as e:
            self.log(logging.ERROR, f"Failed to connect to MySQL database: {str(e)}")
            raise ConnectionError(f"Failed to connect to MySQL: {str(e)}") from e

    def disconnect(self):
        """Close connection to MySQL database."""
        if self._connection:
            try:
                # Rollback any active transaction
                if self.transaction_manager.is_active:
                    self.transaction_manager.rollback()
                
                self._connection.close()
                self._connection = None
                self.log(logging.INFO, "Disconnected from MySQL database")
            except MySQLError as e:
                self.log(logging.ERROR, f"Error during disconnection: {str(e)}")
                raise OperationalError(f"Error during MySQL disconnection: {str(e)}") from e

    def _get_cursor(self):
        """Get a database cursor, ensuring connection is active."""
        if not self._connection:
            self.connect()
        
        return self._connection.cursor()


    def execute_many(self, sql: str, params_list: List[Tuple]) -> QueryResult:
        """Execute the same SQL statement multiple times with different parameters."""
        if not self._connection:
            self.connect()
        
        cursor = None
        start_time = datetime.datetime.now()
        
        try:
            cursor = self._get_cursor()
            
            # Log the batch operation if logging is enabled
            if getattr(self.config, 'log_queries', False):
                self.log(logging.DEBUG, f"Executing batch operation: {sql}")
                self.log(logging.DEBUG, f"With {len(params_list)} parameter sets")
            
            # Execute multiple statements
            affected_rows = 0
            for params in params_list:
                cursor.execute(sql, params)
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
                cursor.close()

    def get_server_version(self) -> tuple:
        """Get MySQL server version."""
        if not self._connection:
            self.connect()
        
        cursor = None
        try:
            cursor = self._get_cursor()
            cursor.execute("SELECT VERSION()")
            version_str = cursor.fetchone()[0]
            
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
                cursor.close()

    def ping(self, reconnect: bool = True) -> bool:
        """Ping the MySQL server to check if the connection is alive."""
        try:
            if not self._connection:
                if reconnect:
                    self.connect()
                    return True
                else:
                    return False
            
            # Try to execute a simple query to check connection
            cursor = self._get_cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            return True
        except (MySQLError, mysql.connector.Error) as e:
            self.log(logging.WARNING, f"MySQL connection ping failed: {str(e)}")
            if reconnect:
                try:
                    self.disconnect()
                    self.connect()
                    return True
                except Exception as connect_error:
                    self.log(logging.ERROR, f"Failed to reconnect after ping failure: {str(connect_error)}")
                    return False
            return False

    def _handle_error(self, error: Exception) -> None:
        """Handle MySQL-specific errors."""
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
            self.log(logging.ERROR, f"Operational error: {str(error)}")
            raise OperationalError(error_msg)
        elif isinstance(error, MySQLError):
            self.log(logging.ERROR, f"MySQL error: {error_msg}")
            raise DatabaseError(error_msg)
        else:
            self.log(logging.ERROR, f"Unexpected error: {error_msg}")
            raise error

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on MySQL connection and transaction state.

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
                    self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise - this is a convenience feature
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit for MySQL.

        MySQL respects the autocommit setting, but we also need to handle explicit commits.
        """
        if not self.in_transaction and self._connection:
            if not getattr(self.config, 'autocommit', True):
                self._connection.commit()
                self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")

    def execute(self, sql: str, params: Optional[Tuple] = None, *, options=None, **kwargs) -> QueryResult:
        """Execute a SQL statement with optional parameters."""
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
            return super().execute(mysql_sql, params, options=options)
        else:
            return super().execute(sql, params, options=options)

    def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script.

        Handles mysql-connector-python version differences:
        - 9.2.0+: Uses execute() + nextset() (multi parameter removed)
        - < 9.2.0: Uses execute(sql, multi=True)

        Args:
            sql_script: A string containing one or more SQL statements separated
                       by semicolons.
        """
        import time
        import mysql.connector

        self.log(logging.INFO, "Executing SQL script.")
        start_time = time.perf_counter()

        if not self._connection:
            self.connect()

        cursor = None
        try:
            cursor = self._connection.cursor()

            # Check mysql-connector-python version for API compatibility
            # Version 9.2.0+ removed the 'multi' parameter
            version = mysql.connector.version.VERSION
            use_new_api = version >= (9, 2, 0)

            if use_new_api:
                # 9.2.0+: Execute directly, use nextset() for multiple result sets
                cursor.execute(sql_script)
                # Consume all result sets
                if cursor.with_rows:
                    cursor.fetchall()
                while cursor.nextset():
                    if cursor.with_rows:
                        cursor.fetchall()
            else:
                # < 9.2.0: Use multi=True parameter
                results = cursor.execute(sql_script, multi=True)
                for result in results:
                    if result.with_rows:
                        result.fetchall()

            duration = time.perf_counter() - start_time
            self.log(logging.INFO, f"SQL script executed successfully, duration={duration:.3f}s")

        except MySQLError as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            self._handle_error(e)
        finally:
            if cursor:
                cursor.close()