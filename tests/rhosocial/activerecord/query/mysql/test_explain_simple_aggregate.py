"""Test explain functionality with simple aggregates for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_explain_count(order_fixtures, request):
    """Test explain with COUNT aggregate"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal('100.00')
        )
        order.save()

    # Test regular EXPLAIN output
    plan = Order.query().explain().count()
    assert isinstance(plan, str)
    assert "COUNT" in str(plan).upper()

    # Test with JSON format if supported
    try:
        plan = (Order.query()
                .explain(format=ExplainFormat.JSON)
                .count())
        assert isinstance(plan, list)
        # JSON plan should include count info
        assert "count" in str(plan).lower() or "function" in str(plan).lower()
    except ValueError as e:
        if "format" in str(e).lower():
            pytest.skip("JSON format not supported in this MySQL version")
        else:
            raise

    # Test with DISTINCT count
    plan = (Order.query()
            .explain()
            .count('id', distinct=True))
    assert isinstance(plan, str)
    assert "COUNT" in str(plan).upper()
    assert "DISTINCT" in str(plan).upper()

def test_explain_sum(order_fixtures, request):
    """Test explain with SUM aggregate"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test regular EXPLAIN
    plan = Order.query().explain().sum('total_amount')
    assert isinstance(plan, str)
    assert "SUM" in str(plan).upper()

    # Test with condition
    plan = (Order.query()
            .where('total_amount > %s', (Decimal('150.00'),))
            .explain()
            .sum('total_amount'))
    assert isinstance(plan, str)
    assert "SUM" in str(plan).upper()
    assert "WHERE" in str(plan).upper()

def test_explain_avg(order_fixtures, request):
    """Test explain with AVG aggregate"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test regular EXPLAIN
    plan = Order.query().explain().avg('total_amount')
    assert isinstance(plan, str)
    assert "AVG" in str(plan).upper()

def test_explain_min_max(order_fixtures, request):
    """Test explain with MIN and MAX aggregates"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test MIN with EXPLAIN
    plan = Order.query().explain().min('total_amount')
    assert isinstance(plan, str)
    assert "MIN" in str(plan).upper()

    # Test MAX with EXPLAIN
    plan = Order.query().explain().max('total_amount')
    assert isinstance(plan, str)
    assert "MAX" in str(plan).upper()

def test_explain_complex_aggregates(order_fixtures, request):
    """Test explain with aggregate functions and complex conditions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=Decimal(f'{(i+1)*100}.00'),
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Test regular EXPLAIN
    plan = (Order.query()
            .where('total_amount > %s', (Decimal('150.00'),))
            .start_or_group()
            .where('status = %s', ('pending',))
            .or_where('status = %s', ('paid',))
            .end_or_group()
            .explain()
            .sum('total_amount'))
    assert isinstance(plan, str)
    assert "SUM" in str(plan).upper()
    assert "WHERE" in str(plan).upper()
    assert any(op in str(plan).upper() for op in ["OR", "UNION"])