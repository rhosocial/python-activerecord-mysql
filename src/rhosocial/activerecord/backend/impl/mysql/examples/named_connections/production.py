# src/rhosocial/activerecord/backend/impl/mysql/examples/named_connections/production.py
"""Production environment connection examples."""

from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def prod_db():
    """Production MySQL database connection.

    Connects to production database server with SSL enabled.

    Returns:
        MySQLConnectionConfig: Production database configuration.
    """
    return MySQLConnectionConfig(
        host="prod-mysql.example.com",
        port=3306,
        user="app_user",
        database="production",
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
        host="prod-mysql.example.com",
        port=3306,
        user="app_user",
        database="production",
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
        host="prod-mysql-replica.example.com",
        port=3306,
        user="app_user",
        database="production",
        autocommit=True,
    )