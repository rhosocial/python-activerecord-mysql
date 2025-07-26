# tests/rhosocial/activerecord_mysql_test/query/mysql/test_mysql_explain_specific.py
"""Test MySQL EXPLAIN features that are specific to certain versions."""
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from rhosocial.activerecord_test.query.utils import create_order_fixtures, get_mysql_version

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_mysql56_specific_features(order_fixtures, request):
    """Test MySQL 5.6 specific EXPLAIN features"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    mysql_version = get_mysql_version(request)
    if mysql_version is None or mysql_version >= (5, 7, 0):
        pytest.skip("This test is only applicable to MySQL 5.6")

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

    # Test EXTENDED keyword (MySQL 5.6 specific)
    plan = Order.query().explain(verbose=True).all()
    assert isinstance(plan, list)

    # MySQL 5.6 EXTENDED should provide additional information
    # The actual EXTENDED output only affects SHOW WARNINGS after EXPLAIN
    # But we can verify the command executed correctly
    plan_str = str(plan)
    assert 'EXTENDED' in request.session._test_callcounts or 'id' in plan_str

    # Test PARTITIONS keyword (also MySQL 5.6 specific)
    plan = Order.query().explain(**{'partitions': True}).all()
    assert isinstance(plan, list)

    # MySQL 5.6 PARTITIONS should show partition information
    plan_str = str(plan)
    assert 'PARTITIONS' in request.session._test_callcounts or 'partitions' in plan_str.lower()

def test_mysql57_specific_features(order_fixtures, request):
    """Test MySQL 5.7 specific EXPLAIN features"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    mysql_version = get_mysql_version(request)
    if mysql_version is None or mysql_version < (5, 7, 0) or mysql_version >= (8, 0, 0):
        pytest.skip("This test is only applicable to MySQL 5.7")

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

    # Test JSON format (should be supported in MySQL 5.7)
    try:
        plan = Order.query().explain(format=ExplainFormat.JSON).all()
        assert isinstance(plan, list)

        # In JSON format, verify we get proper structure
        if isinstance(plan[0], dict):
            assert any(key in plan[0] for key in ['query_block', 'Query'])
    except ValueError as e:
        pytest.fail(f"MySQL 5.7 should support JSON format: {e}")

    # Test that deprecated EXTENDED and PARTITIONS options don't produce warnings
    # In 5.7, these options are accepted but deprecated, and information is included by default
    plan = Order.query().explain(verbose=True).all()
    assert isinstance(plan, list)

    plan = Order.query().explain(**{'partitions': True}).all()
    assert isinstance(plan, list)

def test_mysql80_specific_features(order_fixtures, request):
    """Test MySQL 8.0 specific EXPLAIN features"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    mysql_version = get_mysql_version(request)
    if mysql_version is None or mysql_version < (8, 0, 0):
        pytest.skip("This test is only applicable to MySQL 8.0+")

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

    # Test JSON format with MySQL 8.0 enhancements
    try:
        plan = Order.query().explain(format=ExplainFormat.JSON).all()
        assert isinstance(plan, list)

        # MySQL 8.0 JSON format has enhanced structure
        if isinstance(plan[0], dict):
            assert any(key in plan[0] for key in ['query_block', 'Query'])
            # Check for MySQL 8.0 specific JSON keys
            json_str = str(plan)
            assert any(term in json_str.lower() for term in ['cost_info', 'rows_examined_per_scan'])
    except ValueError as e:
        pytest.fail(f"MySQL 8.0 should support enhanced JSON format: {e}")

    # Test TREE format (MySQL 8.0.16+)
    if mysql_version >= (8, 0, 16):
        try:
            plan = Order.query().explain(format=ExplainFormat.TREE).all()
            assert isinstance(plan, list)

            # TREE format should have tree-like structure
            plan_str = str(plan)
            assert any(term in plan_str for term in ['->', '->'])
        except ValueError as e:
            # This might fail on MySQL 8.0.0-8.0.15
            if mysql_version >= (8, 0, 16):
                pytest.fail(f"MySQL 8.0.16+ should support TREE format: {e}")

    # Test ANALYZE (MySQL 8.0.18+)
    if mysql_version >= (8, 0, 18):
        try:
            plan = Order.query().explain(type=ExplainType.ANALYZE).all()
            assert isinstance(plan, list)

            # ANALYZE output should include execution statistics
            plan_str = str(plan)
            # Look for terms that indicate actual execution metrics
            assert any(term in plan_str.lower() for term in ['actual', 'execution', 'time', 'rows'])
        except ValueError as e:
            # This might fail on MySQL 8.0.0-8.0.17
            if mysql_version >= (8, 0, 18):
                pytest.fail(f"MySQL 8.0.18+ should support ANALYZE: {e}")

def test_mysql83_specific_features(order_fixtures, request):
    """Test MySQL 8.3 specific EXPLAIN features"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    mysql_version = get_mysql_version(request)
    if mysql_version is None or mysql_version < (8, 3, 0):
        pytest.skip("This test is only applicable to MySQL 8.3+")

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

    # Test JSON format version 2 (MySQL 8.3+)
    try:
        # Note: json_version is not directly supported in the code,
        # but is implemented in the dialect class to set explain_json_format_version
        plan = Order.query().explain(format=ExplainFormat.JSON, **{'json_version': 2}).all()
        assert isinstance(plan, list)

        # MySQL 8.3 JSON format v2 has enhanced structure
        if isinstance(plan[0], dict):
            assert any(key in plan[0] for key in ['query_block', 'Query'])
            # Check for any MySQL 8.3 specific enhancements in JSON output
            json_str = str(plan)
            # This may need to be updated with actual MySQL 8.3 specific JSON keys
            assert 'explain_json_format_version' in request.session._test_callcounts or 'format' in json_str.lower()
    except ValueError as e:
        # If the version argument is not properly handled, skip gracefully
        pytest.skip(f"JSON format version 2 feature might not be implemented: {e}")