# src/rhosocial/activerecord/backend/impl/mysql/examples/named_connections/production.py
"""Production environment connection examples.

All configuration values can be overridden via environment variables:
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
"""

import os

from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def _env_or_default(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int_or_default(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


def prod_db():
    """Production MySQL database connection.

    Reads connection parameters from environment variables with
    fallback to example.com documentation defaults.

    Returns:
        MySQLConnectionConfig: Production database configuration.
    """
    return MySQLConnectionConfig(
        host=_env_or_default("MYSQL_HOST", "prod-mysql.example.com"),
        port=_env_int_or_default("MYSQL_PORT", 3306),
        user=_env_or_default("MYSQL_USER", "app_user"),
        password=_env_or_default("MYSQL_PASSWORD", ""),
        database=_env_or_default("MYSQL_DATABASE", "production"),
        autocommit=True,
        init_command="SET sql_mode='STRICT_TRANS_TABLES'",
        ssl_enabled=True,
    )


def prod_db_ssl():
    """Production MySQL database with full SSL verification.

    Uses SSL with certificate verification for secure
    production connections.

    Returns:
        MySQLConnectionConfig: SSL-verified database configuration.
    """
    return MySQLConnectionConfig(
        host=_env_or_default("MYSQL_HOST", "prod-mysql.example.com"),
        port=_env_int_or_default("MYSQL_PORT", 3306),
        user=_env_or_default("MYSQL_USER", "app_user"),
        password=_env_or_default("MYSQL_PASSWORD", ""),
        database=_env_or_default("MYSQL_DATABASE", "production"),
        autocommit=True,
        init_command="SET sql_mode='STRICT_TRANS_TABLES'",
        ssl_enabled=True,
        ssl_verify_server_cert=True,
    )


def prod_replica():
    """Production MySQL read replica connection.

    For read-heavy workloads, connect to a read replica
    to distribute load.

    Returns:
        MySQLConnectionConfig: Read replica database configuration.
    """
    return MySQLConnectionConfig(
        host=_env_or_default("MYSQL_REPLICA_HOST", "prod-mysql-replica.example.com"),
        port=_env_int_or_default("MYSQL_REPLICA_PORT", 3306),
        user=_env_or_default("MYSQL_REPLICA_USER", "app_user"),
        password=_env_or_default("MYSQL_REPLICA_PASSWORD", ""),
        database=_env_or_default("MYSQL_DATABASE", "production"),
        autocommit=True,
    )