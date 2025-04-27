"""
MySQL backend implementation for the Python ORM.

This module provides a MySQL-specific implementation including:
- MySQL backend with connection management and query execution
- Type mapping and value conversion
- Transaction management with savepoint support
- MySQL dialect and expression handling
- MySQL-specific type definitions and mappings
"""

__version__ = "1.0.0.dev2"

from .backend import MySQLBackend
from .dialect import (
    MySQLDialect,
    MySQLExpression,
    MySQLSQLBuilder,
    MySQLAggregateHandler,
    MySQLJsonHandler,
)
from .transaction import MySQLTransactionManager
from .types import (
    MySQLTypes,
    MySQLColumnType,
    MYSQL_TYPE_MAPPINGS,
)

__all__ = [
    # Backend
    'MySQLBackend',

    # Dialect related
    'MySQLDialect',
    'MySQLExpression',
    'MySQLAggregateHandler',  # Add MySQLAggregateHandler
    'MySQLJsonHandler',  # Add MySQLJsonHandler

    # Transaction
    'MySQLTransactionManager',

    # Types
    'MySQLTypes',
    'MySQLColumnType',
    'MYSQL_TYPE_MAPPINGS',

    # Builder
    'MySQLSQLBuilder',
]