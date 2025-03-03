import logging
from typing import Dict, Optional
from mysql.connector.errors import Error as MySQLError, ProgrammingError

from ...errors import TransactionError, IsolationLevelError
from ...transaction import TransactionManager, IsolationLevel, TransactionState


class MySQLTransactionManager(TransactionManager):
    """MySQL transaction manager implementation.

    Provides MySQL-specific transaction management with support for:
    - Different isolation levels
    - Savepoint handling
    - Automatic rollback on exceptions
    - Nested transactions using savepoints
    """

    # Mapping of isolation levels to MySQL-connector-python supported values
    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",  # MySQL default
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    def __init__(self, connection, logger=None):
        """Initialize MySQL transaction manager.

        Args:
            connection: MySQL database connection
            logger: Optional logger instance
        """
        super().__init__(connection, logger)
        # MySQL specific initialization
        self._isolation_level = IsolationLevel.REPEATABLE_READ  # MySQL default
        self._state = TransactionState.INACTIVE  # 初始状态为非活动

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level.

        Returns:
            Optional[IsolationLevel]: Current isolation level
        """
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level.

        Args:
            level: Isolation level to set

        Raises:
            IsolationLevelError: If attempting to change isolation level during active transaction
            TransactionError: If isolation level is not supported by MySQL
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        # Check if MySQL supports this isolation level
        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level

    def _ensure_connection_ready(self):
        """Ensure connection is ready for transaction operations.

        Checks if connection is alive and (if possible) if in auto-commit mode.
        """
        if not self._connection or not hasattr(self._connection, 'is_connected'):
            error_msg = "No valid connection for transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        # Check if connection is alive
        if not self._connection.is_connected():
            try:
                self._connection.reconnect()
                self.log(logging.WARNING, "Connection was lost, reconnected")
            except MySQLError as e:
                error_msg = f"Failed to reconnect: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise TransactionError(error_msg)

    def _do_begin(self) -> None:
        """Begin MySQL transaction.

        Uses mysql-connector-python's start_transaction method
        with the appropriate isolation level parameter.

        Raises:
            TransactionError: If beginning the transaction fails
        """
        self._ensure_connection_ready()

        try:
            # Get MySQL isolation level string
            isolation_string = self._ISOLATION_LEVELS.get(self._isolation_level)

            # Check if a transaction is already active at server level
            cursor = self._connection.cursor()
            cursor.execute("SELECT @@autocommit")
            auto_commit = cursor.fetchone()[0]
            cursor.close()

            # If autocommit is 0, a transaction is already active
            if auto_commit == 0 and self._transaction_level == 0:
                # Try to clean up the existing transaction
                self.log(logging.WARNING, "Found existing transaction, attempting to rollback")
                try:
                    self._connection.rollback()
                except MySQLError:
                    pass

            # Use mysql-connector-python's native isolation level support
            self._connection.start_transaction(isolation_level=isolation_string)
            self._state = TransactionState.ACTIVE

            self.log(logging.DEBUG, f"Started MySQL transaction with isolation level {isolation_string}")
        except ProgrammingError as e:
            # Special handling for "Transaction already in progress" error
            if "Transaction already in progress" in str(e) and self._transaction_level == 0:
                self.log(logging.WARNING, "Transaction already in progress at server level")
                self._state = TransactionState.ACTIVE
                # Don't throw an error, just adapt to the existing transaction
            else:
                error_msg = f"Failed to begin transaction: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise TransactionError(error_msg)
        except MySQLError as e:
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_commit(self) -> None:
        """Commit MySQL transaction.

        Raises:
            TransactionError: If commit fails
        """
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
        """Rollback MySQL transaction.

        Raises:
            TransactionError: If rollback fails
        """
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
        """Create MySQL savepoint.

        Args:
            name: Savepoint name

        Raises:
            TransactionError: If creating savepoint fails
        """
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
        """Release MySQL savepoint.

        Args:
            name: Savepoint name

        Raises:
            TransactionError: If releasing savepoint fails
        """
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
        """Rollback to MySQL savepoint.

        Args:
            name: Savepoint name

        Raises:
            TransactionError: If rollback to savepoint fails
        """
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
        """Check if savepoints are supported.

        Returns:
            bool: Always returns True for MySQL
        """
        return True