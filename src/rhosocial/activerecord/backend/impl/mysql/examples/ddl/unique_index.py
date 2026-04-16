"""
CREATE UNIQUE INDEX - MySQL.

This example demonstrates:
1. CREATE UNIQUE INDEX
2. CREATE INDEX with multiple columns
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

from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ]),
        ColumnDefinition('email', 'VARCHAR(100)'),
        ColumnDefinition('name', 'VARCHAR(100)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE UNIQUE INDEX
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexExpression

unique_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_users_email_unique',
    table_name='users',
    columns=['email'],
    unique=True,
    if_not_exists=True,
)
sql, params = unique_idx.to_sql()
print(f"CREATE UNIQUE INDEX SQL: {sql}")
print(f"Params: {params}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE INDEX with multiple columns
# ============================================================
composite_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_users_name_email',
    table_name='users',
    columns=['name', 'email'],
    if_not_exists=True,
)
sql, params = composite_idx.to_sql()
print(f"CREATE INDEX multi-col SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Teardown
# ============================================================
from rhosocial.activerecord.backend.expression import DropIndexExpression, DropTableExpression

drop_idx = DropIndexExpression(dialect=dialect, index_name='idx_users_email_unique')
sql, params = drop_idx.to_sql()
backend.execute(sql, params)

drop_table = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use CreateIndexExpression with unique=True
# 2. Use columns=[col1, col2] for composite index
# 3. Use DropIndexExpression to drop