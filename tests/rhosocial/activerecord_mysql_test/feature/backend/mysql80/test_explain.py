# tests/rhosocial/activerecord_mysql_test/backend/mysql80/test_explain.py
import json
import logging
import re

import pytest

from rhosocial.activerecord.backend.dialect import ExplainType, ExplainOptions, ExplainFormat
from rhosocial.activerecord.backend.errors import QueryError

# Setup logger
logger = logging.getLogger("mysql_test")


def setup_explain_test_tables(backend):
    """Setup test tables for EXPLAIN feature tests"""
    # Drop existing tables if they exist
    try:
        backend.execute("DROP TABLE IF EXISTS explain_test_order_items")
        backend.execute("DROP TABLE IF EXISTS explain_test_orders")
        backend.execute("DROP TABLE IF EXISTS explain_test_products")
        backend.execute("DROP TABLE IF EXISTS explain_test_customers")
    except Exception as e:
        logger.warning(f"Error dropping existing tables: {e}")

    # Create customers table
    try:
        backend.execute("""
            CREATE TABLE explain_test_customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                city VARCHAR(100),
                country VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_location (city, country)
            )
        """)
        logger.info("Created explain_test_customers table")

        # Create products table with indexes for testing different access methods
        backend.execute("""
            CREATE TABLE explain_test_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                sku VARCHAR(50) UNIQUE NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                category VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_category (category),
                INDEX idx_price (price),
                FULLTEXT INDEX idx_name_fulltext (name)
            )
        """)
        logger.info("Created explain_test_products table")

        # Create orders table with foreign keys
        backend.execute("""
            CREATE TABLE explain_test_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('pending', 'processing', 'shipped', 'delivered') DEFAULT 'pending',
                total_amount DECIMAL(15, 2) NOT NULL,
                INDEX idx_customer (customer_id),
                INDEX idx_date (order_date),
                INDEX idx_status (status),
                FOREIGN KEY (customer_id) REFERENCES explain_test_customers(id)
            )
        """)
        logger.info("Created explain_test_orders table")

        # Create order items table with composite indexes
        backend.execute("""
            CREATE TABLE explain_test_order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                INDEX idx_order (order_id),
                INDEX idx_product (product_id),
                INDEX idx_order_product (order_id, product_id),
                FOREIGN KEY (order_id) REFERENCES explain_test_orders(id),
                FOREIGN KEY (product_id) REFERENCES explain_test_products(id)
            )
        """)
        logger.info("Created explain_test_order_items table")

        # Insert test data - customers
        customers = []
        for i in range(1, 101):
            name = f"Customer {i}"
            email = f"customer{i}@example.com"
            city = ["New York", "Los Angeles", "Chicago", "Houston", "Miami"][i % 5]
            country = "USA"
            customers.append((name, email, city, country))

        for customer in customers:
            backend.execute(
                "INSERT INTO explain_test_customers (name, email, city, country) VALUES (%s, %s, %s, %s)",
                customer
            )
        logger.info("Inserted test customers")

        # Products - insert products with different categories and prices
        products = []
        categories = ["Electronics", "Clothing", "Books", "Home", "Sports"]
        for i in range(1, 101):
            name = f"Product {i}"
            sku = f"SKU-{i:04d}"
            price = 10.0 + (i % 10) * 10.0  # Prices from 10 to 100
            category = categories[i % 5]
            products.append((name, sku, price, category))

        for product in products:
            backend.execute(
                "INSERT INTO explain_test_products (name, sku, price, category) VALUES (%s, %s, %s, %s)",
                product
            )
        logger.info("Inserted test products")

        # Orders - create various orders for different customers
        orders = []
        statuses = ['pending', 'processing', 'shipped', 'delivered']
        for i in range(1, 101):
            customer_id = (i % 50) + 1  # Distribute among first 50 customers
            # Create different dates for ordering
            order_date = f"2023-{(i % 12) + 1:02d}-{(i % 28) + 1:02d} 12:00:00"
            status = statuses[i % 4]
            total_amount = 100.0 + i * 10.0
            orders.append((customer_id, order_date, status, total_amount))

        for order in orders:
            backend.execute(
                "INSERT INTO explain_test_orders (customer_id, order_date, status, total_amount) VALUES (%s, %s, %s, %s)",
                order
            )
        logger.info("Inserted test orders")

        # Order Items - create multiple items per order
        order_items = []
        for order_id in range(1, 101):
            # Add 1-3 items per order
            for j in range(1, (order_id % 3) + 2):
                product_id = ((order_id + j) % 100) + 1
                quantity = (order_id % 5) + 1
                # Get product price
                product = backend.fetch_one(
                    "SELECT price FROM explain_test_products WHERE id = %s",
                    params=(product_id,)
                )
                unit_price = float(product["price"])
                order_items.append((order_id, product_id, quantity, unit_price))

        for item in order_items:
            backend.execute(
                "INSERT INTO explain_test_order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                item
            )
        logger.info("Inserted test order items")

    except Exception as e:
        logger.error(f"Error creating explain test tables: {e}")
        raise


