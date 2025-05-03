import datetime
import decimal
import logging
import uuid

from src.rhosocial.activerecord.backend import DatabaseType

# Setup logger
logger = logging.getLogger("mysql_test")


def setup_test_table(backend):
    """Create test table for CRUD operations"""
    # First try to drop the table if it exists
    try:
        backend.execute("DROP TABLE IF EXISTS crud_test")
    except Exception as e:
        logger.warning(f"Error when removing existing table: {e}")

    # Create test table
    try:
        backend.execute("""
            CREATE TABLE crud_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                created_at DATETIME,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                amount DECIMAL(10, 2),
                is_active TINYINT(1) DEFAULT 1,
                tags JSON,
                settings JSON,
                uuid CHAR(36),
                description TEXT
            )
        """)
        logger.info("Test table created successfully")
    except Exception as e:
        logger.error(f"Error creating test table: {e}")
        raise


def teardown_test_table(backend):
    """Clean up test table"""
    try:
        backend.execute("DROP TABLE IF EXISTS crud_test")
        logger.info("Test table deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting test table: {e}")


def test_mysql_connection(mysql_test_db):
    """Test if MySQL connection works properly"""
    # Execute simple query
    result = mysql_test_db.execute("SELECT 1 as test")
    assert result is not None
    logger.info("Connection test successful")


def test_mysql_insert_basic(mysql_test_db):
    """Test basic insert operation"""
    # Insert single record
    result = mysql_test_db.insert(
        "crud_test",
        {
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "2024-03-01 10:00:00"
        }
    )

    # Verify result
    assert result is not None
    assert result.affected_rows == 1
    assert result.last_insert_id > 0
    logger.info(f"Record inserted successfully, ID: {result.last_insert_id}")

    # Query the inserted record
    row = mysql_test_db.fetch_one(
        "SELECT id, name, email, created_at FROM crud_test WHERE id = %s",
        params=(result.last_insert_id,)
    )

    # Verify query result
    assert row is not None
    assert row["id"] == result.last_insert_id
    assert row["name"] == "Test User"
    assert row["email"] == "test@example.com"
    logger.info("Inserted data verification successful")


def test_mysql_insert_with_types(mysql_test_db):
    """Test insert operation with type conversion"""
    test_uuid = uuid.uuid4()
    current_time = datetime.datetime.now()
    decimal_value = decimal.Decimal("123.45")

    # Insert record with various types
    result = mysql_test_db.insert(
        "crud_test",
        {
            "name": "Type Test",
            "email": "types@example.com",
            "created_at": current_time,
            "amount": decimal_value,
            "is_active": True,
            "tags": ["mysql", "python", "test"],
            "settings": {"theme": "dark", "notifications": True},
            "uuid": test_uuid
        },
        column_types={
            "created_at": DatabaseType.DATETIME,
            "amount": DatabaseType.DECIMAL,
            "is_active": DatabaseType.BOOLEAN,
            "tags": DatabaseType.JSON,
            "settings": DatabaseType.JSON,
            "uuid": DatabaseType.UUID
        }
    )

    # Verify result
    assert result is not None
    assert result.affected_rows == 1
    assert result.last_insert_id > 0
    logger.info(f"Typed record inserted successfully, ID: {result.last_insert_id}")

    # Query the inserted record
    row = mysql_test_db.fetch_one(
        "SELECT * FROM crud_test WHERE id = %s",
        params=(result.last_insert_id,),
        column_types={
            "created_at": DatabaseType.DATETIME,
            "amount": DatabaseType.DECIMAL,
            "is_active": DatabaseType.BOOLEAN,
            "tags": DatabaseType.JSON,
            "settings": DatabaseType.JSON,
            "uuid": DatabaseType.UUID
        }
    )

    # Verify query result with type checking
    assert row is not None
    assert row["id"] == result.last_insert_id
    assert row["name"] == "Type Test"
    assert row["email"] == "types@example.com"
    assert isinstance(row["created_at"], datetime.datetime)
    assert isinstance(row["amount"], decimal.Decimal)
    assert row["amount"] == decimal_value
    assert isinstance(row["is_active"], bool)
    assert row["is_active"] is True
    assert isinstance(row["tags"], list)
    assert "mysql" in row["tags"]
    assert isinstance(row["settings"], dict)
    assert row["settings"]["theme"] == "dark"
    assert row["settings"]["notifications"] is True
    assert str(row["uuid"]) == str(test_uuid)
    logger.info("Type conversion verification successful")


