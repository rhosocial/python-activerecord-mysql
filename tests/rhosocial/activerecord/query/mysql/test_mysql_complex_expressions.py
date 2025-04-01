"""Test complex expressions and aggregate queries."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from src.rhosocial.activerecord.query.expression import (
    AggregateExpression, WindowExpression, CaseExpression,
    ArithmeticExpression, FunctionExpression
)
from tests.rhosocial.activerecord.query.utils import create_order_fixtures, create_blog_fixtures

# Create test fixtures
order_fixtures = create_order_fixtures()
blog_fixtures = create_blog_fixtures()

def test_complex_case_with_subquery(order_fixtures, request):
    """Test CASE expressions with subqueries."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with various amounts
    amounts = [50, 150, 350, 500, 1000]

    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{amount}.00')
        )
        order.save()

    # Test CASE expression with subqueries using raw SQL
    # Categorize orders based on how they compare to average order amount
    sql = f"""
    SELECT 
        id,
        order_number,
        total_amount,
        CASE
            WHEN total_amount > (SELECT AVG(total_amount) FROM {Order.__table_name__}) THEN 'Above Average'
            WHEN total_amount = (SELECT AVG(total_amount) FROM {Order.__table_name__}) THEN 'Average'
            ELSE 'Below Average'
        END as amount_category
    FROM {Order.__table_name__}
    ORDER BY total_amount
    """

    backend = Order.__backend__
    result = backend.fetch_all(sql)

    # Verify results
    assert len(result) == 5

    # Calculate average
    avg_amount = sum(amounts) / len(amounts)  # (50 + 150 + 350 + 500 + 1000) / 5 = 410

    # Check categorization
    for r in result:
        amount = float(r['total_amount'])
        if amount > avg_amount:
            assert r['amount_category'] == 'Above Average'
        elif amount == avg_amount:
            assert r['amount_category'] == 'Average'
        else:
            assert r['amount_category'] == 'Below Average'

    # Specifically check a few values
    assert result[0]['amount_category'] == 'Below Average'  # 50
    assert result[4]['amount_category'] == 'Above Average'  # 1000

