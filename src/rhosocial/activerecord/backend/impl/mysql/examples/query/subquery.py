"""
Subquery expressions - WHERE and FROM subqueries.
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

    drop_departments = DropTableStatement(dialect=dialect, table=Table(dialect, "departments"), if_exists=True)
    sql, params = drop_departments.to_sql()
    backend.execute(sql, params)

    drop_employees = DropTableStatement(dialect=dialect, table=Table(dialect, "employees"), if_exists=True)
    sql, params = drop_employees.to_sql()
    backend.execute(sql, params)

    create_departments = CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, "departments"),
        columns=[
            ColumnDefinition(
                "id",
                integer_auto_increment_parts(None, "INT")[0],
                constraints=[
                    ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
                    ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
                ],
             attributes=integer_auto_increment_parts(None, "INT")[1]),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition("budget", "DECIMAL(15,2)"),
        ],
        if_not_exists=True,
    )
    sql, params = create_departments.to_sql()
    backend.execute(sql, params)

    create_employees = CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, "employees"),
        columns=[
            ColumnDefinition(
                "id",
                integer_auto_increment_parts(None, "INT")[0],
                constraints=[
                    ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
                    ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
                ],
             attributes=integer_auto_increment_parts(None, "INT")[1]),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition("salary", "DECIMAL(10,2)"),
            ColumnDefinition("department_id", "INT"),
        ],
        if_not_exists=True,
    )
    sql, params = create_employees.to_sql()
    backend.execute(sql, params)

    insert_departments = InsertStatement(
        dialect=dialect,
        into=Table(dialect, "departments"),
        columns=["name", "budget"],
        source=ValuesSource(
            dialect,
            [
                [Parameter(dialect, "Engineering"), Parameter(dialect, 1000000)],
                [Parameter(dialect, "Sales"), Parameter(dialect, 500000)],
            ],
        ),
    )
    sql, params = insert_departments.to_sql()
    backend.execute(sql, params)

    insert_employees = InsertStatement(
        dialect=dialect,
        into=Table(dialect, "employees"),
        columns=["name", "salary", "department_id"],
        source=ValuesSource(
            dialect,
            [
                [Parameter(dialect, "Alice"), Parameter(dialect, 80000), Parameter(dialect, 1)],
                [Parameter(dialect, "Bob"), Parameter(dialect, 90000), Parameter(dialect, 1)],
                [Parameter(dialect, "Charlie"), Parameter(dialect, 60000), Parameter(dialect, 2)],
                [Parameter(dialect, "David"), Parameter(dialect, 70000), Parameter(dialect, 2)],
            ],
        ),
    )
    sql, params = insert_employees.to_sql()
    backend.execute(sql, params)

    # ============================================================
    # SECTION: Business Logic (the pattern to learn)
    # ============================================================
    from rhosocial.activerecord.backend.expression import (  # noqa: E402
        QueryStatement,
        Column,
        WhereClause,
        Subquery,
    )
    from rhosocial.activerecord.backend.expression import functions as F  # noqa: E402
    from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate  # noqa: E402
    from rhosocial.activerecord.backend.expression.objects import Table

    subquery_query = QueryStatement(
        dialect=dialect,
        select=[F.avg(dialect, Column(dialect, "salary"))],
        from_=Table(dialect, "employees"),
    )
    sql, params = subquery_query.to_sql()
    subquery = Subquery(dialect, sql, params)

    query = QueryStatement(
        dialect=dialect,
        select=[
            Column(dialect, "name"),
            Column(dialect, "salary"),
        ],
        from_=Table(dialect, "employees"),
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(
                dialect,
                ">",
                Column(dialect, "salary"),
                subquery,
            ),
        ),
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