def test_mysql_select_multiple(mysql_test_db):
    """Test selecting multiple records"""
    # First insert multiple test records
    for i in range(5):
        mysql_test_db.insert(
            "crud_test",
            {
                "name": f"Batch User {i + 1}",
                "email": f"batch{i + 1}@example.com",
                "created_at": datetime.datetime.now()
            }
        )
    logger.info("Multiple test records inserted successfully")

    # Query all records
    rows = mysql_test_db.fetch_all(
        "SELECT id, name, email FROM crud_test WHERE name LIKE %s ORDER BY id",
        params=("Batch User%",)
    )

    # Verify query results
    assert rows is not None
    assert len(rows) >= 5
    for i, row in enumerate(rows[-5:]):
        assert row["name"] == f"Batch User {i + 1}"
        assert row["email"] == f"batch{i + 1}@example.com"
    logger.info(f"Multiple records query successful, record count: {len(rows)}")


def test_mysql_update(mysql_test_db):
    """Test update operation"""
    # First insert a test record
    insert_result = mysql_test_db.insert(
        "crud_test",
        {
            "name": "Update Test",
            "email": "update@example.com",
            "amount": 100.00
        }
    )

    record_id = insert_result.last_insert_id
    logger.info(f"Record for update inserted successfully, ID: {record_id}")

    # Update the record
    update_result = mysql_test_db.update(
        "crud_test",
        {
            "name": "Updated Name",
            "email": "updated@example.com",
            "amount": 200.50,
            "description": "This record was updated"
        },
        "id = %s",
        (record_id,),
        column_types={
            "amount": DatabaseType.DECIMAL
        }
    )

    # Verify update result
    assert update_result is not None
    assert update_result.affected_rows == 1
    logger.info(f"Record update successful, affected rows: {update_result.affected_rows}")

    # Query the updated record
    row = mysql_test_db.fetch_one(
        "SELECT * FROM crud_test WHERE id = %s",
        params=(record_id,),
        column_types={
            "amount": DatabaseType.DECIMAL
        }
    )

    # Verify the record was updated
    assert row is not None
    assert row["name"] == "Updated Name"
    assert row["email"] == "updated@example.com"
    assert row["amount"] == decimal.Decimal("200.50")
    assert row["description"] == "This record was updated"
    logger.info("Updated record verification successful")


def test_mysql_delete(mysql_test_db):
    """Test delete operation"""
    # First insert a test record
    insert_result = mysql_test_db.insert(
        "crud_test",
        {
            "name": "Delete Test",
            "email": "delete@example.com"
        }
    )

    record_id = insert_result.last_insert_id
    logger.info(f"Record for deletion inserted successfully, ID: {record_id}")

    # Confirm record exists
    row = mysql_test_db.fetch_one(
        "SELECT id FROM crud_test WHERE id = %s",
        params=(record_id,)
    )
    assert row is not None

    # Delete the record
    delete_result = mysql_test_db.delete(
        "crud_test",
        "id = %s",
        (record_id,)
    )

    # Verify delete result
    assert delete_result is not None
    assert delete_result.affected_rows == 1
    logger.info(f"Record deletion successful, affected rows: {delete_result.affected_rows}")

    # Confirm record is deleted
    row = mysql_test_db.fetch_one(
        "SELECT id FROM crud_test WHERE id = %s",
        params=(record_id,)
    )
    assert row is None
    logger.info("Record deletion verification successful")


