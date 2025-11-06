# tests/rhosocial/activerecord_mysql_test/feature/query/test_basic.py
"""
Basic query functionality tests for MySQL backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MySQL backend compatibility.
"""
# IMPORTANT: These imports are essential for pytest to work correctly.
# Even though they may be flagged as "unused" by some IDEs or linters,
# they must not be removed. They are the mechanism by which pytest discovers
# the fixtures and the tests from the external testsuite package.

# Although the root conftest.py sets up the environment, explicitly importing
# the fixtures here makes the dependency clear and can help with test discovery
# in some IDEs. These fixtures are defined in the testsuite package and are
# parameterized to run against the scenarios defined in `providers/scenarios.py`.
from rhosocial.activerecord.testsuite.feature.query.conftest import (
    order_fixtures,
    blog_fixtures,
    tree_fixtures,
    combined_fixtures,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.query.test_basic import *