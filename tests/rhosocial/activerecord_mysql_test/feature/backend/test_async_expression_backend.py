# tests/rhosocial/activerecord_mysql_test/feature/backend/test_async_expression.py
import pytest
import pytest_asyncio
from datetime import datetime

from rhosocial.activerecord.backend.errors import DatabaseError, OperationalError


@pytest_asyncio.fixture
async def setup_test_table(async_mysql_backend):
    await async_mysql_backend.execute("DROP TABLE IF EXISTS test_table")
    await async_mysql_backend.execute("""
        CREATE TABLE test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            age INT,
            created_at DATETIME
        )
    """)
    yield
    await async_mysql_backend.execute("DROP TABLE IF EXISTS test_table")


@pytest.mark.asyncio
async def test_update_with_expression(async_mysql_backend, setup_test_table):
    """Test updating with an expression"""
    # Insert test data
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    # Use expression to update age
    result = await async_mysql_backend.execute(
        "UPDATE test_table SET age = %s WHERE name = %s",
        (async_mysql_backend.create_expression("age + 1"), "test_user")
    )

    assert result.affected_rows == 1

    # Verify update result
    row = await async_mysql_backend.fetch_one(
        "SELECT age FROM test_table WHERE name = %s",
        ("test_user",)
    )
    assert row["age"] == 21


@pytest.mark.asyncio
async def test_multiple_expressions(async_mysql_backend, setup_test_table):
    """Test using multiple expressions in the same SQL"""
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    result = await async_mysql_backend.execute(
        "UPDATE test_table SET age = %s, name = %s WHERE name = %s",
        (
            async_mysql_backend.create_expression("age + 10"),
            async_mysql_backend.create_expression("CONCAT(name, '_updated')"),
            "test_user"
        )
    )

    assert result.affected_rows == 1

    row = await async_mysql_backend.fetch_one(
        "SELECT name, age FROM test_table WHERE name = %s",
        ("test_user_updated",)
    )
    assert row["age"] == 30
    assert row["name"] == "test_user_updated"


@pytest.mark.asyncio
async def test_mixed_params_and_expressions(async_mysql_backend, setup_test_table):
    """Test mixing regular parameters and expressions"""
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    result = await async_mysql_backend.execute(
        "UPDATE test_table SET age = %s, name = %s WHERE name = %s AND age >= %s",
        (
            async_mysql_backend.create_expression("age * 2"),
            "new_name",
            "test_user",
            18
        )
    )

    assert result.affected_rows == 1

    row = await async_mysql_backend.fetch_one(
        "SELECT name, age FROM test_table WHERE name = %s",
        ("new_name",)
    )
    assert row["age"] == 40
    assert row["name"] == "new_name"


@pytest.mark.asyncio
async def test_expression_with_placeholder(async_mysql_backend, setup_test_table):
    """Test expression containing a question mark"""
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )
    with pytest.raises(DatabaseError):
        await async_mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s",
            (async_mysql_backend.create_expression("age + ?"), "test_user")
        )


@pytest.mark.asyncio
async def test_expression_in_subquery(async_mysql_backend, setup_test_table):
    """Test using expression in subquery"""
    # Insert test data
    result = await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s), (%s, %s)",
        ("user1", 20, "user2", 30)
    )
    assert result.affected_rows == 2, "Should insert two records"

    # Verify inserted data
    rows = await async_mysql_backend.fetch_all(
        "SELECT * FROM test_table ORDER BY age"
    )
    assert len(rows) == 2, "Should have two records"
    assert rows[0]["age"] == 20, "First record age should be 20"
    assert rows[1]["age"] == 30, "Second record age should be 30"

    # Test subquery with expression
    result = await async_mysql_backend.execute(
        """
        SELECT *
        FROM test_table
        WHERE age > %s
          AND age < %s
        """,
        (
            async_mysql_backend.create_expression("(SELECT MIN(age) FROM test_table)"),
            async_mysql_backend.create_expression("(SELECT MAX(age) FROM test_table)")
        )
    )

    assert len(result.data) == 0, "Should not have matching records since condition is MIN < age < MAX"


@pytest.mark.asyncio
async def test_expression_in_insert(async_mysql_backend, setup_test_table):
    """Test using expression in INSERT statement"""
    # Get max age first
    max_age_result = await async_mysql_backend.fetch_one("SELECT MAX(age) as max_age FROM test_table")
    max_age = max_age_result["max_age"] if max_age_result and max_age_result["max_age"] is not None else 0

    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age, created_at) VALUES (%s, %s, %s)",
        (
            "test_user",
            max_age + 1,
            async_mysql_backend.create_expression("CURRENT_TIMESTAMP")
        )
    )

    row = await async_mysql_backend.fetch_one(
        "SELECT * FROM test_table WHERE name = %s",
        ("test_user",)
    )

    assert row["age"] == max_age + 1
    assert isinstance(row["created_at"], datetime)  # Ensure timestamp is correctly set


@pytest.mark.asyncio
async def test_complex_expression(async_mysql_backend, setup_test_table):
    """Test complex expression"""
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    result = await async_mysql_backend.execute(
        "UPDATE test_table SET age = %s WHERE name = %s",
        (
            async_mysql_backend.create_expression("""
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

    row = await async_mysql_backend.fetch_one(
        "SELECT age FROM test_table WHERE name = %s",
        ("test_user",)
    )
    assert row["age"] == 25


@pytest.mark.asyncio
async def test_invalid_expression(async_mysql_backend, setup_test_table):
    """Test invalid expression"""
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    with pytest.raises(OperationalError):
        await async_mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s",
            (async_mysql_backend.create_expression("invalid_column + 1"), "test_user")
        )


@pytest.mark.asyncio
async def test_expression_count_mismatch(async_mysql_backend, setup_test_table):
    """Test parameter count mismatch scenario"""
    await async_mysql_backend.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("test_user", 20)
    )

    # Case 1: Too few parameters
    with pytest.raises(ValueError, match="Parameter count mismatch: SQL needs 3 parameters but 2 were provided"):
        await async_mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s AND age = %s",
            (async_mysql_backend.create_expression("age + 1"), "test_user")  # Missing last parameter
        )

    # Case 2: Too many parameters
    with pytest.raises(ValueError, match="Parameter count mismatch: SQL needs 2 parameters but 3 were provided"):
        await async_mysql_backend.execute(
            "UPDATE test_table SET age = %s WHERE name = %s",
            (async_mysql_backend.create_expression("age + 1"), "test_user", 20)  # Extra parameter
        )
