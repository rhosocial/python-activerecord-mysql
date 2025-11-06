# src/rhosocial/activerecord/backend/impl/mysql/transaction.py
import logging
from typing import Dict, Optional
from mysql.connector.errors import Error as MySQLError, ProgrammingError

from rhosocial.activerecord.backend.errors import TransactionError, IsolationLevelError
from rhosocial.activerecord.backend.transaction import (
    TransactionManager,
    AsyncTransactionManager,
    IsolationLevel,
    TransactionState
)


class MySQLTransactionManager(TransactionManager):
    """MySQL synchronous transaction manager implementation."""

    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    def __init__(self, connection, logger=None):
        """Initialize MySQL transaction manager."""
        super().__init__(connection, logger)
        self._isolation_level = IsolationLevel.REPEATABLE_READ
        self._state = TransactionState.INACTIVE

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level."""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level

    def _ensure_connection_ready(self):
        """Ensure connection is ready for transaction operations."""
        if not self._connection or not hasattr(self._connection, 'is_connected'):
            error_msg = "No valid connection for transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        if not self._connection.is_connected():
            try:
                self._connection.reconnect()
                self.log(logging.WARNING, "Connection was lost, reconnected")
            except MySQLError as e:
                error_msg = f"Failed to reconnect: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise TransactionError(error_msg)

    def _do_begin(self) -> None:
        """Begin MySQL transaction."""
        self._ensure_connection_ready()

        try:
            isolation_string = self._ISOLATION_LEVELS.get(self._isolation_level)

            cursor = self._connection.cursor()
            cursor.execute("SELECT @@autocommit")
            auto_commit = cursor.fetchone()[0]
            cursor.close()

            if auto_commit == 0 and self._transaction_level == 0:
                self.log(logging.WARNING, "Found existing transaction, attempting to rollback")
                try:
                    self._connection.rollback()
                except MySQLError:
                    pass

            self._connection.start_transaction(isolation_level=isolation_string)
            self._state = TransactionState.ACTIVE

            self.log(logging.DEBUG, f"Started MySQL transaction with isolation level {isolation_string}")
        except ProgrammingError as e:
            if "Transaction already in progress" in str(e) and self._transaction_level == 0:
                self.log(logging.WARNING, "Transaction already in progress at server level")
                self._state = TransactionState.ACTIVE
            else:
                error_msg = f"Failed to begin transaction: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise TransactionError(error_msg)
        except MySQLError as e:
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_commit(self) -> None:
        """Commit MySQL transaction."""
        self._ensure_connection_ready()

        try:
            self._connection.commit()
            self._state = TransactionState.COMMITTED
            self.log(logging.DEBUG, "Committed MySQL transaction")
        except MySQLError as e:
            error_msg = f"Failed to commit transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_rollback(self) -> None:
        """Rollback MySQL transaction."""
        self._ensure_connection_ready()

        try:
            self._connection.rollback()
            self._state = TransactionState.ROLLED_BACK
            self.log(logging.DEBUG, "Rolled back MySQL transaction")
        except MySQLError as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_create_savepoint(self, name: str) -> None:
        """Create MySQL savepoint."""
        self._ensure_connection_ready()

        try:
            cursor = self._connection.cursor()
            cursor.execute(f"SAVEPOINT {name}")
            cursor.close()
            self.log(logging.DEBUG, f"Created savepoint: {name}")
        except MySQLError as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_release_savepoint(self, name: str) -> None:
        """Release MySQL savepoint."""
        self._ensure_connection_ready()

        try:
            cursor = self._connection.cursor()
            cursor.execute(f"RELEASE SAVEPOINT {name}")
            cursor.close()
            self.log(logging.DEBUG, f"Released savepoint: {name}")
        except MySQLError as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to MySQL savepoint."""
        self._ensure_connection_ready()

        try:
            cursor = self._connection.cursor()
            cursor.execute(f"ROLLBACK TO SAVEPOINT {name}")
            cursor.close()
            self.log(logging.DEBUG, f"Rolled back to savepoint: {name}")
        except MySQLError as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported."""
        return True


class AsyncMySQLTransactionManager(AsyncTransactionManager):
    """MySQL asynchronous transaction manager implementation."""

    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    def __init__(self, connection, logger=None):
        """Initialize async MySQL transaction manager."""
        super().__init__(connection, logger)
        self._isolation_level = IsolationLevel.REPEATABLE_READ
        self._state = TransactionState.INACTIVE

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level."""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level

    async def _ensure_connection_ready(self):
        """Ensure connection is ready for transaction operations asynchronously."""
        if not self._connection:
            error_msg = "No valid connection for transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        # For async connections, we might need to check differently
        # This depends on the async MySQL driver being used (aiomysql, asyncmy, etc.)

    async def _do_begin(self) -> None:
        """Begin MySQL transaction asynchronously."""
        await self._ensure_connection_ready()

        try:
            isolation_string = self._ISOLATION_LEVELS.get(self._isolation_level)

            # Set isolation level
            cursor = await self._connection.cursor()
            await cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_string}")

            # Start transaction
            await cursor.execute("START TRANSACTION")
            await cursor.close()

            self._state = TransactionState.ACTIVE
            self.log(logging.DEBUG, f"Started MySQL transaction with isolation level {isolation_string}")
        except Exception as e:
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    async def _do_commit(self) -> None:
        """Commit MySQL transaction asynchronously."""
        await self._ensure_connection_ready()

        try:
            await self._connection.commit()
            self._state = TransactionState.COMMITTED
            self.log(logging.DEBUG, "Committed MySQL transaction")
        except Exception as e:
            error_msg = f"Failed to commit transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    async def _do_rollback(self) -> None:
        """Rollback MySQL transaction asynchronously."""
        await self._ensure_connection_ready()

        try:
            await self._connection.rollback()
            self._state = TransactionState.ROLLED_BACK
            self.log(logging.DEBUG, "Rolled back MySQL transaction")
        except Exception as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    async def _do_create_savepoint(self, name: str) -> None:
        """Create MySQL savepoint asynchronously."""
        await self._ensure_connection_ready()

        try:
            cursor = await self._connection.cursor()
            await cursor.execute(f"SAVEPOINT {name}")
            await cursor.close()
            self.log(logging.DEBUG, f"Created savepoint: {name}")
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    async def _do_release_savepoint(self, name: str) -> None:
        """Release MySQL savepoint asynchronously."""
        await self._ensure_connection_ready()

        try:
            cursor = await self._connection.cursor()
            await cursor.execute(f"RELEASE SAVEPOINT {name}")
            await cursor.close()
            self.log(logging.DEBUG, f"Released savepoint: {name}")
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to MySQL savepoint asynchronously."""
        await self._ensure_connection_ready()

        try:
            cursor = await self._connection.cursor()
            await cursor.execute(f"ROLLBACK TO SAVEPOINT {name}")
            await cursor.close()
            self.log(logging.DEBUG, f"Rolled back to savepoint: {name}")
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    async def supports_savepoint(self) -> bool:
        """Check if savepoints are supported asynchronously."""
        return True