def test_mysql_batch_operations(mysql_test_db):
    """Test batch operations"""
    # First clean up any existing test data
    mysql_test_db.execute("DELETE FROM crud_test WHERE name LIKE 'Batch Operation%'")

    # Batch insert
    records = []
    for i in range(10):
        records.append((
            f"Batch Operation {i + 1}",
            f"batch_op{i + 1}@example.com",
            f"Description for record {i + 1}"
        ))

    batch_result = mysql_test_db.execute_many(
        "INSERT INTO crud_test (name, email, description) VALUES (%s, %s, %s)",
        records
    )

    # Verify batch insert result
    assert batch_result is not None
    assert batch_result.affected_rows == 10
    logger.info(f"Batch insert successful, affected rows: {batch_result.affected_rows}")

    # Verify inserted records
    rows = mysql_test_db.fetch_all(
        "SELECT * FROM crud_test WHERE name LIKE 'Batch Operation%' ORDER BY id"
    )
    assert len(rows) == 10
    for i, row in enumerate(rows):
        assert row["name"] == f"Batch Operation {i + 1}"
        assert row["email"] == f"batch_op{i + 1}@example.com"
    logger.info(f"Batch insert verification successful, record count: {len(rows)}")


def test_mysql_transaction_commit(mysql_test_db):
    """Test transaction commit"""
    # Get transaction manager
    transaction_manager = mysql_test_db.transaction_manager
    logger.info("Starting transaction commit test")

    # Begin transaction
    transaction_manager.begin()
    logger.info("Transaction started")

    try:
        # Execute multiple operations in transaction
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Transaction Test 1",
                "email": "tx1@example.com"
            }
        )

        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Transaction Test 2",
                "email": "tx2@example.com"
            }
        )
        logger.info("Inserted two records in transaction")

        # Commit transaction
        transaction_manager.commit()
        logger.info("Transaction committed")

        # Verify transaction is committed
        assert not transaction_manager.is_active

        # Verify records are inserted
        rows = mysql_test_db.fetch_all(
            "SELECT * FROM crud_test WHERE name LIKE 'Transaction Test%'"
        )
        assert len(rows) == 2
        logger.info(f"Transaction commit verification successful, record count: {len(rows)}")

    except Exception as e:
        # Ensure transaction rollback
        if transaction_manager.is_active:
            transaction_manager.rollback()
            logger.error(f"Transaction test error, rolled back: {e}")
        raise


def test_mysql_transaction_rollback(mysql_test_db):
    """Test transaction rollback"""
    # Get transaction manager
    transaction_manager = mysql_test_db.transaction_manager
    logger.info("Starting transaction rollback test")

    # Count records before operation
    before_count = len(mysql_test_db.fetch_all(
        "SELECT * FROM crud_test WHERE name LIKE 'Rollback Test%'"
    ))
    logger.info(f"Record count before rollback test: {before_count}")

    # Begin transaction
    transaction_manager.begin()
    logger.info("Transaction started")

    try:
        # Execute operations in transaction
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Rollback Test 1",
                "email": "rollback1@example.com"
            }
        )

        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Rollback Test 2",
                "email": "rollback2@example.com"
            }
        )
        logger.info("Inserted two records in transaction")

        # Rollback transaction
        transaction_manager.rollback()
        logger.info("Transaction rolled back")

        # Verify transaction is rolled back
        assert not transaction_manager.is_active

        # Verify records were not inserted
        after_count = len(mysql_test_db.fetch_all(
            "SELECT * FROM crud_test WHERE name LIKE 'Rollback Test%'"
        ))
        assert after_count == before_count
        logger.info(f"Transaction rollback verification successful, record count unchanged: {after_count}")

    except Exception as e:
        # Ensure transaction rollback
        if transaction_manager.is_active:
            transaction_manager.rollback()
            logger.error(f"Transaction test error, rolled back: {e}")
        raise


def test_mysql_transaction_context_manager(mysql_test_db):
    """Test transaction context manager"""
    logger.info("Starting transaction context manager test")

    # Count records before operation
    before_count = len(mysql_test_db.fetch_all(
        "SELECT * FROM crud_test WHERE name LIKE 'Context Test%'"
    ))
    logger.info(f"Record count before context manager test: {before_count}")

    # Test successful commit
    with mysql_test_db.transaction():
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Context Test Success",
                "email": "context_success@example.com"
            }
        )
        logger.info("Inserted record in transaction context")

    # Verify record was inserted
    mid_count = len(mysql_test_db.fetch_all(
        "SELECT * FROM crud_test WHERE name LIKE 'Context Test%'"
    ))
    assert mid_count == before_count + 1
    logger.info(f"Successful transaction count verification: {mid_count}")

    # Test exception rollback
    try:
        with mysql_test_db.transaction():
            mysql_test_db.insert(
                "crud_test",
                {
                    "name": "Context Test Rollback",
                    "email": "context_rollback@example.com"
                }
            )
            logger.info("Inserted record in transaction context then raising exception")
            # Raise exception to trigger rollback
            raise ValueError("Test rollback")
    except ValueError:
        logger.info("Caught expected exception")
        pass

    # Verify record was not inserted
    after_count = len(mysql_test_db.fetch_all(
        "SELECT * FROM crud_test WHERE name LIKE 'Context Test%'"
    ))
    assert after_count == mid_count
    logger.info(f"Exception rollback verification successful, record count unchanged: {after_count}")


