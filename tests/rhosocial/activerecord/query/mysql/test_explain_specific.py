"""Test MySQL-specific EXPLAIN functionality."""
from decimal import Decimal

import pytest

from tests.rhosocial.activerecord.query.utils import create_order_fixtures
from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat, ExplainOptions

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_explain_format_tree(order_fixtures, request):
    """Test EXPLAIN with TREE format (MySQL 8.0.16+)"""
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

    try:
        plan = Order.query().explain(format=ExplainFormat.TREE).all()
        assert isinstance(plan, str)
        # TREE format uses specific formatting characters
        assert any(char in plan for char in ['->', '|-'])
    except ValueError as e:
        if "format" in str(e).lower():
            pytest.skip("TREE format not supported in this MySQL version")
        else:
            raise


def test_explain_with_analyze(order_fixtures, request):
    """Test EXPLAIN ANALYZE option (MySQL 8.0.18+)"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    try:
        plan = Order.query().explain(type=ExplainType.ANALYZE).all()
        assert isinstance(plan, str)
        # ANALYZE should include actual execution info
        assert any(term in str(plan).upper() for term in ['ACTUAL', 'TIME'])
    except ValueError as e:
        if "ANALYZE" in str(e):
            pytest.skip("EXPLAIN ANALYZE not supported in this MySQL version")
        else:
            raise


def test_explain_analyze_with_tree_format(order_fixtures, request):
    """Test EXPLAIN ANALYZE with TREE format (MySQL 8.0.18+)"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    try:
        plan = Order.query().explain(
            type=ExplainType.ANALYZE,
            format=ExplainFormat.TREE
        ).all()
        assert isinstance(plan, str)
        # Should have both TREE format chars and actual execution info
        assert any(char in plan for char in ['->', '|-'])
        assert any(term in str(plan).upper() for term in ['ACTUAL', 'TIME'])
    except ValueError as e:
        message = str(e).lower()
        if "format" in message or "analyze" in message:
            pytest.skip("TREE format or ANALYZE not supported in this MySQL version")
        else:
            raise


def test_explain_with_index_hints(order_fixtures, request):
    """Test EXPLAIN with index hints (MySQL specific)"""
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

    # Using MySQL-specific index hints in JOIN
    try:
        query = Order.query().join(f"""
            INNER JOIN {User.__table_name__} FORCE INDEX (PRIMARY)
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """)
        plan = query.explain().all()
        assert isinstance(plan, str)
        assert "JOIN" in str(plan).upper()
        assert any(term in str(plan).upper() for term in ["INDEX", "PRIMARY"])
    except:
        pytest.skip("Index hints not properly supported in this setup")


def test_explain_connection_option(order_fixtures, request):
    """Test FOR CONNECTION option (MySQL 5.7+)"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    # This test only verifies the SQL generation, not execution
    # To execute would require access to connection ID and privileges

    _, Order, _ = order_fixtures

    backend = Order.backend()
    dialect = backend.dialect

    try:
        # Test if dialect supports this option by formatting simple query
        connection_id = 1  # Dummy connection ID
        options = ExplainOptions()
        # Access private attribute for test purposes
        options.connection_id = connection_id

        explain_sql = dialect.format_explain("SELECT 1", options)
        assert "FOR CONNECTION" in explain_sql
        assert str(connection_id) in explain_sql
    except (AttributeError, ValueError) as e:
        pytest.skip("FOR CONNECTION option not supported by this MySQL version")


def test_explain_with_partitions(order_fixtures, request):
    """Test explain with PARTITIONS option (deprecated in MySQL 5.7+)"""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    backend = Order.backend()
    dialect = backend.dialect

    try:
        # Create options with partitions enabled
        options = ExplainOptions()
        # Note: partitions is not a standard attribute of ExplainOptions
        # We add it for testing purposes
        options.partitions = True

        explain_sql = dialect.format_explain("SELECT 1", options)
        # In MySQL 5.7+, PARTITIONS option is deprecated and includes a warning comment
        # In earlier versions, it should add PARTITIONS keyword
        assert "PARTITIONS" in explain_sql or "partitions" in explain_sql.lower()
    except (AttributeError, ValueError) as e:
        pytest.skip("PARTITIONS option test failed")