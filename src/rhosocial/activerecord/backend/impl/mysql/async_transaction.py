# src/rhosocial/activerecord/backend/impl/mysql/async_transaction.py
"""
Asynchronous transaction management for MySQL backend.

This module provides async transaction management capabilities for MySQL,
including savepoints and proper isolation level handling.
"""
import logging

from rhosocial.activerecord.backend.transaction import (
    AsyncTransactionManager,
    IsolationLevel,
    TransactionState,
    TransactionError,
)
from .mixins import MySQLTransactionMixin


class AsyncMySQLTransactionManager(MySQLTransactionMixin, AsyncTransactionManager):
    """Asynchronous transaction manager for MySQL backend."""

    _ISOLATION_LEVELS = MySQLTransactionMixin._ISOLATION_LEVELS

    def __init__(self, connection, logger=None):
        """Initialize async MySQL transaction manager."""
        super().__init__(connection, logger)
        self._savepoint_counter = 0
        self._isolation_level = IsolationLevel.REPEATABLE_READ
        self._state = TransactionState.INACTIVE

    async def _ensure_connection_ready(self):
        """Ensure connection is ready for transaction operations asynchronously."""
        # For MySQL, we need to check if the connection exists and is valid
        if not self._connection:
            error_msg = "No valid connection for transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        # Check if the connection is still alive
        try:
            # Use ping to check connection health
            await self._connection.ping(reconnect=False)
        except Exception:
            error_msg = "Connection is not active"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from None

    async def _do_begin(self) -> None:
        """Begin a new transaction"""
        # Set isolation level if specified
        if self._isolation_level:
            isolation_map = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
            }
            isolation_str = isolation_map.get(self._isolation_level)
            if isolation_str:
                await self._execute_sql(f"SET TRANSACTION ISOLATION LEVEL {isolation_str}")

        # Start transaction
        await self._execute_sql("START TRANSACTION")
        self.log(logging.INFO, f"Started transaction with isolation level: {self._isolation_level or 'DEFAULT'}")

    async def _do_commit(self) -> None:
        """Commit the current transaction"""
        await self._execute_sql("COMMIT")
        self.log(logging.INFO, "Transaction committed successfully")

    async def _do_rollback(self) -> None:
        """Rollback the current transaction"""
        await self._execute_sql("ROLLBACK")
        self.log(logging.INFO, "Transaction rolled back successfully")

    async def _do_create_savepoint(self, name: str) -> None:
        """Create a savepoint"""
        await self._execute_sql(f"SAVEPOINT {name}")
        self.log(logging.INFO, f"Created savepoint: {name}")

    async def _do_release_savepoint(self, name: str) -> None:
        """Release a savepoint"""
        await self._execute_sql(f"RELEASE SAVEPOINT {name}")
        self.log(logging.INFO, f"Released savepoint: {name}")

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to a specified savepoint"""
        await self._execute_sql(f"ROLLBACK TO SAVEPOINT {name}")
        self.log(logging.INFO, f"Rolled back to savepoint: {name}")

    async def supports_savepoint(self) -> bool:
        """Check if savepoints are supported"""
        # MySQL supports savepoints since version 4.0.14
        try:
            version = await self.backend.get_server_version()
            # Savepoints are supported in MySQL 4.0.14 and later
            return version >= (4, 0, 14)
        except Exception:
            # If we can't determine the version, assume savepoints are supported
            return True

    # The base class AsyncTransactionManager provides the public interface methods
    # (begin, commit, rollback, create_savepoint, etc.) which delegate to the
    # abstract methods (_do_begin, _do_commit, etc.) that we've implemented above.
    # So we don't need to reimplement these methods here.

    async def _execute_sql(self, sql: str) -> None:
        """Execute a raw SQL statement using the connection."""
        # Use the connection directly
        cursor = await self._connection.cursor()
        await cursor.execute(sql)
        await cursor.close()

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, '_logger') and self._logger:
            self._logger.log(level, message)
        else:
            # Fallback logging
            print(f"[TRANSACTION] {message}")