def test_mysql_savepoints(mysql_test_db):
    """Test MySQL savepoint functionality"""
    # Get transaction manager
    transaction_manager = mysql_test_db.transaction_manager
    logger.info("Starting savepoint test")

    # Begin transaction
    transaction_manager.begin()
    logger.info("Transaction started")

    try:
        # Insert first record
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Savepoint Base",
                "email": "savepoint_base@example.com"
            }
        )
        logger.info("Inserted base record")

        # Create savepoint
        sp1 = transaction_manager.savepoint("SP1")
        logger.info(f"Created savepoint SP1: {sp1}")

        # Insert second record
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Savepoint Test 1",
                "email": "savepoint1@example.com"
            }
        )
        logger.info("Inserted first test record")

        # Create second savepoint
        sp2 = transaction_manager.savepoint("SP2")
        logger.info(f"Created savepoint SP2: {sp2}")

        # Insert third record
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Savepoint Test 2",
                "email": "savepoint2@example.com"
            }
        )
        logger.info("Inserted second test record")

        # Rollback to first savepoint
        transaction_manager.rollback_to(sp1)
        logger.info(f"Rolled back to savepoint SP1: {sp1}")

        # Insert new record
        mysql_test_db.insert(
            "crud_test",
            {
                "name": "Savepoint After Rollback",
                "email": "savepoint_after@example.com"
            }
        )
        logger.info("Inserted post-rollback record")

        # Commit transaction
        transaction_manager.commit()
        logger.info("Transaction committed")

        # Verify records
        rows = mysql_test_db.fetch_all(
            "SELECT * FROM crud_test WHERE name LIKE 'Savepoint%' ORDER BY id"
        )

        # Should only have two records: Base and After Rollback
        assert len(rows) == 2
        assert rows[0]["name"] == "Savepoint Base"
        assert rows[1]["name"] == "Savepoint After Rollback"
        logger.info(f"Savepoint rollback verification successful, record count: {len(rows)}")

    except Exception as e:
        # Ensure transaction rollback
        if transaction_manager.is_active:
            transaction_manager.rollback()
            logger.error(f"Savepoint test error, rolled back: {e}")
        raise


def test_mysql_isolation_levels(mysql_test_db):
    """Test MySQL isolation level settings"""
    from src.rhosocial.activerecord.backend.transaction import IsolationLevel
    logger.info("Starting isolation level test")

    # Get transaction manager
    transaction_manager = mysql_test_db.transaction_manager

    # Test different isolation levels
    isolation_levels = [
        IsolationLevel.READ_UNCOMMITTED,
        IsolationLevel.READ_COMMITTED,
        IsolationLevel.REPEATABLE_READ,
        IsolationLevel.SERIALIZABLE
    ]

    for level in isolation_levels:
        # Set isolation level
        transaction_manager.isolation_level = level
        assert transaction_manager.isolation_level == level
        logger.info(f"Set isolation level: {level.name}")

        # Execute simple transaction with this isolation level
        transaction_manager.begin()
        mysql_test_db.insert(
            "crud_test",
            {
                "name": f"Isolation {level.name}",
                "email": f"isolation_{level.name.lower()}@example.com"
            }
        )
        transaction_manager.commit()
        logger.info(f"Transaction with isolation level {level.name} successful")

    # Verify all isolation level records were inserted
    rows = mysql_test_db.fetch_all(
        "SELECT * FROM crud_test WHERE name LIKE 'Isolation%'"
    )
    assert len(rows) == len(isolation_levels)
    logger.info(f"Verified all isolation level records, count: {len(rows)}")


