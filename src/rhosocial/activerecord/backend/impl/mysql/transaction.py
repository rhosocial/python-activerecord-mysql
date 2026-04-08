# src/rhosocial/activerecord/backend/impl/mysql/transaction.py
"""MySQL synchronous transaction manager implementation.

This module provides MySQL-specific transaction management that handles
MySQL's requirement for SET TRANSACTION before START TRANSACTION.
"""
import logging
from typing import TYPE_CHECKING, Optional, Tuple

from rhosocial.activerecord.backend.transaction import (
    IsolationLevel,
    IsolationLevelError,
    TransactionManager,
)

if TYPE_CHECKING:
    from .backend import MySQLBackend


class MySQLTransactionManager(TransactionManager):
    """MySQL synchronous transaction manager implementation.

    MySQL requires SET TRANSACTION ISOLATION LEVEL to be executed before
    START TRANSACTION when a specific isolation level is needed. This class
    overrides _do_begin() to handle this sequencing.

    The format_begin_transaction() in MySQLDialect returns only "START TRANSACTION",
    while this class handles the SET TRANSACTION step separately.
    """

    # Isolation level mapping for MySQL
    _ISOLATION_LEVELS = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
    }

    def __init__(self, backend: "MySQLBackend", logger=None):
        """Initialize MySQL transaction manager.

        Args:
            backend: MySQLBackend instance.
            logger: Optional logger instance.
        """
        super().__init__(backend, logger)
        # Note: _isolation_level defaults to None (use database default).
        # MySQL's default isolation level is REPEATABLE READ, but we only
        # send SET TRANSACTION when user explicitly specifies a level.

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level.

        Note: In MySQL, isolation level can only be set before transaction starts.
        This setter only updates the internal state. The actual SET TRANSACTION
        statement is executed in _do_begin().

        Args:
            level: The isolation level to be set

        Raises:
            IsolationLevelError: If attempting to change isolation level while
                                 transaction is active
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")

        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        self._isolation_level = level
        self.log(logging.INFO, f"Isolation level set to {level}")

    def _build_set_isolation_sql(self, level: IsolationLevel) -> Tuple[str, tuple]:
        """Build SET TRANSACTION ISOLATION LEVEL SQL statement.

        Args:
            level: The isolation level to set.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            IsolationLevelError: If the isolation level is not supported.
        """
        level_str = self._ISOLATION_LEVELS.get(level)
        if not level_str:
            raise IsolationLevelError(f"Unsupported isolation level: {level}")
        return f"SET TRANSACTION ISOLATION LEVEL {level_str}", ()

    def _do_begin(self) -> None:
        """Begin a new transaction with MySQL-specific sequencing.

        MySQL requires:
        1. SET TRANSACTION ISOLATION LEVEL (if needed, before START)
        2. START TRANSACTION [READ ONLY]

        Each statement is executed separately via backend.execute().
        """
        # Step 1: Set isolation level if needed
        if self._isolation_level is not None:
            sql, params = self._build_set_isolation_sql(self._isolation_level)
            self.log(logging.DEBUG, f"Executing: {sql}")
            self._backend.execute(sql, params)

        # Step 2: Execute START TRANSACTION
        sql, params = self._build_begin_sql()
        self.log(logging.DEBUG, f"Executing: {sql}")
        self._backend.execute(sql, params)