def test_window_functions_with_joins(order_fixtures, request):
    """Test window functions with table joins."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data: user with orders and order items
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal('0.00')  # Will be calculated from items
        )
        order.save()

    # Add items to each order with different quantities and prices
    orders = Order.query().all()

    # First order: 2 items
    OrderItem(
        order_id=orders[0].id,
        product_name='Product A',
        quantity=2,
        unit_price=Decimal('10.00'),
        subtotal=Decimal('20.00')
    ).save()

    OrderItem(
        order_id=orders[0].id,
        product_name='Product B',
        quantity=1,
        unit_price=Decimal('15.00'),
        subtotal=Decimal('15.00')
    ).save()

    # Second order: 3 items
    OrderItem(
        order_id=orders[1].id,
        product_name='Product A',
        quantity=1,
        unit_price=Decimal('10.00'),
        subtotal=Decimal('10.00')
    ).save()

    OrderItem(
        order_id=orders[1].id,
        product_name='Product C',
        quantity=3,
        unit_price=Decimal('20.00'),
        subtotal=Decimal('60.00')
    ).save()

    OrderItem(
        order_id=orders[1].id,
        product_name='Product D',
        quantity=2,
        unit_price=Decimal('25.00'),
        subtotal=Decimal('50.00')
    ).save()

    # Third order: 1 item
    OrderItem(
        order_id=orders[2].id,
        product_name='Product E',
        quantity=4,
        unit_price=Decimal('30.00'),
        subtotal=Decimal('120.00')
    ).save()

    # Update order totals
    for order in orders:
        items = OrderItem.query().where('order_id = ?', (order.id,)).all()
        total = sum(item.subtotal for item in items)
        order.total_amount = total
        order.save()

    # Test window function with joins using custom SQL
    # Calculate each order's percentage of the total sales
    sql = f"""
    SELECT 
        o.id, 
        o.order_number,
        o.total_amount,
        SUM(o.total_amount) OVER () as total_sales,
        (o.total_amount / SUM(o.total_amount) OVER ()) * 100 as percentage
    FROM {Order.__table_name__} o
    ORDER BY o.id
    """

    backend = Order.__backend__
    result = backend.fetch_all(sql)

    # Verify results
    assert len(result) == 3  # 3 orders

    # Calculate expected percentages
    order_totals = [orders[0].total_amount, orders[1].total_amount, orders[2].total_amount]
    total_sales = sum(order_totals)
    expected_percentages = [(amount / total_sales) * 100 for amount in order_totals]

    # Check that percentages are correct
    for i, r in enumerate(result):
        assert abs(float(r['percentage']) - float(expected_percentages[i])) < 0.01

def test_nested_window_functions(order_fixtures, request):
    """Test nested window functions (multiple windows)."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data: multiple users with orders
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

    # Test nested window functions using custom SQL
    # For each order, calculate:
    # 1. The running total by user
    # 2. Each user's percentage of the global total
    sql = f"""
    SELECT 
        o.user_id,
        o.id,
        o.order_number,
        o.total_amount,
        SUM(o.total_amount) OVER (PARTITION BY o.user_id ORDER BY o.id) as user_running_total,
        SUM(o.total_amount) OVER () as global_total,
        (SUM(o.total_amount) OVER (PARTITION BY o.user_id)) / SUM(o.total_amount) OVER () * 100 as user_percentage
    FROM {Order.__table_name__} o
    ORDER BY o.user_id, o.id
    """

    backend = Order.__backend__
    result = backend.fetch_all(sql)

    # Verify results
    assert len(result) == 5  # 5 orders total

    # Calculate expected values
    user1_total = 100 + 200 + 300  # 600
    user2_total = 150 + 300        # 450
    global_total = user1_total + user2_total  # 1050

    user1_percentage = (user1_total / global_total) * 100  # (600/1050) * 100 = 57.14%
    user2_percentage = (user2_total / global_total) * 100  # (450/1050) * 100 = 42.86%

    # User1 running totals
    user1_running = [100, 300, 600]  # 100, 100+200, 100+200+300

    # User2 running totals
    user2_running = [150, 450]  # 150, 150+300

    # Check user1 results
    user1_results = [r for r in result if r['user_id'] == user1.id]
    assert len(user1_results) == 3

    for i, r in enumerate(user1_results):
        assert abs(float(r['user_running_total']) - float(user1_running[i])) < 0.01
        assert abs(float(r['user_percentage']) - float(user1_percentage)) < 0.01

    # Check user2 results
    user2_results = [r for r in result if r['user_id'] == user2.id]
    assert len(user2_results) == 2

    for i, r in enumerate(user2_results):
        assert abs(float(r['user_running_total']) - float(user2_running[i])) < 0.01
        assert abs(float(r['user_percentage']) - float(user2_percentage)) < 0.01

