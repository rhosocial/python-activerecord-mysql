# tests/rhosocial/activerecord_mysql_test/backend/mysql80/test_expression.py
import datetime
import logging

import pytest

from rhosocial.activerecord.backend import DatabaseType

# Setup logger
logger = logging.getLogger("mysql_test")


def setup_expression_tables(backend):
    """Setup test tables for SQL expression tests"""
    # Drop existing tables if they exist
    try:
        backend.execute("DROP TABLE IF EXISTS expression_test_order_items")
        backend.execute("DROP TABLE IF EXISTS expression_test_orders")
        backend.execute("DROP TABLE IF EXISTS expression_test_products")
        backend.execute("DROP TABLE IF EXISTS expression_test_customers")
    except Exception as e:
        logger.warning(f"Error dropping existing tables: {e}")

    # Create customers table
    try:
        backend.execute("""
            CREATE TABLE expression_test_customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                status ENUM('active', 'inactive', 'pending') DEFAULT 'active',
                join_date DATE NOT NULL,
                last_purchase_date DATE NULL,
                total_purchases DECIMAL(15, 2) DEFAULT 0.00,
                metadata JSON NULL
            )
        """)
        logger.info("Created expression_test_customers table")

        # Create products table
        backend.execute("""
            CREATE TABLE expression_test_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                sku VARCHAR(50) UNIQUE NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                cost DECIMAL(10, 2) NOT NULL,
                stock_quantity INT NOT NULL DEFAULT 0,
                category VARCHAR(50) NOT NULL,
                tags JSON NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created expression_test_products table")

        # Create orders table
        backend.execute("""
            CREATE TABLE expression_test_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                order_number VARCHAR(20) UNIQUE NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('pending', 'paid', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
                total_amount DECIMAL(15, 2) NOT NULL,
                shipping_address TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES expression_test_customers(id)
            )
        """)
        logger.info("Created expression_test_orders table")

        # Create order items table
        backend.execute("""
            CREATE TABLE expression_test_order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(15, 2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES expression_test_orders(id),
                FOREIGN KEY (product_id) REFERENCES expression_test_products(id)
            )
        """)
        logger.info("Created expression_test_order_items table")

        # Insert test data

        # Customers
        customers = [
            ("John Doe", "john@example.com", "active", "2023-01-15", "2023-12-10", 1250.50,
             '{"preferences": {"theme": "dark", "notifications": true}, "address": {"city": "New York", "country": "USA"}}'),
            ("Jane Smith", "jane@example.com", "active", "2023-02-20", "2023-11-28", 890.75,
             '{"preferences": {"theme": "light", "notifications": false}, "address": {"city": "Los Angeles", "country": "USA"}}'),
            ("Robert Johnson", "robert@example.com", "inactive", "2023-03-05", "2023-07-15", 450.25,
             '{"preferences": {"theme": "light", "notifications": true}, "address": {"city": "Chicago", "country": "USA"}}'),
            ("Emily Davis", "emily@example.com", "active", "2023-04-10", None, 0.00,
             '{"preferences": {"theme": "auto", "notifications": true}, "address": {"city": "Miami", "country": "USA"}}'),
            ("Michael Brown", "michael@example.com", "pending", "2023-05-12", "2023-12-01", 325.80,
             '{"preferences": {"theme": "dark", "notifications": false}, "address": {"city": "Seattle", "country": "USA"}}')
        ]

        for customer in customers:
            backend.execute(
                "INSERT INTO expression_test_customers (name, email, status, join_date, last_purchase_date, total_purchases, metadata) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                customer
            )
        logger.info("Inserted test customers")

        # Products
        products = [
            ("Smartphone X", "PROD-001", 999.99, 750.00, 50, "Electronics",
             '["tech", "mobile", "5G"]'),
            ("Leather Wallet", "PROD-002", 49.99, 20.00, 200, "Accessories",
             '["fashion", "leather", "accessories"]'),
            ("Running Shoes", "PROD-003", 129.99, 60.00, 75, "Footwear",
             '["sports", "running", "shoes"]'),
            ("Coffee Maker", "PROD-004", 89.99, 45.00, 30, "Home Appliances",
             '["kitchen", "appliances", "coffee"]'),
            ("Bluetooth Headphones", "PROD-005", 79.99, 35.00, 100, "Electronics",
             '["audio", "wireless", "tech"]')
        ]

        for product in products:
            backend.execute(
                "INSERT INTO expression_test_products (name, sku, price, cost, stock_quantity, category, tags) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                product
            )
        logger.info("Inserted test products")

        # Orders
        orders = [
            (1, "ORD-2023-001", "2023-10-15 14:30:00", "delivered", 1049.98, "123 Main St, New York, NY 10001"),
            (2, "ORD-2023-002", "2023-11-20 09:15:00", "shipped", 129.99, "456 Oak Ave, Los Angeles, CA 90001"),
            (3, "ORD-2023-003", "2023-07-05 16:45:00", "cancelled", 89.99, "789 Pine St, Chicago, IL 60007"),
            (1, "ORD-2023-004", "2023-12-01 11:20:00", "paid", 179.98, "123 Main St, New York, NY 10001"),
            (4, "ORD-2023-005", "2023-11-30 13:10:00", "pending", 999.99, "321 Palm Dr, Miami, FL 33101")
        ]

        for order in orders:
            backend.execute(
                "INSERT INTO expression_test_orders (customer_id, order_number, order_date, status, total_amount, shipping_address) VALUES (%s, %s, %s, %s, %s, %s)",
                order
            )
        logger.info("Inserted test orders")

        # Order Items
        order_items = [
            (1, 1, 1, 999.99, 999.99),
            (1, 2, 1, 49.99, 49.99),
            (2, 3, 1, 129.99, 129.99),
            (3, 4, 1, 89.99, 89.99),
            (4, 1, 1, 49.99, 49.99),
            (4, 2, 1, 129.99, 129.99),
            (5, 1, 1, 999.99, 999.99)
        ]

        for item in order_items:
            backend.execute(
                "INSERT INTO expression_test_order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (%s, %s, %s, %s, %s)",
                item
            )
        logger.info("Inserted test order items")

    except Exception as e:
        logger.error(f"Error creating expression test tables: {e}")
        raise


def teardown_expression_tables(backend):
    """Clean up expression test tables"""
    try:
        backend.execute("DROP TABLE IF EXISTS expression_test_order_items")
        backend.execute("DROP TABLE IF EXISTS expression_test_orders")
        backend.execute("DROP TABLE IF EXISTS expression_test_products")
        backend.execute("DROP TABLE IF EXISTS expression_test_customers")
        logger.info("Dropped expression test tables")
    except Exception as e:
        logger.error(f"Error dropping expression test tables: {e}")


@pytest.fixture(scope="function")
def mysql_expression_test_db(mysql_test_db):
    """Setup and teardown for expression tests"""
    setup_expression_tables(mysql_test_db)
    yield mysql_test_db
    teardown_expression_tables(mysql_test_db)


def test_expression_select_with_calculated_field(mysql_expression_test_db):
    """Test SELECT with calculated fields using SQL expressions"""
    logger.info("Starting SELECT with calculated fields test")

    # Create SQL expressions for calculated fields
    profit_expr = mysql_expression_test_db.create_expression("(price - cost) * stock_quantity")
    profit_margin_expr = mysql_expression_test_db.create_expression("(price - cost) / price * 100")

    # Query with expressions
    result = mysql_expression_test_db.execute(
        """
        SELECT 
            id, name, price, cost, stock_quantity, 
            %s AS total_profit,
            %s AS profit_margin
        FROM expression_test_products
        ORDER BY total_profit DESC
        """,
        params=(profit_expr, profit_margin_expr),
        returning=True
    )

    # Verify result
    assert result.data is not None
    assert len(result.data) == 5

    # Verify calculated fields
    for product in result.data:
        price = float(product["price"])
        cost = float(product["cost"])
        quantity = int(product["stock_quantity"])

        # Calculate expected values
        expected_profit = (price - cost) * quantity
        expected_margin = (price - cost) / price * 100

        # Compare with actual values (using approximate comparison for floating point)
        assert abs(float(product["total_profit"]) - expected_profit) < 0.01
        assert abs(float(product["profit_margin"]) - expected_margin) < 0.01

    logger.info(f"Successfully verified calculations for {len(result.data)} products")


def test_expression_where_condition(mysql_expression_test_db):
    """Test WHERE conditions using expressions"""
    logger.info("Starting WHERE with expressions test")

    # Create expression for high-margin products (margin > 50%)
    margin_expr = mysql_expression_test_db.create_expression("(price - cost) / price * 100 > 50")

    # Query using expression in WHERE clause
    result = mysql_expression_test_db.execute(
        "SELECT id, name, price, cost FROM expression_test_products WHERE %s",
        params=(margin_expr,),
        returning=True
    )

    # Verify that all returned products have margin > 50%
    for product in result.data:
        price = float(product["price"])
        cost = float(product["cost"])
        margin = (price - cost) / price * 100
        assert margin > 50

    logger.info(f"Found {len(result.data)} high-margin products")

    # Another test with more complex expression
    stock_value_expr = mysql_expression_test_db.create_expression("price * stock_quantity > 5000")

    result = mysql_expression_test_db.execute(
        "SELECT id, name, price, stock_quantity FROM expression_test_products WHERE %s",
        params=(stock_value_expr,),
        returning=True
    )

    # Verify products with stock value > 5000
    for product in result.data:
        price = float(product["price"])
        quantity = int(product["stock_quantity"])
        stock_value = price * quantity
        assert stock_value > 5000

    logger.info(f"Found {len(result.data)} products with high stock value")


def test_expression_update_with_expression(mysql_expression_test_db):
    """Test UPDATE using expressions"""
    logger.info("Starting UPDATE with expressions test")

    # Get initial stock quantities
    initial_stocks = mysql_expression_test_db.fetch_all(
        "SELECT id, stock_quantity FROM expression_test_products",
        column_types={"stock_quantity": DatabaseType.INTEGER}
    )
    initial_stock_map = {item["id"]: item["stock_quantity"] for item in initial_stocks}

    # Create expression to increase stock by 10%
    increase_expr = mysql_expression_test_db.create_expression("stock_quantity * 1.1")

    # Update using expression
    update_result = mysql_expression_test_db.execute(
        "UPDATE expression_test_products SET stock_quantity = %s WHERE category = 'Electronics'",
        params=(increase_expr,)
    )

    # Verify update worked
    assert update_result.affected_rows > 0
    logger.info(f"Updated {update_result.affected_rows} electronics products")

    # Get updated stock quantities
    updated_stocks = mysql_expression_test_db.fetch_all(
        "SELECT id, category, stock_quantity FROM expression_test_products",
        column_types={"stock_quantity": DatabaseType.INTEGER}
    )

    # Verify each product's stock quantity
    for product in updated_stocks:
        product_id = product["id"]
        if product["category"] == "Electronics":
            # Electronics should have increased by 10%
            expected_stock = int(initial_stock_map[product_id] * 1.1)
            assert product["stock_quantity"] == expected_stock
        else:
            # Other categories should remain unchanged
            assert product["stock_quantity"] == initial_stock_map[product_id]

    logger.info("Verified stock quantity updates")


def test_expression_insert_with_expression(mysql_expression_test_db):
    """Test INSERT using expressions"""
    logger.info("Starting INSERT with expressions test")

    # Get a product for reference
    product = mysql_expression_test_db.fetch_one(
        "SELECT price, cost FROM expression_test_products WHERE id = 1"
    )
    reference_price = float(product["price"])
    reference_cost = float(product["cost"])

    # Create expressions for new product
    price_expr = mysql_expression_test_db.create_expression(f"{reference_price} * 1.2")  # 20% higher price
    cost_expr = mysql_expression_test_db.create_expression(f"{reference_cost} * 1.15")  # 15% higher cost

    # Insert new product using expressions
    insert_result = mysql_expression_test_db.execute(
        """
        INSERT INTO expression_test_products 
        (name, sku, price, cost, stock_quantity, category, tags) 
        VALUES ('New Product', 'PROD-NEW', %s, %s, 20, 'Electronics', '["new", "test"]')
        """,
        params=(price_expr, cost_expr)
    )

    # Verify the insert worked
    assert insert_result.affected_rows == 1
    assert insert_result.last_insert_id > 0
    new_product_id = insert_result.last_insert_id
    logger.info(f"Inserted new product with ID: {new_product_id}")

    # Retrieve the new product
    new_product = mysql_expression_test_db.fetch_one(
        "SELECT price, cost FROM expression_test_products WHERE id = %s",
        params=(new_product_id,)
    )

    # Verify the values match our expressions
    expected_price = reference_price * 1.2
    expected_cost = reference_cost * 1.15

    assert abs(float(new_product["price"]) - expected_price) < 0.01
    assert abs(float(new_product["cost"]) - expected_cost) < 0.01

    logger.info("Verified new product has correct calculated values")


def test_expression_join_condition(mysql_expression_test_db):
    """Test JOIN conditions using expressions"""
    logger.info("Starting JOIN with expressions test")

    # Create expression for joining orders with their high-value items
    join_expr = mysql_expression_test_db.create_expression("o.id = oi.order_id AND oi.subtotal > 500")

    # Query using expression in JOIN condition
    result = mysql_expression_test_db.execute(
        """
        SELECT o.id as order_id, o.order_number, o.total_amount, 
               oi.id as item_id, oi.product_id, oi.subtotal
        FROM expression_test_orders o
        JOIN expression_test_order_items oi ON %s
        ORDER BY o.id, oi.id
        """,
        params=(join_expr,),
        returning=True
    )

    # Verify that all returned items have subtotal > 500
    for item in result.data:
        assert float(item["subtotal"]) > 500

    logger.info(f"Found {len(result.data)} high-value order items")


def test_expression_aggregate_functions(mysql_expression_test_db):
    """Test aggregate functions with expressions"""
    logger.info("Starting aggregate functions with expressions test")

    # Create expression for customer lifetime value calculation
    lifetime_value_expr = mysql_expression_test_db.create_expression("SUM(o.total_amount)")
    order_count_expr = mysql_expression_test_db.create_expression("COUNT(o.id)")
    avg_order_expr = mysql_expression_test_db.create_expression("AVG(o.total_amount)")

    # Query using expressions with aggregate functions
    result = mysql_expression_test_db.execute(
        """
        SELECT 
            c.id, c.name, c.email,
            %s AS lifetime_value,
            %s AS order_count,
            %s AS avg_order_value
        FROM expression_test_customers c
        LEFT JOIN expression_test_orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name, c.email
        HAVING %s > 0
        ORDER BY lifetime_value DESC
        """,
        params=(lifetime_value_expr, order_count_expr, avg_order_expr, order_count_expr),
        returning=True
    )

    # Verify results - should exclude customers with no orders
    assert result.data is not None

    # Check that all customers in result have at least one order
    for customer in result.data:
        assert int(customer["order_count"]) > 0

        # Verify calculated fields
        assert float(customer["lifetime_value"]) > 0
        assert float(customer["avg_order_value"]) > 0

        # Verify average order value is correct
        expected_avg = float(customer["lifetime_value"]) / int(customer["order_count"])
        assert abs(float(customer["avg_order_value"]) - expected_avg) < 0.01

    logger.info(f"Successfully verified aggregate calculations for {len(result.data)} customers")


def test_expression_case_statements(mysql_expression_test_db):
    """Test CASE statements using expressions"""
    logger.info("Starting CASE statements with expressions test")

    # Create expressions for categorizing products by price and stock
    price_category_expr = mysql_expression_test_db.create_expression("""
        CASE 
            WHEN price < 50 THEN 'Budget'
            WHEN price >= 50 AND price < 100 THEN 'Mid-range'
            WHEN price >= 100 AND price < 500 THEN 'Premium'
            ELSE 'Luxury'
        END
    """)

    stock_status_expr = mysql_expression_test_db.create_expression("""
        CASE 
            WHEN stock_quantity <= 30 THEN 'Low Stock'
            WHEN stock_quantity > 30 AND stock_quantity <= 100 THEN 'Medium Stock'
            ELSE 'High Stock'
        END
    """)

    # Query products with expressions for categorization
    result = mysql_expression_test_db.execute(
        """
        SELECT 
            id, name, price, stock_quantity,
            %s AS price_category,
            %s AS stock_status
        FROM expression_test_products
        ORDER BY price DESC
        """,
        params=(price_category_expr, stock_status_expr),
        returning=True
    )

    # Verify categorization
    for product in result.data:
        price = float(product["price"])
        stock = int(product["stock_quantity"])

        # Verify price category
        if price < 50:
            assert product["price_category"] == 'Budget'
        elif price >= 50 and price < 100:
            assert product["price_category"] == 'Mid-range'
        elif price >= 100 and price < 500:
            assert product["price_category"] == 'Premium'
        else:
            assert product["price_category"] == 'Luxury'

        # Verify stock status
        if stock <= 30:
            assert product["stock_status"] == 'Low Stock'
        elif stock > 30 and stock <= 100:
            assert product["stock_status"] == 'Medium Stock'
        else:
            assert product["stock_status"] == 'High Stock'

    logger.info(f"Successfully verified categorization for {len(result.data)} products")


def test_expression_subqueries(mysql_expression_test_db):
    """Test subqueries using expressions"""
    logger.info("Starting subqueries with expressions test")

    # Create expression for subquery filtering
    active_status_expr = mysql_expression_test_db.create_expression("status = 'active'")

    # Subquery to find customers with active status
    customers_subquery = mysql_expression_test_db.create_expression(f"""
        (SELECT id FROM expression_test_customers WHERE {active_status_expr.expression})
    """)

    # Query orders from active customers using expression with subquery
    result = mysql_expression_test_db.execute(
        """
        SELECT 
            o.id, o.order_number, o.total_amount,
            c.name as customer_name, c.status
        FROM expression_test_orders o
        JOIN expression_test_customers c ON o.customer_id = c.id
        WHERE o.customer_id IN %s
        ORDER BY o.order_date DESC
        """,
        params=(customers_subquery,),
        returning=True
    )

    # Verify all orders belong to active customers
    for order in result.data:
        assert order["status"] == "active"

    logger.info(f"Found {len(result.data)} orders from active customers")


def test_expression_date_functions(mysql_expression_test_db):
    """Test date functions with expressions"""
    logger.info("Starting date functions with expressions test")

    # Create expressions for date calculations
    days_since_purchase_expr = mysql_expression_test_db.create_expression("DATEDIFF(CURRENT_DATE, last_purchase_date)")
    purchase_in_last_30_days_expr = mysql_expression_test_db.create_expression("DATEDIFF(CURRENT_DATE, last_purchase_date) <= 30")

    # Query customers with date expressions
    result = mysql_expression_test_db.execute(
        """
        SELECT 
            id, name, last_purchase_date,
            %s AS days_since_purchase,
            %s AS recent_purchase
        FROM expression_test_customers
        WHERE last_purchase_date IS NOT NULL
        ORDER BY days_since_purchase
        """,
        params=(days_since_purchase_expr, purchase_in_last_30_days_expr),
        returning=True
    )

    # Get current date for verification
    current_date_result = mysql_expression_test_db.fetch_one("SELECT CURRENT_DATE as today")
    current_date = datetime.datetime.strptime(str(current_date_result["today"]), "%Y-%m-%d").date()

    # Verify date calculations
    for customer in result.data:
        last_purchase = datetime.datetime.strptime(str(customer["last_purchase_date"]), "%Y-%m-%d").date()
        expected_days = (current_date - last_purchase).days

        assert int(customer["days_since_purchase"]) == expected_days
        assert bool(int(customer["recent_purchase"])) == (expected_days <= 30)

    logger.info(f"Successfully verified date calculations for {len(result.data)} customers")


def test_complex_expressions_combination(mysql_expression_test_db):
    """Test combination of multiple expressions in a complex query"""
    logger.info("Starting complex expressions combination test")

    # Create multiple expressions for a comprehensive product analysis
    profit_margin_expr = mysql_expression_test_db.create_expression("(price - cost) / price * 100")
    stock_value_expr = mysql_expression_test_db.create_expression("price * stock_quantity")
    potential_profit_expr = mysql_expression_test_db.create_expression("(price - cost) * stock_quantity")

    # High profit filter (margin > 40% or potential profit > 2000)
    high_profit_filter = mysql_expression_test_db.create_expression("""
        ((price - cost) / price * 100 > 40) OR ((price - cost) * stock_quantity > 2000)
    """)

    # Complex query combining multiple expressions
    result = mysql_expression_test_db.execute(
        """
        SELECT 
            id, name, category, price, cost, stock_quantity,
            %s AS profit_margin,
            %s AS stock_value,
            %s AS potential_profit
        FROM expression_test_products
        WHERE %s
        ORDER BY potential_profit DESC
        """,
        params=(profit_margin_expr, stock_value_expr, potential_profit_expr, high_profit_filter),
        returning=True
    )

    # Verify all products meet the high profit criteria
    for product in result.data:
        price = float(product["price"])
        cost = float(product["cost"])
        quantity = int(product["stock_quantity"])

        margin = (price - cost) / price * 100
        potential_profit = (price - cost) * quantity

        # Verify calculated fields
        assert abs(float(product["profit_margin"]) - margin) < 0.01
        assert abs(float(product["stock_value"]) - (price * quantity)) < 0.01
        assert abs(float(product["potential_profit"]) - potential_profit) < 0.01

        # Verify filter condition
        assert margin > 40 or potential_profit > 2000

    logger.info(f"Successfully verified complex analysis for {len(result.data)} products")