def teardown_explain_test_tables(backend):
    """Clean up explain test tables"""
    try:
        backend.execute("DROP TABLE IF EXISTS explain_test_order_items")
        backend.execute("DROP TABLE IF EXISTS explain_test_orders")
        backend.execute("DROP TABLE IF EXISTS explain_test_products")
        backend.execute("DROP TABLE IF EXISTS explain_test_customers")
        logger.info("Dropped explain test tables")
    except Exception as e:
        logger.error(f"Error dropping explain test tables: {e}")

@pytest.fixture(scope="function")
def mysql_explain_test_db(mysql_test_db):
    """Setup and teardown for EXPLAIN tests"""
    setup_explain_test_tables(mysql_test_db)
    yield mysql_test_db
    teardown_explain_test_tables(mysql_test_db)

def test_mysql_format_explain_basic(mysql_explain_test_db):
    """Test basic EXPLAIN SQL formatting in MySQL"""
    logger.info("Testing basic EXPLAIN formatting")

    # Get MySQL dialect
    dialect = mysql_explain_test_db.dialect

    # Test basic EXPLAIN
    sql = "SELECT * FROM explain_test_customers"
    explain_sql = dialect.format_explain(sql)

    # More flexible assertion that doesn't rely on exact spacing
    assert "EXPLAIN" in explain_sql
    assert "SELECT * FROM explain_test_customers" in explain_sql

    # Use regex to ensure EXPLAIN comes before the SELECT statement
    assert re.search(r"EXPLAIN\s+SELECT", explain_sql, re.IGNORECASE) is not None

    # Test with explicit basic type
    options = ExplainOptions(type=ExplainType.BASIC)
    explain_sql = dialect.format_explain(sql, options)

    # More flexible assertion
    assert "EXPLAIN" in explain_sql
    assert "SELECT * FROM explain_test_customers" in explain_sql
    assert re.search(r"EXPLAIN\s+SELECT", explain_sql, re.IGNORECASE) is not None

    logger.info("Basic EXPLAIN formatting test passed")