def test_complex_grouping_with_having(blog_fixtures, request):
    """Test complex GROUP BY with HAVING clause."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Post, Comment = blog_fixtures

    # Create test data: multiple users with posts and comments
    users = []
    for i in range(3):
        user = User(
            username=f'user{i+1}',
            email=f'user{i+1}@example.com',
            age=30 + i
        )
        user.save()
        users.append(user)

    # Create posts for each user
    posts_per_user = [3, 2, 1]  # user1: 3 posts, user2: 2 posts, user3: 1 post

    for user_idx, user in enumerate(users):
        for i in range(posts_per_user[user_idx]):
            post = Post(
                user_id=user.id,
                title=f'Post by {user.username} #{i+1}',
                content=f'Content for post {i+1} by {user.username}'
            )
            post.save()

    # Add varied comments to posts
    posts = Post.query().all()

    # For first user's posts: add 5, 3, 2 comments
    comment_counts = [5, 3, 2]
    for i, post in enumerate(posts[:3]):  # First user's 3 posts
        for j in range(comment_counts[i]):
            Comment(
                user_id=users[j % 3].id,  # Mix of comment authors
                post_id=post.id,
                content=f'Comment {j+1} on post {post.id}'
            ).save()

    # For second user's posts: add 1, 0 comments
    Comment(
        user_id=users[0].id,
        post_id=posts[3].id,  # Second user's first post
        content='Comment on second user post'
    ).save()

    # No comments for other posts

    # Test complex grouping with HAVING
    # Find users who have posts with an average of more than 2 comments per post
    sql = f"""
    SELECT 
        u.id,
        u.username,
        COUNT(DISTINCT p.id) as post_count,
        COUNT(c.id) as comment_count,
        COUNT(c.id) / COUNT(DISTINCT p.id) as avg_comments_per_post
    FROM {User.__table_name__} u
    JOIN {Post.__table_name__} p ON u.id = p.user_id
    LEFT JOIN {Comment.__table_name__} c ON p.id = c.post_id
    GROUP BY u.id, u.username
    HAVING COUNT(c.id) / COUNT(DISTINCT p.id) > 2
    ORDER BY avg_comments_per_post DESC
    """

    backend = User.__backend__
    result = backend.fetch_all(sql)

    # Verify results
    assert len(result) == 1  # Only user1 should have >2 comments per post on average

    # Check user1's stats
    assert result[0]['username'] == 'user1'
    assert result[0]['post_count'] == 3
    assert result[0]['comment_count'] == 10  # Total 5+3+2 = 10 comments
    assert float(result[0]['avg_comments_per_post']) > 2  # 10/3 = 3.33

def test_advanced_arithmetic_expressions(order_fixtures, request):
    """Test advanced arithmetic expressions in window functions."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data: orders with different amounts over time
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with increasing amounts
    amounts = [100, 150, 200, 250, 300]

    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{amount}.00')
        )
        order.save()

    # Test arithmetic expressions in window functions using custom SQL
    # Calculate growth metrics:
    # 1. Amount difference from previous order
    # 2. Percentage growth from previous order
    # 3. Percentage of the total amount
    sql = f"""
    SELECT 
        id,
        order_number,
        total_amount,
        total_amount - LAG(total_amount, 1, total_amount) OVER (ORDER BY id) as amount_diff,
        CASE 
            WHEN LAG(total_amount, 1, total_amount) OVER (ORDER BY id) = total_amount THEN 0
            ELSE (total_amount - LAG(total_amount, 1, total_amount) OVER (ORDER BY id)) / LAG(total_amount, 1, total_amount) OVER (ORDER BY id) * 100
        END as growth_percentage,
        total_amount / SUM(total_amount) OVER () * 100 as percentage_of_total
    FROM {Order.__table_name__}
    ORDER BY id
    """

    backend = Order.__backend__
    result = backend.fetch_all(sql)

    # Verify results
    assert len(result) == 5  # 5 orders

    # Calculate expected values
    total = sum(amounts)
    percentages_of_total = [(amount / total) * 100 for amount in amounts]

    # The first order has no previous to compare to (diff = 0, growth = 0%)
    assert float(result[0]['amount_diff']) == 0
    assert float(result[0]['growth_percentage']) == 0

    # Check subsequent orders
    for i in range(1, 5):
        # Amount diff
        expected_diff = amounts[i] - amounts[i-1]
        assert float(result[i]['amount_diff']) == expected_diff

        # Growth percentage
        expected_growth = (expected_diff / amounts[i-1]) * 100
        assert abs(float(result[i]['growth_percentage']) - expected_growth) < 0.01

        # Percentage of total
        assert abs(float(result[i]['percentage_of_total']) - percentages_of_total[i]) < 0.01