def test_mysql_server_version(mysql_test_db):
    """Test MySQL server version detection"""
    version = mysql_test_db.get_server_version()

    # Verify version format
    assert version is not None
    assert isinstance(version, tuple)
    assert len(version) == 3

    # Print version for reference
    logger.info(f"MySQL server version: {version[0]}.{version[1]}.{version[2]}")

    # Verify version numbers are reasonable
    assert version[0] > 0  # Major version
    assert version[1] >= 0  # Minor version
    assert version[2] >= 0  # Patch version


def test_mysql_supports_returning(mysql_test_db):
    """Test MySQL RETURNING clause support detection"""
    # MySQL doesn't support RETURNING clause
    supports = mysql_test_db.supports_returning
    logger.info(f"MySQL supports RETURNING clause: {supports}")
    assert supports is False


def test_fetch_with_type_conversion(mysql_test_db):
    """Test query with type conversion"""
    # First insert record with various types
    test_uuid = uuid.uuid4()
    test_time = datetime.datetime.now()

    mysql_test_db.insert(
        "crud_test",
        {
            "name": "Type Conversion Test",
            "email": "types_fetch@example.com",
            "created_at": test_time,
            "amount": 456.78,
            "is_active": True,
            "tags": ["test", "conversion", "fetch"],
            "settings": {"mode": "advanced", "color": "blue"},
            "uuid": test_uuid,
            "description": "Testing type conversions in fetch operations"
        },
        column_types={
            "created_at": DatabaseType.DATETIME,
            "amount": DatabaseType.DECIMAL,
            "is_active": DatabaseType.BOOLEAN,
            "tags": DatabaseType.JSON,
            "settings": DatabaseType.JSON,
            "uuid": DatabaseType.UUID
        }
    )
    logger.info("Inserted type conversion test record")

    # Query with type conversion
    row = mysql_test_db.fetch_one(
        "SELECT * FROM crud_test WHERE name = %s",
        params=("Type Conversion Test",),
        column_types={
            "created_at": DatabaseType.DATETIME,
            "updated_at": DatabaseType.DATETIME,
            "amount": DatabaseType.DECIMAL,
            "is_active": DatabaseType.BOOLEAN,
            "tags": DatabaseType.JSON,
            "settings": DatabaseType.JSON,
            "uuid": DatabaseType.UUID
        }
    )

    # Verify type conversion
    assert row is not None
    assert row["name"] == "Type Conversion Test"
    assert isinstance(row["created_at"], datetime.datetime)
    assert isinstance(row["updated_at"], datetime.datetime)
    assert isinstance(row["amount"], decimal.Decimal)
    assert row["amount"] == decimal.Decimal("456.78")
    assert isinstance(row["is_active"], bool)
    assert row["is_active"] is True
    assert isinstance(row["tags"], list)
    assert "test" in row["tags"]
    assert "conversion" in row["tags"]
    assert isinstance(row["settings"], dict)
    assert row["settings"]["mode"] == "advanced"
    assert row["settings"]["color"] == "blue"
    assert str(row["uuid"]) == str(test_uuid)
    logger.info("Type conversion in query verification successful")


def test_non_query_execute(mysql_test_db):
    """Test non-query execution"""
    # Test ALTER TABLE statement
    result = mysql_test_db.execute(
        "ALTER TABLE crud_test ADD COLUMN temp_column VARCHAR(50)"
    )
    assert result is not None
    logger.info("ALTER TABLE statement executed successfully")

    # Verify column was added
    mysql_test_db.execute(
        "INSERT INTO crud_test (name, temp_column) VALUES (%s, %s)",
        params=("Temp Column Test", "Temp Value")
    )

    row = mysql_test_db.fetch_one(
        "SELECT name, temp_column FROM crud_test WHERE name = %s",
        params=("Temp Column Test",)
    )
    assert row is not None
    assert row["temp_column"] == "Temp Value"
    logger.info("Verified added column is usable")

    # Cleanup: drop temporary column
    mysql_test_db.execute(
        "ALTER TABLE crud_test DROP COLUMN temp_column"
    )
    logger.info("Cleanup: temporary column dropped successfully")