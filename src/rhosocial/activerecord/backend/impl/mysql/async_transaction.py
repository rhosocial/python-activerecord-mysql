# src/rhosocial/activerecord/backend/impl/mysql/async_transaction.py
"""
Asynchronous transaction management for MySQL backend.

This module provides async transaction management capabilities for MySQL.
All transaction operations are delegated to the base class
which uses backend.execute() for SQL execution.
"""
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.transaction import (
    AsyncTransactionManager,
    IsolationLevel,
)

if TYPE_CHECKING:
    from .backend import AsyncMySQLBackend


class AsyncMySQLTransactionManager(AsyncTransactionManager):
    """Asynchronous transaction manager for MySQL backend.

    All transaction operations are delegated to the base class
    which uses backend.execute() for SQL execution.
    """

    def __init__(self, backend: "AsyncMySQLBackend", logger=None):
        super().__init__(backend, logger)
        # MySQL default isolation level is REPEATABLE READ
        self._isolation_level = IsolationLevel.REPEATABLE_READ
