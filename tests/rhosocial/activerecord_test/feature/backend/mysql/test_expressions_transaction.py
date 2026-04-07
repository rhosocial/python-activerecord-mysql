# tests/rhosocial/activerecord_test/feature/backend/mysql/test_expressions_transaction.py
"""Tests for MySQL transaction expression classes.

MySQL Transaction Behavior:
- Isolation level must be set BEFORE START TRANSACTION using SET TRANSACTION
- START TRANSACTION can include READ ONLY / READ WRITE modes
- The dialect's format_begin_transaction() only returns START TRANSACTION
- SetTransactionExpression is used for isolation level settings
"""
import pytest
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    CommitTransactionExpression,
    RollbackTransactionExpression,
    SavepointExpression,
    ReleaseSavepointExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode


class TestMySQLBeginTransactionExpression:
    """Tests for MySQL BeginTransactionExpression.

    Note: MySQL does not support isolation level in START TRANSACTION.
    The dialect's supports_isolation_level_in_begin() returns False.
    Use SetTransactionExpression to set isolation level before START TRANSACTION.
    """

    def test_basic_begin(self, mysql_dialect):
        """Test basic START TRANSACTION."""
        expr = BeginTransactionExpression(mysql_dialect)
        sql, params = expr.to_sql()
        assert sql == "START TRANSACTION"
        assert params == ()

    def test_begin_with_isolation_level_returns_only_start(self, mysql_dialect):
        """Test that isolation level is NOT included in START TRANSACTION.

        MySQL requires SET TRANSACTION ISOLATION LEVEL to be executed
        separately before START TRANSACTION. The dialect's format_begin_transaction()
        only returns the START TRANSACTION statement.
        """
        expr = BeginTransactionExpression(mysql_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        # MySQL dialect does NOT include isolation level in START TRANSACTION
        assert sql == "START TRANSACTION"
        assert params == ()
        # Verify dialect capability
        assert mysql_dialect.supports_isolation_level_in_begin() == False

    def test_begin_read_only(self, mysql_dialect):
        """Test START TRANSACTION READ ONLY."""
        expr = BeginTransactionExpression(mysql_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert sql == "START TRANSACTION READ ONLY"
        assert params == ()

    def test_begin_read_write(self, mysql_dialect):
        """Test START TRANSACTION READ WRITE."""
        expr = BeginTransactionExpression(mysql_dialect)
        expr.read_write()
        sql, params = expr.to_sql()
        assert sql == "START TRANSACTION"
        assert params == ()

    def test_begin_with_isolation_and_read_only(self, mysql_dialect):
        """Test START TRANSACTION with isolation level and READ ONLY.

        The isolation level is ignored by the dialect in START TRANSACTION.
        Use SetTransactionExpression for isolation level, then BeginTransactionExpression
        for READ ONLY mode.
        """
        expr = BeginTransactionExpression(mysql_dialect)
        expr.isolation_level(IsolationLevel.READ_COMMITTED).read_only()
        sql, params = expr.to_sql()
        # Only READ ONLY mode is included, isolation level is NOT
        assert sql == "START TRANSACTION READ ONLY"
        assert params == ()

    @pytest.mark.parametrize("level", [
        IsolationLevel.READ_UNCOMMITTED,
        IsolationLevel.READ_COMMITTED,
        IsolationLevel.REPEATABLE_READ,
        IsolationLevel.SERIALIZABLE,
    ])
    def test_begin_with_isolation_returns_start_transaction(self, mysql_dialect, level):
        """Test that START TRANSACTION does not include isolation level.

        MySQL requires separate SET TRANSACTION ISOLATION LEVEL statement.
        """
        expr = BeginTransactionExpression(mysql_dialect)
        expr.isolation_level(level)
        sql, params = expr.to_sql()
        # MySQL dialect does NOT include isolation level
        assert sql == "START TRANSACTION"
        assert params == ()


class TestMySQLSetTransactionExpression:
    """Tests for MySQL SetTransactionExpression.

    MySQL uses SET TRANSACTION ISOLATION LEVEL before START TRANSACTION
    to set the isolation level for the next transaction.
    """

    def test_set_isolation_level(self, mysql_dialect):
        """Test SET TRANSACTION ISOLATION LEVEL."""
        expr = SetTransactionExpression(mysql_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
        assert params == ()

    @pytest.mark.parametrize("level,expected_name", [
        (IsolationLevel.READ_UNCOMMITTED, "READ UNCOMMITTED"),
        (IsolationLevel.READ_COMMITTED, "READ COMMITTED"),
        (IsolationLevel.REPEATABLE_READ, "REPEATABLE READ"),
        (IsolationLevel.SERIALIZABLE, "SERIALIZABLE"),
    ])
    def test_all_isolation_levels(self, mysql_dialect, level, expected_name):
        """Test all isolation levels in SET TRANSACTION."""
        expr = SetTransactionExpression(mysql_dialect)
        expr.isolation_level(level)
        sql, params = expr.to_sql()
        assert expected_name in sql
        assert params == ()

    def test_set_read_only(self, mysql_dialect):
        """Test SET TRANSACTION READ ONLY."""
        expr = SetTransactionExpression(mysql_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION READ ONLY"
        assert params == ()

    def test_set_read_write(self, mysql_dialect):
        """Test SET TRANSACTION READ WRITE."""
        expr = SetTransactionExpression(mysql_dialect)
        expr.read_write()
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION READ WRITE"
        assert params == ()


class TestMySQLCommitRollback:
    """Tests for MySQL COMMIT and ROLLBACK."""

    def test_commit(self, mysql_dialect):
        """Test COMMIT statement."""
        expr = CommitTransactionExpression(mysql_dialect)
        sql, params = expr.to_sql()
        assert sql == "COMMIT"
        assert params == ()

    def test_rollback(self, mysql_dialect):
        """Test ROLLBACK statement."""
        expr = RollbackTransactionExpression(mysql_dialect)
        sql, params = expr.to_sql()
        assert sql == "ROLLBACK"
        assert params == ()

    def test_rollback_to_savepoint(self, mysql_dialect):
        """Test ROLLBACK TO SAVEPOINT statement."""
        expr = RollbackTransactionExpression(mysql_dialect)
        expr.to_savepoint("my_savepoint")
        sql, params = expr.to_sql()
        assert "ROLLBACK" in sql
        assert "SAVEPOINT" in sql
        assert params == ()


class TestMySQLSavepoint:
    """Tests for MySQL SAVEPOINT operations."""

    def test_savepoint(self, mysql_dialect):
        """Test SAVEPOINT statement."""
        expr = SavepointExpression(mysql_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_release_savepoint(self, mysql_dialect):
        """Test RELEASE SAVEPOINT statement."""
        expr = ReleaseSavepointExpression(mysql_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "RELEASE SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()


class TestMySQLTransactionCapabilities:
    """Tests for MySQL transaction capabilities."""

    def test_supports_transaction_mode(self, mysql_dialect):
        """Test MySQL supports transaction mode."""
        assert mysql_dialect.supports_transaction_mode() == True

    def test_supports_isolation_level_in_begin(self, mysql_dialect):
        """Test MySQL does not support isolation level in BEGIN."""
        assert mysql_dialect.supports_isolation_level_in_begin() == False

    def test_supports_read_only_transaction(self, mysql_dialect):
        """Test MySQL supports READ ONLY transactions (5.6.5+)."""
        assert mysql_dialect.supports_read_only_transaction() == True

    def test_supports_deferrable_transaction(self, mysql_dialect):
        """Test MySQL does not support DEFERRABLE transactions."""
        assert mysql_dialect.supports_deferrable_transaction() == False

    def test_supports_savepoint(self, mysql_dialect):
        """Test MySQL supports savepoints."""
        assert mysql_dialect.supports_savepoint() == True
