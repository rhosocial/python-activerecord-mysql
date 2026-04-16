"""
Common Table Expressions (CTE) - MySQL 8.0+.

This example demonstrates:
1. Basic CTE with WITH clause
2. Recursive CTE for hierarchical data
3. CTE for simplifying complex queries
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
)
backend = MySQLBackend(connection_config=config)
backend.connect()

# Create tables for testing
backend.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        manager_id INT NULL
    )
""")
backend.execute("DELETE FROM employees")
backend.execute("""
    INSERT INTO employees (id, name, manager_id) VALUES
    (1, 'CEO', NULL),
    (2, 'VP Sales', 1),
    (3, 'VP Engineering', 1),
    (4, 'Sales Manager', 2),
    (5, 'Engineer', 3)
""")

# ============================================================
# SECTION: Basic CTE
# ============================================================
# CTE simplifies complex queries by defining temporary named result sets

result = backend.execute("""
    WITH high_earners AS (
        SELECT id, name FROM employees WHERE id > 2
    )
    SELECT * FROM high_earners
""")
print(f"Basic CTE result: {result.data}")

# ============================================================
# SECTION: Recursive CTE
# ============================================================
# Recursive CTE for hierarchical data (organizational chart)

result = backend.execute("""
    WITH RECURSIVE org_chart AS (
        -- Base case: top-level employees
        SELECT id, name, manager_id, 1 AS level
        FROM employees
        WHERE manager_id IS NULL

        UNION ALL

        -- Recursive case: employees with a manager
        SELECT e.id, e.name, e.manager_id, oc.level + 1
        FROM employees e
        INNER JOIN org_chart oc ON e.manager_id = oc.id
    )
    SELECT * FROM org_chart ORDER BY level, name
""")
print(f"Recursive CTE result:")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Multiple CTEs
# ============================================================
# Multiple CTEs can be defined in a single WITH clause

result = backend.execute("""
    WITH
        active_employees AS (
            SELECT id, name FROM employees WHERE id > 0
        ),
        top_employees AS (
            SELECT * FROM active_employees WHERE id > 2
        )
    SELECT te.* FROM top_employees te
    JOIN active_employees ae ON te.id = ae.id
""")
print(f"Multiple CTEs result: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.execute("DROP TABLE IF EXISTS employees")
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. CTE requires MySQL 8.0+
# 2. Use WITH clause to define CTEs
# 3. RECURSIVE keyword needed for hierarchical queries
# 4. Multiple CTEs can be defined in single WITH clause
# 5. CTE improves readability vs subqueries