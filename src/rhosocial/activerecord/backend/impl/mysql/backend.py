# src/rhosocial/activerecord/backend/impl/mysql/backend.py
import datetime
import logging
import re
import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Type, Union

import mysql.connector
import time
from mysql.connector.errors import (
    DatabaseError as MySQLDatabaseError,
    Error as MySQLError,
    IntegrityError as MySQLIntegrityError,
    OperationalError as MySQLOperationalError,
    ProgrammingError,
)

from rhosocial.activerecord.backend.base import AsyncStorageBackend, StorageBackend
from rhosocial.activerecord.backend.capabilities import (
    AggregateFunctionCapability,
    BulkOperationCapability,
    CapabilityCategory,
    CTECapability,
    ConstraintCapability,
    DatabaseCapabilities,
    DateTimeFunctionCapability,
    JSONCapability,
    JoinCapability,
    MathematicalFunctionCapability,
    StringFunctionCapability,
    TransactionCapability,
    WindowFunctionCapability, SetOperationCapability,
)
from rhosocial.activerecord.backend.dialect import ReturningOptions
from rhosocial.activerecord.backend.errors import (
    ConnectionError,
    DatabaseError,
    DeadlockError,
    IntegrityError,
    OperationalError,
    QueryError,
    ReturningNotSupportedError,
)
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.typing import QueryResult, ConnectionConfig
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
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect, MySQLSQLBuilder
from .transaction import AsyncMySQLTransactionManager, MySQLTransactionManager


