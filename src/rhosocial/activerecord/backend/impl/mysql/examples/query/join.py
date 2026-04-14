"""
JOIN queries - INNER JOIN and LEFT JOIN.
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

from rhosocial.activerecord.backend.expression import CreateTableExpression, ColumnDefinition
from rhosocial.activerecord.backend.expression.core import Literal

create_customers = CreateTableExpression(
    dialect=dialect,
    table_name='customers',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'name', 'VARCHAR(100)', nullable=False),
        ColumnDefinition(dialect, 'email', 'VARCHAR(100)'),
    ],
    if_not_exists=True,
)
sql, params = create_customers.to_sql()
backend.execute(sql, params)

create_orders = CreateTableExpression(
    dialect=dialect,
    table_name='orders',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'customer_id', 'INT'),
        ColumnDefinition(dialect, 'total', 'DECIMAL(10,2)'),
        ColumnDefinition(dialect, 'status', 'VARCHAR(20)'),
    ],
    if_not_exists=True,
)
sql, params = create_orders.to_sql()
backend.execute(sql, params)

from rhosocial.activerecord.backend.expression import InsertExpression
insert_customers = InsertExpression(
    dialect=dialect,
    table_name='customers',
    columns=['name', 'email'],
    values=[
        [Literal(dialect, 'Alice'), Literal(dialect, 'alice@example.com')],
        [Literal(dialect, 'Bob'), Literal(dialect, 'bob@example.com')],
    ],
)
sql, params = insert_customers.to_sql()
backend.execute(sql, params)

insert_orders = InsertExpression(
    dialect=dialect,
    table_name='orders',
    columns=['customer_id', 'total', 'status'],
    values=[
        [Literal(dialect, 1), Literal(dialect, 100.00), Literal(dialect, 'completed')],
        [Literal(dialect, 1), Literal(dialect, 50.00), Literal(dialect, 'pending')],
        [Literal(dialect, 2), Literal(dialect, 75.00), Literal(dialect, 'completed')],
    ],
)
sql, params = insert_orders.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    JoinClause,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'customers', 'name'),
        Column(dialect, 'orders', 'total'),
        Column(dialect, 'orders', 'status'),
    ],
    from_=TableExpression(dialect, 'customers'),
    join=[
        JoinClause(
            dialect,
            join_type='INNER',
            target=TableExpression(dialect, 'orders'),
            condition=ComparisonPredicate(
                dialect,
                '=',
                Column(dialect, 'customers', 'id'),
                Column(dialect, 'orders', 'customer_id'),
            ),
        ),
    ],
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '=',
            Column(dialect, 'orders', 'status'),
            Literal(dialect, 'completed'),
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