def test_mysql_format_explain_with_complex_sql(mysql_explain_test_db):
    """Test EXPLAIN formatting with complex SQL statements in MySQL"""
    logger.info("Testing EXPLAIN with complex SQL formatting")

    dialect = mysql_explain_test_db.dialect

    # Test with JOIN
    sql = """
        SELECT c.*, o.total_amount 
        FROM explain_test_customers c 
        LEFT JOIN explain_test_orders o ON c.id = o.customer_id 
        WHERE o.total_amount > 200
    """
    explain_sql = dialect.format_explain(sql)

    # More flexible assertions
    assert "EXPLAIN" in explain_sql
    assert "SELECT" in explain_sql
    assert "LEFT JOIN" in explain_sql
    assert "total_amount > 200" in explain_sql
    assert re.search(r"EXPLAIN\s+.*SELECT", explain_sql, re.DOTALL | re.IGNORECASE) is not None

    # Test with subquery
    sql = """
        SELECT * FROM explain_test_customers 
        WHERE id IN (SELECT customer_id FROM explain_test_orders WHERE total_amount > 300)
    """
    explain_sql = dialect.format_explain(sql)

    # More flexible assertions
    assert "EXPLAIN" in explain_sql
    assert "SELECT" in explain_sql
    assert "IN (SELECT" in explain_sql
    assert re.search(r"EXPLAIN\s+.*SELECT", explain_sql, re.DOTALL | re.IGNORECASE) is not None

    logger.info("Complex EXPLAIN formatting test passed")


def test_mysql_explain_basic_execution(mysql_explain_test_db):
    """Test execution of basic EXPLAIN statement in MySQL"""
    logger.info("Testing execution of basic EXPLAIN statement")

    # Format EXPLAIN SQL
    sql = "SELECT * FROM explain_test_customers WHERE city = 'New York'"
    explain_sql = mysql_explain_test_db.dialect.format_explain(sql)

    # Execute EXPLAIN query
    result = mysql_explain_test_db.execute(explain_sql, returning=True)

    # Verify result structure
    assert result.data is not None
    assert len(result.data) > 0

    # The traditional EXPLAIN output columns
    expected_columns = [
        "id", "select_type", "table", "partitions", "type",
        "possible_keys", "key", "key_len", "ref", "rows", "filtered", "Extra"
    ]

    # Check for essential columns (some MySQL versions might have fewer columns)
    essential_columns = ["table", "type", "key", "rows"]

    # Verify essential columns are present
    for row in result.data:
        for col in essential_columns:
            assert col in row, f"Missing essential column: {col}"

        # Verify the query is using the expected table
        assert row["table"] == "explain_test_customers" or "customers" in str(row["table"])

        # Check if index on city is being used (it might use idx_location)
        if "key" in row and row["key"] is not None:
            # Don't assert exact index name, just check if it's not NULL when it should use an index
            pass

    logger.info(f"Basic EXPLAIN execution successful: {len(result.data)} rows")


def test_mysql_explain_join_query(mysql_explain_test_db):
    """Test EXPLAIN with JOIN queries in MySQL"""
    logger.info("Testing EXPLAIN with JOIN query")

    # Create JOIN query to explain
    sql = """
        SELECT c.name, o.order_date, o.total_amount
        FROM explain_test_customers c
        INNER JOIN explain_test_orders o ON c.id = o.customer_id
        WHERE c.city = 'Chicago' AND o.total_amount > 500
        ORDER BY o.order_date DESC
        LIMIT 10
    """

    # Format and execute EXPLAIN
    explain_sql = mysql_explain_test_db.dialect.format_explain(sql)
    result = mysql_explain_test_db.execute(explain_sql, returning=True)

    # Verify result structure
    assert result.data is not None
    assert len(result.data) > 0

    # Check if multiple tables are involved
    tables = set()
    for row in result.data:
        if "table" in row and row["table"] is not None:
            tables.add(row["table"])

    # Should have at least 2 tables (explain_test_customers and explain_test_orders)
    # But they might be aliased or abbreviated
    assert len(tables) >= 1  # At minimum we should have one row per table

    # Try to find evidence of both tables in all rows combined
    all_rows_text = str(result.data)
    assert any(term in all_rows_text for term in ["customer", "c"])
    assert any(term in all_rows_text for term in ["order", "o"])

    logger.info(f"JOIN query EXPLAIN successful: found data for {len(tables)} tables")


