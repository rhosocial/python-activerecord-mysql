"""
UPSERT (INSERT ... ON DUPLICATE KEY UPDATE) - MySQL.

This example demonstrates:
1. INSERT ... ON DUPLICATE KEY UPDATE
2. Using VALUES() to reference attempted values
3. Affected rows tracking
4. UPSERT with multiple values
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
    DropTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INT AUTO_INCREMENT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ]),
        ColumnDefinition('username', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
            ColumnConstraint(ColumnConstraintType.UNIQUE),
        ]),
        ColumnDefinition('email', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('login_count', 'INT', default_value='0'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

truncate_sql = "TRUNCATE TABLE users"
backend.execute(truncate_sql)

# ============================================================
# SECTION: INSERT ON DUPLICATE KEY UPDATE
# ============================================================
# Update on duplicate key

backend.execute("""
    INSERT INTO users (username, email, login_count)
    VALUES ('alice', 'alice@example.com', 1)
    ON DUPLICATE KEY UPDATE login_count = login_count + 1
""")

result = backend.execute("SELECT * FROM users WHERE username = 'alice'")
print(f"Initial insert: {result.data}")

# Insert again - will update
backend.execute("""
    INSERT INTO users (username, email, login_count)
    VALUES ('alice', 'alice@example.com', 1)
    ON DUPLICATE KEY UPDATE login_count = login_count + 1
""")

result = backend.execute("SELECT * FROM users WHERE username = 'alice'")
print(f"After UPSERT: {result.data}")

# ============================================================
# SECTION: Using VALUES() function
# ============================================================
# Reference the values being inserted

backend.execute("""
    INSERT INTO users (username, email, login_count)
    VALUES ('bob', 'bob@example.com', 1)
    ON DUPLICATE KEY UPDATE email = VALUES(email)
""")

# ============================================================
# SECTION: UPSERT with affected rows
# ============================================================
# affected_rows: 1 = inserted, 2 = updated

result = backend.execute("""
    INSERT INTO users (username, email, login_count)
    VALUES ('charlie', 'charlie@example.com', 1)
    ON DUPLICATE KEY UPDATE login_count = login_count + 1
""")
print(f"Insert affected_rows: {result.affected_rows}")

result = backend.execute("""
    INSERT INTO users (username, email, login_count)
    VALUES ('charlie', 'charlie@example.com', 1)
    ON DUPLICATE KEY UPDATE login_count = login_count + 1
""")
print(f"Update affected_rows: {result.affected_rows}")

# ============================================================
# SECTION: Multiple row UPSERT
# ============================================================
# MySQL supports multiple row VALUES()

backend.execute("""
    INSERT INTO users (username, email, login_count) VALUES
        ('david', 'david@example.com', 1),
        ('eve', 'eve@example.com', 1)
    ON DUPLICATE KEY UPDATE login_count = login_count + 1
""")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Requires unique key or primary key for conflict detection
# 2. Use ON DUPLICATE KEY UPDATE clause
# 3. VALUES(col) references attempted values
# 4. affected_rows = 1 for insert, 2 for update
# 5. Works with multiple rows at once