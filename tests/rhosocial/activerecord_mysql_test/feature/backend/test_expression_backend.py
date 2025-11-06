# tests/rhosocial/activerecord_mysql_test/feature/backend/test_expression.py
import pytest
from datetime import datetime

from rhosocial.activerecord.backend.errors import DatabaseError, OperationalError


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


def test_update_with_expression(mysql_backend, setup_test_table):
    """Test updating with an expression"""
    # Insert test data
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    # Use expression to update age
    result = mysql_backend.execute(
        "UPDATE test_table SET age = %s WHERE name = %s",
        (mysql_backend.create_expression("age + 1"), "test_user")
    )

    assert result.affected_rows == 1

    # Verify update result
    row = mysql_backend.fetch_one(
        "SELECT age FROM test_table WHERE name = %s",
        ("test_user",)
    )
    assert row["age"] == 21


def test_multiple_expressions(mysql_backend, setup_test_table):
    """Test using multiple expressions in the same SQL"""
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    result = mysql_backend.execute(
        "UPDATE test_table SET age = %s, name = %s WHERE name = %s",
        (
            mysql_backend.create_expression("age + 10"),
            mysql_backend.create_expression("CONCAT(name, '_updated')"),
            "test_user"
        )
    )

    assert result.affected_rows == 1

    row = mysql_backend.fetch_one(
        "SELECT name, age FROM test_table WHERE name = %s",
        ("test_user_updated",)
    )
    assert row["age"] == 30
    assert row["name"] == "test_user_updated"


def test_mixed_params_and_expressions(mysql_backend, setup_test_table):
    """Test mixing regular parameters and expressions"""
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    result = mysql_backend.execute(
        "UPDATE test_table SET age = %s, name = %s WHERE name = %s AND age >= %s",
        (
            mysql_backend.create_expression("age * 2"),
            "new_name",
            "test_user",
            18
        )
    )

    assert result.affected_rows == 1

    row = mysql_backend.fetch_one(
        "SELECT name, age FROM test_table WHERE name = %s",
        ("new_name",)
    )
    assert row["age"] == 40
    assert row["name"] == "new_name"


def test_expression_with_placeholder(mysql_backend, setup_test_table):
    """Test expression containing a question mark"""
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )
    with pytest.raises(DatabaseError):
        mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s",
            (mysql_backend.create_expression("age + ?"), "test_user")
        )


def test_expression_in_subquery(mysql_backend, setup_test_table):
    """Test using expression in subquery"""
    # Insert test data
    result = mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s), (%s, %s)",
        ("user1", 20, "user2", 30)
    )
    assert result.affected_rows == 2, "Should insert two records"

    # Verify inserted data
    rows = mysql_backend.fetch_all(
        "SELECT * FROM test_table ORDER BY age"
    )
    assert len(rows) == 2, "Should have two records"
    assert rows[0]["age"] == 20, "First record age should be 20"
    assert rows[1]["age"] == 30, "Second record age should be 30"

    # Test subquery with expression
    result = mysql_backend.execute(
        """
        SELECT *
        FROM test_table
        WHERE age > %s
          AND age < %s
        """,
        (
            mysql_backend.create_expression("(SELECT MIN(age) FROM test_table)"),
            mysql_backend.create_expression("(SELECT MAX(age) FROM test_table)")
        )
    )

    assert len(result.data) == 0, "Should not have matching records since condition is MIN < age < MAX"


def test_expression_in_insert(mysql_backend, setup_test_table):
    """Test using expression in INSERT statement"""
    # Get max age first
    max_age_result = mysql_backend.fetch_one("SELECT MAX(age) as max_age FROM test_table")
    max_age = max_age_result["max_age"] if max_age_result and max_age_result["max_age"] is not None else 0

    mysql_backend.execute(
        "INSERT INTO test_table (name, age, created_at) VALUES (%s, %s, %s)",
        (
            "test_user",
            max_age + 1,
            mysql_backend.create_expression("CURRENT_TIMESTAMP")
        )
    )

    row = mysql_backend.fetch_one(
        "SELECT * FROM test_table WHERE name = %s",
        ("test_user",)
    )

    assert row["age"] == max_age + 1
    assert isinstance(row["created_at"], datetime)  # Ensure timestamp is correctly set


def test_complex_expression(mysql_backend, setup_test_table):
    """Test complex expression"""
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    result = mysql_backend.execute(
        "UPDATE test_table SET age = %s WHERE name = %s",
        (
            mysql_backend.create_expression("""
                CASE 
                    WHEN age < 18 THEN 18 
                    WHEN age > 60 THEN 60 
                    ELSE age + 5 
                END
            """),
            "test_user"
        )
    )

    assert result.affected_rows == 1

    row = mysql_backend.fetch_one(
        "SELECT age FROM test_table WHERE name = %s",
        ("test_user",)
    )
    assert row["age"] == 25


def test_invalid_expression(mysql_backend, setup_test_table):
    """Test invalid expression"""
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    with pytest.raises(OperationalError):
        mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s",
            (mysql_backend.create_expression("invalid_column + 1"), "test_user")
        )


def test_expression_count_mismatch(mysql_backend, setup_test_table):
    """Test parameter count mismatch scenario"""
    mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    # Case 1: Too few parameters
    with pytest.raises(ValueError, match="Parameter count mismatch: SQL needs 3 parameters but 2 were provided"):
        mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s AND age = %s",
            (mysql_backend.create_expression("age + 1"), "test_user")  # Missing last parameter
        )

    # Case 2: Too many parameters
    with pytest.raises(ValueError, match="Parameter count mismatch: SQL needs 2 parameters but 3 were provided"):
        mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s",
            (mysql_backend.create_expression("age + 1"), "test_user", 20)  # Extra parameter
        )
