"""
FOR UPDATE Row Locking - MySQL.

This example demonstrates:
1. SELECT ... FOR UPDATE to lock rows
2. Preventing dirty reads in concurrent scenarios
3. Using SKIP LOCKED for non-blocking locks
4. NOWAIT for immediate failure on lock
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
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='accounts',
    columns=[
        ColumnDefinition('id', 'INT AUTO_INCREMENT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ]),
        ColumnDefinition('name', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('balance', 'DECIMAL(10,2)', default_value='0'),
    ],
    if_not_exists=True,
    extra='ENGINE=InnoDB',
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

truncate_table = DropTableExpression(dialect=dialect, table_name='accounts')
sql, params = truncate_table.to_sql()
if_exists = truncate_table.if_exists
truncate_sql = f"TRUNCATE TABLE accounts"
backend.execute(truncate_sql)

insert_expr = InsertExpression(
    dialect=dialect,
    table_name='accounts',
    columns=['name', 'balance'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Alice'), Literal(dialect, 1000)],
        [Literal(dialect, 'Bob'), Literal(dialect, 500)],
    ]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: SELECT FOR UPDATE
# ============================================================
# Lock rows to prevent concurrent modifications

# In a transaction, select with FOR UPDATE
with backend.transaction():
    # Lock Alice's row
    result = backend.execute(
        "SELECT * FROM accounts WHERE name = 'Alice' FOR UPDATE"
    )
    print(f"Locked row: {result.data}")

    # Update the balance
    backend.execute(
        "UPDATE accounts SET balance = balance - 100 WHERE name = 'Alice'"
    )

# The lock is released after commit

# ============================================================
# SECTION: FOR UPDATE with WHERE Conditions
# ============================================================
# Lock specific rows based on conditions

with backend.transaction():
    result = backend.execute(
        "SELECT * FROM accounts WHERE balance > 500 FOR UPDATE"
    )
    print(f"Locked high balance accounts: {len(result.data)} rows")

# ============================================================
# SECTION: SKIP LOCKED (MySQL 8.0+)
# ============================================================
# Skip locked rows instead of waiting

result = backend.execute("""
    SELECT * FROM accounts FOR UPDATE SKIP LOCKED
""")
print(f"SKIP LOCKED result: {result.data}")

# ============================================================
# SECTION: NOWAIT (MySQL 8.0+)
# ============================================================
# Fail immediately if rows are locked

try:
    result = backend.execute(
        "SELECT * FROM accounts WHERE name = 'Alice' FOR UPDATE NOWAIT"
    )
    print(f"NOWAIT result: {result.data}")
except Exception as e:
    print(f"NOWAIT failed (expected if locked): {e}")

# ============================================================
# SECTION: Lock Modes
# ============================================================
# FOR UPDATE - exclusive lock (write lock)
# FOR SHARE - shared lock (read lock)

with backend.transaction():
    # Shared lock - allows other transactions to also read
    result = backend.execute(
        "SELECT * FROM accounts FOR SHARE"
    )
    print(f"FOR SHARE result: {len(result.data)} rows")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table_name='accounts', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use FOR UPDATE to lock rows during transaction
# 2. Prevents other transactions from modifying locked rows
# 3. SKIP LOCKED skips locked rows (MySQL 8.0+)
# 4. NOWAIT fails immediately if locked (MySQL 8.0+)
# 5. FOR SHARE allows concurrent reads
# 6. Requires InnoDB engine
# 7. Locks released on COMMIT/ROLLBACK