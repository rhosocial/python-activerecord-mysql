# tests/rhosocial/activerecord_mysql_test/feature/query/test_mysql_datetime_functions.py
"""MySQL-specific datetime function tests."""
import re
from decimal import Decimal
import pytest


def test_mysql_datetime_functions(order_fixtures):
    """Test MySQL-specific datetime functions."""
    from rhosocial.activerecord.query.expression import FunctionExpression

    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with specific timestamps if we have updated_at field
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    try:
        # Test DATE_FORMAT function (MySQL datetime function)
        query = Order.query().where('id = ?', (order.id,))
        query.select_expr(FunctionExpression('DATE_FORMAT', 'created_at', "'%Y-%m-%d'", alias='order_date'))
        results = query.aggregate()[0]

        assert 'order_date' in results
        # Convert to string for consistent comparison across different database drivers
        order_date_str = str(results['order_date'])
        # Verify it's a properly formatted date
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', order_date_str) is not None

        # Test DATE function
        query = Order.query().where('id = ?', (order.id,))
        query.select_expr(FunctionExpression('DATE', 'created_at', alias='order_date_only'))
        results = query.aggregate()[0]

        assert 'order_date_only' in results
        # Convert to string for consistent comparison across different database drivers
        order_date_only_str = str(results['order_date_only'])
        # Should be in YYYY-MM-DD format
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', order_date_only_str) is not None

        # Test current date/time functions
        query = Order.query().where('id = ?', (order.id,))
        query.select_expr(FunctionExpression('CURDATE'))
        results = query.aggregate()[0]

        # The result will be in the first column (without alias), so we get the first value
        result_values = list(results.values())
        assert len(result_values) > 0, "Query should return at least one value"
        result_value = result_values[0]
        assert result_value is not None, "CURDATE function should return a non-null value"
        current_date_str = str(result_value)
        # CURDATE() returns the current date in YYYY-MM-DD format
        # Convert to string for consistent comparison across different database drivers
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', current_date_str) is not None

        # Test NOW() function
        query = Order.query().where('id = ?', (order.id,))
        query.select_expr(FunctionExpression('NOW', alias='current_datetime'))
        results = query.aggregate()[0]

        assert 'current_datetime' in results
        # NOW() returns datetime in YYYY-MM-DD HH:MM:SS format
        # Convert to string for consistent comparison across different database drivers
        current_datetime_str = str(results['current_datetime'])
        assert re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', current_datetime_str) is not None

    except Exception as e:
        # Handle cases where datetime functions are not supported
        if 'FUNCTION' in str(e).upper() and 'does not exist' in str(e):
            pytest.skip(f"MySQL installation doesn't support the tested datetime functions: {e}")
        elif 'no such column' in str(e).lower() and 'created_at' in str(e).lower():
            pytest.skip("Order model doesn't have created_at column")
        raise