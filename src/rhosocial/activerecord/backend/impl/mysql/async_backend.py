# src/rhosocial/activerecord/backend/impl/mysql/async_backend.py
"""
Asynchronous MySQL backend implementation using mysql-connector-python's async functionality.

This module provides an async implementation for interacting with MySQL databases,
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
    ReturningNotSupportedError,
)
from rhosocial.activerecord.backend.result import QueryResult
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect
from .async_transaction import AsyncMySQLTransactionManager


class AsyncMySQLBackend(AsyncStorageBackend):
    """Asynchronous MySQL-specific backend implementation."""

    def __init__(self, **kwargs):
        """Initialize async MySQL backend with connection configuration."""
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
        
        # Initialize MySQL-specific components
        self._dialect = MySQLDialect(self.get_server_version())
        self._transaction_manager = AsyncMySQLTransactionManager(self)

        # Register MySQL-specific type adapters (same as sync backend)
        self._register_mysql_adapters()

        self.log(logging.INFO, "AsyncMySQLBackend initialized")

    def _register_mysql_adapters(self):
        """Register MySQL-specific type adapters."""
        from .adapters import (
            MySQLBlobAdapter,
            MySQLBooleanAdapter,
            MySQLDateAdapter,
            MySQLDatetimeAdapter,
            MySQLDecimalAdapter,
            MySQLJSONAdapter,
            MySQLTimeAdapter,
            MySQLUUIDAdapter,
        )
        
        mysql_adapters = [
            MySQLBlobAdapter(),
            MySQLBooleanAdapter(),
            MySQLDateAdapter(),
            MySQLDatetimeAdapter(),
            MySQLDecimalAdapter(),
            MySQLJSONAdapter(),
            MySQLTimeAdapter(),
            MySQLUUIDAdapter(),
        ]
        
        for adapter in mysql_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        
        self.log(logging.DEBUG, "Registered MySQL-specific type adapters")

    @property
    def dialect(self):
        """Get the MySQL dialect instance."""
        return self._dialect

    @property
    def transaction_manager(self):
        """Get the async MySQL transaction manager."""
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
            additional_params = [
                'pool_name', 'pool_size', 'pool_reset_session', 
                'pool_pre_ping', 'auth_plugin', 'init_command',
                'connect_timeout', 'read_timeout', 'write_timeout',
                'use_pure', 'get_warnings', 'buffered', 'raw',
                'compress', 'allow_local_infile', 'conn_attrs',
                'client_flags', 'unix_socket', 'allow_local_infile_in_path'
            ]
            
            for param in additional_params:
                if hasattr(self.config, param):
                    conn_params[param] = getattr(self.config, param)

            self._connection = await mysql_async.connect(**conn_params)
            
            # Set additional session settings if specified
            init_command = getattr(self.config, 'init_command', None)
            if init_command:
                cursor = await self._connection.cursor()
                await cursor.execute(init_command)
                await cursor.close()
            
            self.log(logging.INFO, f"Connected to MySQL database: {self.config.host}:{self.config.port}/{self.config.database}")
        except MySQLError as e:
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
            except MySQLError as e:
                self.log(logging.ERROR, f"Error during disconnection: {str(e)}")
                raise OperationalError(f"Error during MySQL disconnection: {str(e)}")

    async def _get_cursor(self):
        """Get a database cursor, ensuring connection is active."""
        if not self._connection:
            await self.connect()
        
        return await self._connection.cursor()

    async def execute(self, sql: str, params: Optional[Tuple] = None) -> QueryResult:
        """Execute a SQL statement with optional parameters asynchronously."""
        if not self._connection:
            await self.connect()
        
        cursor = None
        start_time = datetime.datetime.now()
        
        try:
            cursor = await self._get_cursor()
            
            # Log the query if logging is enabled
            if getattr(self.config, 'log_queries', False):
                self.log(logging.DEBUG, f"Executing SQL: {sql}")
                if params:
                    self.log(logging.DEBUG, f"With params: {params}")
            
            # Execute the query
            if params:
                await cursor.execute(sql, params)
            else:
                await cursor.execute(sql)
            
            # Get results
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            # For SELECT queries, fetch results
            if sql.strip().upper().startswith(('SELECT', 'WITH', 'PRAGMA', 'SHOW')):
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(zip(columns, row)) for row in rows] if rows else []
            else:
                data = None
            
            result = QueryResult(
                affected_rows=cursor.rowcount,
                data=data,
                duration=duration
            )
            
            self.log(logging.INFO, f"Query executed successfully, affected {cursor.rowcount} rows, duration={duration:.3f}s")
            return result
            
        except MySQLIntegrityError as e:
            self.log(logging.ERROR, f"Integrity error: {str(e)}")
            raise IntegrityError(str(e))
        except MySQLError as e:
            self.log(logging.ERROR, f"MySQL error: {str(e)}")
            raise DatabaseError(str(e))
        except Exception as e:
            self.log(logging.ERROR, f"Unexpected error during execution: {str(e)}")
            raise QueryError(str(e))
        finally:
            if cursor:
                await cursor.close()

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
                await cursor.execute(sql, params)
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
            raise ReturningNotSupportedError(
                "RETURNING clause is not supported by MySQL. "
                "Consider using LAST_INSERT_ID() or alternative approaches."
            )

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, '_logger') and self._logger:
            self._logger.log(level, message)
        else:
            # Fallback logging
            print(f"[{logging.getLevelName(level)}] {message}")