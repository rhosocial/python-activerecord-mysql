"""Test basic explain functionality for MySQL."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_basic_explain(order_fixtures, request):
    """Test basic EXPLAIN output"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Default EXPLAIN should output human-readable plan
    plan = Order.query().explain().all()
    assert isinstance(plan, str)
    assert any(term in plan.upper() for term in ['TABLE', 'ORDER', 'SELECT'])

def test_explain_format_options(order_fixtures, request):
    """Test EXPLAIN with different format options"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Test with default format (TEXT)
    plan = Order.query().explain(format=ExplainFormat.TEXT).all()
    assert isinstance(plan, str)
    assert any(term in plan.upper() for term in ['TABLE', 'ORDER', 'SELECT'])

    # Test with JSON format (MySQL 5.6.5+)
    try:
        plan = Order.query().explain(format=ExplainFormat.JSON).all()
        assert isinstance(plan, list)
        # JSON output is returned as list of dictionaries
        assert len(plan) > 0
        assert "query_block" in str(plan)
    except ValueError as e:
        # Skip if JSON format not supported by MySQL version
        if "format" in str(e).lower():
            pytest.skip("JSON format not supported in this MySQL version")
        else:
            raise

    # Test with TREE format (MySQL 8.0.16+)
    try:
        plan = Order.query().explain(format=ExplainFormat.TREE).all()
        assert isinstance(plan, str)
        assert "|-" in plan
    except ValueError as e:
        # Skip if TREE format not supported by MySQL version
        if "format" in str(e).lower():
            pytest.skip("TREE format not supported in this MySQL version")
        else:
            raise

def test_explain_analyze_option(order_fixtures, request):
    """Test EXPLAIN ANALYZE option (MySQL 8.0.18+)"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    try:
        plan = Order.query().explain(type=ExplainType.ANALYZE).all()
        assert isinstance(plan, str)
        # ANALYZE includes actual execution statistics
        assert any(term in str(plan).upper() for term in ['ACTUAL', 'ROWS', 'TIME', 'COST'])
    except ValueError as e:
        # Skip if ANALYZE not supported by MySQL version
        if "requires MySQL 8.0" in str(e):
            pytest.skip("EXPLAIN ANALYZE not supported in this MySQL version")
        else:
            raise

def test_explain_query_building(order_fixtures, request):
    """Test explain with query building methods"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Query can be built before explain
    query = Order.query().where('id > %s', (0,))
    plan = query.explain().all()
    assert isinstance(plan, str)

    # Explain can be added before other methods
    plan = Order.query().explain().where('id > %s', (0,)).all()
    assert isinstance(plan, str)

def test_invalid_explain_options(order_fixtures, request):
    """Test invalid explain options"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Format not supported by MySQL version
    try:
        Order.query().explain(format=ExplainFormat.XML).all()
        assert False, "Should raise ValueError for unsupported format"
    except ValueError as e:
        assert "format" in str(e).lower()

    try:
        Order.query().explain(format=ExplainFormat.YAML).all()
        assert False, "Should raise ValueError for unsupported format"
    except ValueError as e:
        assert "format" in str(e).lower()