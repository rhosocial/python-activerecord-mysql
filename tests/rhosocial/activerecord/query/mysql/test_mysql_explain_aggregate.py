"""Test explain functionality with aggregate functions for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_explain_simple_aggregate(order_fixtures, request):
    """Test explain with simple aggregate functions for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
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

    # Test COUNT function
    plan = Order.query().explain().count()
    assert isinstance(plan, str)

    # MySQL EXPLAIN for COUNT should show optimization info
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()
    # MySQL might optimize COUNT(*) with index information
    assert any(term in plan_str.lower() for term in ['count', 'select_type', 'simple'])

def test_explain_group_by(order_fixtures, request):
    """Test explain with GROUP BY for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        for i in range(2):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{i}',
                status=status,
                total_amount=Decimal(f'{(i+1)*100}.00')
            )
            order.save()

    # Test GROUP BY with aggregate
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .explain()
            .aggregate())
    assert isinstance(plan, str)

    # MySQL EXPLAIN for GROUP BY should show grouping-related operations
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()

    # MySQL uses temporary tables and filesort for group by operations
    backend_name = request.node.name.split('-')[0]
    indicators = ['group by', 'temporary', 'filesort']
    if backend_name.startswith('mysql8'):
        # MySQL 8.0+ might use hash aggregation
        indicators.extend(['hash', 'aggregate'])

    assert any(term in plan_str.lower() for term in indicators)

def test_explain_having(order_fixtures, request):
    """Test explain with HAVING clause for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        for i in range(3):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{i}',
                status=status,
                total_amount=Decimal(f'{(i+1)*100}.00')
            )
            order.save()

    # Test GROUP BY with HAVING
    plan = (Order.query()
            .group_by('status')
            .having('COUNT(*) > ?', (2,))
            .explain()
            .aggregate())
    assert isinstance(plan, str)

    # MySQL EXPLAIN for HAVING should show filtering after grouping
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()

    # MySQL might handle HAVING in different ways
    having_indicators = ['having', 'filter', 'where']
    assert any(term in plan_str.lower() for term in having_indicators)

def test_explain_json_format_aggregates(order_fixtures, request):
    """Test explain with JSON format for aggregates (MySQL 5.6.5+)"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    backend_name = request.node.name.split('-')[0]
    if not backend_name.startswith('mysql8'):
        pytest.skip("This test requires MySQL 8.0+")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i}',
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Test GROUP BY with JSON format
    try:
        plan = (Order.query()
                .group_by('status')
                .count('*', 'count')
                .explain(format=ExplainFormat.JSON)
                .aggregate())
        assert isinstance(plan, list)

        # In JSON format, check that the result contains expected JSON structure
        if plan and isinstance(plan[0], dict):
            # Look for query_block and aggregation info
            assert any(key in plan[0] for key in ['query_block', 'Query'])

            # Check for grouping information in JSON
            json_str = str(plan)
            assert 'group' in json_str.lower()
            assert 'orders' in json_str.lower()
    except ValueError as e:
        # This might happen on MySQL versions that don't fully support the format
        assert "format" in str(e).lower()

def test_explain_complex_aggregates(order_fixtures, request):
    """Test explain with complex aggregate expressions for MySQL"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i}',
            total_amount=Decimal(f'{(i+1)*100}.00'),
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Test multiple aggregates
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .sum('total_amount', 'total')
            .avg('total_amount', 'average')
            .explain()
            .aggregate())
    assert isinstance(plan, str)

    # MySQL EXPLAIN for multiple aggregates should show grouping operations
    plan_str = str(plan)
    assert 'orders' in plan_str.lower()

    # MySQL typically uses temporary tables and filesort for complex grouping
    backend_name = request.node.name.split('-')[0]
    aggregate_indicators = ['group by', 'temporary', 'filesort']
    if backend_name.startswith('mysql8'):
        # MySQL 8.0+ might show more detail on the aggregation
        aggregate_indicators.extend(['aggregate', 'hash', 'group'])

    assert any(term in plan_str.lower() for term in aggregate_indicators)