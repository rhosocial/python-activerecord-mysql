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
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

config = MySQLConnectionConfig(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    database=os.getenv("MYSQL_DATABASE", "test"),
    username=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
)
backend = MySQLBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import CreateTableStatement, DropTableStatement  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnConstraint,
    ColumnDefinition,
    ColumnPrimaryKeyConstraint,
)

# Drop dependent tables first for clean setup
drop_orders = DropTableStatement(dialect=dialect, table=Table(dialect, "orders"), if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, "users"), if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    columns=[
        ColumnDefinition(
            "id",
            "INT",
            constraints=[
                ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
            ],
        ),
        ColumnDefinition("email", "VARCHAR(100)"),
        ColumnDefinition("name", "VARCHAR(100)"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE UNIQUE INDEX
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexStatement, DropIndexStatement  # noqa: E402
from rhosocial.activerecord.backend.expression.objects import Index, Table

# Drop index first if exists (MySQL does not support IF NOT EXISTS in CREATE INDEX)
try:
    drop_idx = DropIndexStatement(dialect=dialect, index=Index(dialect, "idx_users_email_unique"))
    sql, params = drop_idx.to_sql()
    backend.execute(sql, params)
except Exception:
    pass

unique_idx = CreateIndexStatement(
    dialect=dialect,
    index=Index(dialect, "idx_users_email_unique"),
    table=Table(dialect, "users"),
    columns=["email"],
    unique=True,
)
sql, params = unique_idx.to_sql()
print(f"CREATE UNIQUE INDEX SQL: {sql}")
print(f"Params: {params}")
backend.execute(sql, params)

# ============================================================
# SECTION: CREATE INDEX with multiple columns
# ============================================================
# Drop composite index first if exists
try:
    drop_idx2 = DropIndexStatement(dialect=dialect, index=Index(dialect, "idx_users_name_email"))
    sql, params = drop_idx2.to_sql()
    backend.execute(sql, params)
except Exception:
    pass

composite_idx = CreateIndexStatement(
    dialect=dialect,
    index=Index(dialect, "idx_users_name_email"),
    table=Table(dialect, "users"),
    columns=["name", "email"],
)
sql, params = composite_idx.to_sql()
print(f"CREATE INDEX multi-col SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Teardown
# ============================================================
drop_orders = DropTableStatement(dialect=dialect, table=Table(dialect, "orders"), if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, "users"), if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use CreateIndexStatement with unique=True
# 2. Use columns=[col1, col2] for composite index
# 3. Use DropIndexStatement to drop
