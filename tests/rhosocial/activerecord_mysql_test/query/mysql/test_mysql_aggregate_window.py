# tests/rhosocial/activerecord_mysql_test/query/mysql/test_mysql_aggregate_window.py
"""Test window functions and CASE expressions in aggregate queries."""
from decimal import Decimal

import pytest
from rhosocial.activerecord.query import (
    AggregateExpression
)
from rhosocial.activerecord_test.query.utils import create_order_fixtures, create_blog_fixtures

# Create test fixtures
order_fixtures = create_order_fixtures()
blog_fixtures = create_blog_fixtures()

def test_window_partition_by(order_fixtures, request):
    """Test window functions with PARTITION BY."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data: multiple users with multiple orders of different amounts
    user1 = User(username='user1', email='user1@example.com', age=30)
    user1.save()

    user2 = User(username='user2', email='user2@example.com', age=35)
    user2.save()

    # Create orders for user1
    for i in range(3):
        order = Order(
            user_id=user1.id,
            order_number=f'ORD-U1-{i+1}',
            total_amount=Decimal(f'{(i+1)*100}.00')
        )
        order.save()

    # Create orders for user2
    for i in range(2):
        order = Order(
            user_id=user2.id,
            order_number=f'ORD-U2-{i+1}',
            total_amount=Decimal(f'{(i+1)*150}.00')
        )
        order.save()

    # Test window function with PARTITION BY
    # Calculate the average order amount per user
    # Use PARTITION BY to separate results by user_id

    # Create the base expression for the window function
    # Note: When using expressions in window functions, do not set alias as it will cause syntax error
    avg_expr = AggregateExpression("AVG", "total_amount", alias=None)

    # Create window expression with PARTITION BY user_id
    result = (Order.query()
              .select("user_id", "order_number", "total_amount")
              .window(avg_expr, partition_by=["user_id"], alias="avg_per_user")
              .order_by("user_id", "total_amount")
              .aggregate())

    # Verify results
    assert len(result) == 5  # Total 5 orders

    # Check the window function results
    user1_results = [r for r in result if r['user_id'] == user1.id]
    user2_results = [r for r in result if r['user_id'] == user2.id]

    # User1 should have 3 orders, all with the same avg_per_user value
    assert len(user1_results) == 3
    avg_user1 = sum([100, 200, 300]) / 3  # Expected average for user1
    for r in user1_results:
        assert abs(float(r['avg_per_user']) - avg_user1) < 0.01

    # User2 should have 2 orders, both with the same avg_per_user value
    assert len(user2_results) == 2
    avg_user2 = sum([150, 300]) / 2  # Expected average for user2
    for r in user2_results:
        assert abs(float(r['avg_per_user']) - avg_user2) < 0.01

def test_window_order_by(order_fixtures, request):
    """Test window functions with ORDER BY for running totals."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    order_amounts = [100, 200, 150, 300, 250]

    for i, amount in enumerate(order_amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{amount}.00')
        )
        order.save()

    # Test window function with ORDER BY
    # Calculate running total of order amounts

    # Create the base expression for the window function
    sum_expr = AggregateExpression("SUM", "total_amount", alias=None)

    # Create window expression with ORDER BY
    result = (Order.query()
              .select("order_number", "total_amount")
              .window(sum_expr, order_by=["order_number"], alias="running_total")
              .order_by("order_number")
              .aggregate())

    # Verify results
    assert len(result) == 5  # Total 5 orders

    # Calculate expected running totals
    expected_running_totals = []
    running_sum = 0

    # Order by order_number, so should match our insertion order
    for amount in order_amounts:
        running_sum += amount
        expected_running_totals.append(running_sum)

    # Check each order has the correct running total
    for i, r in enumerate(result):
        assert abs(float(r['running_total']) - expected_running_totals[i]) < 0.01

