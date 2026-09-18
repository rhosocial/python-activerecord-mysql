# src/rhosocial/activerecord/backend/impl/mysql/mixins/transaction.py
import logging
from typing import Dict, Optional, Tuple

from rhosocial.activerecord.backend.transaction import IsolationLevel


class MySQLTransactionMixin:
    """MySQL transaction common functionality."""

    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
    }

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level."""
        from rhosocial.activerecord.backend.transaction import IsolationLevelError

        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise IsolationLevelError(error_msg)

        self._isolation_level = level
        self.log(logging.INFO, f"Isolation level set to {level}")

    def _build_set_isolation_sql(self, level: IsolationLevel) -> Tuple[str, tuple]:
        """Build SET TRANSACTION ISOLATION LEVEL SQL statement."""
        from rhosocial.activerecord.backend.transaction import IsolationLevelError

        level_str = self._ISOLATION_LEVELS.get(level)
        if not level_str:
            raise IsolationLevelError(f"Unsupported isolation level: {level}")
        return f"SET TRANSACTION ISOLATION LEVEL {level_str}", ()

    # --- Dialect-level transaction capability checks ---

    def supports_transaction_mode(self) -> bool:
        """MySQL supports READ ONLY transactions (5.6.5+)."""
        return self.version >= (5, 6, 5)

    def supports_isolation_level_in_begin(self) -> bool:
        """MySQL does not support isolation level in START TRANSACTION."""
        return False

    def supports_read_only_transaction(self) -> bool:
        """MySQL supports READ ONLY transactions (5.6.5+)."""
        return self.version >= (5, 6, 5)

    def supports_deferrable_transaction(self) -> bool:
        """MySQL does not support DEFERRABLE mode."""
        return False

    def supports_savepoint(self) -> bool:
        """MySQL supports savepoints."""
        return True

    def format_set_transaction(self, expr: "SetTransactionExpression") -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for MySQL."""
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        params = expr.get_params()
        parts = []

        isolation_level = params.get("isolation_level")
        if isolation_level is not None:
            level_names = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
            }
            level_name = level_names.get(isolation_level)
            if level_name:
                parts.append(f"ISOLATION LEVEL {level_name}")

        mode = params.get("mode")
        if mode is not None:
            if mode == TransactionMode.READ_ONLY:
                parts.append("READ ONLY")
            elif mode == TransactionMode.READ_WRITE:
                parts.append("READ WRITE")

        if not parts:
            return "SET TRANSACTION", ()

        return f"SET TRANSACTION {' '.join(parts)}", ()

    def format_begin_transaction(self, expr: "BeginTransactionExpression") -> Tuple[str, tuple]:
        """Format START TRANSACTION statement for MySQL."""
        from rhosocial.activerecord.backend.transaction import TransactionMode

        params = expr.get_params()

        mode = params.get("mode")
        if mode == TransactionMode.READ_ONLY:
            if self.supports_read_only_transaction():
                return "START TRANSACTION READ ONLY", ()
            else:
                from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError

                raise UnsupportedTransactionModeError(
                    feature="READ ONLY transactions",
                    backend="MySQL",
                    message="READ ONLY transactions require MySQL 5.6.5 or later.",
                )
        else:
            return "START TRANSACTION", ()
