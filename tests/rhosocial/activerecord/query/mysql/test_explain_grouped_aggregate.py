"""Test explain functionality with grouped aggregates for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_explain_basic_group_by(order_fixtures, request):
    """Test explain with basic GROUP BY"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    statuses = ['pending', 'paid']
    for status in statuses:
        for i in range(2):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{i}',
                status=status,
                total_amount=Decimal('100.00')
            )
            order.save()

    # Test EXPLAIN with TEXT format
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    assert "GROUP BY" in str(plan).upper()

    # Test with JSON format if supported
    try:
        plan = (Order.query()
                .group_by('status')
                .count('*', 'count')
                .explain(format=ExplainFormat.JSON)
                .aggregate())
        assert isinstance(plan, list)
        # JSON format should include group by info
        assert "group_by" in str(plan).lower() or "grouping_operation" in str(plan).lower()
    except ValueError as e:
        if "format" in str(e).lower():
            pytest.skip("JSON format not supported in this MySQL version")
        else:
            raise


def test_explain_aggregate_with_having(order_fixtures, request):
    """Test explain with GROUP BY and HAVING"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]

    for status in statuses:
        for amount in amounts:
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{amount}',
                status=status,
                total_amount=amount
            )
            order.save()

    # Test explain with HAVING condition
    plan = (Order.query()
            .group_by('status')
            .having('COUNT(*) > %s AND SUM(total_amount) > %s',
                    (2, Decimal('500.00')))
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    assert "GROUP BY" in str(plan).upper()
    assert "HAVING" in str(plan).upper()


def test_explain_multiple_aggregates(order_fixtures, request):
    """Test explain with multiple aggregate functions"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test explain with multiple aggregates
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .sum('total_amount', 'total')
            .avg('total_amount', 'average')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    assert "GROUP BY" in str(plan).upper()
    # MySQL will show multiple aggregate functions
    assert "COUNT" in str(plan).upper()
    assert "SUM" in str(plan).upper() or "total" in str(plan).lower()
    assert "AVG" in str(plan).upper() or "average" in str(plan).lower()


def test_explain_multiple_group_by(order_fixtures, request):
    """Test explain with multiple GROUP BY columns"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    for i in range(2):
        user = User(
            username=f'user{i}',
            email=f'user{i}@example.com',
            age=30 + i
        )
        user.save()

        for status in ['pending', 'paid']:
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{i}-{status}',
                status=status,
                total_amount=Decimal('100.00')
            )
            order.save()

    # Test multiple grouping columns
    plan = (Order.query()
            .group_by('user_id', 'status')
            .count('*', 'count')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    assert "GROUP BY" in str(plan).upper()
    assert "user_id" in str(plan).lower()
    assert "status" in str(plan).lower()


def test_explain_aggregate_with_joins(order_fixtures, request):
    """Test explain with aggregates and joins"""
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

    # Test explain with join and aggregates
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .group_by(f'{User.__table_name__}.username')
            .count('*', 'order_count')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    assert "JOIN" in str(plan).upper()
    assert "GROUP BY" in str(plan).upper()
    assert User.__table_name__ in str(plan).lower()
    assert Order.__table_name__ in str(plan).lower()


def test_explain_aggregate_with_subqueries(order_fixtures, request):
    """Test explain with aggregates containing subqueries"""
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
            status='pending',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test with subquery in HAVING
    plan = (Order.query()
            .group_by('status')
            .having('COUNT(*) > (SELECT COUNT(*)/2 FROM orders)')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    assert "GROUP BY" in str(plan).upper()
    assert "HAVING" in str(plan).upper()
    # MySQL will show subquery in execution plan
    assert "SELECT" in str(plan).upper() and "FROM orders" in str(plan)