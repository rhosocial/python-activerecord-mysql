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

# Create table with TEXT column instead of JSON (MySQL 5.6)
backend.execute("""
    CREATE TABLE documents (
        id INT PRIMARY KEY AUTO_INCREMENT,
        data TEXT NOT NULL
    )
""")

backend.execute("""
    INSERT INTO documents (data) VALUES 
    ('{"name": "Alice", "age": 30}'),
    ('{"name": "Bob", "age": 25}')
""")

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