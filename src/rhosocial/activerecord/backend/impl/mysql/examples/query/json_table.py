"""
MySQL JSON_TABLE - Convert JSON data to relational format (MySQL 8.0+).

Note: JSON_TABLE is a MySQL-specific feature that requires manual SQL modification
since JSONTableExpression integration with FROM clause is limited.
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

backend.execute("DROP TABLE IF EXISTS orders")

from rhosocial.activerecord.backend.expression import CreateTableExpression, InsertExpression, ValuesSource
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='orders',
    columns=[
        ColumnDefinition(
            'id',
            'INT',
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition('order_data', 'JSON'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='orders',
    columns=['order_data'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, '{"customer": "Alice", "items": [{"product": "Widget", "qty": 5, "price": 10.00}, {"product": "Gadget", "qty": 3, "price": 15.00}]}')],
            [Literal(dialect, '{"customer": "Bob", "items": [{"product": "Widget", "qty": 2, "price": 10.00}]}')],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.impl.mysql.expression.json_table import (
    JSONTableExpression,
    JSONTableColumn,
)

json_table = JSONTableExpression(
    dialect=dialect,
    json_doc='order_data',
    path='$.items[*]',
    columns=[
        JSONTableColumn(name='product', type='VARCHAR(100)', path='$.product'),
        JSONTableColumn(name='qty', type='INT', path='$.qty'),
        JSONTableColumn(name='price', type='DECIMAL(10,2)', path='$.price'),
    ],
    alias='items',
)

json_table_sql, json_table_params = json_table.to_sql()
print(f"JSON_TABLE SQL: {json_table_sql}")

raw_sql = f"SELECT o.id, items.product, items.qty, items.price FROM orders o, {json_table_sql}"

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# MySQL JSON_TABLE expression converted to raw SQL
# Note: JSONTableExpression cannot handle complex nested arrays properly, so use raw SQL
json_table_sql = """JSON_TABLE(order_data, '$.items[*]' COLUMNS (
    product VARCHAR(100) PATH '$.product',
    qty INT PATH '$.qty',
    price DECIMAL(10,2) PATH '$.price'
)) AS items"""

raw_sql = f"SELECT o.id, items.product, items.qty, items.price FROM orders o, {json_table_sql}"
print(f"JSON_TABLE SQL: {json_table_sql}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(raw_sql)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