def test_window_partition_and_order(order_fixtures, request):
    """Test window functions with both PARTITION BY and ORDER BY."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data: multiple users with multiple orders
    user1 = User(username='user1', email='user1@example.com', age=30)
    user1.save()

    user2 = User(username='user2', email='user2@example.com', age=35)
    user2.save()

    # Create orders for user1
    for i, amount in enumerate([100, 200, 300]):
        order = Order(
            user_id=user1.id,
            order_number=f'ORD-U1-{i+1}',
            total_amount=Decimal(f'{amount}.00')
        )
        order.save()

    # Create orders for user2
    for i, amount in enumerate([150, 250]):
        order = Order(
            user_id=user2.id,
            order_number=f'ORD-U2-{i+1}',
            total_amount=Decimal(f'{amount}.00')
        )
        order.save()

    # Test window function with both PARTITION BY and ORDER BY
    # Calculate running total of order amounts per user

    # Create the base expression for the window function
    sum_expr = AggregateExpression("SUM", "total_amount", alias=None)

    # Create window expression with PARTITION BY and ORDER BY
    result = (Order.query()
              .select("user_id", "order_number", "total_amount")
              .window(sum_expr,
                     partition_by=["user_id"],
                     order_by=["total_amount"],
                     alias="user_running_total")
              .order_by("user_id", "total_amount")
              .aggregate())

    # Verify results
    assert len(result) == 5  # Total 5 orders

    # Check user1's running totals (ordered by amount)
    user1_results = [r for r in result if r['user_id'] == user1.id]
    assert len(user1_results) == 3
    assert abs(float(user1_results[0]['user_running_total']) - 100) < 0.01  # First amount: 100
    assert abs(float(user1_results[1]['user_running_total']) - 300) < 0.01  # Running total: 100 + 200
    assert abs(float(user1_results[2]['user_running_total']) - 600) < 0.01  # Running total: 100 + 200 + 300

    # Check user2's running totals (ordered by amount)
    user2_results = [r for r in result if r['user_id'] == user2.id]
    assert len(user2_results) == 2
    assert abs(float(user2_results[0]['user_running_total']) - 150) < 0.01  # First amount: 150
    assert abs(float(user2_results[1]['user_running_total']) - 400) < 0.01  # Running total: 150 + 250

def test_multiple_window_functions(order_fixtures, request):
    """Test multiple window functions in a single query."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    order_amounts = [100, 200, 150, 300, 250]

    for i, amount in enumerate(order_amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{amount}.00')
        )
        order.save()

    # Test multiple window functions
    # 1. Calculate running total
    # 2. Calculate running average

    # Create base expressions
    sum_expr = AggregateExpression("SUM", "total_amount", alias=None)
    avg_expr = AggregateExpression("AVG", "total_amount", alias=None)

    # Query with multiple window functions
    result = (Order.query()
              .select("order_number", "total_amount")
              .window(sum_expr, order_by=["order_number"], alias="running_total")
              .window(avg_expr, order_by=["order_number"], alias="running_avg")
              .order_by("order_number")
              .aggregate())

    # Verify results
    assert len(result) == 5  # Total 5 orders

    # Calculate expected running totals and averages
    expected_running_totals = []
    expected_running_avgs = []
    running_sum = 0

    for i, amount in enumerate(order_amounts):
        running_sum += amount
        expected_running_totals.append(running_sum)
        expected_running_avgs.append(running_sum / (i + 1))

    # Check each order has correct running total and average
    for i, r in enumerate(result):
        assert abs(float(r['running_total']) - expected_running_totals[i]) < 0.01
        assert abs(float(r['running_avg']) - expected_running_avgs[i]) < 0.01

def test_window_rank_functions(blog_fixtures, request):
    """Test window functions with ranking functions."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Post, Comment = blog_fixtures

    # Create test data: users with posts and comments
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create posts
    for i in range(3):
        post = Post(
            user_id=user.id,
            title=f'Post {i+1}',
            content=f'Content for post {i+1}'
        )
        post.save()

    # Add varied numbers of comments to each post
    posts = Post.query().all()

    # Add 5 comments to first post
    for i in range(5):
        comment = Comment(
            user_id=user.id,
            post_id=posts[0].id,
            content=f'Comment {i+1} on post 1'
        )
        comment.save()

    # Add 3 comments to second post
    for i in range(3):
        comment = Comment(
            user_id=user.id,
            post_id=posts[1].id,
            content=f'Comment {i+1} on post 2'
        )
        comment.save()

    # Add 1 comment to third post
    comment = Comment(
        user_id=user.id,
        post_id=posts[2].id,
        content='Comment 1 on post 3'
    )
    comment.save()

    # Test RANK() window function to rank posts by comment count
    # This query joins posts with comments, groups by post, and ranks by comment count

    # Custom SQL for rank function (since it's not directly supported in expression.py)
    sql = f"""
    SELECT p.id, p.title, COUNT(c.id) as comment_count,
           RANK() OVER (ORDER BY COUNT(c.id) DESC) as post_rank
    FROM {Post.__table_name__} p
    LEFT JOIN {Comment.__table_name__} c ON p.id = c.post_id
    GROUP BY p.id, p.title
    ORDER BY post_rank
    """

    # Execute raw SQL since our expression system doesn't directly support RANK()
    backend = Post.__backend__
    result = backend.fetch_all(sql)

    # Verify results
    assert len(result) == 3  # 3 posts

    # Posts should be ranked by comment count (5, 3, 1)
    assert result[0]['comment_count'] == 5
    assert result[0]['post_rank'] == 1  # Highest rank (most comments)

    assert result[1]['comment_count'] == 3
    assert result[1]['post_rank'] == 2  # Second rank

    assert result[2]['comment_count'] == 1
    assert result[2]['post_rank'] == 3  # Lowest rank (fewest comments)

def test_case_expression_simple(order_fixtures, request):
    """Test simple CASE expression."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped', 'cancelled']

    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal('100.00'),
            status=status
        )
        order.save()

    # Test simple CASE expression
    # Categorize orders by their status
    conditions = [
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Processing"),
        ("status = 'shipped'", "Completed")
    ]

    result = (Order.query()
              .select("order_number", "status")
              .case(conditions, else_result="Other", alias="status_category")
              .order_by("order_number")
              .aggregate())

    # Verify results
    assert len(result) == 4  # Total 4 orders

    # Check the CASE results
    status_mapping = {
        'pending': 'New',
        'paid': 'Processing',
        'shipped': 'Completed',
        'cancelled': 'Other'  # Falls to ELSE
    }

    for r in result:
        assert r['status_category'] == status_mapping[r['status']]

