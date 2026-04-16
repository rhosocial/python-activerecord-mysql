"""
MySQL JSON operations using TEXT storage.

Note: MySQL 5.6 does not support JSON data type.
Use TEXT column and parse with string functions.

Supported versions: MySQL 5.6
Unsupported versions: MySQL 5.7+ (use json_basic.py instead)
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

config = MySQLConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USERNAME', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    charset='utf8mb4',
)
backend = MySQLBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    DropTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

drop_table = DropTableExpression(dialect=dialect, table_name='documents', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

from rhosocial.activerecord.backend.expression import CreateTableExpression
create_table = CreateTableExpression(
    dialect=dialect,
    table_name='documents',
    columns=[
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ], autoincrement=True),
        ColumnDefinition('data', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
    ],
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert_expr = InsertExpression(
    dialect=dialect,
    table_name='documents',
    columns=['data'],
    source=ValuesSource(dialect, [
        [Literal(dialect, '{"name": "Alice", "age": 30}')],
        [Literal(dialect, '{"name": "Bob", "age": 25}')],
    ]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# MySQL 5.6: Use TEXT column directly
# JSON parsing with string functions is error-prone, so we just show the raw data
sql = "SELECT id, data FROM documents"
params = ()

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