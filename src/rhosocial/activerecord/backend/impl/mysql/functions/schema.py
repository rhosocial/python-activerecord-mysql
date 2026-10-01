# src/rhosocial/activerecord/backend/impl/mysql/functions/schema.py
"""
MySQL schema resolution functions.

Provides a SQL expression factory for asking the server which namespace an
unqualified reference resolves against.

Follows the expression-dialect separation architecture:
- First parameter is always the dialect instance
- Returns an Expression object (FunctionCall)
- Does not concatenate SQL strings directly
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression import core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def current_schema(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """Create a function call for the current schema.

    Returns the current database. MySQL has no schema namespace distinct from
    the database, so this is the namespace an unqualified reference resolves
    against. NULL when no database has been selected.

    Usage:
        - current_schema(dialect)

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance that evaluates to the current schema name
    """
    return core.FunctionCall(dialect, "DATABASE")
