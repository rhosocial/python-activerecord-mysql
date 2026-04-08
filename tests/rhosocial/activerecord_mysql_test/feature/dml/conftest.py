# tests/rhosocial/activerecord_mysql_test/feature/dml/conftest.py
"""
Configuration for DML feature tests.
"""
import pytest
import pytest_asyncio

# Import fixtures from backend conftest
# The mysql_backend and async_mysql_backend fixtures are defined in
# feature/backend/conftest.py and are automatically discovered by pytest