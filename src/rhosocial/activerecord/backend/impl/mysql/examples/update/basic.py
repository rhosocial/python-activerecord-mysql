"""
UPDATE using UpdateStatement - MySQL.

This example demonstrates:
1. Update single row
2. Update with WHERE condition
3. Update multiple rows
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

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
    UpdateStatement,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column  # noqa: E402
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate  # noqa: E402
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table

# Drop table first for clean setup
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
                ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None, is_auto_increment=True)),
                ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
            ],
        ),
        ColumnDefinition(
            "name",
            "VARCHAR(100)",
            constraints=[
                ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
            ],
        ),
        ColumnDefinition("age", "INT"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, "users"),
    columns=["name", "age"],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, "Alice"), Literal(dialect, 25)],
            [Literal(dialect, "Bob"), Literal(dialect, 30)],
        ],
    ),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Update Single Row
# ============================================================
update_expr = UpdateStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    assignments={"age": Literal(dialect, 26)},
    where=ComparisonPredicate(dialect, "=", Column(dialect, "name"), Literal(dialect, "Alice")),
)
sql, params = update_expr.to_sql()
print(f"Update SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DML)
result = backend.execute(sql, params, options=options)
print(f"Updated rows: {result.affected_rows}")

# ============================================================
# SECTION: Update with Expression
# ============================================================
update_expr = UpdateStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    assignments={
        "age": BinaryArithmeticExpression(dialect, "+", Column(dialect, "age"), Literal(dialect, 1)),
    },
    where=ComparisonPredicate(dialect, "=", Column(dialect, "name"), Literal(dialect, "Alice")),
)
sql, params = update_expr.to_sql()
print(f"Update with expression SQL: {sql}")
result = backend.execute(sql, params, options=options)
print(f"Updated rows: {result.affected_rows}")

# ============================================================
# SECTION: Update All Rows
# ============================================================
update_expr = UpdateStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    assignments={"age": Literal(dialect, 99)},
)
sql, params = update_expr.to_sql()
print(f"Update all SQL: {sql}")
result = backend.execute(sql, params, options=options)
print(f"Updated rows: {result.affected_rows}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_expr = DropTableStatement(dialect=dialect, table=Table(dialect, "users"), if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use UpdateStatement with assignments dict for SET clause
# 2. Use BinaryArithmeticExpression for expressions like age + 1
# 3. Omit where parameter to update all rows
# 4. affected_rows shows number of updated rows
