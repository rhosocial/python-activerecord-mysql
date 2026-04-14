"""
Window functions - ROW_NUMBER, RANK, and aggregate over windows.
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
    table_name='sales_data',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'salesperson', 'VARCHAR(100)'),
        ColumnDefinition(dialect, 'region', 'VARCHAR(50)'),
        ColumnDefinition(dialect, 'amount', 'DECIMAL(10,2)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    table_name='sales_data',
    columns=['salesperson', 'region', 'amount'],
    values=[
        [Literal(dialect, 'Alice'), Literal(dialect, 'North'), Literal(dialect, 1000)],
        [Literal(dialect, 'Alice'), Literal(dialect, 'North'), Literal(dialect, 1500)],
        [Literal(dialect, 'Bob'), Literal(dialect, 'North'), Literal(dialect, 1200)],
        [Literal(dialect, 'Bob'), Literal(dialect, 'South'), Literal(dialect, 1800)],
        [Literal(dialect, 'Charlie'), Literal(dialect, 'South'), Literal(dialect, 2000)],
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
    WindowSpecification,
    OrderByClause,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'salesperson'),
        Column(dialect, 'region'),
        Column(dialect, 'amount'),
        FunctionCall(dialect, 'ROW_NUMBER').over(
            WindowSpecification(
                dialect,
                partition_by=[Column(dialect, 'region')],
                order_by=OrderByClause(dialect, expressions=[(Column(dialect, 'amount'), 'DESC')]),
            )
        ).as_('row_num'),
        FunctionCall(dialect, 'SUM', Column(dialect, 'amount')).over(
            WindowSpecification(
                dialect,
                partition_by=[Column(dialect, 'region')],
            )
        ).as_('region_total'),
    ],
    from_=TableExpression(dialect, 'sales_data'),
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
