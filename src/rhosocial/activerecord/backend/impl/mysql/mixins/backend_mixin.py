# src/rhosocial/activerecord/backend/impl/mysql/mixins/backend_mixin.py
import logging
from typing import Dict, Tuple, Type

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class MySQLBackendMixin:
    """MySQL backend common functionality."""

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
            MySQLUUIDBinaryAdapter,
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
            MySQLUUIDBinaryAdapter(),
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

        if self.dialect.supports_returning_clause():
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
            (UUID, bytes),
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

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, "_logger") and self._logger:
            self._logger.log(level, message)
        else:
            print(f"[{logging.getLevelName(level)}] {message}")

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
        """Handle MySQL-specific errors."""
        from mysql.connector.errors import (
            DatabaseError as MySQLDatabaseError,
            Error as MySQLError,
            IntegrityError as MySQLIntegrityError,
            OperationalError as MySQLOperationalError,
        )
        from rhosocial.activerecord.backend.errors import (
            DatabaseError,
            DeadlockError,
            IntegrityError,
            OperationalError,
        )

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
