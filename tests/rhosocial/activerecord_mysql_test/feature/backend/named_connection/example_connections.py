# tests/rhosocial/activerecord_mysql_test/feature/backend/named_connection/example_connections.py
"""
Example named connections for MySQL testing.

This module contains sample connection definitions for testing
the named connection functionality with MySQL backend.
"""
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def mysql_96(database: str = "test_db"):
    """MySQL 9.6 development server connection."""
    return MySQLConnectionConfig(
        host="db-dev-1-n.rho.im",
        port=13694,
        database=database,
        username="root",
        password="password",
        charset="utf8mb4",
        autocommit=True,
        ssl_verify_cert=False,
        init_command="SET time_zone = '+00:00'",
    )


def mysql_96_with_pool(pool_size: int = 5):
    """MySQL 9.6 connection with custom pool size."""
    if isinstance(pool_size, str):
        pool_size = int(pool_size)
    return MySQLConnectionConfig(
        host="db-dev-1-n.rho.im",
        port=13694,
        database="test_db",
        username="root",
        password="password",
        charset="utf8mb4",
        autocommit=True,
        ssl_verify_cert=False,
        init_command="SET time_zone = '+00:00'",
        pool_size=pool_size,
    )


def mysql_96_readonly():
    """MySQL 9.6 read-only connection (shorter timeout)."""
    return MySQLConnectionConfig(
        host="db-dev-1-n.rho.im",
        port=13694,
        database="test_db",
        username="root",
        password="password",
        charset="utf8mb4",
        autocommit=True,
        ssl_verify_cert=False,
        init_command="SET time_zone = '+00:00'",
        pool_timeout=10,
    )
