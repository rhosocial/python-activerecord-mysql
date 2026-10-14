"""
DDL Test Script for MySQL Backend
Tests CreateTableStatement, DropTableStatement, AlterTableStatement, etc.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.expression import (
    ColumnDefinition,
    CreateTableStatement,
    DropTableStatement,
    AlterTableStatement,
    AddColumn,
    DropColumn,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)


class User(ActiveRecord):
    """User Model for DDL test"""
    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "ddl_test_users"


def main():
    # Configure with MySQL backend
    from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

    config = MySQLConnectionConfig(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        database=os.environ.get("MYSQL_DATABASE", "test_db"),
        username=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
        ssl_verify_cert=False,
    )
    User.configure(config, MySQLBackend)

    dialect = User.__backend__.dialect
    backend = User.__backend__
    introspector = backend.introspector

    print(f"Connected to MySQL: {dialect.get_server_version()}")
    print()

    # ============================================================
    # Test 1: Create Table
    # ============================================================
    print("=== Test 1: Create Table ===")
    columns = [
        ColumnDefinition(
            "id",
            "INTEGER",
            constraints=[ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None))]
        ),
        ColumnDefinition(
            "name",
            "VARCHAR(100)",
            constraints=[ColumnConstraint(None, branch=ColumnNotNullConstraint(None))]
        ),
        ColumnDefinition(
            "email",
            "VARCHAR(255)",
            constraints=[ColumnConstraint(None, branch=ColumnNotNullConstraint(None))]
        ),
    ]

    create = CreateTableStatement(
        dialect=dialect,
        table_name="ddl_test_users",
        columns=columns,
    )

    sql, params = create.to_sql()
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection
    tables = introspector.list_tables()
    print(f"Tables after create: {[t.name for t in tables]}")
    print()

    # ============================================================
    # Test 2: Create Table with IF NOT EXISTS
    # ============================================================
    print("=== Test 2: Create Table with IF NOT EXISTS ===")
    create2 = CreateTableStatement(
        dialect=dialect,
        table_name="ddl_test_users",
        columns=columns,
        if_not_exists=True,
    )

    sql, params = create2.to_sql()
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create2.to_sql()
    backend.execute(sql_str, params_str)
    print("Created with IF NOT EXISTS successfully")
    print()

    # ============================================================
    # Test 3: Alter Table - Add Column
    # ============================================================
    print("=== Test 3: Alter Table - Add Column ===")
    alter = AlterTableStatement(
        dialect,
        table_name="ddl_test_users",
        actions=[
            AddColumn(ColumnDefinition("phone", "VARCHAR(20)"))
        ]
    )

    sql, params = alter.to_sql()
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = alter.to_sql()
    backend.execute(sql_str, params_str)

    # Verify column added
    table_info = introspector.get_table_info("ddl_test_users")
    if table_info and table_info.columns:
        print(f"Columns: {[c.name for c in table_info.columns]}")
    print()

    # ============================================================
    # Test 4: Alter Table - Drop Column
    # ============================================================
    print("=== Test 4: Alter Table - Drop Column ===")
    # First add a column to drop
    alter_add = AlterTableStatement(
        dialect,
        table_name="ddl_test_users",
        actions=[AddColumn(ColumnDefinition("temp_field", "TEXT"))]
    )
    sql_str, params_str = alter_add.to_sql()
    backend.execute(sql_str, params_str)

    alter_drop = AlterTableStatement(
        dialect,
        table_name="ddl_test_users",
        actions=[DropColumn("temp_field")]
    )

    sql, params = alter_drop.to_sql()
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = alter_drop.to_sql()
    backend.execute(sql_str, params_str)

    table_info = introspector.get_table_info("ddl_test_users")
    if table_info and table_info.columns:
        print(f"Columns after drop: {[c.name for c in table_info.columns]}")
    print()

    # ============================================================
    # Test 5: Drop Table
    # ============================================================
    print("=== Test 5: Drop Table ===")
    drop = DropTableStatement(
        dialect,
        table_name="ddl_test_users",
        if_exists=True,
    )

    sql, params = drop.to_sql()
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = drop.to_sql()
    backend.execute(sql_str, params_str)

    tables = introspector.list_tables()
    print(f"Tables after drop: {[t.name for t in tables]}")
    print()

    print("=== All MySQL DDL tests completed! ===")


if __name__ == "__main__":
    main()