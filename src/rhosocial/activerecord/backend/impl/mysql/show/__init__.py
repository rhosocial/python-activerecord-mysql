# src/rhosocial/activerecord/backend/impl/mysql/show/__init__.py
"""
MySQL SHOW functionality module.

This module provides MySQL-specific SHOW command support:
- Expression classes for SHOW commands
- Dialect mixin for SQL generation
- Functionality classes for executing SHOW commands
- Backend mixins for show() method

Usage:
    # Via backend
    result = backend.show().create_table("users")
    columns = backend.show().columns("users", full=True)
    indexes = backend.show().indexes("users")
    tables = backend.show().tables()
    databases = backend.show().databases()
"""

from .expressions import (
    ShowExpression,
    ShowCreateTableExpression,
    ShowCreateViewExpression,
    ShowColumnsExpression,
    ShowIndexExpression,
    ShowTablesExpression,
    ShowDatabasesExpression,
    ShowTableStatusExpression,
    ShowTriggersExpression,
    ShowCreateTriggerExpression,
    ShowVariablesExpression,
    ShowStatusExpression,
    ShowProcessListExpression,
    ShowWarningsExpression,
    ShowErrorsExpression,
    ShowEnginesExpression,
    ShowCharsetExpression,
    ShowCollationExpression,
    ShowGrantsExpression,
    ShowPluginsExpression,
)
from .dialect import MySQLShowDialectMixin
from .functionality import MySQLShowFunctionality, AsyncMySQLShowFunctionality
from .backend_mixin import MySQLShowMixin, AsyncMySQLShowMixin

__all__ = [
    # Expression classes
    "ShowExpression",
    "ShowCreateTableExpression",
    "ShowCreateViewExpression",
    "ShowColumnsExpression",
    "ShowIndexExpression",
    "ShowTablesExpression",
    "ShowDatabasesExpression",
    "ShowTableStatusExpression",
    "ShowTriggersExpression",
    "ShowCreateTriggerExpression",
    "ShowVariablesExpression",
    "ShowStatusExpression",
    "ShowProcessListExpression",
    "ShowWarningsExpression",
    "ShowErrorsExpression",
    "ShowEnginesExpression",
    "ShowCharsetExpression",
    "ShowCollationExpression",
    "ShowGrantsExpression",
    "ShowPluginsExpression",
    # Dialect mixin
    "MySQLShowDialectMixin",
    # Functionality classes
    "MySQLShowFunctionality",
    "AsyncMySQLShowFunctionality",
    # Backend mixins
    "MySQLShowMixin",
    "AsyncMySQLShowMixin",
]
