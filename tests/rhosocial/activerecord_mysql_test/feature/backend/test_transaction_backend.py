# tests/rhosocial/activerecord_mysql_test/feature/backend/test_transaction.py
import pytest


@pytest.fixture
def setup_test_table(mysql_backend):
    mysql_backend.execute("DROP TABLE IF EXISTS test_table")
    mysql_backend.execute("""
        CREATE TABLE test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            age INT
        )
    """)
    yield
    mysql_backend.execute("DROP TABLE IF EXISTS test_table")


def test_transaction_commit(mysql_backend, setup_test_table):
    """Test transaction commit"""
    with mysql_backend.transaction():
        sql = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
        params = ("test", 20)
        mysql_backend.execute(sql, params)
    row = mysql_backend.fetch_one("SELECT * FROM test_table WHERE name = %s", ("test",))
    assert row is not None


def test_transaction_rollback(mysql_backend, setup_test_table):
    """Test transaction rollback"""
    try:
        with mysql_backend.transaction():
            sql = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
            params = ("test", 20)
            mysql_backend.execute(sql, params)
            raise Exception("Force rollback")
    except Exception:
        pass
    row = mysql_backend.fetch_one("SELECT * FROM test_table WHERE name = %s", ("test",))
    assert row is None


def test_nested_transaction(mysql_backend, setup_test_table):
    """Test nested transactions"""
    with mysql_backend.transaction():
        sql_outer = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
        params_outer = ("outer", 20)
        mysql_backend.execute(sql_outer, params_outer)
        with mysql_backend.transaction():
            sql_inner = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
            params_inner = ("inner", 30)
            mysql_backend.execute(sql_inner, params_inner)
    rows = mysql_backend.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 2


def test_transaction_get_cursor(mysql_backend):
    """Test that _get_cursor can be called within a transaction context."""
    with mysql_backend.transaction():
        cursor = mysql_backend._get_cursor()
        assert cursor is not None
