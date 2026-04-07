# tests/rhosocial/activerecord_test/feature/backend/mysql/test_expressions_transaction.py
"""Tests for MySQL transaction expression classes."""
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
    """Tests for MySQL BeginTransactionExpression."""

    def test_basic_begin(self, mysql_dialect):
        """Test basic START TRANSACTION."""
        expr = BeginTransactionExpression(mysql_dialect)
        sql, params = expr.to_sql()
        assert sql == "START TRANSACTION"
        assert params == ()

    def test_begin_with_isolation_level(self, mysql_dialect):
        """Test START TRANSACTION with isolation level (requires SET TRANSACTION first)."""
        expr = BeginTransactionExpression(mysql_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE" in sql
        assert "START TRANSACTION" in sql
        assert params == ()

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
        """Test START TRANSACTION with isolation level and READ ONLY."""
        expr = BeginTransactionExpression(mysql_dialect)
        expr.isolation_level(IsolationLevel.READ_COMMITTED).read_only()
        sql, params = expr.to_sql()
        assert "SET TRANSACTION ISOLATION LEVEL READ COMMITTED" in sql
        assert "START TRANSACTION READ ONLY" in sql
        assert params == ()

    @pytest.mark.parametrize("level,expected_name", [
        (IsolationLevel.READ_UNCOMMITTED, "READ UNCOMMITTED"),
        (IsolationLevel.READ_COMMITTED, "READ COMMITTED"),
        (IsolationLevel.REPEATABLE_READ, "REPEATABLE READ"),
        (IsolationLevel.SERIALIZABLE, "SERIALIZABLE"),
    ])
    def test_all_isolation_levels(self, mysql_dialect, level, expected_name):
        """Test all isolation levels."""
        expr = BeginTransactionExpression(mysql_dialect)
        expr.isolation_level(level)
        sql, params = expr.to_sql()
        assert expected_name in sql
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
