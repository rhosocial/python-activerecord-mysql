# src/rhosocial/activerecord/backend/impl/mysql/expression/system.py
"""MySQL server queries that ask the engine a question, as expression nodes.

These are the statements a MySQL backend runs to learn about *itself* rather
than about a user's schema: the server version, whether the connection still
answers, and the session's own account. They are built here, once, because both
the backend and the status introspector ask them -- and because a caller that
writes ``"SELECT VERSION()"`` as text has bypassed the expression layer, leaving
the command as a string the framework cannot inspect.

Each builder returns a node; the caller renders it with ``to_sql()``. Nothing
here executes anything.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal
from rhosocial.activerecord.backend.expression.statements.dql import QueryStatement

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase

__all__ = ["current_user_query", "ping_query", "version_query"]


def version_query(dialect: "SQLDialectBase") -> BaseExpression:
    """``SELECT VERSION()`` -- the server's own version string.

    No alias: the column label MySQL returns for the bare call is what callers
    read back, and naming it here would rename it for them.
    """
    return QueryStatement(dialect, select=[FunctionCall(dialect, "VERSION")])


def ping_query(dialect: "SQLDialectBase") -> BaseExpression:
    """``SELECT 1`` -- the cheapest question a live connection can answer.

    The literal is inline so the statement carries no parameters at all: a ping
    that needs the driver to bind something tests the driver as well as the
    connection.
    """
    return QueryStatement(dialect, select=[Literal(dialect, 1, inline=True)])


def current_user_query(dialect: "SQLDialectBase") -> BaseExpression:
    """``SELECT CURRENT_USER`` -- the account this session authenticated as.

    Core's node spells the niladic form, so the column label is
    ``CURRENT_USER`` rather than ``CURRENT_USER()``.
    """
    from rhosocial.activerecord.backend.expression.functions.system import CurrentUserFunction

    return QueryStatement(dialect, select=[CurrentUserFunction(dialect)])
