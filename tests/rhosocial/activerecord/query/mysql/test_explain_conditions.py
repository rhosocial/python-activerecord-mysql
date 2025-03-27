"""Test explain functionality with various conditions for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_explain_simple_where(order_fixtures, request):
    """Test explain with simple WHERE conditions for MySQL"""
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

    # Test EXPLAIN with normal output
    plan = (Order.query()
            .where('status = ?', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, list)
    assert len(plan) > 0

    # MySQL EXPLAIN should indicate a table scan or index usage
    # Check for common terms in MySQL EXPLAIN output
    plan_str = str(plan)
    assert any(term in plan_str.lower() for term in ['table', 'type', 'rows', 'extra'])

def test_explain_primary_key_condition(order_fixtures, request):
    """Test explain with primary key conditions for MySQL"""
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

    # Query on primary key should use index (const access)
    plan = (Order.query()
            .where('id = ?', (order.id,))
            .explain()
            .all())
    assert isinstance(plan, list)

    # For MySQL, look for 'const' in the 'type' column or 'PRIMARY' in key column
    plan_str = str(plan)
    assert any(term in plan_str.lower() for term in ['const', 'primary', 'eq_ref'])

def test_explain_foreign_key_condition(order_fixtures, request):
    """Test explain with foreign key conditions for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(user_id=user.id, order_number='ORD-001')
    order.save()

    # Query on foreign key should show table access method
    plan = (Order.query()
            .where('user_id = ?', (user.id,))
            .explain()
            .all())
    assert isinstance(plan, list)

    # Verify the MySQL EXPLAIN output includes expected table scan information
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()

    # Check access type (might be ALL for table scan or ref if there's an index)
    assert any(term in plan_str.lower() for term in ['all', 'ref', 'range'])

def test_explain_complex_conditions(order_fixtures, request):
    """Test explain with complex condition combinations for MySQL"""
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
            .where('total_amount > ?', (Decimal('100.00'),))
            .where('status = ?', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, list)

    # MySQL EXPLAIN for multiple conditions should show filtering
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()
    # Look for filtering indicators in MySQL EXPLAIN
    assert any(term in plan_str.lower() for term in ['where', 'filter', 'extra'])

def test_explain_or_conditions(order_fixtures, request):
    """Test explain with OR conditions for MySQL"""
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
            .where('status = ?', ('pending',))
            .or_where('status = ?', ('paid',))
            .explain()
            .all())
    assert isinstance(plan, list)

    # MySQL OR conditions might use index_merge or filesort
    plan_str = str(plan)
    assert any(term in plan_str.lower() for term in ['filesort', 'index_merge', 'using or', 'using where'])

def test_explain_in_conditions(order_fixtures, request):
    """Test explain with IN conditions for MySQL"""
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
    assert isinstance(plan, list)

    # MySQL IN conditions should show in the EXPLAIN
    plan_str = str(plan)
    assert any(term in plan_str.lower() for term in ['in', 'range', 'where'])

    # Test IN condition on primary key
    orders = Order.query().limit(2).all()
    order_ids = [o.id for o in orders]
    plan = (Order.query()
            .in_list('id', order_ids)
            .explain()
            .all())
    assert isinstance(plan, list)

    # IN on primary key should use index
    plan_str = str(plan)
    assert any(term in plan_str.lower() for term in ['range', 'primary', 'index'])