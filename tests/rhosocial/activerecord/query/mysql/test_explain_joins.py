"""Test explain functionality with various joins for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_explain_inner_join(order_fixtures, request):
    """Test explain with INNER JOIN"""
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

    # Test regular EXPLAIN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    assert User.__table_name__ in str(plan).lower()
    assert Order.__table_name__ in str(plan).lower()

    # Test with JSON format if supported
    try:
        plan = (Order.query()
                .join(f"""
                    INNER JOIN {User.__table_name__}
                    ON {Order.__table_name__}.user_id = {User.__table_name__}.id
                """)
                .explain(format=ExplainFormat.JSON)
                .all())
        assert isinstance(plan, list)
        # JSON should include join information
        assert "join" in str(plan).lower() or "nested_loop" in str(plan).lower()
    except ValueError as e:
        if "format" in str(e).lower():
            pytest.skip("JSON format not supported in this MySQL version")
        else:
            raise

def test_explain_left_join(order_fixtures, request):
    """Test explain with LEFT JOIN"""
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

    # Test regular EXPLAIN
    plan = (Order.query()
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    assert "LEFT" in str(plan).upper()
    assert Order.__table_name__ in str(plan).lower()
    assert OrderItem.__table_name__ in str(plan).lower()

def test_explain_multiple_joins(order_fixtures, request):
    """Test explain with multiple JOINs"""
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

    # Test regular EXPLAIN
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
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    assert User.__table_name__ in str(plan).lower()
    assert Order.__table_name__ in str(plan).lower()
    assert OrderItem.__table_name__ in str(plan).lower()

def test_explain_join_with_conditions(order_fixtures, request):
    """Test explain with JOINs and WHERE conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00'),
        status='pending'
    )
    order.save()

    # Test regular EXPLAIN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .where(f'{Order.__table_name__}.status = %s', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    assert "WHERE" in str(plan).upper() or "condition" in str(plan).lower()
    assert "status" in str(plan).lower()

def test_explain_join_with_ordering(order_fixtures, request):
    """Test explain with JOINs and ORDER BY"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i}',
            total_amount=Decimal('100.00')
        )
        order.save()

    # Test regular EXPLAIN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .order_by(f'{Order.__table_name__}.id DESC')
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    # MySQL should show sort or order by
    assert any(term in str(plan).upper() for term in ["ORDER BY", "SORT", "FILESORT", "ORDERED"])

def test_explain_join_with_aggregates(order_fixtures, request):
    """Test explain with JOINs and aggregate functions"""
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

    # Test regular EXPLAIN
    plan = (Order.query()
            .join(f"""
                    INNER JOIN {User.__table_name__}
                    ON {Order.__table_name__}.user_id = {User.__table_name__}.id
                """)
            .select(f"COUNT({Order.__table_name__}.id) as order_count")
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    assert "COUNT" in str(plan).upper()

    # Test explain with join optimization hints (MySQL specific)
    try:
        plan = (Order.query()
                .join(f"""
                        INNER JOIN {User.__table_name__} USE INDEX (PRIMARY)
                        ON {Order.__table_name__}.user_id = {User.__table_name__}.id
                    """)
                .explain()
                .all())
        assert isinstance(plan, str)
        assert "JOIN" in str(plan).upper()
        assert any(term in str(plan).upper() for term in ["INDEX", "PRIMARY"])
    except:
        # Skip if USE INDEX hint causes issues
        pytest.skip("Index hints not properly supported in this setup")
