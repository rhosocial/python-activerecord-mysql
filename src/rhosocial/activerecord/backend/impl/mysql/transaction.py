# src/rhosocial/activerecord/backend/impl/mysql/transaction.py
"""MySQL synchronous transaction manager implementation.

This module provides MySQL-specific transaction management that handles
MySQL's requirement for SET TRANSACTION before START TRANSACTION.
"""
import logging
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.transaction import (
    TransactionManager,
)

from .mixins import MySQLTransactionMixin

if TYPE_CHECKING:
    from .backend import MySQLBackend


class MySQLTransactionManager(MySQLTransactionMixin, TransactionManager):
    """MySQL synchronous transaction manager implementation.

    MySQL requires SET TRANSACTION ISOLATION LEVEL to be executed before
    START TRANSACTION when a specific isolation level is needed. This class
    overrides _do_begin() to handle this sequencing.

    The format_begin_transaction() in MySQLDialect returns only "START TRANSACTION",
    while this class handles the SET TRANSACTION step separately.

    Non-I/O methods (isolation_level, _build_set_isolation_sql, _ISOLATION_LEVELS)
    are inherited from MySQLTransactionMixin.
    """

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
