# src/rhosocial/activerecord/backend/impl/mysql/mixins/backend_mixin.py
import logging
from typing import Dict, Tuple, Type

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class MySQLBackendMixin:
    """MySQL backend common functionality.

    Logging is inherited from ``BackendLoggingMixin``: the mixin pins the
    library logger name so the sync and async backends share
    ``rhosocial.activerecord.backend.mysql`` and the canonical execution
    records stay in one place.
    """

    # Both MySQLBackend and AsyncMySQLBackend report under the same library
    # logger; without this the derived Async* name would produce
    # ``rhosocial.activerecord.backend.asyncmysql``.
    _logger_name = "rhosocial.activerecord.backend.mysql"

    def _register_mysql_adapters(self):
        """Register MySQL-specific type adapters."""
        from ..adapters import (
            MySQLBlobAdapter,
            MySQLBooleanAdapter,
            MySQLDateAdapter,
            MySQLDatetimeAdapter,
            MySQLDecimalAdapter,
            MySQLEnumAdapter,
            MySQLJSONAdapter,
            MySQLSetAdapter,
            MySQLTimeAdapter,
            MySQLUUIDAdapter,
        )

        mysql_adapters = [
            MySQLBlobAdapter(),
            MySQLBooleanAdapter(),
            MySQLDateAdapter(),
            MySQLDatetimeAdapter(self._version),
            MySQLDecimalAdapter(),
            MySQLEnumAdapter(use_int_storage=False),
            MySQLJSONAdapter(),
            MySQLSetAdapter(),
            MySQLTimeAdapter(),
            MySQLUUIDAdapter(),
        ]

        for adapter in mysql_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)

        self.log(logging.DEBUG, "Registered MySQL-specific type adapters")

    @property
    def dialect(self):
        """Get the MySQL dialect instance (lazy loads with configured version)."""
        from ..dialect import MySQLDialect

        if self._dialect is None:
            self._dialect = MySQLDialect(
                self._version,
                sql_mode=getattr(self.config, "sql_mode", None),
            )
        return self._dialect

    @property
    def transaction_manager(self):
        """Get the MySQL transaction manager."""
        return self._transaction_manager

    @property
    def threadsafety(self) -> int:
        """Return driver threadsafety level."""
        import mysql.connector

        return mysql.connector.threadsafety

    def requires_manual_commit(self) -> bool:
        """Check if manual commit is required for this database."""
        return not getattr(self.config, "autocommit", True)

    def _check_returning_compatibility(self, _returning_clause):
        """Check if RETURNING clause is compatible with this MySQL version."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if (self.dialect.supports_returning_insert() or
                self.dialect.supports_returning_update() or
                self.dialect.supports_returning_delete()):
            return True
        else:
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                "MySQL does not support RETURNING clause. Consider using LAST_INSERT_ID() or alternative approaches.",
            )

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """Provides default type adapter suggestions for MySQL."""
        from datetime import date, datetime, time
        from decimal import Decimal
        from uuid import UUID
        from enum import Enum

        suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]] = {}

        type_mappings = [
            (bool, int),
            (datetime, str),
            (date, str),
            (time, str),
            (Decimal, float),
            (UUID, str),
            (dict, str),
            (list, str),
            (Enum, str),
            (set, str),
            (frozenset, str),
        ]

        for py_type, db_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter:
                suggestions[py_type] = (adapter, db_type)
            else:
                self.log(
                    logging.DEBUG,
                    f"No adapter found for ({py_type.__name__}, {db_type.__name__}). "
                    "Suggestion will not be provided for this type.",
                )

        return suggestions

    CONNECTION_ERROR_CODES = {
        2003,
        2006,
        2013,
        2048,
        2055,
    }

    def _is_connection_error(self, error: Exception) -> bool:
        """Check if an error indicates a connection loss."""
        if hasattr(error, "errno"):
            if error.errno in self.CONNECTION_ERROR_CODES:
                return True

        error_str = str(error).lower()
        connection_error_patterns = [
            "server has gone away",
            "lost connection",
            "can't connect to mysql server",
            "connection refused",
            "broken pipe",
            "connection reset",
        ]
        return any(pattern in error_str for pattern in connection_error_patterns)

    def _handle_error(self, error: Exception) -> None:
        """Handle MySQL-specific errors.

        Deadlock and lock-wait are recognized first by error code or message,
        because the driver reports them under more than one exception class.
        Everything else is recognized by driver exception class, then error
        code, then message text; codes are the stable signal across driver
        versions.
        """
        from mysql.connector.errors import (
            DatabaseError as MySQLDatabaseError,
            Error as MySQLError,
            IntegrityError as MySQLIntegrityError,
            OperationalError as MySQLOperationalError,
            ProgrammingError as MySQLProgrammingError,
        )
        from rhosocial.activerecord.backend.errors import (
            DatabaseError,
            DeadlockError,
            IntegrityError,
            LockError,
            OperationalError,
            QueryError,
            attach_diagnostics,
        )

        # Framework errors are already translated; translating them again would
        # rewrite their semantic type. Let them pass through unchanged.
        if isinstance(error, DatabaseError):
            raise error

        error_msg = str(error)
        errno = getattr(error, "errno", None)
        backend = "mysql"

        # Deadlock and lock-wait signatures take precedence over the driver
        # exception class: mysql-connector reports them as both
        # OperationalError and DatabaseError depending on the code path, and
        # classifying by code/message keeps the concurrency semantics stable.
        if errno == 1213 or "Deadlock found" in error_msg:
            self.log(logging.DEBUG, f"Deadlock error: {error_msg}")
            raise attach_diagnostics(
                DeadlockError(error_msg),
                operation="execute",
                driver_code=errno or 1213,
                backend=backend,
                transient=True,
            ) from error
        if errno == 1205 or "Lock wait timeout exceeded" in error_msg:
            self.log(logging.DEBUG, f"Lock timeout error: {error_msg}")
            raise attach_diagnostics(
                LockError(error_msg),
                operation="execute",
                driver_code=errno or 1205,
                backend=backend,
                transient=True,
            ) from error

        if isinstance(error, MySQLIntegrityError):
            if errno == 1062 or "Duplicate entry" in error_msg:
                self.log(logging.DEBUG, f"Unique constraint violation: {error_msg}")
                raise attach_diagnostics(
                    IntegrityError(f"Unique constraint violation: {error_msg}"),
                    operation="execute",
                    driver_code=errno or 1062,
                    backend=backend,
                ) from error
            elif (
                errno in (1451, 1452)
                or "Cannot delete or update" in error_msg
                or "a foreign key constraint fails" in error_msg
            ):
                self.log(logging.DEBUG, f"Foreign key constraint violation: {error_msg}")
                raise attach_diagnostics(
                    IntegrityError(f"Foreign key constraint violation: {error_msg}"),
                    operation="execute",
                    driver_code=errno,
                    backend=backend,
                ) from error
            self.log(logging.DEBUG, f"Integrity error: {error_msg}")
            raise attach_diagnostics(
                IntegrityError(error_msg),
                operation="execute",
                driver_code=errno,
                backend=backend,
            ) from error
        elif isinstance(error, MySQLOperationalError):
            transient = errno in (2006, 2013, 2055) or "Lost connection" in error_msg
            self.log(logging.DEBUG, f"Operational error: {error_msg}")
            raise attach_diagnostics(
                OperationalError(error_msg),
                operation="execute",
                driver_code=errno,
                backend=backend,
                transient=transient,
            ) from error
        elif isinstance(error, MySQLProgrammingError):
            self.log(logging.DEBUG, f"Programming error: {error_msg}")
            raise attach_diagnostics(
                QueryError(error_msg),
                operation="execute",
                driver_code=errno,
                backend=backend,
            ) from error
        elif isinstance(error, MySQLDatabaseError):
            if errno == 1290 or "read-only" in error_msg.lower():
                self.log(logging.DEBUG, f"Read-only server: {error_msg}")
                raise attach_diagnostics(
                    OperationalError(error_msg),
                    operation="execute",
                    sqlstate="HY000",
                    driver_code=errno or 1290,
                    backend=backend,
                    transient=False,
                ) from error
            self.log(logging.DEBUG, f"Database error: {error_msg}")
            raise attach_diagnostics(
                DatabaseError(error_msg),
                operation="execute",
                driver_code=errno,
                backend=backend,
            ) from error
        elif isinstance(error, MySQLError):
            self.log(logging.DEBUG, f"MySQL error: {error_msg}")
            raise attach_diagnostics(
                DatabaseError(error_msg), operation="execute", backend=backend
            ) from error
        else:
            self.log(logging.DEBUG, f"Unexpected error: {error_msg}")
            raise error
