# src/rhosocial/activerecord/backend/impl/mysql/async_transaction.py
"""
Asynchronous transaction management for MySQL backend.

This module provides async transaction management capabilities for MySQL,
including savepoints and proper isolation level handling.
"""
import logging
from typing import Dict, Optional

from rhosocial.activerecord.backend.transaction import (
    AsyncTransactionManager,
    IsolationLevel,
    TransactionState,
    TransactionError
)


class AsyncMySQLTransactionManager(AsyncTransactionManager):
    """Asynchronous transaction manager for MySQL backend."""

    def __init__(self, backend):
        """Initialize async MySQL transaction manager."""
        super().__init__(backend)
        self._savepoint_counter = 0

    async def begin(self, isolation_level: Optional[IsolationLevel] = None) -> None:
        """Begin a new transaction asynchronously."""
        if self.state == TransactionState.ACTIVE:
            raise TransactionError("Transaction already active. Use savepoints for nested transactions.")

        # Set isolation level if specified
        if isolation_level:
            isolation_map = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
            }
            isolation_str = isolation_map.get(isolation_level)
            if isolation_str:
                await self._execute_sql(f"SET TRANSACTION ISOLATION LEVEL {isolation_str}")

        # Start transaction
        await self._execute_sql("START TRANSACTION")
        self.state = TransactionState.ACTIVE
        self.log(logging.INFO, f"Started transaction with isolation level: {isolation_level or 'DEFAULT'}")

    async def commit(self) -> None:
        """Commit the current transaction asynchronously."""
        if self.state != TransactionState.ACTIVE:
            raise TransactionError("No active transaction to commit.")

        await self._execute_sql("COMMIT")
        self.state = TransactionState.COMMITTED
        self.log(logging.INFO, "Transaction committed successfully")

    async def rollback(self) -> None:
        """Rollback the current transaction asynchronously."""
        if self.state not in [TransactionState.ACTIVE, TransactionState.FAILED]:
            raise TransactionError("No active or failed transaction to rollback.")

        await self._execute_sql("ROLLBACK")
        self.state = TransactionState.ROLLEDBACK
        self.log(logging.INFO, "Transaction rolled back successfully")

    async def create_savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint within the current transaction asynchronously."""
        if self.state != TransactionState.ACTIVE:
            raise TransactionError("Cannot create savepoint outside of an active transaction.")

        savepoint_name = name or f"sp_{self._savepoint_counter}"
        self._savepoint_counter += 1

        await self._execute_sql(f"SAVEPOINT {savepoint_name}")
        self.savepoints.append(savepoint_name)
        self.log(logging.INFO, f"Created savepoint: {savepoint_name}")

        return savepoint_name

    async def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a specific savepoint asynchronously."""
        if name not in self.savepoints:
            raise TransactionError(f"Savepoint '{name}' does not exist or has already been released.")

        await self._execute_sql(f"ROLLBACK TO SAVEPOINT {name}")
        # Remove savepoints after the rolled-back one
        sp_index = self.savepoints.index(name)
        self.savepoints = self.savepoints[:sp_index + 1]
        self.log(logging.INFO, f"Rolled back to savepoint: {name}")

    async def release_savepoint(self, name: str) -> None:
        """Release a savepoint asynchronously."""
        if name not in self.savepoints:
            raise TransactionError(f"Savepoint '{name}' does not exist.")

        await self._execute_sql(f"RELEASE SAVEPOINT {name}")
        self.savepoints.remove(name)
        self.log(logging.INFO, f"Released savepoint: {name}")

    async def _execute_sql(self, sql: str) -> None:
        """Execute a raw SQL statement using the backend."""
        # This method assumes the backend has an async execute method
        # that can be used for transaction control statements
        await self.backend.execute(sql)

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, '_logger') and self._logger:
            self._logger.log(level, message)
        else:
            # Fallback logging
            print(f"[TRANSACTION] {message}")