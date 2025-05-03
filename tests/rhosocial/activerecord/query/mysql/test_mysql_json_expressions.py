"""Test JSON expression functionality in ActiveQuery for MySQL."""
import json

import pytest

from tests.rhosocial.activerecord.query.utils import create_json_test_fixtures

# Create multi-table test fixtures
json_fixtures = create_json_test_fixtures()


@pytest.fixture(scope="function")
def skip_if_not_mysql(request):
    """Skip tests if not using MySQL backend."""
    if 'mysql' not in request.node.name:
        pytest.skip("This test is only applicable to MySQL")


def test_explain_json_expressions(json_fixtures, skip_if_not_mysql):
    """Test explain functionality with JSON expressions for MySQL."""
    User = json_fixtures[0]

    # Create test user with JSON data
    user = User(
        username='test_user',
        email='test@example.com',
        settings=json.dumps({
            "theme": "dark",
            "notifications": {"email": True}
        })
    )
    user.save()

    try:
        # Test explain with JSON extract
        query = User.query()
        query.json_expr('settings', '$.theme', alias='theme')

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        # MySQL explain output typically includes 'select_type', 'table', 'type' etc.
        assert any(op in plan for op in ['select_type', 'table', 'type', 'possible_keys'])

        # Test explain with JSON in WHERE clause
        query = User.query()
        query.where("json_extract(settings, '$.theme') = 'dark'")

        plan = query.explain().all()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['select_type', 'table', 'type', 'possible_keys'])

        # Test explain with JSON in GROUP BY
        query = User.query()
        query.select("json_extract(settings, '$.theme') as theme")
        query.count("*", "user_count")
        query.group_by("json_extract(settings, '$.theme')")

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['select_type', 'table', 'type', 'possible_keys', 'Extra'])
    except Exception as e:
        if 'does not support JSON' in str(e).lower():
            pytest.skip("MySQL version doesn't support JSON functions")
        raise