# src/rhosocial/activerecord/backend/impl/mysql/transaction.py
"""MySQL synchronous transaction manager implementation.

This module provides a simplified MySQL transaction manager that uses
the base TransactionManager for all operations via backend.execute().
"""
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.transaction import (
    IsolationLevel,
    TransactionManager,
)

if TYPE_CHECKING:
    from .backend import MySQLBackend


class MySQLTransactionManager(TransactionManager):
    """MySQL synchronous transaction manager implementation.

    All transaction operations are delegated to the base class
    which uses backend.execute() for SQL execution.
    """

    def __init__(self, backend: "MySQLBackend", logger=None):
        """Initialize MySQL transaction manager.

        Args:
            backend: MySQLBackend instance.
            logger: Optional logger instance.
        """
        super().__init__(backend, logger)
        # MySQL default isolation level is REPEATABLE READ
        self._isolation_level = IsolationLevel.REPEATABLE_READ
