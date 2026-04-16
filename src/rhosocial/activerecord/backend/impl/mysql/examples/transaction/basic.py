"""
Basic transaction control using transaction manager.

This example demonstrates:
1. How to use the transaction context manager
2. How to handle transaction rollback on error
3. How to use savepoints for nested transactions
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

config = MySQLConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USERNAME', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
)
backend = MySQLBackend(connection_config=config)
backend.connect()

# Create table for testing
backend.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        balance DECIMAL(10,2) DEFAULT 0
    )
""")
backend.execute("INSERT INTO accounts (name, balance) VALUES ('Alice', 100)")

# ============================================================
# SECTION: Transaction Context Manager
# ============================================================
# The transaction() method returns a context manager
# that automatically handles COMMIT/ROLLBACK

# Auto-commit is disabled by default, each statement is in its own transaction
# Use transaction() for explicit control

# Simple transaction - auto commits on success
with backend.transaction():
    backend.execute("UPDATE accounts SET balance = balance - 50 WHERE name = 'Alice'")

# Verify
result = backend.execute("SELECT balance FROM accounts WHERE name = 'Alice'")
print(f"Balance after transaction: {result.data[0]['balance']}")

# ============================================================
# SECTION: Transaction with Rollback
# ============================================================
# If an exception is raised, the transaction is rolled back

try:
    with backend.transaction():
        backend.execute("UPDATE accounts SET balance = balance - 50 WHERE name = 'Alice'")
        # This will fail - balance cannot be negative
        backend.execute("UPDATE accounts SET balance = -100 WHERE name = 'Alice'")
except Exception as e:
    print(f"Transaction rolled back: {e}")

# ============================================================
# SECTION: Savepoints (Nested Transactions)
# ============================================================
# MySQL supports savepoints for nested transactions

with backend.transaction() as txn:
    backend.execute("UPDATE accounts SET balance = balance - 10 WHERE name = 'Alice'")
    txn.savepoint("sp1")

    try:
        backend.execute("UPDATE accounts SET balance = balance - 20 WHERE name = 'Alice'")
    except Exception:
        txn.rollback_to("sp1")  # Rollback to savepoint, continue transaction

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use backend.transaction() as a context manager
# 2. Exceptions automatically trigger rollback
# 3. Use savepoints for partial rollback
# 4. MySQL requires InnoDB engine for transactions