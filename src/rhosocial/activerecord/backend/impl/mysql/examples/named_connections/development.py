# src/rhosocial/activerecord/backend/impl/mysql/examples/named_connections/development.py
"""Development environment connection examples."""

from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def local_dev():
    """Local development MySQL database connection.

    Connects to localhost with default credentials.
    Useful for local development and testing.

    Returns:
        MySQLConnectionConfig: Development database configuration.
    """
    return MySQLConnectionConfig(
        host="localhost",
        port=3306,
        user="root",
        database="dev",
        autocommit=True,
        init_command=None,
    )


def local_dev_no_auth():
    """Local MySQL connection without authentication.

    For MySQL installations that don't require passwords.

    Returns:
        MySQLConnectionConfig: No-auth database configuration.
    """
    return MySQLConnectionConfig(
        host="localhost",
        port=3306,
        user="root",
        password="",
        database="dev",
        autocommit=True,
        init_command=None,
    )


def test_db():
    """Test database connection.

    Returns:
        MySQLConnectionConfig: Test database configuration.
    """
    return MySQLConnectionConfig(
        host="localhost",
        port=3306,
        user="root",
        database="test",
        autocommit=True,
        get_warnings=True,
    )