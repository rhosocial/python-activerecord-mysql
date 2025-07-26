# tests/rhosocial/activerecord_mysql_test/query/mysql/test_mysql_explain_basic.py
"""Test basic explain functionality for MySQL."""
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from rhosocial.activerecord_test.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_basic_explain(order_fixtures, request):
    """Test basic EXPLAIN output for MySQL"""
    # Skip if not MySQL
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

    # Default EXPLAIN should output basic execution plan
    plan = Order.query().explain().all()
    assert isinstance(plan, str)

    # MySQL EXPLAIN returns a result set with specific columns
    # Different MySQL versions have different column sets, but id, select_type, and table are common
    expected_columns = ['id', 'select_type', 'table']
    for column in expected_columns:
        assert column in plan

def test_explain_formats(order_fixtures, request):
    """Test EXPLAIN output formats for different MySQL versions"""
    # Skip if not MySQL
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures
    backend_name = request.node.name.split('-')[0]  # Extract mysql56 or mysql80 from test name

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Test with JSON format (supported in MySQL 5.6.5+)
    try:
        plan = Order.query().explain(format=ExplainFormat.JSON).all()
        assert isinstance(plan, list)

        # JSON format should return a structured document
        if backend_name == 'mysql80':
            # MySQL 8.0+ has more detailed JSON output
            assert isinstance(plan[0], dict)
            assert 'query_block' in plan[0] or 'Query' in plan[0]
    except ValueError as e:
        # If this version doesn't support the format, verify the error message
        assert "format" in str(e).lower()

    # Test with TREE format (MySQL 8.0.16+)
    if backend_name == 'mysql80':
        try:
            plan = Order.query().explain(format=ExplainFormat.TREE).all()
            assert isinstance(plan, list)
            # TREE format should return text-based tree structure
            assert any('-> ' in str(row) for row in plan) or any('->' in str(row) for row in plan)
        except ValueError as e:
            # This might still fail on MySQL 8.0.0-8.0.15
            assert "format" in str(e).lower() or "tree" in str(e).lower()

def test_explain_with_analyze(order_fixtures, request):
    """Test EXPLAIN ANALYZE which is only supported in MySQL 8.0.18+"""
    # Skip if not MySQL
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures
    backend_name = request.node.name.split('-')[0]

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # ANALYZE option is only supported in MySQL 8.0.18+
    if backend_name == 'mysql80':
        try:
            plan = Order.query().explain(type=ExplainType.ANALYZE).all()
            assert isinstance(plan, list)

            # ANALYZE output should include actual execution statistics
            # This might be in a column called 'actual' or shown in the TREE format
            if len(plan) > 0 and isinstance(plan[0], dict):
                assert any('actual' in str(row).lower() or 'cost' in str(row).lower() for row in plan)
        except ValueError as e:
            # This might fail on MySQL < 8.0.18
            assert "analyze" in str(e).lower() or "requires" in str(e).lower()

def test_version_specific_features(order_fixtures, request):
    """Test version-specific EXPLAIN features"""
    # Skip if not MySQL
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures
    backend_name = request.node.name.split('-')[0]

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # MySQL 5.6.x features - PARTITIONS and EXTENDED are separate keywords
    if backend_name == 'mysql56':
        try:
            # Test with partitions option
            plan = Order.query().explain(**{'partitions': True}).all()
            assert isinstance(plan, list)

            # Test with extended verbose output
            plan = Order.query().explain(verbose=True).all()
            assert isinstance(plan, list)
        except ValueError as e:
            pytest.fail(f"MySQL 5.6 should support PARTITIONS and EXTENDED options: {e}")

    # MySQL 5.7+ automatically includes the PARTITIONS and EXTENDED info
    elif backend_name.startswith('mysql'):
        # Just verify standard EXPLAIN works
        plan = Order.query().explain().all()
        assert isinstance(plan, list)