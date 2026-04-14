"""
Create an index on an existing table.
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
    table_name='products',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'name', 'VARCHAR(100)'),
        ColumnDefinition(dialect, 'category', 'VARCHAR(50)'),
        ColumnDefinition(dialect, 'price', 'DECIMAL(10,2)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexExpression

create_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_category_price',
    table_name='products',
    columns=['category', 'price'],
)

sql, params = create_idx.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
backend.execute(sql, params)
print("Index created successfully")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute("SHOW INDEX FROM products WHERE Key_name = 'idx_category_price'", options=options)
print(f"Index info: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