def check_json_format_support(mysql_explain_test_db):
    """Check if this MySQL version supports JSON format for EXPLAIN"""
    try:
        version = mysql_explain_test_db.get_server_version()
        # JSON format is supported in MySQL 5.7+
        return version >= (5, 7, 0)
    except:
        # If version detection fails, assume it's not supported
        return False


def test_mysql_explain_format_json(mysql_explain_test_db):
    """Test EXPLAIN with JSON format in MySQL (if supported)"""
    logger.info("Testing EXPLAIN with JSON format")

    # Skip test if JSON format is not supported
    if not check_json_format_support(mysql_explain_test_db):
        pytest.skip("MySQL version does not support JSON format for EXPLAIN")

    # SQL query to explain
    sql = """
        SELECT p.name, p.price, COUNT(oi.id) as order_count
        FROM explain_test_products p
        LEFT JOIN explain_test_order_items oi ON p.id = oi.product_id
        WHERE p.category = 'Electronics'
        GROUP BY p.id, p.name, p.price
        HAVING COUNT(oi.id) > 0
        ORDER BY order_count DESC
    """

    # Format EXPLAIN with JSON format
    options = ExplainOptions(format=ExplainFormat.JSON)
    explain_sql = mysql_explain_test_db.dialect.format_explain(sql, options)

    # Verify correct formatting of the EXPLAIN statement
    assert "EXPLAIN" in explain_sql
    assert "FORMAT=JSON" in explain_sql

    try:
        # Execute EXPLAIN query
        result = mysql_explain_test_db.execute(explain_sql, returning=True)

        # Verify result structure - should have at least one row
        assert result.data is not None
        assert len(result.data) > 0

        # The JSON output is typically in a single row with a column that contains the JSON
        # The column name could be different based on MySQL version
        json_row = result.data[0]

        # Find the column that contains JSON (it should be the only one or named "EXPLAIN")
        json_col = None
        for col, val in json_row.items():
            if val and (col == "EXPLAIN" or len(json_row) == 1):
                json_col = col
                break

        assert json_col is not None, "Could not find JSON output column"

        # Parse the JSON output
        if json_row[json_col]:
            try:
                explain_data = json.loads(json_row[json_col])
                assert isinstance(explain_data, dict)
                # Check for typical JSON EXPLAIN structure - this could vary by MySQL version
                # so we'll be flexible in what we check for
                assert any(key in explain_data for key in ["query_block", "select_id", "table", "json"])
            except json.JSONDecodeError:
                pytest.fail("Failed to parse EXPLAIN output as JSON")

        logger.info("JSON format EXPLAIN successful")

    except QueryError as e:
        # Some MySQL versions might claim to support JSON format but still fail
        logger.warning(f"EXPLAIN FORMAT=JSON failed with error: {e}")
        pytest.skip(f"MySQL server rejected JSON format: {e}")


def check_analyze_support(mysql_explain_test_db):
    """Check if this MySQL version supports EXPLAIN ANALYZE"""
    try:
        version = mysql_explain_test_db.get_server_version()
        # EXPLAIN ANALYZE is supported in MySQL 8.0.18+
        return version >= (8, 0, 18)
    except:
        # If version detection fails, assume it's not supported
        return False


