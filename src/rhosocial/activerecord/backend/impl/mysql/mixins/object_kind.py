# src/rhosocial/activerecord/backend/impl/mysql/mixins/object_kind.py
"""The object-kind check the formatters share.

Every statement in this backend names at least one catalogue object, and every
object renders itself: a ``Table`` has its own ``format_table_object``, a
``Database`` its own ``format_database_object``. That is what makes a qualified
name work without this dialect assembling a prefix, and it is also why a wrong
kind used to render quietly.

``CreateDatabaseExpression(dialect, Table(dialect, "users"))`` reached
``format_database_object`` -- the ``Table``'s own method -- and produced
``CREATE DATABASE `users```: well-formed SQL naming something other than what
the caller asked for. No error, no warning, and a statement the server would
happily run.

The check belongs in the formatter rather than the constructor because objects
are routinely built before a dialect is settled. The testsuite's foreign-key
fixture is ``Table(None, "ddl_spec_orders")``, and serialization rebuilds
objects too, so a constructor-time check would fire on objects that are simply
not finished yet. Rendering is the earliest point at which the dialect is known
*and* the slots are filled.

The message is deliberately identical in shape to core's, which writes the same
check out inline:

    CreateDatabaseExpression.database must be a Database, got Table

Matching the wording means a caller who reads one dialect's error can read
every dialect's, and a test may assert on it without knowing which dialect
rendered the statement.
"""

from typing import Any, Type, TypeVar

__all__ = ["require_kind"]

_CatalogueObject = TypeVar("_CatalogueObject")


def require_kind(
    value: Any, kind: Type[_CatalogueObject], label: str
) -> _CatalogueObject:
    """Return *value* when it is a *kind*, and refuse it when it is not.

    Args:
        value: The object a formatter was handed.
        kind: The class that object must be an instance of.
        label: How to name the slot in the message, as
            ``Expression.attribute``. The attribute is part of the message
            because the same object is often reachable from several places and
            the caller needs to know which one was wrong.

    Returns:
        *value*, so a formatter can write
        ``table = require_kind(expr.table, Table, "SomeExpression.table")``
        and keep the narrowed type.

    Raises:
        TypeError: *value* is not a *kind*. The message says what was expected
            and what arrived, because a rendered identifier is enough for the
            engine to accept and not enough for the reader to notice.
    """
    if not isinstance(value, kind):
        raise TypeError(
            f"{label} must be a {kind.__name__}, got {type(value).__name__}"
        )
    return value