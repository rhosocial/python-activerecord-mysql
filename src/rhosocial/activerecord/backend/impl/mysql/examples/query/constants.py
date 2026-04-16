"""
Query runtime functions and statement-level constants without a data source.

This example demonstrates:
1. SELECT CURRENT_TIMESTAMP, NOW(), etc. without FROM clause
2. How to use FunctionCall for SQL functions in SELECT list
3. Various MySQL date/time functions as standalone queries
4. Expression API for constant expressions
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

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

# ============================================================
# SECTION: SELECT CURRENT_TIMESTAMP
# ============================================================
# Use FunctionCall for SQL statement-level constants.
# FunctionCall(dialect, 'CURRENT_TIMESTAMP') generates CURRENT_TIMESTAMP()
# which is valid in MySQL for both DDL DEFAULT and SELECT contexts.

from rhosocial.activerecord.backend.expression import QueryExpression
from rhosocial.activerecord.backend.expression.core import FunctionCall

query_ts = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'CURRENT_TIMESTAMP')],
)
sql, params = query_ts.to_sql()
print(f"CURRENT_TIMESTAMP SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: SELECT NOW()
# ============================================================
query_now = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'NOW')],
)
sql, params = query_now.to_sql()
print(f"NOW() SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: SELECT CURRENT_DATE, CURRENT_TIME
# ============================================================
query_date = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'CURRENT_DATE'),
        FunctionCall(dialect, 'CURRENT_TIME'),
    ],
)
sql, params = query_date.to_sql()
print(f"CURRENT_DATE/CURRENT_TIME SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: SELECT with multiple functions
# ============================================================
from rhosocial.activerecord.backend.expression.core import Literal

query_multi = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'NOW').as_('current_time'),
        FunctionCall(dialect, 'CURRENT_DATE').as_('current_date'),
        FunctionCall(dialect, 'DATABASE').as_('db_name'),
        FunctionCall(dialect, 'VERSION').as_('db_version'),
    ],
)
sql, params = query_multi.to_sql()
print(f"Multi-function SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: SELECT with function arguments
# ============================================================
# FunctionCall supports arguments, e.g., DATE_FORMAT, ROUND

query_format = QueryExpression(
    dialect=dialect,
    select=[
        FunctionCall(dialect, 'DATE_FORMAT', FunctionCall(dialect, 'NOW'), Literal(dialect, '%Y-%m-%d')).as_('formatted_date'),
    ],
)
sql, params = query_format.to_sql()
print(f"DATE_FORMAT SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: SELECT with UUID() (MySQL 8.0+)
# ============================================================
query_uuid = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'UUID').as_('uuid_value')],
)
sql, params = query_uuid.to_sql()
print(f"UUID() SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use FunctionCall(dialect, 'FUNCTION_NAME') for SQL functions and constants
# 2. QueryExpression without from_ clause generates "SELECT ..." without FROM
# 3. FunctionCall supports arguments: FunctionCall(dialect, 'FUNC', arg1, arg2)
# 4. Use .as_('alias') for column aliases in SELECT
# 5. Common MySQL constants: CURRENT_TIMESTAMP, NOW, CURRENT_DATE, CURRENT_TIME
# 6. Common MySQL info functions: DATABASE, VERSION, USER, UUID