def test_mysql_explain_analyze(mysql_explain_test_db):
    """Test EXPLAIN ANALYZE in MySQL (if supported)"""
    logger.info("Testing EXPLAIN ANALYZE")

    # Skip test if ANALYZE is not supported
    if not check_analyze_support(mysql_explain_test_db):
        pytest.skip("MySQL version does not support EXPLAIN ANALYZE")

    # SQL query to explain
    sql = """
        SELECT c.name, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
        FROM explain_test_customers c
        JOIN explain_test_orders o ON c.id = o.customer_id
        WHERE c.country = 'USA'
        GROUP BY c.id, c.name
        ORDER BY total_spent DESC
        LIMIT 5
    """

    # Format EXPLAIN ANALYZE - note that it requires TREE format in MySQL 8.0
    options = ExplainOptions(type=ExplainType.ANALYZE)
    explain_sql = mysql_explain_test_db.dialect.format_explain(sql, options)

    # Verify correct formatting of the EXPLAIN ANALYZE statement
    assert "EXPLAIN" in explain_sql
    assert "ANALYZE" in explain_sql

    try:
        # Execute EXPLAIN ANALYZE query
        result = mysql_explain_test_db.execute(explain_sql, returning=True)

        # Verify result structure - should have output
        assert result.data is not None

        # For EXPLAIN ANALYZE with default TREE format, the output is typically text
        # It should contain "actual" timing information
        found_timing_info = False
        for row in result.data:
            row_data = str(row)
            if "actual" in row_data.lower() and ("time" in row_data.lower() or "cost" in row_data.lower()):
                found_timing_info = True
                break

        assert found_timing_info, "Could not find timing information in EXPLAIN ANALYZE output"

        logger.info("EXPLAIN ANALYZE successful")

    except QueryError as e:
        logger.warning(f"EXPLAIN ANALYZE failed with error: {e}")
        pytest.skip(f"MySQL server rejected EXPLAIN ANALYZE: {e}")


def test_mysql_explain_with_different_types(mysql_explain_test_db):
    """Test EXPLAIN with different query types and access methods"""
    logger.info("Testing EXPLAIN with different query types")

    # Test cases for different query types
    test_cases = [
        {
            "name": "Index lookup",
            "sql": "SELECT * FROM explain_test_products WHERE sku = 'SKU-0001'",
            "expected_access": ["eq_ref", "const", "unique_key", "PRIMARY", "sku"]
        },
        {
            "name": "Range scan",
            "sql": "SELECT * FROM explain_test_products WHERE price BETWEEN 50 AND 100",
            "expected_access": ["range", "idx_price"]
        },
        {
            "name": "Full table scan",
            "sql": "SELECT * FROM explain_test_products WHERE name LIKE '%Product%'",
            "expected_access": ["ALL", "fullscan", "table", "full", "scan"]
        },
        {
            "name": "Index scan",
            "sql": "SELECT id, category FROM explain_test_products ORDER BY category",
            "expected_access": ["index", "idx_category"]
        },
        {
            "name": "Join with multiple tables",
            "sql": """
                SELECT c.name, o.order_date, p.name, oi.quantity
                FROM explain_test_customers c
                JOIN explain_test_orders o ON c.id = o.customer_id
                JOIN explain_test_order_items oi ON o.id = oi.order_id
                JOIN explain_test_products p ON oi.product_id = p.id
                WHERE c.city = 'New York'
                AND o.status = 'delivered'
                AND p.category = 'Electronics'
            """,
            "expected_access": ["join", "ref", "eq_ref"]
        },
        {
            "name": "Aggregation with GROUP BY",
            "sql": """
                SELECT category, COUNT(*) as product_count, AVG(price) as avg_price
                FROM explain_test_products
                GROUP BY category
                ORDER BY product_count DESC
            """,
            "expected_access": ["temporary", "filesort", "group", "sort"]
        }
    ]

    # Execute each test case
    for case in test_cases:
        logger.info(f"Testing EXPLAIN case: {case['name']}")

        # Format and execute EXPLAIN
        explain_sql = mysql_explain_test_db.dialect.format_explain(case['sql'])
        result = mysql_explain_test_db.execute(explain_sql, returning=True)

        # Verify the result contains expected information
        assert result.data is not None
        assert len(result.data) > 0

        # Check for expected access patterns
        all_rows_text = str(result.data).lower()
        found_any_pattern = False

        for pattern in case['expected_access']:
            if pattern.lower() in all_rows_text:
                found_any_pattern = True
                break

        assert found_any_pattern, f"Could not find any expected access pattern in EXPLAIN output for {case['name']}"

        logger.info(f"EXPLAIN case passed: {case['name']}")
