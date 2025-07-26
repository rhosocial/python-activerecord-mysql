# tests/rhosocial/activerecord_mysql_test/basic/conftest.py
"""Pytest configuration for MySQL basic functionality tests

This module configures pytest for MySQL backend testing, including
database setup, teardown, and test isolation.
"""

import os
import logging
from pathlib import Path

import pytest

from rhosocial.activerecord_test.utils import get_schema_sql

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_mysql_test_environment():
    """Set up MySQL test environment once per test session"""
    logger.info("Setting up MySQL test environment")

    # Ensure MySQL backend is available
    try:
        import rhosocial.activerecord_mysql
        logger.info("MySQL backend module loaded successfully")
    except ImportError as e:
        pytest.skip(f"MySQL backend not available: {e}")

    yield

    logger.info("Tearing down MySQL test environment")


@pytest.fixture(scope="function", autouse=True)
def setup_mysql_test_database():
    """Set up test database schema before each test function

    This fixture ensures that each test starts with a clean database state
    by recreating the necessary tables from schema files.
    """
    logger.info("Setting up MySQL test database")

    # Get the directory containing schema files
    schema_dir = Path(__file__).parent / "fixtures" / "schema"

    # Determine MySQL version and use appropriate schema
    mysql_version = os.environ.get("MYSQL_VERSION", "mysql80")
    if mysql_version not in ["mysql56", "mysql80"]:
        mysql_version = "mysql80"  # Default to MySQL 8.0

    schema_path = schema_dir / mysql_version

    # List of required schema files in dependency order
    schema_files = [
        "users.sql",
        "type_cases.sql",
        "type_tests.sql",
        "validated_users.sql",
        "validated_field_users.sql",
    ]

    try:
        # Import MySQL backend and get connection
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
        from rhosocial.activerecord_mysql_test.utils import get_test_database_config

        # Get test database configuration
        db_config = get_test_database_config()
        backend = MySQLBackend(db_config)

        # Drop existing tables first (in reverse order to handle dependencies)
        for schema_file in reversed(schema_files):
            table_name = schema_file.replace('.sql', '')
            try:
                backend.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                logger.debug(f"Dropped table {table_name}")
            except Exception as e:
                logger.warning(f"Could not drop table {table_name}: {e}")

        # Create tables from schema files
        for schema_file in schema_files:
            schema_file_path = schema_path / schema_file
            if schema_file_path.exists():
                schema_sql = get_schema_sql(str(schema_file_path))
                backend.execute(schema_sql)
                logger.debug(f"Created table from {schema_file}")
            else:
                logger.warning(f"Schema file not found: {schema_file_path}")

        logger.info(f"MySQL test database setup completed using {mysql_version} schema")

    except Exception as e:
        logger.error(f"Failed to set up MySQL test database: {e}")
        pytest.skip(f"Cannot set up MySQL test database: {e}")

    yield

    # Cleanup after test (optional, as next test will recreate)
    logger.debug("MySQL test database cleanup completed")


@pytest.fixture(scope="function")
def mysql_test_backend():
    """Provide MySQL backend instance for direct testing

    This fixture provides access to the MySQL backend for tests that need
    to perform direct database operations.
    """
    try:
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
        from rhosocial.activerecord_mysql_test.utils import get_test_database_config

        db_config = get_test_database_config()
        backend = MySQLBackend(db_config)

        yield backend

    except Exception as e:
        pytest.skip(f"MySQL backend not available: {e}")


@pytest.fixture(scope="function")
def mysql_test_connection():
    """Provide direct MySQL connection for low-level testing

    This fixture provides direct access to the MySQL connection for tests
    that need to perform database-specific operations.
    """
    try:
        from rhosocial.activerecord_mysql_test.utils import get_test_database_config
        import mysql.connector

        db_config = get_test_database_config()
        connection = mysql.connector.connect(**db_config)

        yield connection

        connection.close()

    except Exception as e:
        pytest.skip(f"MySQL connection not available: {e}")


# Configure pytest markers for MySQL-specific tests
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "mysql: mark test as MySQL-specific"
    )
    config.addinivalue_line(
        "markers", "mysql56: mark test as MySQL 5.6 specific"
    )
    config.addinivalue_line(
        "markers", "mysql80: mark test as MySQL 8.0 specific"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Add mysql marker to all tests in this module
        if "mysql_test" in str(item.fspath):
            item.add_marker(pytest.mark.mysql)

        # Add specific version markers
        if "mysql56" in item.name or "mysql56" in str(item.fspath):
            item.add_marker(pytest.mark.mysql56)
        elif "mysql80" in item.name or "mysql80" in str(item.fspath):
            item.add_marker(pytest.mark.mysql80)

        # Add slow marker for tests that might be time-consuming
        if any(keyword in item.name for keyword in ["transaction", "large", "performance"]):
            item.add_marker(pytest.mark.slow)