class MySQLBackendMixin:
    """Mixin for MySQL-specific functionality shared between sync and async backends."""

    def _ensure_mysql_config(self, kwargs):
        """Ensure kwargs contains a proper MySQLConnectionConfig"""
        connection_config = kwargs.get('connection_config')

        if connection_config is None:
            config_params = {}
            mysql_specific_params = [
                'host', 'port', 'database', 'username', 'password',
                'charset', 'collation', 'timezone', 'version',
                'pool_size', 'pool_timeout', 'pool_name', 'pool_reset_session', 'pool_pre_ping',
                'ssl_ca', 'ssl_cert', 'ssl_key', 'ssl_verify_cert', 'ssl_verify_identity',
                'log_queries', 'log_level',
                'auth_plugin', 'autocommit', 'init_command', 'connect_timeout',
                'read_timeout', 'write_timeout', 'use_pure', 'get_warnings',
                'options'
            ]

            for param in mysql_specific_params:
                if param in kwargs:
                    config_params[param] = kwargs[param]

            if 'charset' not in config_params:
                config_params['charset'] = 'utf8mb4'
            if 'autocommit' not in config_params:
                config_params['autocommit'] = True
            if 'init_command' not in config_params:
                config_params['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"

            kwargs['connection_config'] = MySQLConnectionConfig(**config_params)

        elif isinstance(connection_config, MySQLConnectionConfig):
            pass
        elif isinstance(connection_config, ConnectionConfig): # This is the generic ConnectionConfig conversion
            from rhosocial.activerecord.backend.config import ConnectionConfig

            mysql_config = MySQLConnectionConfig(
                host=getattr(connection_config, 'host', 'localhost'),
                port=getattr(connection_config, 'port', 3306),
                database=getattr(connection_config, 'database', None),
                username=getattr(connection_config, 'username', None),
                password=getattr(connection_config, 'password', None),
                charset=getattr(connection_config, 'charset', 'utf8mb4'),
                collation=getattr(connection_config, 'collation', None),
                timezone=getattr(connection_config, 'timezone', None),
                use_timezone=getattr(connection_config, 'use_timezone', True),
                version=getattr(connection_config, 'version', (8, 0, 0)),
                pool_size=getattr(connection_config, 'pool_size', 5),
                pool_timeout=getattr(connection_config, 'pool_timeout', 30),
                pool_name=getattr(connection_config, 'pool_name', 'mysql_pool'),
                pool_reset_session=getattr(connection_config, 'pool_reset_session', True),
                pool_pre_ping=getattr(connection_config, 'pool_pre_ping', False),
                ssl_ca=getattr(connection_config, 'ssl_ca', None),
                ssl_cert=getattr(connection_config, 'ssl_cert', None),
                ssl_key=getattr(connection_config, 'ssl_key', None),
                ssl_verify_cert=getattr(connection_config, 'ssl_verify_cert', False),
                ssl_verify_identity=getattr(connection_config, 'ssl_verify_identity', False),
                log_queries=getattr(connection_config, 'log_queries', False),
                log_level=getattr(connection_config, 'log_level', logging.INFO),
                autocommit=True,
                init_command="SET sql_mode='STRICT_TRANS_TABLES'",
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
                use_pure=True,
                get_warnings=True,
                options=getattr(connection_config, 'options', {})
            )
            kwargs['connection_config'] = mysql_config
        else:
            raise ValueError(f"Unsupported connection_config type: {type(connection_config)}")
    def _prepare_mysql_connection_args(self) -> Dict:
        """Prepare MySQL connection arguments from MySQLConnectionConfig"""
        connection_args = self.config.to_dict()

        if 'username' in connection_args:
            connection_args['user'] = connection_args.pop('username')

        if any(getattr(self.config, key, None) for key in ['ssl_ca', 'ssl_cert', 'ssl_key']):
            ssl_config = {}
            if self.config.ssl_ca:
                ssl_config['ca'] = self.config.ssl_ca
            if self.config.ssl_cert:
                ssl_config['cert'] = self.config.ssl_cert
            if self.config.ssl_key:
                ssl_config['key'] = self.config.ssl_key
            if self.config.ssl_verify_cert:
                ssl_config['verify_cert'] = self.config.ssl_verify_cert
            if self.config.ssl_verify_identity:
                ssl_config['verify_identity'] = self.config.ssl_verify_identity

            if ssl_config:
                connection_args['ssl'] = ssl_config
                for key in ['ssl_ca', 'ssl_cert', 'ssl_key', 'ssl_verify_cert', 'ssl_verify_identity']:
                    connection_args.pop(key, None)

        if self.config.ssl_disabled is not None:
            connection_args['ssl_disabled'] = self.config.ssl_disabled

        for key in ['pool_size', 'pool_timeout', 'pool_name', 'pool_reset_session', 'pool_pre_ping',
                    'version', 'log_queries', 'log_level', 'options', 'use_timezone', 'collation', 'auto_add_local_tz']:
            connection_args.pop(key, None)
        return connection_args

    def _register_mysql_adapters(self):
        """Register MySQL-specific type adapters to the adapter_registry."""
        mysql_adapters = [
            MySQLBlobAdapter(),
            MySQLJSONAdapter(),
            MySQLUUIDAdapter(),
            MySQLBooleanAdapter(),
            MySQLDecimalAdapter(),
            MySQLDateAdapter(),
            MySQLTimeAdapter(),
            MySQLDatetimeAdapter()
        ]
        for adapter in mysql_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    # Register with override allowed for backend-specific converters
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)
        self.logger.debug("Registered MySQL-specific type adapters.")

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

        type_mappings = [
            (bool, int),        # Python bool -> DB driver int (MySQL TINYINT(1))
            (datetime.datetime, datetime.datetime),    # Python datetime -> DB driver datetime (MySQL DATETIME/TIMESTAMP)
            (datetime.date, datetime.date),        # Python date -> DB driver date (MySQL DATE)
            (datetime.time, datetime.time),        # Python time -> DB driver time (MySQL TIME)
            (Decimal, Decimal),   # Python Decimal -> DB driver Decimal (MySQL DECIMAL/NUMERIC)
            (uuid.UUID, str),        # Python UUID -> DB driver str (MySQL CHAR(36))
            (dict, str),        # Python dict -> DB driver str (MySQL JSON)
            (list, str),        # Python list -> DB driver str (MySQL JSON)
            (bytes, bytes),     # Python bytes -> DB driver bytes (MySQL BLOB)
            # Add Enum if a specific adapter is created for it
            # (enum.Enum, str),
        ]

        for py_type, db_driver_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_driver_type)
            if adapter:
                suggestions[py_type] = (adapter, db_driver_type)
            else:
                self.logger.debug(f"No adapter found for ({py_type.__name__}, {db_driver_type.__name__}). "
                                  "Suggestion will not be provided for this type.")

        return suggestions

    def _update_dialect_version(self, version: tuple) -> None:
        """Update the dialect's version information"""
        self._dialect._version = version

        if hasattr(self._dialect, '_returning_handler'):
            self._dialect._returning_handler._version = version

        if hasattr(self._dialect, '_aggregate_handler'):
            self._dialect._aggregate_handler._version = version

        if hasattr(self._dialect, '_json_operation_handler'):
            self._dialect._json_operation_handler._version = version

    def _is_select_statement(self, stmt_type: str) -> bool:
        """Check if statement is a SELECT-like query (MySQL specific)"""
        return stmt_type in ("SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE", "DESC", "ANALYZE")

    def _get_statement_type(self, sql: str) -> str:
        """Parse the SQL statement type (MySQL specific)"""
        clean_sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE).strip()

        if not clean_sql:
            return ""

        upper_sql = clean_sql.upper()

        if upper_sql.startswith('SHOW'):
            return 'SHOW'
        if upper_sql.startswith('SET'):
            return 'SET'
        if upper_sql.startswith('USE'):
            return 'USE'

        if upper_sql.startswith('WITH'):
            for main_type in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                if main_type in upper_sql:
                    return main_type
            return 'SELECT'

        return super()._get_statement_type(clean_sql) if hasattr(super(), '_get_statement_type') else clean_sql.split()[
            0].upper()

    def _initialize_capabilities(self) -> DatabaseCapabilities:
        """Initialize MySQL capabilities based on version."""
        capabilities = DatabaseCapabilities()
        version = self.get_server_version()

        capabilities.add_transaction([
            TransactionCapability.SAVEPOINT,
            TransactionCapability.ISOLATION_LEVELS
        ])
        capabilities.add_bulk_operation([
            BulkOperationCapability.MULTI_ROW_INSERT,
            BulkOperationCapability.BATCH_OPERATIONS,
            BulkOperationCapability.UPSERT
        ])
        capabilities.add_join_operation([
            JoinCapability.INNER_JOIN,
            JoinCapability.LEFT_OUTER_JOIN,
            JoinCapability.RIGHT_OUTER_JOIN
        ])
        capabilities.add_constraint([
            ConstraintCapability.PRIMARY_KEY,
            ConstraintCapability.FOREIGN_KEY,
            ConstraintCapability.UNIQUE,
            ConstraintCapability.NOT_NULL,
            ConstraintCapability.CHECK,
            ConstraintCapability.DEFAULT
        ])
        capabilities.add_datetime_function([
            DateTimeFunctionCapability.DATE_ADD,
            DateTimeFunctionCapability.DATE_SUB
        ])
        capabilities.add_string_function([
            StringFunctionCapability.CONCAT,
            StringFunctionCapability.CONCAT_WS,
            StringFunctionCapability.LOWER,
            StringFunctionCapability.UPPER,
            StringFunctionCapability.SUBSTRING,
            StringFunctionCapability.TRIM
        ])
        capabilities.add_mathematical_function([
            MathematicalFunctionCapability.ABS,
            MathematicalFunctionCapability.ROUND,
            MathematicalFunctionCapability.CEIL,
            MathematicalFunctionCapability.FLOOR,
            MathematicalFunctionCapability.POWER
        ])
        capabilities.add_aggregate_function([
            AggregateFunctionCapability.GROUP_CONCAT
        ])

        if version >= (5, 7, 0):
            capabilities.add_json([
                JSONCapability.JSON_EXTRACT,
                JSONCapability.JSON_SET,
                JSONCapability.JSON_INSERT,
                JSONCapability.JSON_REPLACE,
                JSONCapability.JSON_CONTAINS,
                JSONCapability.JSON_EXISTS,
                JSONCapability.JSON_REMOVE,
                JSONCapability.JSON_KEYS,
                JSONCapability.JSON_ARRAY,
                JSONCapability.JSON_OBJECT
            ])
            capabilities.add_window_function([
                WindowFunctionCapability.LAG,
                WindowFunctionCapability.LEAD,
                WindowFunctionCapability.FIRST_VALUE,
                WindowFunctionCapability.LAST_VALUE
            ])
            capabilities.add_constraint(ConstraintCapability.CHECK)

        if version >= (8, 0, 0):
            capabilities.add_window_function([
                WindowFunctionCapability.ROW_NUMBER,
                WindowFunctionCapability.RANK,
                WindowFunctionCapability.DENSE_RANK,
                WindowFunctionCapability.NTH_VALUE,
                WindowFunctionCapability.CUME_DIST,
                WindowFunctionCapability.PERCENT_RANK,
                WindowFunctionCapability.NTILE
            ])
            capabilities.add_cte([
                CTECapability.BASIC_CTE,
                CTECapability.RECURSIVE_CTE
            ])
            capabilities.add_set_operation(SetOperationCapability.UNION)
            capabilities.add_set_operation(SetOperationCapability.UNION_ALL)
            capabilities.add_set_operation(SetOperationCapability.INTERSECT)
            capabilities.add_set_operation(SetOperationCapability.INTERSECT_ALL)
            capabilities.add_set_operation(SetOperationCapability.EXCEPT)
            capabilities.add_set_operation(SetOperationCapability.EXCEPT_ALL)

        capabilities.add_category(CapabilityCategory.FULL_TEXT_SEARCH)
        capabilities.add_category(CapabilityCategory.SPATIAL_OPERATIONS)
        capabilities.add_category(CapabilityCategory.SECURITY_FEATURES)

        return capabilities


