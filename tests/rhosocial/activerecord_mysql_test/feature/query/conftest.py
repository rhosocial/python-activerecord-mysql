# tests/rhosocial/activerecord_mysql_test/feature/query/conftest.py
"""
Pytest configuration for query feature tests.

This file imports fixtures from the corresponding testsuite, making them
available to the tests in this directory.
"""
import pytest
import pytest_asyncio

# Import fixtures from backend conftest
# The mysql_backend and async_mysql_backend fixtures are defined in
# feature/backend/conftest.py
from rhosocial.activerecord_mysql_test.feature.backend.conftest import (
    mysql_backend,
    mysql_backend_single,
    async_mysql_backend,
    async_mysql_backend_single,
)

from rhosocial.activerecord.testsuite.feature.query.conftest import *
