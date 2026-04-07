# tests/rhosocial/activerecord_test/feature/backend/mysql/conftest.py
"""Fixtures for MySQL transaction expression tests."""
import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


@pytest.fixture(scope="function")
def mysql_dialect():
    """Fixture providing MySQLDialect instance for testing transaction expressions."""
    return MySQLDialect()
