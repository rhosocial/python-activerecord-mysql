"""
Alter table statements - ADD COLUMN, MODIFY COLUMN.

Note: MySQL supports multiple actions in a single ALTER TABLE statement,
but for simplicity we demonstrate individual operations.
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
    table_name='users',
    columns=[
        ColumnDefinition(dialect, 'id', 'INT', primary_key=True, auto_increment=True),
        ColumnDefinition(dialect, 'name', 'VARCHAR(100)'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    table_name='users',
    columns=['name'],
    values=[[Literal(dialect, 'Alice')]],
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    AlterTableExpression,
    RawExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddColumn

add_col_action = AddColumn(
    column=ColumnDefinition(
        name='email',
        data_type='VARCHAR(100)',
    ),
)

add_col_expr = AlterTableExpression(
    dialect=dialect,
    table_name='users',
    actions=[add_col_action],
)

sql, params = add_col_expr.to_sql()
print(f"SQL (Add Column email): {sql}")
print(f"Params: {params}")

backend.execute(sql, params)
print("Column email added successfully")

add_age_action = AddColumn(
    column=ColumnDefinition(
        name='age',
        data_type='INT',
        default=Literal(dialect, 0),
    ),
)

add_age_expr = AlterTableExpression(
    dialect=dialect,
    table_name='users',
    actions=[add_age_action],
)

sql, params = add_age_expr.to_sql()
print(f"SQL (Add Column age): {sql}")
print(f"Params: {params}")

backend.execute(sql, params)
print("Column age added successfully")

modify_expr = RawExpression("ALTER TABLE users MODIFY COLUMN name VARCHAR(200) NOT NULL")
sql, params = modify_expr.to_sql()
print(f"SQL (Modify Column name): {sql}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
backend.execute(sql, params)
print("Column name modified successfully")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute("DESCRIBE users", options=options)
print(f"Table structure after alterations:")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