def test_case_expression_with_aggregation(order_fixtures, request):
    """Test CASE expression with aggregation."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    data = [
        ('pending', 100),
        ('pending', 200),
        ('paid', 150),
        ('paid', 250),
        ('shipped', 300),
        ('cancelled', 50)
    ]

    for i, (status, amount) in enumerate(data):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{amount}.00'),
            status=status
        )
        order.save()

    # Test CASE with aggregation
    # Count orders by category
    case_conditions = [
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Processing"),
        ("status = 'shipped'", "Completed")
    ]

    # First, add the CASE expression
    query = Order.query().case(case_conditions, else_result="Other", alias='category')

    # Then use GROUP BY on the result and count
    result = (query
              .group_by("category")
              .count("*", "count")
              .order_by("category")
              .aggregate())

    # Verify results
    assert len(result) == 4  # 4 categories

    # Calculate expected counts
    expected_counts = {
        'New': 2,       # 2 pending orders
        'Processing': 2, # 2 paid orders
        'Completed': 1,  # 1 shipped order
        'Other': 1       # 1 cancelled order
    }

    # Check that counts match expectations
    for r in result:
        assert r['count'] == expected_counts[r['category']]


def test_case_expression_with_window(order_fixtures, request):
    """Test combining CASE expression with window function."""
    # Only run this test in MySQL environment
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data: multiple users with orders of different statuses
    user1 = User(username='user1', email='user1@example.com', age=30)
    user1.save()

    user2 = User(username='user2', email='user2@example.com', age=35)
    user2.save()

    # Create orders for users with different statuses and amounts
    data = [
        (user1.id, 'pending', 100),
        (user1.id, 'pending', 200),
        (user1.id, 'paid', 300),
        (user2.id, 'pending', 150),
        (user2.id, 'paid', 250),
        (user2.id, 'shipped', 350)
    ]

    for i, (user_id, status, amount) in enumerate(data):
        order = Order(
            user_id=user_id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{amount}.00'),
            status=status
        )
        order.save()

    # Define CASE expression for order priority - using numeric values without quotes
    case_conditions = [
        ("status = 'shipped'", 3),  # Highest priority - numeric literal, not string
        ("status = 'paid'", 2),  # Numeric literal
        ("status = 'pending'", 1)  # Numeric literal
    ]

    # Step 1: Create base query with CASE expression for priority
    base_query = Order.query()
    base_query.select("user_id", "order_number", "status", "total_amount")
    base_query.case(case_conditions, else_result=0, alias="priority")  # Using numeric 0

    # Get the SQL for CTE definition
    base_sql, base_params = base_query.to_sql()

    # Step 2: Create a CTE with the base query
    window_query = Order.query()
    window_query.with_cte("orders_with_priority", base_sql)

    # Step 3: Query from the CTE and apply window function
    window_query.from_cte("orders_with_priority")

    # Select all columns from the CTE
    window_query.select("user_id", "order_number", "status", "total_amount", "priority")

    # Define window function for max priority per user
    from rhosocial.activerecord.query.expression import AggregateExpression
    max_priority_expr = AggregateExpression("MAX", "priority", alias=None)

    # Add window function as additional column
    window_query.window(max_priority_expr, partition_by=["user_id"], alias="max_user_priority")

    # Order results and execute query
    window_query.order_by("user_id", "priority DESC")
    result = window_query.aggregate()

    # Verify results
    assert len(result) == 6  # Total 6 orders

    # Check window function results
    user1_results = [r for r in result if r['user_id'] == user1.id]
    user2_results = [r for r in result if r['user_id'] == user2.id]

    # User1's max priority should be 2 (paid)
    assert len(user1_results) == 3
    for r in user1_results:
        # Check if the value is numeric or string and adapt accordingly
        # MySQL might return integers or strings depending on configuration
        max_priority = r['max_user_priority']
        if isinstance(max_priority, str):
            assert max_priority == '2'
        else:
            assert max_priority == 2

    # User2's max priority should be 3 (shipped)
    assert len(user2_results) == 3
    for r in user2_results:
        max_priority = r['max_user_priority']
        if isinstance(max_priority, str):
            assert max_priority == '3'
        else:
            assert max_priority == 3


def test_explain_window_function(order_fixtures, request):
    """Test EXPLAIN with window functions."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{(i+1)*100}.00')
        )
        order.save()

    # Create the base expression for the window function
    sum_expr = AggregateExpression("SUM", "total_amount", alias=None)

    # Create window query with EXPLAIN
    plan = (Order.query()
            .select("order_number", "total_amount")
            .window(sum_expr, order_by=["order_number"], alias="running_total")
            .explain()
            .aggregate())

    # Verify EXPLAIN output
    assert isinstance(plan, str)
    plan_str = str(plan)

    # MySQL EXPLAIN for window function should reference specific operations
    backend_name = request.node.name.split('-')[0]

    if backend_name.startswith('mysql8'):
        # MySQL 8.0+ has better window function support and might show it in EXPLAIN
        assert any(term in plan_str.lower() for term in ['window', 'temporary', 'filesort'])

    # For all MySQL versions, should at least show the table
    assert 'orders' in plan_str.lower()

