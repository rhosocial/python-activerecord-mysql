import datetime
import logging
import time
import threading
from decimal import Decimal

import pytest
from src.rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionError
from src.rhosocial.activerecord.backend.errors import DeadlockError, QueryError

# Setup logger
logger = logging.getLogger("mysql_test")


def setup_transaction_tables(backend):
    """Setup test tables for transaction tests"""
    # Drop existing tables if they exist
    try:
        backend.execute("DROP TABLE IF EXISTS transaction_test_accounts")
        backend.execute("DROP TABLE IF EXISTS transaction_test_transfers")
    except Exception as e:
        logger.warning(f"Error dropping existing tables: {e}")

    # Create accounts table
    try:
        result = backend.execute("""
            CREATE TABLE transaction_test_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_number VARCHAR(20) UNIQUE NOT NULL,
                balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                owner_name VARCHAR(100) NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        logger.info(f"Created transaction_test_accounts table: {result}")

        # Create transfers table
        result = backend.execute("""
            CREATE TABLE transaction_test_transfers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                from_account VARCHAR(20) NOT NULL,
                to_account VARCHAR(20) NOT NULL,
                amount DECIMAL(15, 2) NOT NULL,
                status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL
            )
        """)
        logger.info(f"Created transaction_test_transfers table: {result}")

        if backend.in_transaction:
            backend.commit_transaction()
            logger.info("Committed table creation transaction")

        backend.begin_transaction()

        # Insert some initial test accounts
        accounts = [
            ("ACC-001", 1000.00, "John Doe"),
            ("ACC-002", 2000.00, "Jane Smith"),
            ("ACC-003", 500.00, "David Johnson"),
            ("ACC-004", 1500.00, "Sarah Williams"),
            ("ACC-005", 3000.00, "Michael Brown")
        ]

        for account in accounts:
            result = backend.execute(
                "INSERT INTO transaction_test_accounts (account_number, balance, owner_name) VALUES (%s, %s, %s)",
                account
            )
            logger.info(f"Inserted account {account[0]} with ID {result.last_insert_id}")

        backend.commit_transaction()
        logger.info("Committed initial test accounts transaction")

        count = backend.fetch_one("SELECT COUNT(*) as count FROM transaction_test_accounts")
        logger.info(f"Verified {count['count']} accounts in database")

    except Exception as e:
        logger.error(f"Error creating transaction test tables: {e}")
        raise


def teardown_transaction_tables(backend):
    """Clean up transaction test tables"""
    try:
        backend.execute("DROP TABLE IF EXISTS transaction_test_transfers")
        backend.execute("DROP TABLE IF EXISTS transaction_test_accounts")
        logger.info("Dropped transaction test tables")
    except Exception as e:
        logger.error(f"Error dropping transaction test tables: {e}")


@pytest.fixture(scope="function")
def mysql_transaction_test_db(mysql_test_db):
    """Setup and teardown for transaction tests"""
    setup_transaction_tables(mysql_test_db)
    yield mysql_test_db
    teardown_transaction_tables(mysql_test_db)


def test_nested_transactions(mysql_transaction_test_db):
    """Test nested transactions with commit and rollback"""
    transaction_manager = mysql_transaction_test_db.transaction_manager
    logger.info("Starting nested transactions test")

    # Begin outer transaction
    transaction_manager.begin()

    try:
        # Update in outer transaction
        result = mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = balance + 100 WHERE account_number = 'ACC-001'"
        )
        logger.info(f"Outer transaction update result: {result}")

        # 在测试开始时添加此代码来确认账户存在
        all_accounts = mysql_transaction_test_db.fetch_all(
            "SELECT * FROM transaction_test_accounts"
        )
        logger.info(f"Available accounts: {all_accounts}")
        # 在fetch_one之前添加
        logger.info(f"Connection is alive: {mysql_transaction_test_db.ping()}")
        # 在fetch_one之前添加
        logger.info(f"Transaction is active: {transaction_manager.is_active}")
        logger.info(f"Transaction level: {transaction_manager.transaction_level}")
        row = mysql_transaction_test_db.fetch_one(
            "SELECT * FROM transaction_test_accounts WHERE account_number = 'ACC-001'"
        )
        logger.info(f"Full row data: {row}")
        # Check balance after outer transaction update
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = %s", ('ACC-001', )
        )
        outer_balance = row["balance"]
        logger.info(f"Balance after outer transaction update: {outer_balance}")

        # Begin first nested transaction
        transaction_manager.begin()

        try:
            # Update in first nested transaction
            mysql_transaction_test_db.execute(
                "UPDATE transaction_test_accounts SET balance = balance + 200 WHERE account_number = 'ACC-001'"
            )

            # Check balance after first nested update
            row = mysql_transaction_test_db.fetch_one(
                "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-001'"
            )
            nested1_balance = row["balance"]
            logger.info(f"Balance after first nested update: {nested1_balance}")
            assert nested1_balance == outer_balance + 200

            # Begin second nested transaction
            transaction_manager.begin()

            try:
                # Update in second nested transaction
                mysql_transaction_test_db.execute(
                    "UPDATE transaction_test_accounts SET balance = balance + 300 WHERE account_number = 'ACC-001'"
                )

                # Check balance after second nested update
                row = mysql_transaction_test_db.fetch_one(
                    "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-001'"
                )
                nested2_balance = row["balance"]
                logger.info(f"Balance after second nested update: {nested2_balance}")
                assert nested2_balance == nested1_balance + 300

                # Rollback the second nested transaction
                transaction_manager.rollback()
                logger.info("Rolled back second nested transaction")

                # Check balance after second nested rollback
                row = mysql_transaction_test_db.fetch_one(
                    "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-001'"
                )
                after_nested2_rollback_balance = row["balance"]
                logger.info(f"Balance after second nested rollback: {after_nested2_rollback_balance}")
                assert after_nested2_rollback_balance == nested1_balance

            except Exception as e:
                transaction_manager.rollback()
                logger.error(f"Error in second nested transaction: {e}")
                raise

            # Commit first nested transaction
            transaction_manager.commit()
            logger.info("Committed first nested transaction")

            # Check balance after first nested commit
            row = mysql_transaction_test_db.fetch_one(
                "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-001'"
            )
            after_nested1_commit_balance = row["balance"]
            logger.info(f"Balance after first nested commit: {after_nested1_commit_balance}")
            assert after_nested1_commit_balance == outer_balance + 200

        except Exception as e:
            transaction_manager.rollback()
            logger.error(f"Error in first nested transaction: {e}")
            raise

        # Rollback the outer transaction
        transaction_manager.rollback()
        logger.info("Rolled back outer transaction")

        # Check final balance after outer rollback
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-001'"
        )
        final_balance = row["balance"]
        logger.info(f"Final balance after outer rollback: {final_balance}")

        # The original balance should be restored (1000)
        assert final_balance == 1000.00

    except Exception as e:
        if transaction_manager.is_active:
            transaction_manager.rollback()
        logger.error(f"Error in nested transaction test: {e}")
        raise


def perform_transfer(backend, from_account, to_account, amount, delay_seconds=0):
    """Helper function to perform a money transfer with transaction"""
    tx_manager = backend.transaction_manager
    transfer_id = None

    try:
        tx_manager.begin()

        # Insert transfer record
        result = backend.execute(
            "INSERT INTO transaction_test_transfers (from_account, to_account, amount) VALUES (%s, %s, %s)",
            (from_account, to_account, amount)
        )
        transfer_id = result.last_insert_id

        # Deduct from source account
        result = backend.execute(
            "UPDATE transaction_test_accounts SET balance = balance - %s WHERE account_number = %s AND balance >= %s",
            (amount, from_account, amount)
        )

        # Check if deduction was successful (affected rows should be 1)
        affected_rows = result.affected_rows

        if affected_rows != 1:
            raise Exception(f"Insufficient funds in account {from_account}")

        # Optional delay to simulate long-running transaction
        if delay_seconds > 0:
            time.sleep(delay_seconds)

        # Add to destination account
        backend.execute(
            "UPDATE transaction_test_accounts SET balance = balance + %s WHERE account_number = %s",
            (amount, to_account)
        )

        # Mark transfer as completed
        backend.execute(
            "UPDATE transaction_test_transfers SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = %s",
            (transfer_id,)
        )

        tx_manager.commit()
        return True, transfer_id

    except Exception as e:
        if tx_manager.is_active:
            tx_manager.rollback()

        # If transfer record was created, mark it as failed
        if transfer_id:
            try:
                backend.execute(
                    "UPDATE transaction_test_transfers SET status = 'failed' WHERE id = %s",
                    (transfer_id,)
                )
            except:
                pass

        logger.error(f"Transfer error: {e}")
        return False, str(e)


def test_multiple_transfers(mysql_transaction_test_db):
    """Test multiple transfers in sequence"""
    logger.info("Starting multiple transfers test")

    # Verify initial balances
    accounts = mysql_transaction_test_db.fetch_all(
        "SELECT account_number, balance FROM transaction_test_accounts WHERE account_number IN ('ACC-001', 'ACC-002', 'ACC-003')"
    )
    initial_balances = {account["account_number"]: account["balance"] for account in accounts}
    logger.info(f"Initial balances: {initial_balances}")

    # Perform multiple transfers
    transfers = [
        ("ACC-001", "ACC-002", 200.00),
        ("ACC-002", "ACC-003", 300.00),
        ("ACC-003", "ACC-001", 100.00)
    ]

    for from_acc, to_acc, amount in transfers:
        success, result = perform_transfer(mysql_transaction_test_db, from_acc, to_acc, amount)
        assert success, f"Transfer failed: {result}"
        logger.info(f"Transfer from {from_acc} to {to_acc} of {amount} completed")

    # Verify final balances
    accounts = mysql_transaction_test_db.fetch_all(
        "SELECT account_number, balance FROM transaction_test_accounts WHERE account_number IN ('ACC-001', 'ACC-002', 'ACC-003')"
    )
    final_balances = {account["account_number"]: account["balance"] for account in accounts}
    logger.info(f"Final balances: {final_balances}")

    # Calculate expected balances
    expected_balances = {
        "ACC-001": initial_balances["ACC-001"] - Decimal("200.00") + Decimal("100.00"),
        "ACC-002": initial_balances["ACC-002"] + Decimal("200.00") - Decimal("300.00"),
        "ACC-003": initial_balances["ACC-003"] + Decimal("300.00") - Decimal("100.00")
    }

    # Verify each account balance
    for acc_num, balance in expected_balances.items():
        assert final_balances[
                   acc_num] == balance, f"Balance mismatch for {acc_num}: expected {balance}, got {final_balances[acc_num]}"

    # Verify transfer records
    transfers = mysql_transaction_test_db.fetch_all(
        "SELECT * FROM transaction_test_transfers ORDER BY id"
    )
    assert len(transfers) == 3
    for transfer in transfers:
        assert transfer["status"] == "completed"

    logger.info("Multiple transfers test completed successfully")


def test_failed_transfer(mysql_transaction_test_db):
    """Test transfer that fails due to insufficient funds"""
    logger.info("Starting failed transfer test")

    # Get initial balance
    row = mysql_transaction_test_db.fetch_one(
        "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-003'"
    )
    initial_balance = row["balance"]
    logger.info(f"Initial balance for ACC-003: {initial_balance}")

    # Attempt transfer with amount greater than balance
    excessive_amount = initial_balance + Decimal("100.00")
    success, result = perform_transfer(mysql_transaction_test_db, "ACC-003", "ACC-001", excessive_amount)

    # Transfer should fail
    assert not success, "Transfer should have failed but succeeded"
    logger.info(f"Transfer failed as expected: {result}")

    # Verify balances didn't change
    row = mysql_transaction_test_db.fetch_one(
        "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-003'"
    )
    final_balance = row["balance"]

    assert final_balance == initial_balance, f"Balance changed despite failed transfer: {final_balance} != {initial_balance}"

    # Verify transfer record was marked as failed
    transfers = mysql_transaction_test_db.fetch_all(
        "SELECT * FROM transaction_test_transfers WHERE from_account = 'ACC-003' AND amount = %s",
        (excessive_amount,)
    )

    if transfers:  # Some implementations might not create the record if the transaction fails
        for transfer in transfers:
            assert transfer["status"] == "failed", "Transfer should be marked as failed"

    logger.info("Failed transfer test completed successfully")


def test_transaction_isolation_read_committed(mysql_transaction_test_db):
    """Test READ COMMITTED isolation level behavior"""
    transaction_manager = mysql_transaction_test_db.transaction_manager

    # Set isolation level to READ COMMITTED
    transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED
    logger.info("Set isolation level to READ COMMITTED")

    # Start a transaction for updating
    transaction_manager.begin()

    try:
        # Update an account
        mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = 5000.00 WHERE account_number = 'ACC-004'"
        )
        logger.info("Updated balance in first transaction but not committed")

        # 修复方案: 创建独立的后端实例并建立自己的连接
        config_copy = mysql_transaction_test_db.config.clone()
        backend2 = mysql_transaction_test_db.__class__(connection_config=config_copy)
        backend2.connect()

        try:
            # The second connection should not see the uncommitted change
            row = backend2.fetch_one(
                "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-004'"
            )
            uncommitted_balance = row["balance"]
            logger.info(f"Balance seen from second connection before commit: {uncommitted_balance}")
            assert uncommitted_balance != 5000.00, "Second transaction should not see uncommitted changes"

            # Now commit the first transaction
            transaction_manager.commit()
            logger.info("Committed first transaction")

            # The second connection should now see the committed change
            row = backend2.fetch_one(
                "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-004'"
            )
            committed_balance = row["balance"]
            logger.info(f"Balance seen from second connection after commit: {committed_balance}")
            assert committed_balance == 5000.00, "Second transaction should see committed changes"
        finally:
            # 确保断开连接
            backend2.disconnect()

    except Exception as e:
        if transaction_manager.is_active:
            transaction_manager.rollback()
        logger.error(f"Error in isolation test: {e}")
        raise


def concurrent_transfer_thread(backend_config, from_account, to_account, amount, delay, result_dict, thread_id):
    """Helper function to run concurrent transfers in separate threads

    Args:
        backend_config: Database connection configuration to create independent connection
        from_account: Source account number
        to_account: Destination account number
        amount: Transfer amount
        delay: Artificial delay in seconds to increase chance of concurrent access
        result_dict: Shared dictionary to store results
        thread_id: Identifier for the thread
    """
    try:
        # Create a new backend instance with independent connection for each thread
        backend = mysql_transaction_test_db.__class__(connection_config=backend_config)
        backend.connect()

        try:
            logger.info(f"Thread {thread_id}: Starting transfer from {from_account} to {to_account} of {amount}")
            success, transfer_id = perform_transfer(backend, from_account, to_account, amount, delay)
            result_dict[thread_id] = (success, transfer_id)
            logger.info(f"Thread {thread_id}: Transfer completed with result: {success}, {transfer_id}")
        finally:
            # Ensure connection is properly closed
            backend.disconnect()

    except Exception as e:
        logger.error(f"Thread {thread_id}: Exception occurred: {str(e)}")
        result_dict[thread_id] = (False, str(e))


def test_concurrent_transfers(mysql_transaction_test_db):
    """Test concurrent transfers with potential deadlock detection

    This test creates two threads that perform transfers in opposite directions:
    - Thread 1: ACC-001 -> ACC-002 (500)
    - Thread 2: ACC-002 -> ACC-001 (300)

    Since the transfers access the same accounts in reverse order, this creates
    a potential deadlock scenario that the database should detect and handle.

    The test accepts that one thread might fail due to deadlock, which is a normal
    database behavior to resolve lock conflicts.
    """
    logger.info("Starting concurrent transfers test")

    # Reset balances to known values for this test
    mysql_transaction_test_db.execute(
        "UPDATE transaction_test_accounts SET balance = 1000.00 WHERE account_number = 'ACC-001'"
    )
    mysql_transaction_test_db.execute(
        "UPDATE transaction_test_accounts SET balance = 1000.00 WHERE account_number = 'ACC-002'"
    )

    # Get initial balances
    accounts = mysql_transaction_test_db.fetch_all(
        "SELECT account_number, balance FROM transaction_test_accounts WHERE account_number IN ('ACC-001', 'ACC-002')"
    )
    initial_balances = {account["account_number"]: account["balance"] for account in accounts}
    logger.info(f"Initial balances: {initial_balances}")

    # Setup concurrent transfers in opposite directions
    thread_results = {}
    threads = []

    # Clone the configuration for independent connections
    config1 = mysql_transaction_test_db.config.clone()
    config2 = mysql_transaction_test_db.config.clone()

    # First transfer: ACC-001 -> ACC-002
    t1 = threading.Thread(
        target=concurrent_transfer_thread,
        args=(config1, "ACC-001", "ACC-002", 500, 1, thread_results, 1)
    )

    # Second transfer: ACC-002 -> ACC-001
    t2 = threading.Thread(
        target=concurrent_transfer_thread,
        args=(config2, "ACC-002", "ACC-001", 300, 1, thread_results, 2)
    )

    # Start threads
    t1.start()
    t2.start()

    # Wait for threads to complete
    t1.join()
    t2.join()

    # Check results
    logger.info(f"Thread results: {thread_results}")

    # Both transfers might succeed or one might fail with deadlock
    # This is expected behavior in concurrent database operations
    deadlock_detected = False
    for thread_id, (success, result) in thread_results.items():
        if not success and "deadlock" in str(result).lower():
            deadlock_detected = True
            logger.info(f"Thread {thread_id} encountered expected deadlock: {result}")

    # Get final balances
    accounts = mysql_transaction_test_db.fetch_all(
        "SELECT account_number, balance FROM transaction_test_accounts WHERE account_number IN ('ACC-001', 'ACC-002')"
    )
    final_balances = {account["account_number"]: account["balance"] for account in accounts}
    logger.info(f"Final balances: {final_balances}")

    # Calculate expected balances based on which transfers succeeded
    # Initialize with no changes
    acc1_change = Decimal("0.00")
    acc2_change = Decimal("0.00")

    # Apply changes for successful transfers only
    if thread_results.get(1, (False, None))[0]:
        # Thread 1 successful: ACC-001 -> ACC-002 (500)
        acc1_change -= Decimal("500.00")
        acc2_change += Decimal("500.00")

    if thread_results.get(2, (False, None))[0]:
        # Thread 2 successful: ACC-002 -> ACC-001 (300)
        acc1_change += Decimal("300.00")
        acc2_change -= Decimal("300.00")

    # Calculate expected final balances
    expected_balances = {
        "ACC-001": initial_balances["ACC-001"] + acc1_change,
        "ACC-002": initial_balances["ACC-002"] + acc2_change
    }

    logger.info(f"Expected balances: {expected_balances}")

    # Verify final balances match expectations
    for acc_num, expected_balance in expected_balances.items():
        assert final_balances[acc_num] == expected_balance, \
            f"Balance mismatch for {acc_num}: expected {expected_balance}, got {final_balances[acc_num]}"

    logger.info("Concurrent transfers test completed successfully")


def test_multiple_savepoints(mysql_transaction_test_db):
    """Test creating, rolling back, and releasing multiple savepoints"""
    transaction_manager = mysql_transaction_test_db.transaction_manager
    logger.info("Starting multiple savepoints test")

    # Begin transaction
    transaction_manager.begin()

    try:
        # Initial update
        mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = 2500.00 WHERE account_number = 'ACC-005'"
        )

        # 首先查询余额确认当前状态
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        balance_initial = row["balance"]
        logger.info(f"Initial balance: {balance_initial}")

        # 创建第一个保存点 - 此时保存的是2500.00状态
        sp1 = transaction_manager.savepoint("POINT1")
        logger.info(f"Created savepoint 1: {sp1} - should preserve state with balance 2500.00")

        # 第一个保存点后的更新
        mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = 3000.00 WHERE account_number = 'ACC-005'"
        )

        # 验证余额
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        balance_after_sp1 = row["balance"]
        assert balance_after_sp1 == 3000.00
        logger.info(f"Balance after savepoint 1 update: {balance_after_sp1}")

        # 创建第二个保存点 - 此时保存的是3000.00状态
        sp2 = transaction_manager.savepoint("POINT2")
        logger.info(f"Created savepoint 2: {sp2} - should preserve state with balance 3000.00")

        # 第二个保存点后的更新
        mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = 3500.00 WHERE account_number = 'ACC-005'"
        )

        # 验证余额
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        balance_after_sp2 = row["balance"]
        assert balance_after_sp2 == 3500.00
        logger.info(f"Balance after savepoint 2 update: {balance_after_sp2}")

        # 创建第三个保存点 - 此时保存的是3500.00状态
        sp3 = transaction_manager.savepoint("POINT3")
        logger.info(f"Created savepoint 3: {sp3} - should preserve state with balance 3500.00")

        # 第三个保存点后的更新
        mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = 4000.00 WHERE account_number = 'ACC-005'"
        )

        # 验证余额
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        balance_after_sp3 = row["balance"]
        assert balance_after_sp3 == 4000.00
        logger.info(f"Balance after savepoint 3 update: {balance_after_sp3}")

        # 回滚到第三个保存点 - 期望回到3500.00
        transaction_manager.rollback_to(sp3)
        logger.info(f"Rolled back to savepoint 3: {sp3} - should restore balance to 3500.00")

        # 验证回滚后的余额
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        balance_after_rollback_sp3 = row["balance"]
        logger.info(f"Balance after rollback to savepoint 3: {balance_after_rollback_sp3}")
        assert balance_after_rollback_sp3 == 3500.00, \
            f"Expected balance 3500.00 after rollback to savepoint 3, got {balance_after_rollback_sp3}"

        # 回滚到第二个保存点 - 期望回到3000.00
        transaction_manager.rollback_to(sp2)
        logger.info(f"Rolled back to savepoint 2: {sp2} - should restore balance to 3000.00")

        # 验证回滚到sp2后的余额
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        balance_after_rollback_sp2 = row["balance"]
        logger.info(f"Balance after rollback to savepoint 2: {balance_after_rollback_sp2}")
        assert balance_after_rollback_sp2 == 3000.00, \
            f"Expected balance 3000.00 after rollback to savepoint 2, got {balance_after_rollback_sp2}"

        # 尝试释放第一个保存点
        transaction_manager.release(sp1)
        logger.info(f"Released savepoint 1: {sp1}")

        # 再次更新余额
        mysql_transaction_test_db.execute(
            "UPDATE transaction_test_accounts SET balance = 3800.00 WHERE account_number = 'ACC-005'"
        )

        # 尝试回滚到已释放的第一个保存点 - 这应该失败
        try:
            transaction_manager.rollback_to(sp1)
            assert False, "Rollback to released savepoint should have failed"
        except TransactionError as e:
            logger.info(f"Caught expected exception when rolling back to released savepoint: {e}")

        # 提交事务
        transaction_manager.commit()
        logger.info("Committed transaction")

        # 验证最终余额
        row = mysql_transaction_test_db.fetch_one(
            "SELECT balance FROM transaction_test_accounts WHERE account_number = 'ACC-005'"
        )
        final_balance = row["balance"]
        assert final_balance == 3800.00, \
            f"Expected final balance 3800.00, got {final_balance}"
        logger.info(f"Final balance after commit: {final_balance}")

    except Exception as e:
        if transaction_manager.is_active:
            transaction_manager.rollback()
        logger.error(f"Error in multiple savepoints test: {e}")