"""
MySQL JSON functions - JSON_EXTRACT, JSON_UNQUOTE.

This example demonstrates:
1. MySQL 5.7+ with native JSON data type (JSON_EXTRACT, etc.)
2. MySQL 5.6 - falls back to TEXT storage with string functions

Supported versions: MySQL 5.7+ (native JSON)
Unsupported versions: MySQL 5.6 (will produce database error - handled gracefully)
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

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

backend.execute("DROP TABLE IF EXISTS documents")

from rhosocial.activerecord.backend.expression import CreateTableExpression, InsertExpression, ValuesSource
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# MySQL 5.7+: Use JSON data type
# MySQL 5.6: Falls back to TEXT column
print("=== MySQL 5.7+ JSON example ===")
print("Attempting to create table with JSON column...")

try:
    create_table = CreateTableExpression(
        dialect=dialect,
        table_name='documents',
        columns=[
            ColumnDefinition(
                'id',
                'INT',
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
                ],
            ),
            ColumnDefinition('data', 'JSON'),
        ],
        if_not_exists=True,
    )
    sql, params = create_table.to_sql()
    backend.execute(sql, params)
    use_json = True
    print("SUCCESS: Created table with JSON column")
except Exception as e:
    use_json = False
    print(f"ERROR (MySQL 5.6): {e}")
    print("Falling back to TEXT column...")
    create_table = CreateTableExpression(
        dialect=dialect,
        table_name='documents',
        columns=[
            ColumnDefinition(
                'id',
                'INT',
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
                ],
            ),
            ColumnDefinition('data', 'TEXT'),
        ],
        if_not_exists=True,
    )
    sql, params = create_table.to_sql()
    backend.execute(sql, params)
    print("SUCCESS: Created table with TEXT column (fallback)")

insert = InsertExpression(
    dialect=dialect,
    into='documents',
    columns=['data'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, '{"name": "Alice", "age": 30, "tags": ["a", "b"]}')],
            [Literal(dialect, '{"name": "Bob", "age": 25, "tags": ["c"]}')],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# Query based on MySQL version
if use_json:
    from rhosocial.activerecord.backend.expression import (
        QueryExpression,
        TableExpression,
        Column,
    )
    from rhosocial.activerecord.backend.impl.mysql.functions.json import json_extract, json_unquote

    query = QueryExpression(
        dialect=dialect,
        select=[
            Column(dialect, 'id'),
            json_unquote(dialect, json_extract(dialect, Column(dialect, 'data'), '$.name')).as_('name'),
            json_extract(dialect, Column(dialect, 'data'), '$.age').as_('age'),
        ],
        from_=TableExpression(dialect, 'documents'),
    )
    sql, params = query.to_sql()
    print("Using JSON_EXTRACT functions")
else:
    # MySQL 5.6 fallback - just select the TEXT column
    # String parsing is error-prone, so we just demonstrate the column
    sql = "SELECT id, data FROM documents"
    params = ()
    print("Using direct TEXT column (MySQL 5.6 fallback - no JSON parsing)")

print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

backend.disconnect()