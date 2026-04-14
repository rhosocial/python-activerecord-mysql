"""
MySQL-specific full-text search using MATCH...AGAINST.
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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    ColumnDefinition,
    InsertExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='articles',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'title', 'VARCHAR(200)'),
        ColumnDefinition(dialect, 'content', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

backend.execute("DROP TABLE IF EXISTS articles")

create_table_with_ft = CreateTableExpression(
    dialect=dialect,
    table_name='articles',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'title', 'VARCHAR(200)'),
        ColumnDefinition(dialect, 'content', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table_with_ft.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    table_name='articles',
    columns=['title', 'content'],
    values=[
        [Literal(dialect, 'MySQL Tutorial'), Literal(dialect, 'This tutorial covers MySQL database basics and advanced features.')],
        [Literal(dialect, 'PostgreSQL Guide'), Literal(dialect, 'Learn PostgreSQL from beginner to advanced level.')],
        [Literal(dialect, 'Database Design'), Literal(dialect, 'Best practices for designing relational databases including MySQL and PostgreSQL.')],
    ],
)
sql, params = insert.to_sql()
backend.execute(sql, params)

from rhosocial.activerecord.backend.expression import CreateIndexExpression
create_ft_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='ft_idx',
    table_name='articles',
    columns=['title', 'content'],
    index_type='FULLTEXT',
)
sql, params = create_ft_idx.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
)
from rhosocial.activerecord.backend.impl.mysql.functions.fulltext import match_against

match_expr = match_against(
    dialect,
    columns=['title', 'content'],
    search_string='MySQL',
    mode='NATURAL_LANGUAGE',
)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'title'),
        match_expr.as_('relevance'),
    ],
    from_=TableExpression(dialect, 'articles'),
    where=WhereClause(dialect, condition=match_expr > 0),
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
