"""Test explain functionality with various joins for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_explain_inner_join(order_fixtures, request):
    """Test explain with INNER JOIN for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Test EXPLAIN with INNER JOIN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .explain()
            .all())
    assert isinstance(plan, list)

    # MySQL EXPLAIN for joins should show both tables
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()
    assert 'users' in plan_str.lower()

    # In MySQL 5.7+, join information is shown in the 'rows' and 'Extra' columns
    backend_name = request.node.name.split('-')[0]
    if backend_name.startswith('mysql8'):
        # MySQL 8.0+ provides more detailed join information
        assert any(term in plan_str.lower() for term in ['nested loop', 'join buffer'])

def test_explain_left_join(order_fixtures, request):
    """Test explain with LEFT JOIN for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Test EXPLAIN with LEFT JOIN
    plan = (Order.query()
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain()
            .all())
    assert isinstance(plan, list)

    # MySQL EXPLAIN for LEFT JOIN should show NULL-complemented info
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()
    assert 'order_items' in plan_str.lower()

    # In MySQL 5.7+, outer join info is shown in the execution plan
    backend_name = request.node.name.split('-')[0]
    if backend_name.startswith('mysql8'):
        # MySQL 8.0+ provides more detailed join information
        assert any(term in plan_str.lower() for term in ['left join', 'outer'])

def test_explain_multiple_joins(order_fixtures, request):
    """Test explain with multiple JOINs for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    item = OrderItem(
        order_id=order.id,
        product_name='Test Product',
        quantity=1,
        unit_price=Decimal('100.00'),
        subtotal=Decimal('100.00')
    )
    item.save()

    # Test EXPLAIN with multiple JOINs
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain()
            .all())
    assert isinstance(plan, list)

    # MySQL EXPLAIN for multiple joins should show all tables
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()
    assert 'users' in plan_str.lower()
    assert 'order_items' in plan_str.lower()

    # Check join order - MySQL typically processes FROM and JOINs from left to right
    backend_name = request.node.name.split('-')[0]
    if backend_name.startswith('mysql8'):
        # MySQL 8.0+ might show join order in the 'select_type' column
        assert any(term in plan_str.lower() for term in ['simple', 'primary', 'derived'])

def test_explain_join_with_format(order_fixtures, request):
    """Test explain with joins and different output formats"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    backend_name = request.node.name.split('-')[0]
    if not backend_name.startswith('mysql8'):
        pytest.skip("JSON format requires MySQL 5.6.5+")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Test EXPLAIN with JSON format (MySQL 5.6.5+)
    try:
        plan = (Order.query()
                .join(f"""
                    INNER JOIN {User.__table_name__}
                    ON {Order.__table_name__}.user_id = {User.__table_name__}.id
                """)
                .explain(format=ExplainFormat.JSON)
                .all())
        assert isinstance(plan, list)

        # In JSON format, check that the result contains the expected JSON structure
        if plan and isinstance(plan[0], dict):
            # JSON format has specific keys to look for
            assert any(key in plan[0] for key in ['query_block', 'Query'])

            # Check for join information in JSON
            json_str = str(plan)
            assert 'orders' in json_str.lower()
            assert 'users' in json_str.lower()
            assert any(term in json_str.lower() for term in ['join', 'nested_loop'])
    except ValueError as e:
        # This might happen on MySQL versions that don't fully support JSON format
        assert "format" in str(e).lower()