# tests/rhosocial/activerecord_mysql_test/feature/backend/test_crud.py
from datetime import datetime
import pytest


@pytest.fixture
def setup_test_table(mysql_backend):
    mysql_backend.execute("DROP TABLE IF EXISTS test_table")
    mysql_backend.execute("""
        CREATE TABLE test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            age INT,
            created_at DATETIME
        )
    """)
    yield
    mysql_backend.execute("DROP TABLE IF EXISTS test_table")


def test_insert_success(mysql_backend, setup_test_table):
    """Test successful insertion"""
    sql = "INSERT INTO test_table (name, age, created_at) VALUES (%s, %s, %s)"
    params = ("test", 20, datetime.now())
    result = mysql_backend.execute(sql, params)
    assert result.affected_rows == 1
    assert result.last_insert_id is not None


def test_insert_with_invalid_data(mysql_backend, setup_test_table):
    """Test inserting invalid data"""
    with pytest.raises(Exception):  # Specific exception type depends on implementation
        sql = "INSERT INTO test_table (invalid_column) VALUES (%s)"
        params = ("value",)
        mysql_backend.execute(sql, params)


def test_fetch_one(mysql_backend, setup_test_table):
    """Test querying a single record"""
    sql = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
    params = ("test", 20)
    mysql_backend.execute(sql, params)
    row = mysql_backend.fetch_one("SELECT * FROM test_table WHERE name = %s", ("test",))
    assert row is not None
    assert row["name"] == "test"
    assert row["age"] == 20


def test_fetch_all(mysql_backend, setup_test_table):
    """Test querying multiple records"""
    sql = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
    params1 = ("test1", 20)
    params2 = ("test2", 30)
    mysql_backend.execute(sql, params1)
    mysql_backend.execute(sql, params2)
    rows = mysql_backend.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 2
    assert rows[0]["age"] == 20
    assert rows[1]["age"] == 30


def test_update(mysql_backend, setup_test_table):
    """Test updating a record"""
    sql = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
    params = ("test", 20)
    mysql_backend.execute(sql, params)

    sql = "UPDATE test_table SET age = %s WHERE name = %s"
    params = (21, "test")
    result = mysql_backend.execute(sql, params)
    assert result.affected_rows == 1

    row = mysql_backend.fetch_one("SELECT * FROM test_table WHERE name = %s", ("test",))
    assert row["age"] == 21


def test_delete(mysql_backend, setup_test_table):
    """Test deleting a record"""
    sql = "INSERT INTO test_table (name, age) VALUES (%s, %s)"
    params = ("test", 20)
    mysql_backend.execute(sql, params)

    sql = "DELETE FROM test_table WHERE name = %s"
    params = ("test",)
    result = mysql_backend.execute(sql, params)
    assert result.affected_rows == 1

    row = mysql_backend.fetch_one("SELECT * FROM test_table WHERE name = %s", ("test",))
    assert row is None


def test_execute_many(mysql_backend, setup_test_table):
    """Test batch insertion"""
    data = [
        ("name1", 20),
        ("name2", 30),
        ("name3", 40)
    ]
    result = mysql_backend.execute_many(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        data
    )
    assert result.affected_rows == 3
    rows = mysql_backend.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 3
