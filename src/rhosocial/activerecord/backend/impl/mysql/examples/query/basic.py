"""
Basic SELECT query with WHERE, ORDER BY, and LIMIT clauses.
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

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'name', 'VARCHAR(100)', nullable=False),
        ColumnDefinition(dialect, 'age', 'INT'),
        ColumnDefinition(dialect, 'status', 'VARCHAR(20)', default=Literal(dialect, 'active')),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

from rhosocial.activerecord.backend.expression import InsertExpression
insert = InsertExpression(
    dialect=dialect,
    table_name='users',
    columns=['name', 'age', 'status'],
    values=[
        [Literal(dialect, 'Alice'), Literal(dialect, 30), Literal(dialect, 'active')],
        [Literal(dialect, 'Bob'), Literal(dialect, 25), Literal(dialect, 'active')],
        [Literal(dialect, 'Charlie'), Literal(dialect, 35), Literal(dialect, 'inactive')],
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
    WhereClause,
    OrderByClause,
    LimitOffsetClause,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'age'),
    ],
    from_=TableExpression(dialect, 'users'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '=',
            Column(dialect, 'status'),
            Literal(dialect, 'active'),
        ),
    ),
    order_by=OrderByClause(
        dialect,
        expressions=[(Column(dialect, 'age'), 'ASC')],
    ),
    limit_offset=LimitOffsetClause(dialect, limit=10),
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
