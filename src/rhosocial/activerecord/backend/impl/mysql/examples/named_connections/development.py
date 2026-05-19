# src/rhosocial/activerecord/backend/impl/mysql/examples/named_connections/development.py
"""Development environment connection examples.

All configuration values can be overridden via environment variables:
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
"""

import os

from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def _env_or_default(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int_or_default(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


def local_dev():
    """Local development MySQL database connection.

    Reads connection parameters from environment variables with
    fallback to localhost defaults.

    Returns:
        MySQLConnectionConfig: Development database configuration.
    """
    return MySQLConnectionConfig(
        host=_env_or_default("MYSQL_HOST", "localhost"),
        port=_env_int_or_default("MYSQL_PORT", 3306),
        user=_env_or_default("MYSQL_USER", "root"),
        password=_env_or_default("MYSQL_PASSWORD", ""),
        database=_env_or_default("MYSQL_DATABASE", "dev"),
        autocommit=True,
        init_command=None,
    )


def local_dev_no_auth():
    """Local MySQL connection without authentication.

    Reads connection parameters from environment variables with
    fallback to localhost defaults (empty password).

    Returns:
        MySQLConnectionConfig: No-auth database configuration.
    """
    return MySQLConnectionConfig(
        host=_env_or_default("MYSQL_HOST", "localhost"),
        port=_env_int_or_default("MYSQL_PORT", 3306),
        user=_env_or_default("MYSQL_USER", "root"),
        password=_env_or_default("MYSQL_PASSWORD", ""),
        database=_env_or_default("MYSQL_DATABASE", "dev"),
        autocommit=True,
        init_command=None,
    )


def test_db():
    """Test database connection.

    Reads connection parameters from environment variables with
    fallback to localhost defaults.

    Returns:
        MySQLConnectionConfig: Test database configuration.
    """
    return MySQLConnectionConfig(
        host=_env_or_default("MYSQL_HOST", "localhost"),
        port=_env_int_or_default("MYSQL_PORT", 3306),
        user=_env_or_default("MYSQL_USER", "root"),
        password=_env_or_default("MYSQL_PASSWORD", ""),
        database=_env_or_default("MYSQL_DATABASE", "test"),
        autocommit=True,
        get_warnings=True,
    )