def test_arithmetic_expression(order_fixtures, request):
    """Test arithmetic expressions in queries."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create an order with items
    order = Order(
        user_id=user.id,
        order_number='ORD-1',
        total_amount=Decimal('0.00')  # We'll calculate this from items
    )
    order.save()

    # Add items with different quantities and prices
    item_data = [
        ('Product 1', 2, Decimal('10.00')),  # 2 x $10 = $20
        ('Product 2', 1, Decimal('25.00')),  # 1 x $25 = $25
        ('Product 3', 3, Decimal('15.00'))   # 3 x $15 = $45
    ]

    for name, qty, price in item_data:
        item = OrderItem(
            order_id=order.id,
            product_name=name,
            quantity=qty,
            unit_price=price,
            subtotal=qty * price
        )
        item.save()

    # Use custom SQL to test arithmetic expressions
    # Calculate total from items using arithmetic
    sql = f"""
    SELECT o.id, o.order_number, 
           SUM(i.quantity * i.unit_price) as calculated_total
    FROM {Order.__table_name__} o
    JOIN {OrderItem.__table_name__} i ON o.id = i.order_id
    WHERE o.id = {order.id}
    GROUP BY o.id, o.order_number
    """

    backend = Order.__backend__
    result = backend.fetch_one(sql)

    # Verify arithmetic calculation
    assert result is not None
    expected_total = sum(qty * price for _, qty, price in item_data)  # $20 + $25 + $45 = $90
    assert abs(float(result['calculated_total']) - float(expected_total)) < 0.01

def test_function_expression(order_fixtures, request):
    """Test SQL function expressions."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{(i+1)*100}.00')
        )
        order.save()

    # Test SQL functions using custom SQL
    # Using CONCAT, UPPER, and ROUND functions
    sql = f"""
    SELECT 
        id,
        CONCAT('Order #', order_number) as order_label,
        UPPER(status) as status_upper,
        ROUND(total_amount, 0) as rounded_total
    FROM {Order.__table_name__}
    ORDER BY id
    """

    backend = Order.__backend__
    result = backend.fetch_all(sql)

    # Verify function results
    assert len(result) == 3

    for i, r in enumerate(result):
        assert r['order_label'] == f"Order #ORD-{i+1}"
        assert r['status_upper'] == "PENDING"  # Default status is 'pending'
        assert float(r['rounded_total']) == (i+1) * 100.0