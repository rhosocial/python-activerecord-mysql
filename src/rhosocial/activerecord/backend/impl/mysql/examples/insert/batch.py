"""
Batch insert with multiple rows.
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
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='logs',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'level', 'VARCHAR(20)'),
        ColumnDefinition(dialect, 'message', 'TEXT'),
        ColumnDefinition(dialect, 'created_at', 'TIMESTAMP', default='CURRENT_TIMESTAMP'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal

insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'logs'),
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'INFO'), Literal(dialect, 'System started')],
            [Literal(dialect, 'DEBUG'), Literal(dialect, 'Loading configuration')],
            [Literal(dialect, 'INFO'), Literal(dialect, 'Application ready')],
            [Literal(dialect, 'WARNING'), Literal(dialect, 'Memory usage high')],
        ],
    ),
    columns=['level', 'message'],
    dialect_options={},
)

sql, params = insert_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute("SELECT * FROM logs ORDER BY id", options=options)
print(f"Total rows in table: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
