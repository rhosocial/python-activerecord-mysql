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
- MySQL-specific type helpers (ENUM, SET)
- MySQL-specific SQL function factories (JSON, spatial, full-text, etc.)

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
from .types import MySQLEnumType, MySQLSetType

# Import MySQL-specific functions directly for convenience
from .functions import (
    # JSON functions
    json_extract,
    json_unquote,
    json_object,
    json_array,
    json_contains,
    json_set,
    json_remove,
    json_type,
    json_valid,
    json_search,
    # Spatial functions
    st_geom_from_text,
    st_geom_from_wkb,
    st_as_text,
    st_as_geojson,
    st_distance,
    st_within,
    st_contains,
    st_intersects,
    # Full-text search
    match_against,
    # SET type functions
    find_in_set,
    # Enum type functions
    elt,
    field,
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

    # Transaction - Sync and Async
    'MySQLTransactionManager',
    'AsyncMySQLTransactionManager',

    # MySQL-specific Type Helpers
    'MySQLEnumType',
    'MySQLSetType',

    # MySQL-specific Functions - JSON
    'json_extract',
    'json_unquote',
    'json_object',
    'json_array',
    'json_contains',
    'json_set',
    'json_remove',
    'json_type',
    'json_valid',
    'json_search',

    # MySQL-specific Functions - Spatial
    'st_geom_from_text',
    'st_geom_from_wkb',
    'st_as_text',
    'st_as_geojson',
    'st_distance',
    'st_within',
    'st_contains',
    'st_intersects',

    # MySQL-specific Functions - Full-text Search
    'match_against',

    # MySQL-specific Functions - SET/Enum
    'find_in_set',
    'elt',
    'field',
]