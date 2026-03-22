# src/rhosocial/activerecord/backend/impl/mysql/transaction.py
"""MySQL synchronous transaction manager implementation."""
import logging
from mysql.connector.errors import Error as MySQLError, ProgrammingError

from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.transaction import (
    IsolationLevel,
    TransactionManager,
    TransactionState,
)
from .mixins import MySQLTransactionMixin


class MySQLTransactionManager(MySQLTransactionMixin, TransactionManager):
    """MySQL synchronous transaction manager implementation."""

    _ISOLATION_LEVELS = MySQLTransactionMixin._ISOLATION_LEVELS

    def __init__(self, connection, logger=None):
        """Initialize MySQL transaction manager."""
        super().__init__(connection, logger)
        self._isolation_level = IsolationLevel.REPEATABLE_READ
        self._state = TransactionState.INACTIVE

    def _ensure_connection_ready(self):
        """Ensure connection is ready for transaction operations."""
        # For MySQL, we need to check if the connection exists and is valid
        # The base TransactionManager class has a _backend reference that we can use
        if not self._connection:
            error_msg = "No valid connection for transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        # Check if the connection is still alive
        try:
            # Use ping to check connection health
            self._connection.ping(reconnect=False)
        except MySQLError:
            error_msg = "Connection is not active"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from None

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
                raise TransactionError(error_msg) from e
        except MySQLError as e:
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

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
            raise TransactionError(error_msg) from e

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
            raise TransactionError(error_msg) from e

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
            raise TransactionError(error_msg) from e

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
            raise TransactionError(error_msg) from e

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
            raise TransactionError(error_msg) from e

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported."""
        return True