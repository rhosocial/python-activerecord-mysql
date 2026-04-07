# tests/rhosocial/activerecord_mysql_test/feature/query/connection/test_active_query_context.py
"""
ActiveQuery Context Test Module for MySQL backend.

This module imports and runs the shared tests from the testsuite package,
ensuring MySQL backend compatibility for ActiveQuery connection pool context awareness.
"""
from rhosocial.activerecord.testsuite.feature.query.connection.conftest import (
    sync_pool_and_model,
    async_pool_and_model,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.query.connection.test_active_query_context import *
