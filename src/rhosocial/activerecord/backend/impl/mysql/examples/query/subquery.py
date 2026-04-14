"""
Subquery expressions - WHERE and FROM subqueries.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = MySQLConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USERNAME', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    charset='utf8mb4',
)
backend = MySQLBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import CreateTableExpression, ColumnDefinition, InsertExpression
from rhosocial.activerecord.backend.expression.core import Literal

create_departments = CreateTableExpression(
    dialect=dialect,
    table_name='departments',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'name', 'VARCHAR(100)'),
        ColumnDefinition(dialect, 'budget', 'DECIMAL(15,2)'),
    ],
    if_not_exists=True,
)
sql, params = create_departments.to_sql()
backend.execute(sql, params)

create_employees = CreateTableExpression(
    dialect=dialect,
    table_name='employees',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'name', 'VARCHAR(100)'),
        ColumnDefinition(dialect, 'salary', 'DECIMAL(10,2)'),
        ColumnDefinition(dialect, 'department_id', 'INT'),
    ],
    if_not_exists=True,
)
sql, params = create_employees.to_sql()
backend.execute(sql, params)

insert_departments = InsertExpression(
    dialect=dialect,
    table_name='departments',
    columns=['name', 'budget'],
    values=[
        [Literal(dialect, 'Engineering'), Literal(dialect, 1000000)],
        [Literal(dialect, 'Sales'), Literal(dialect, 500000)],
    ],
)
sql, params = insert_departments.to_sql()
backend.execute(sql, params)

insert_employees = InsertExpression(
    dialect=dialect,
    table_name='employees',
    columns=['name', 'salary', 'department_id'],
    values=[
        [Literal(dialect, 'Alice'), Literal(dialect, 80000), Literal(dialect, 1)],
        [Literal(dialect, 'Bob'), Literal(dialect, 90000), Literal(dialect, 1)],
        [Literal(dialect, 'Charlie'), Literal(dialect, 60000), Literal(dialect, 2)],
        [Literal(dialect, 'David'), Literal(dialect, 70000), Literal(dialect, 2)],
    ],
)
sql, params = insert_employees.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
    SubqueryExpression,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

subquery = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'AVG', Column(dialect, 'salary'))],
    from_=TableExpression(dialect, 'employees'),
)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'name'),
        Column(dialect, 'salary'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '>',
            Column(dialect, 'salary'),
            SubqueryExpression(dialect, subquery),
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
