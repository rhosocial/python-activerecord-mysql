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

from ..expression.show import (
    ShowExpression,
    ShowCreateTableStatement,
    ShowCreateViewStatement,
    ShowColumnsStatement,
    ShowIndexStatement,
    ShowTablesStatement,
    ShowDatabasesStatement,
    ShowTableStatusStatement,
    ShowTriggersStatement,
    ShowCreateTriggerStatement,
    ShowVariablesStatement,
    ShowStatusStatement,
    ShowProcessListStatement,
    ShowWarningsStatement,
    ShowErrorsStatement,
    ShowEnginesStatement,
    ShowCharsetStatement,
    ShowCollationStatement,
    ShowGrantsStatement,
    ShowPluginsStatement,
    ShowBinaryLogsStatement,
    ShowMasterStatusStatement,
    ShowSlaveStatusStatement,
)
from .dialect import MySQLShowDialectMixin
from .functionality import MySQLShowFunctionality, AsyncMySQLShowFunctionality
from .backend_mixin import MySQLShowMixin, AsyncMySQLShowMixin

__all__ = [
    # Expression classes
    "ShowExpression",
    "ShowCreateTableStatement",
    "ShowCreateViewStatement",
    "ShowColumnsStatement",
    "ShowIndexStatement",
    "ShowTablesStatement",
    "ShowDatabasesStatement",
    "ShowTableStatusStatement",
    "ShowTriggersStatement",
    "ShowCreateTriggerStatement",
    "ShowVariablesStatement",
    "ShowStatusStatement",
    "ShowProcessListStatement",
    "ShowWarningsStatement",
    "ShowErrorsStatement",
    "ShowEnginesStatement",
    "ShowCharsetStatement",
    "ShowCollationStatement",
    "ShowGrantsStatement",
    "ShowPluginsStatement",
    "ShowBinaryLogsStatement",
    "ShowMasterStatusStatement",
    "ShowSlaveStatusStatement",
    # Dialect mixin
    "MySQLShowDialectMixin",
    # Functionality classes
    "MySQLShowFunctionality",
    "AsyncMySQLShowFunctionality",
    # Backend mixins
    "MySQLShowMixin",
    "AsyncMySQLShowMixin",
]
