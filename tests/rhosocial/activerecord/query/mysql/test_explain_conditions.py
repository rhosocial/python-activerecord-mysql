"""Test explain functionality with various conditions for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_explain_simple_where(order_fixtures, request):
    """Test explain with simple WHERE conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00'),
        status='pending'
    )
    order.save()

    # Test EXPLAIN with TEXT format
    plan = (Order.query()
            .where('status = %s', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(term in str(plan).upper() for term in ['TABLE', 'SELECT', 'WHERE'])

    # Test EXPLAIN with JSON format if supported
    try:
        plan = (Order.query()
                .where('status = %s', ('pending',))
                .explain(format=ExplainFormat.JSON)
                .all())
        assert isinstance(plan, list)
        # JSON plan should include where condition info
        assert "where" in str(plan).lower()
    except ValueError as e:
        if "format" in str(e).lower():
            pytest.skip("JSON format not supported in this MySQL version")
        else:
            raise

def test_explain_primary_key_condition(order_fixtures, request):
    """Test explain with primary key conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Query on primary key should use index
    plan = (Order.query()
            .where('id = %s', (order.id,))
            .explain()
            .all())
    assert isinstance(plan, str)
    # MySQL should indicate primary key or unique index usage
    assert any(term in str(plan).upper() for term in ['PRIMARY', 'UNIQUE'])

def test_explain_foreign_key_condition(order_fixtures, request):
    """Test explain with foreign key conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(user_id=user.id, order_number='ORD-001')
    order.save()

    # Query on foreign key
    plan = (Order.query()
            .where('user_id = %s', (user.id,))
            .explain()
            .all())
    assert isinstance(plan, str)
    # Check if foreign key column is mentioned
    assert "user_id" in str(plan).lower()

def test_explain_complex_conditions(order_fixtures, request):
    """Test explain with complex condition combinations"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('150.00'),
        status='pending'
    )
    order.save()

    # Test compound conditions
    plan = (Order.query()
            .where('total_amount > %s', (Decimal('100.00'),))
            .where('status = %s', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "WHERE" in str(plan).upper()
    assert "total_amount" in str(plan).lower()
    assert "status" in str(plan).lower()

def test_explain_or_conditions(order_fixtures, request):
    """Test explain with OR conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{status}',
            status=status
        )
        order.save()

    # Test OR conditions
    plan = (Order.query()
            .where('status = %s', ('pending',))
            .or_where('status = %s', ('paid',))
            .explain()
            .all())
    assert isinstance(plan, str)
    # MySQL will show OR in execution plan
    assert any(term in str(plan).upper() for term in ['OR', 'UNION'])

def test_explain_range_conditions(order_fixtures, request):
    """Test explain with range conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test BETWEEN condition
    plan = (Order.query()
            .between('total_amount', Decimal('150.00'), Decimal('250.00'))
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "total_amount" in str(plan).lower()
    assert "BETWEEN" in str(plan).upper()

    # Test LIKE condition
    plan = (Order.query()
            .like('order_number', 'ORD-%')
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "order_number" in str(plan).lower()
    assert "LIKE" in str(plan).upper()

def test_explain_in_conditions(order_fixtures, request):
    """Test explain with IN conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{status}',
            status=status
        )
        order.save()

    # Test IN condition
    plan = (Order.query()
            .in_list('status', ['pending', 'paid'])
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "status" in str(plan).lower()
    assert "IN" in str(plan).upper()

    # Test IN condition on primary key
    orders = Order.query().limit(2).all()
    order_ids = [o.id for o in orders]
    plan = (Order.query()
            .in_list('id', order_ids)
            .explain()
            .all())
    assert isinstance(plan, str)
    assert "id" in str(plan).lower()
    assert "IN" in str(plan).upper()
    # Primary key IN should use index
    assert any(term in str(plan).upper() for term in ['PRIMARY', 'UNIQUE', 'INDEX'])