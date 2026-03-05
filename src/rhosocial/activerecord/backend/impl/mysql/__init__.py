# src/rhosocial/activerecord/backend/impl/mysql/__init__.py
"""
MySQL backend implementation for the Python ORM.

This module provides:
- MySQL synchronous backend with connection management and query execution
- MySQL asynchronous backend with async/await support
- MySQL-specific connection configuration
- Type mapping and value conversion
- Transaction management with savepoint support (sync and async)
- MySQL dialect and expression handling

Architecture:
- MySQLBackend: Synchronous implementation using mysql-connector-python
- AsyncMySQLBackend: Asynchronous implementation using aiomysql
- Independent from ORM frameworks - uses only native drivers
"""

from .backend import MySQLBackend
from .async_backend import AsyncMySQLBackend
from .config import MySQLConnectionConfig
from .dialect import MySQLDialect
from .transaction import MySQLTransactionManager
from .async_transaction import AsyncMySQLTransactionManager


__all__ = [
    # Synchronous Backend
    'MySQLBackend',

    # Asynchronous Backend
    'AsyncMySQLBackend',

    # Configuration
    'MySQLConnectionConfig',

    # Dialect related
    'MySQLDialect',

    # Transaction - Sync and Async
    'MySQLTransactionManager',
    'AsyncMySQLTransactionManager',
]