class MySQLBackend(MySQLBackendMixin, StorageBackend):
    """MySQL synchronous storage backend implementation"""

    def __init__(self, **kwargs):
        """Initialize MySQL backend"""
        self._ensure_mysql_config(kwargs)
        super().__init__(**kwargs)

        self._cursor = None
        self._pool = None
        self._connection_args = self._prepare_mysql_connection_args()
        self._dialect = MySQLDialect(self.config)
        version = self.get_server_version()
        self._register_mysql_adapters()

        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            self._update_dialect_version(self.config.version)

    @property
    def dialect(self) -> MySQLDialect:
        """Get the MySQL dialect instance"""
        return self._dialect

    @property
    def transaction_manager(self) -> MySQLTransactionManager:
        """Get transaction manager"""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = MySQLTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    def connect(self) -> None:
        """Establish connection to MySQL database"""
        try:
            self._connection = mysql.connector.connect(**self._connection_args)

            if self.config.timezone:
                cursor = self._connection.cursor()
                try:
                    cursor.execute(f"SET time_zone = '{self.config.timezone}'")
                except Exception as e:
                    self.logger.warning(f"Could not set MySQL timezone to {self.config.timezone}: {e}")
                finally:
                    cursor.close()

            version = self.get_server_version()
            self._update_dialect_version(version)
            self._transaction_manager = MySQLTransactionManager(self._connection)
            self.log(logging.INFO, f"Connected to MySQL server version {'.'.join(map(str, version))}")
        except MySQLError as e:
            raise ConnectionError(f"Failed to connect to MySQL: {e}")

    def disconnect(self) -> None:
        """Close connection to MySQL database"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._connection:
            self._connection.close()
            self._connection = None

        self._transaction_manager = None
        self.log(logging.INFO, "Disconnected from MySQL")

    def ping(self, reconnect: bool = True) -> bool:
        """Check if connection is valid"""
        try:
            if not self._connection:
                if reconnect:
                    self.connect()
                    return True
                return False

            self._connection.ping(reconnect=False)
            return True

        except MySQLError:
            if reconnect:
                try:
                    if self._connection:
                        try:
                            self._connection.close()
                        except:
                            pass
                        self._connection = None

                    self.connect()
                    return True
                except Exception:
                    return False
            return False

    def _handle_error(self, error: Exception) -> None:
        """Handle database errors"""
        if isinstance(error, MySQLIntegrityError):
            raise IntegrityError(f"MySQL integrity error: {error}")
        elif isinstance(error, ProgrammingError) and hasattr(error, 'errno') and error.errno == 1054:
            raise OperationalError(f"MySQL operational error: {error}")
        elif isinstance(error, MySQLOperationalError):
            if hasattr(error, 'errno') and error.errno == 1213:
                raise DeadlockError(f"MySQL deadlock detected: {error}")
            raise OperationalError(f"MySQL operational error: {error}")
        elif isinstance(error, MySQLDatabaseError):
            raise DatabaseError(f"MySQL database error: {error}")
        elif isinstance(error, MySQLError):
            raise QueryError(f"MySQL query error: {error}")
        else:
            raise error

    def get_server_version(self, fallback_to_default: bool = False) -> tuple:
        """Get MySQL server version"""
        if self._server_version_cache:
            return self._server_version_cache

        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            self._update_dialect_version(self.config.version)
            return self._server_version_cache

        try:
            if not self._connection:
                self.connect()

            self.log(logging.DEBUG, "Querying MySQL server version")
            cursor = self._connection.cursor()
            cursor.execute("SELECT VERSION()")
            version_str = cursor.fetchone()[0]
            cursor.close()

            version_parts = version_str.split('-')[0].split('.')
            version = tuple(int(part) for part in version_parts[:3])

            if len(version) < 3:
                version = version + (0,) * (3 - len(version))

            self._server_version_cache = version
            self._update_dialect_version(version)

            self.log(logging.DEBUG, f"Detected MySQL server version: {'.'.join(map(str, version))}")
            return version

        except Exception as e:
            if fallback_to_default:
                default_version = (8, 0, 0)
                self.log(logging.WARNING, f"Failed to get server version, using default {default_version}: {e}")
                self._server_version_cache = default_version
                self._update_dialect_version(default_version)
                return default_version
            else:
                raise Exception(f"Failed to determine MySQL server version: {e}")

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters for MySQL"""
        builder = MySQLSQLBuilder(self.dialect)
        return builder.build(sql, params)

    def _prepare_returning_clause(self, sql: str, options: ReturningOptions, stmt_type: str) -> str:
        """Prepare RETURNING clause for MySQL (not natively supported)"""
        if not options.force:
            error_msg = (
                "RETURNING clause is not supported by MySQL. "
                "This is a fundamental limitation of the database engine, not a driver issue. "
                "Use force=True to attempt emulation if you understand the limitations."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

        if stmt_type == "INSERT":
            self._returning_emulation = {
                "type": "insert",
                "options": options,
                "statement": sql
            }

            match = re.search(r"INSERT\s+INTO\s+`?(\w+)`?", sql, re.IGNORECASE)
            if match:
                self._returning_emulation["table"] = match.group(1)

            self.log(logging.WARNING,
                     "MySQL doesn't support RETURNING. Will attempt to emulate using "
                     "LAST_INSERT_ID() which only works reliably for single row inserts "
                     "with auto-increment primary keys.")

        elif stmt_type in ("UPDATE", "DELETE"):
            table_match = None
            if stmt_type == "UPDATE":
                table_match = re.search(r"UPDATE\s+`?(\w+)`?", sql, re.IGNORECASE)
            else:
                table_match = re.search(r"DELETE\s+FROM\s+`?(\w+)`?", sql, re.IGNORECASE)

            if table_match:
                table_name = table_match.group(1)

                self._returning_emulation = {
                    "type": stmt_type.lower(),
                    "options": options,
                    "table": table_name,
                    "statement": sql
                }

                self.log(logging.WARNING,
                         f"MySQL doesn't support RETURNING for {stmt_type}. Emulation is very "
                         f"limited and requires separate queries. Results may be incomplete.")
            else:
                self.log(logging.ERROR, f"Could not parse table name from {stmt_type} query")

        return sql

    def _get_cursor(self):
        """Get or create cursor for MySQL"""
        if self._cursor:
            return self._cursor

        cursor = self._connection.cursor(dictionary=True)
        return cursor



    def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit for MySQL"""
        try:
            if not self._connection:
                return

            if hasattr(self._connection, 'autocommit') and not self._connection.autocommit:
                if not self._transaction_manager or not self._transaction_manager.is_active:
                    self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def _handle_execution_error(self, error: Exception):
        """Handle MySQL-specific errors during execution"""
        if hasattr(error, 'errno'):
            code = getattr(error, 'errno', None)
            msg = str(error)

            if code == 1062:
                self.log(logging.ERROR, f"Unique constraint violation: {msg}")
                raise IntegrityError(f"Unique constraint violation: {msg}")
            elif code == 1452:
                self.log(logging.ERROR, f"Foreign key constraint violation: {msg}")
                raise IntegrityError(f"Foreign key constraint violation: {msg}")
            elif code in (1205, 1213):
                self.log(logging.ERROR, f"Deadlock or lock wait timeout: {msg}")
                raise DeadlockError(msg)

        super()._handle_execution_error(error)

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on MySQL connection and transaction state"""
        try:
            if not self._connection:
                return

            if hasattr(self._connection, 'autocommit') and not self._connection.autocommit:
                if not self._transaction_manager or not self._transaction_manager.is_active:
                    self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """Execute batch operations"""
        start_time = time.perf_counter()
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._connection.cursor()

            converted_params = []
            for params in params_list:
                if params:
                    converted = tuple(
                        self.adapter_registry.to_database(value, None)
                        for value in params
                    )
                    converted_params.append(converted)

            cursor.executemany(sql, converted_params)
            duration = time.perf_counter() - start_time

            self.log(logging.INFO,
                     f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s")

            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )

        except MySQLError as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)
            return None

    def insert(self, table: str, data: Dict, returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None, auto_commit: Optional[bool] = True,
               primary_key: Optional[str] = None) -> QueryResult:
        """Insert record with MySQL-specific handling"""
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = list(cleaned_data.values())
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        result = self.execute(sql, tuple(values), returning, column_adapters)

        if auto_commit:
            self._handle_auto_commit_if_needed()

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

    def update(self, table: str, data: Dict, where: str, params: Tuple,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None, auto_commit: bool = True) -> QueryResult:
        """Update record with MySQL-specific handling"""
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in cleaned_data.keys()]

        values = list(data.values())

        sql = f"UPDATE {table} SET {', '.join(set_items)} WHERE {where}"

        result = self.execute(sql, tuple(values) + params, returning, column_adapters)

        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    @property
    def supports_returning(self) -> bool:
        """Check if RETURNING is supported"""
        return self.dialect.returning_handler.is_supported


