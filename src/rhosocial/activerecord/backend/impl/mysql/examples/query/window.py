"""
Window functions - ROW_NUMBER, RANK, and aggregate over windows.
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
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "test"),
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
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
    from rhosocial.activerecord.backend.expression.core import Parameter  # noqa: E402
    from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
        ColumnConstraint,
        ColumnDefinition,
        ColumnNotNullConstraint,
        ColumnPrimaryKeyConstraint,
    )

    drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, "sales_data"), if_exists=True)
    sql, params = drop_table.to_sql()
    backend.execute(sql, params)

    create_table = CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, "sales_data"),
        columns=[
            ColumnDefinition(
                "id",
                integer_auto_increment_parts(None, "INT")[0],
                constraints=[
                    ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
                    ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
                ],
             attributes=integer_auto_increment_parts(None, "INT")[1]),
            ColumnDefinition("salesperson", "VARCHAR(100)"),
            ColumnDefinition("region", "VARCHAR(50)"),
            ColumnDefinition("amount", "DECIMAL(10,2)"),
        ],
        if_not_exists=True,
    )
    sql, params = create_table.to_sql()
    backend.execute(sql, params)

    insert = InsertStatement(
        dialect=dialect,
        into=Table(dialect, "sales_data"),
        columns=["salesperson", "region", "amount"],
        source=ValuesSource(
            dialect,
            [
                [Parameter(dialect, "Alice"), Parameter(dialect, "North"), Parameter(dialect, 1000)],
                [Parameter(dialect, "Alice"), Parameter(dialect, "North"), Parameter(dialect, 1500)],
                [Parameter(dialect, "Bob"), Parameter(dialect, "North"), Parameter(dialect, 1200)],
                [Parameter(dialect, "Bob"), Parameter(dialect, "South"), Parameter(dialect, 1800)],
                [Parameter(dialect, "Charlie"), Parameter(dialect, "South"), Parameter(dialect, 2000)],
            ],
        ),
    )
    sql, params = insert.to_sql()
    backend.execute(sql, params)

    # ============================================================
    # SECTION: Business Logic (the pattern to learn)
    # ============================================================
    from rhosocial.activerecord.backend.expression import (  # noqa: E402
        QueryStatement,
        Column,
        WindowSpecification,
        OrderByClause,
    )
    from rhosocial.activerecord.backend.expression.core import FunctionCall  # noqa: E402
    from rhosocial.activerecord.backend.expression.objects import Table

    query = QueryStatement(
        dialect=dialect,
        select=[
            Column(dialect, "salesperson"),
            Column(dialect, "region"),
            Column(dialect, "amount"),
            FunctionCall(
                dialect,
                "ROW_NUMBER",
                window_spec=WindowSpecification(
                    dialect,
                    partition_by=[Column(dialect, "region")],
                    order_by=OrderByClause(dialect, expressions=[(Column(dialect, "amount"), "DESC")]),
                ),
                alias="row_num",
            ),
            FunctionCall(
                dialect,
                "SUM",
                Column(dialect, "amount"),
                window_spec=WindowSpecification(
                    dialect,
                    partition_by=[Column(dialect, "region")],
                ),
                alias="region_total",
            ),
        ],
        from_=Table(dialect, "sales_data"),
    )

    sql, params = query.to_sql()
    print(f"SQL: {sql}")
    print(f"Params: {params}")

    # ============================================================
    # SECTION: Execution (run the expression)
    # ============================================================
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = backend.execute(sql, params, options=options)
    print(f"Rows returned: {len(result.data) if result.data else 0}")
    for row in result.data or []:
        print(f" {row}")

    # ============================================================
    # SECTION: Teardown (necessary for execution, reference only)
    # ============================================================
    backend.disconnect()
