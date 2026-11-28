"""
DELETE using DeleteStatement - MySQL.

This example demonstrates:
1. Delete single row using DeleteStatement
2. Delete with WHERE condition
3. Delete all rows
"""
from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

if __name__ == "__main__":
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

    from rhosocial.activerecord.backend.expression import (  # noqa: E402
        CreateTableStatement,
        InsertStatement,
        ValuesSource,
        DropTableStatement,
    )
    from rhosocial.activerecord.backend.expression.core import Parameter, Column  # noqa: E402
    from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
        ColumnConstraint,
        ColumnDefinition,
        ColumnNotNullConstraint,
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
                integer_auto_increment_parts(None, "INT")[0],
                constraints=[
                    ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
                    ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
                ],
             attributes=integer_auto_increment_parts(None, "INT")[1]),
            ColumnDefinition(
                "name",
                "VARCHAR(100)",
                constraints=[
                    ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
                ],
            ),
        ],
        if_not_exists=True,
    )
    sql, params = create_table.to_sql()
    print(f"Create table SQL: {sql}")
    backend.execute(sql, params)

    insert = InsertStatement(
        dialect=dialect,
        into=Table(dialect, "users"),
        columns=["name"],
        source=ValuesSource(
            dialect,
            [
                [Parameter(dialect, "Alice")],
                [Parameter(dialect, "Bob")],
                [Parameter(dialect, "Charlie")],
            ],
        ),
    )
    sql, params = insert.to_sql()
    print(f"Insert SQL: {sql}")
    backend.execute(sql, params)

    # ============================================================
    # SECTION: Delete Single Row
    # ============================================================
    from rhosocial.activerecord.backend.expression import DeleteStatement  # noqa: E402
    from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate  # noqa: E402
    from rhosocial.activerecord.backend.expression.objects import Table

    delete_expr = DeleteStatement(
        dialect=dialect,
        tables=Table(dialect, "users"),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "name"), Parameter(dialect, "Alice")),
    )
    sql, params = delete_expr.to_sql()
    print(f"Delete SQL: {sql}")
    print(f"Params: {params}")

    options = ExecutionOptions(stmt_type=StatementType.DML)
    result = backend.execute(sql, params, options=options)
    print(f"Deleted rows: {result.affected_rows}")

    # ============================================================
    # SECTION: Delete with Condition
    # ============================================================
    delete_expr = DeleteStatement(
        dialect=dialect,
        tables=Table(dialect, "users"),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "name"), Parameter(dialect, "Bob")),
    )
    sql, params = delete_expr.to_sql()
    print(f"Delete SQL: {sql}")
    result = backend.execute(sql, params, options=options)
    print(f"Deleted rows: {result.affected_rows}")

    # ============================================================
    # SECTION: Delete All Rows
    # ============================================================
    delete_expr = DeleteStatement(dialect=dialect, tables=Table(dialect, "users"))
    sql, params = delete_expr.to_sql()
    print(f"Delete all SQL: {sql}")
    result = backend.execute(sql, params, options=options)
    print(f"Deleted rows: {result.affected_rows}")

    # ============================================================
    # SECTION: Teardown (necessary for execution, reference only)
    # ============================================================
    drop_orders = DropTableStatement(dialect=dialect, table=Table(dialect, "orders"), if_exists=True)
    sql, params = drop_orders.to_sql()
    backend.execute(sql, params)

    drop_expr = DropTableStatement(dialect=dialect, table=Table(dialect, "users"), if_exists=True)
    sql, params = drop_expr.to_sql()
    backend.execute(sql, params)
    backend.disconnect()

    # ============================================================
    # SECTION: Summary
    # ============================================================
    # Key points:
    # 1. Use DeleteStatement to build DELETE query
    # 2. Use ComparisonPredicate for WHERE conditions
    # 3. Omit where parameter to delete all rows
    # 4. affected_rows shows number of deleted rows
