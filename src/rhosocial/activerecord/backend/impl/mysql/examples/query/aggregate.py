"""
Aggregate queries with GROUP BY and HAVING.
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

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='sales',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'product', 'VARCHAR(100)'),
        ColumnDefinition(dialect, 'quantity', 'INT'),
        ColumnDefinition(dialect, 'price', 'DECIMAL(10,2)'),
        ColumnDefinition(dialect, 'region', 'VARCHAR(50)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    table_name='sales',
    columns=['product', 'quantity', 'price', 'region'],
    values=[
        [Literal(dialect, 'Widget'), Literal(dialect, 10), Literal(dialect, 5.00), Literal(dialect, 'North')],
        [Literal(dialect, 'Widget'), Literal(dialect, 5), Literal(dialect, 5.00), Literal(dialect, 'South')],
        [Literal(dialect, 'Gadget'), Literal(dialect, 8), Literal(dialect, 10.00), Literal(dialect, 'North')],
        [Literal(dialect, 'Gadget'), Literal(dialect, 3), Literal(dialect, 10.00), Literal(dialect, 'South')],
        [Literal(dialect, 'Widget'), Literal(dialect, 7), Literal(dialect, 5.00), Literal(dialect, 'East')],
    ],
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    GroupByClause,
    HavingClause,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'product'),
        FunctionCall(dialect, 'SUM', Column(dialect, 'quantity')).as_('total_qty'),
        FunctionCall(dialect, 'AVG', Column(dialect, 'price')).as_('avg_price'),
    ],
    from_=TableExpression(dialect, 'sales'),
    group_by=GroupByClause(
        dialect,
        expressions=[Column(dialect, 'product')],
    ),
    having=HavingClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '>',
            FunctionCall(dialect, 'SUM', Column(dialect, 'quantity')),
            Literal(dialect, 10),
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
