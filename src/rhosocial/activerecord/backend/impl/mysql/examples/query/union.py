"""
UNION using SetOperation - MySQL.

This example demonstrates:
1. UNION (distinct)
2. UNION ALL
3. UNION with ORDER BY
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
)
from rhosocial.activerecord.backend.expression.core import Literal, Column  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnConstraint,
    ColumnDefinition,
    ColumnPrimaryKeyConstraint,
)

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
                ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
            ],
        ),
        ColumnDefinition("name", "VARCHAR(100)"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# Insert data into table_a
insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, "users"),
    columns=["id", "name"],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 1), Literal(dialect, "Alice")],
            [Literal(dialect, 2), Literal(dialect, "Bob")],
        ],
    ),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: UNION (distinct)
# ============================================================
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    QueryStatement,
    SetOperation,
)
from rhosocial.activerecord.backend.expression.objects import Table

# First query
query1 = QueryStatement(
    dialect=dialect,
    select=[Column(dialect, "name")],
    from_=Table(dialect, "users"),
)

query2 = QueryStatement(
    dialect=dialect,
    select=[Literal(dialect, "Charlie")],
)

# Union. The node states the operation as a word and the dialect writes the
# spelling, so a backend that gates UNION behind a probe refuses it there.
union_expr = SetOperation(
    dialect=dialect,
    op="union",
    left=query1,
    right=query2,
)
sql, params = union_expr.to_sql()
print(f"UNION SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"UNION result: {result.data}")

# ============================================================
# SECTION: UNION ALL
# ============================================================
union_all = SetOperation(
    dialect=dialect,
    op="union_all",
    left=query1,
    right=query2,
)
sql, params = union_all.to_sql()
print(f"UNION ALL SQL: {sql}")
result = backend.execute(sql, params, options=options)
print(f"UNION ALL result: {result.data}")

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
# 1. Use SetOperation with op='union' / op='union_all'; the dialect writes the
#    SQL spelling and gates it behind its own capability probes
# 2. UNION removes duplicates, UNION ALL keeps all rows
# 3. Can add ORDER BY using query1.with_order_by()
