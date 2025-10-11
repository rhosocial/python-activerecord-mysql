# tests/rhosocial/activerecord_mysql_test/query/mysql/test_mysql_explain_window.py
"""Test EXPLAIN functionality with window functions in ActiveQuery."""
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from rhosocial.activerecord_test.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_explain_window_function(order_fixtures, request):
    """Test explain with window functions for MySQL 8.0+."""
    # Skip test if not MySQL
    backend_name = request.node.name.split('-')[0] if hasattr(request, 'node') else ""
    if not backend_name.startswith('mysql'):
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Check MySQL version
    backend = Order.__backend__
    version = backend.get_server_version()

    # Window functions were introduced in MySQL 8.0
    if version < (8, 0, 0):
        pytest.skip(f"MySQL version {version} does not support window functions")

    # Create test data
    user = User(username='window_test', email='window@example.com', age=30)
    user.save()

    # Create several orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'WIN-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test EXPLAIN with window function
    query = Order.query()

    # Create window function expression
    row_num_expr = query.create_expression("ROW_NUMBER() OVER (ORDER BY total_amount DESC)")

    # Build query with window function
    query = (query
             .select("id", "order_number", "total_amount")
             .select_expr(row_num_expr.alias("row_num"))
             .explain()
             .order_by("total_amount DESC"))

    # Execute EXPLAIN plan
    plan = query.all()

    # Verify EXPLAIN output format
    assert isinstance(plan, list)
    plan_text = str(plan)

    # Verify MySQL 8.0+ specific explain output
    # Look for window function processing information
    if version >= (8, 0, 16):
        # In newer MySQL versions, window functions should be mentioned in the plan
        assert any(term in plan_text.lower() for term in ['window', 'filesort', 'temporary', 'sort'])


def test_explain_partitioned_window(order_fixtures, request):
    """Test explain with partitioned window functions for MySQL 8.0+."""
    # Skip test if not MySQL
    backend_name = request.node.name.split('-')[0] if hasattr(request, 'node') else ""
    if not backend_name.startswith('mysql'):
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Check MySQL version
    backend = Order.__backend__
    version = backend.get_server_version()

    # Window functions were introduced in MySQL 8.0
    if version < (8, 0, 0):
        pytest.skip(f"MySQL version {version} does not support window functions")

    # Create test data
    users = []
    for i in range(3):
        user = User(username=f'dept{i + 1}', email=f'dept{i + 1}@example.com', age=30)
        user.save()
        users.append(user)

    # Create orders for each user
    for user in users:
        for i in range(3):
            order = Order(
                user_id=user.id,
                order_number=f'USR{user.id}-{i + 1}',
                total_amount=Decimal(f'{(i + 1) * 100}.00')
            )
            order.save()

    # Test EXPLAIN with partitioned window function
    query = Order.query()

    # Create window function expression with PARTITION BY
    rank_expr = query.create_expression(
        "RANK() OVER (PARTITION BY user_id ORDER BY total_amount DESC)"
    )

    # Build query with window function
    query = (query
             .select("id", "user_id", "order_number", "total_amount")
             .select_expr(rank_expr.alias("user_rank"))
             .explain(format=ExplainFormat.JSON)
             .order_by("user_id", "user_rank"))

    try:
        # Execute EXPLAIN plan with JSON format
        plan = query.all()

        # Verify EXPLAIN JSON output format
        assert isinstance(plan, list)

        # Check for window function information in the JSON explain
        if isinstance(plan[0], dict):
            json_str = str(plan)

            # Look for window operation indicators
            window_terms = ['window', 'sort', 'filesort', 'temporary']
            assert any(term in json_str.lower() for term in window_terms)
    except ValueError as e:
        # This might happen on MySQL versions that don't fully support JSON format with window functions
        assert "format" in str(e).lower()


def test_explain_aggregated_window(order_fixtures, request):
    """Test explain with aggregated window functions for MySQL 8.0+."""
    # Skip test if not MySQL
    backend_name = request.node.name.split('-')[0] if hasattr(request, 'node') else ""
    if not backend_name.startswith('mysql'):
        pytest.skip("This test is only applicable to MySQL")

    User, Order, OrderItem = order_fixtures

    # Check MySQL version
    backend = Order.__backend__
    version = backend.get_server_version()

    # Window functions were introduced in MySQL 8.0
    if version < (8, 0, 0):
        pytest.skip(f"MySQL version {version} does not support window functions")

    # Create test data
    user = User(username='agg_test', email='agg@example.com', age=30)
    user.save()

    # Create orders with different dates
    dates = ["2023-01-15", "2023-02-20", "2023-03-10", "2023-04-05"]
    for i, date in enumerate(dates):
        order = Order(
            user_id=user.id,
            order_number=f'AGG-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00'),
            created_at=date
        )
        order.save()

    # Test EXPLAIN with aggregated window function
    query = Order.query()

    # Create running total window function
    running_sum_expr = query.create_expression(
        "SUM(total_amount) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING)"
    )

    # Build query with aggregated window function
    query = (query
             .select("id", "created_at", "total_amount")
             .select_expr(running_sum_expr.alias("running_total"))
             .explain(type=ExplainType.ANALYZE if version >= (8, 0, 18) else ExplainType.BASIC)
             .order_by("created_at"))

    # Execute EXPLAIN plan
    plan = query.all()

    # Verify EXPLAIN output
    assert isinstance(plan, list)
    plan_text = str(plan)

    # Verify MySQL 8.0+ specific explain output for window aggregates
    # Look for window function processing information
    assert any(term in plan_text.lower() for term in ['sort', 'aggregate', 'filesort', 'temporary'])

    # If it's ANALYZE output, it should contain execution information
    if version >= (8, 0, 18):
        assert any(term in plan_text.lower() for term in ['actual', 'rows', 'time'])