class AsyncMySQLBackend(MySQLBackendMixin, AsyncStorageBackend):
    """MySQL asynchronous storage backend implementation"""

    async def _handle_auto_commit(self) -> None:
        """Handle auto commit based on MySQL connection and transaction state asynchronously."""
        try:
            if not self._connection:
                return

            # THIS IS THE CORRECTED LINE, using get_autocommit()
            if hasattr(self._connection, 'get_autocommit') and not await self._connection.get_autocommit():
                if not self._transaction_manager or not self._transaction_manager.is_active:
                    await self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    def __init__(self, **kwargs):
        """Initialize async MySQL backend"""
        self._ensure_mysql_config(kwargs)
        super().__init__(**kwargs)

        self._cursor = None
        self._pool = None
        self._connection_args = self._prepare_mysql_connection_args()
        self._dialect = MySQLDialect(self.config)
        self._register_mysql_adapters()  # Call _register_mysql_adapters here

        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            self._update_dialect_version(self.config.version)

    @property
    def dialect(self) -> MySQLDialect:
        """Get the MySQL dialect instance"""
        return self._dialect

    @property
    def transaction_manager(self) -> AsyncMySQLTransactionManager:
        """Get async transaction manager"""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.WARNING, "Transaction manager accessed before connection established")
            self.log(logging.DEBUG, "Creating new async transaction manager")
            self._transaction_manager = AsyncMySQLTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    async def connect(self) -> None:
        """Establish connection to MySQL database asynchronously"""
        try:
            from mysql.connector.aio import connect

            try:
                self._connection = await connect(**self._connection_args)
            except TypeError as e:
                if "cannot unpack non-iterable NoneType object" in str(e):
                    raise ConnectionError(
                        "Failed to connect to MySQL due to a TypeError. "
                        "This might be caused by an SSL handshake issue. "
                        "If you are connecting to MySQL 5.6 or older, "
                        "consider explicitly setting `ssl_disabled=True` in your connection configuration."
                    ) from e
                raise

            if self.config.timezone:
                cursor = await self._connection.cursor()
                try:
                    await cursor.execute(f"SET time_zone = '{self.config.timezone}'")
                except Exception as e:
                    self.logger.warning(f"Could not set MySQL timezone to {self.config.timezone}: {e}")
                finally:
                    await cursor.close()

            version = await self.get_server_version()
            self._update_dialect_version(version)
            self._transaction_manager = AsyncMySQLTransactionManager(self._connection)
            self.log(logging.INFO, f"Connected to MySQL server version {'.'.join(map(str, version))}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MySQL: {e}")

    async def disconnect(self) -> None:
        """Close connection to MySQL database asynchronously"""
        if self._cursor:
            await self._cursor.close()
            self._cursor = None

        if self._connection:
            try:
                await self._connection.close()
            except RuntimeError as e:
                if "Set changed size during iteration" in str(e):
                    self.log(logging.WARNING, f"Ignoring RuntimeError during connection close: {e}")
                else:
                    raise
            self._connection = None

        self._transaction_manager = None
        self.log(logging.INFO, "Disconnected from MySQL")

    async def ping(self, reconnect: bool = True) -> bool:
        """Check if connection is valid asynchronously"""
        try:
            if not self._connection:
                if reconnect:
                    await self.connect()
                    return True
                return False

            await self._connection.ping(reconnect=False)
            return True

        except Exception:
            if reconnect:
                try:
                    if self._connection:
                        try:
                            await self._connection.close()
                        except:
                            pass
                        self._connection = None

                    await self.connect()
                    return True
                except Exception:
                    return False
            return False

    async def _handle_error(self, error: Exception) -> None:
        """Handle database errors asynchronously"""
        if isinstance(error, MySQLIntegrityError):
            raise IntegrityError(f"MySQL integrity error: {error}")
        elif isinstance(error, ProgrammingError) and hasattr(error, 'errno') and error.errno == 1054:
            raise OperationalError(f"MySQL operational error: {error}")
        elif isinstance(error, MySQLOperationalError):
            if hasattr(error, 'errno') and error.errno == 1213:
                raise DeadlockError(f"MySQL deadlock detected: {error}")
            raise OperationalError(f"MySQL operational error: {error}")
        elif isinstance(error, MySQLDatabaseError):
            raise DatabaseError(f"MySQL database error: {e}")
        elif isinstance(error, MySQLError):
            raise QueryError(f"MySQL query error: {e}")
        else:
            raise error

    async def get_server_version(self, fallback_to_default: bool = False) -> tuple:
        """Get MySQL server version asynchronously"""
        if self._server_version_cache:
            return self._server_version_cache

        if hasattr(self.config, 'version') and self.config.version:
            self._server_version_cache = self.config.version
            self._update_dialect_version(self.config.version)
            return self._server_version_cache

        try:
            if not self._connection:
                await self.connect()

            self.log(logging.DEBUG, "Querying MySQL server version asynchronously")
            cursor = await self._connection.cursor()
            await cursor.execute("SELECT VERSION()")
            result = await cursor.fetchone()
            version_str = result[0]
            await cursor.close()

            version_parts = version_str.split('-')[0].split('.')
            version = tuple(int(part) for part in version_parts[:3])

            if len(version) < 3:
                version = version + (0,) * (3 - len(version))

            self._server_version_cache = version
            self._update_dialect_version(version)

            self.log(logging.DEBUG, f"Detected MySQL server version: {'.'.join(map(str, version))}")
            return version

        except Exception as e:
            if fallback_to_default:
                default_version = (8, 0, 0)
                self.log(logging.WARNING, f"Failed to get server version, using default {default_version}: {e}")
                self._server_version_cache = default_version
                self._update_dialect_version(default_version)
                return default_version
            else:
                raise Exception(f"Failed to determine MySQL server version: {e}")

    async def _get_cursor(self):
        """Get cursor asynchronously"""
        if self._cursor:
            return self._cursor
        return await self._connection.cursor(dictionary=True)

    async def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute query asynchronously"""
        if params:
            processed_params = tuple(
                self.adapter_registry.to_database(value, None)
                for value in params
            )
            await cursor.execute(sql, processed_params)
        else:
            await cursor.execute(sql)
        return cursor

    async def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit asynchronously"""
        try:
            if not self._connection:
                return

            if hasattr(self._connection, 'get_autocommit') and not await self._connection.get_autocommit():
                if not self._transaction_manager or not self._transaction_manager.is_active:
                    await self._connection.commit()
                    self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    async def _handle_execution_error(self, error: Exception):
        """Handle execution errors asynchronously"""
        await self._handle_error(error)

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters for MySQL"""
        builder = MySQLSQLBuilder(self.dialect)
        return builder.build(sql, params)

    @property
    def supports_returning(self) -> bool:
        """Check if RETURNING is supported"""
        return self.dialect.returning_handler.is_supported