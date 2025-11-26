# src/rhosocial/activerecord/backend/impl/mysql/__init__.py
"""
MySQL backend implementation for the Python ORM.

This module provides both synchronous and asynchronous MySQL implementations:
- MySQL synchronous backend with connection management and query execution
- MySQL asynchronous backend for async/await workflows
- MySQL-specific connection configuration
- Type mapping and value conversion
- Transaction management with savepoint support (sync and async)
- MySQL dialect and expression handling
- MySQL-specific type definitions and mappings

Architecture:
- MySQLBackend: Synchronous implementation using mysql-connector-python
- AsyncMySQLBackend: Asynchronous implementation using aiomysql
- Both share common logic through MySQLBackendMixin
- Independent from ORM frameworks - uses only native drivers
"""

from .backend import MySQLBackend, AsyncMySQLBackend
from .config import MySQLConnectionConfig
from .dialect import (
    MySQLDialect,
    MySQLExpression,
    MySQLSQLBuilder,
    MySQLAggregateHandler,
    MySQLJsonHandler,
)
from .transaction import MySQLTransactionManager, AsyncMySQLTransactionManager
from .types import (
    MySQLTypes,
    MySQLColumnType,
    MYSQL_TYPE_MAPPINGS,
)


__all__ = [
    # Synchronous Backend
    'MySQLBackend',

    # Asynchronous Backend
    'AsyncMySQLBackend',

    # Configuration
    'MySQLConnectionConfig',

    # Dialect related
    'MySQLDialect',
    'MySQLExpression',
    'MySQLAggregateHandler',
    'MySQLJsonHandler',

    # Transaction - Sync and Async
    'MySQLTransactionManager',
    'AsyncMySQLTransactionManager',

    # Types
    'MySQLTypes',
    'MySQLColumnType',
    'MYSQL_TYPE_MAPPINGS',



    # Builder
    'MySQLSQLBuilder',
]