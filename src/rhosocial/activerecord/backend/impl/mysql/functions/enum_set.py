# src/rhosocial/activerecord/backend/impl/mysql/functions/enum_set.py
"""
MySQL SET and Enum type function factories.

Functions: find_in_set, elt, field

Every argument except :func:`find_in_set`'s searched value and :func:`elt`'s
index and values is an expression: pass a ``Column`` to read a column and a
``Literal`` to write a value.  Those arguments used to be accepted as bare
strings and numbers, and a bare string became a column reference -- so
``FIELD("b", "a", "b")`` did not report that "b" is the second value but read
columns ``a`` and ``b`` and reported where their *contents* sat, and it did so
without raising when such columns happened to exist.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MySQLDialect


def find_in_set(
    dialect: "MySQLDialect",
    value: str,
    set_column: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a FIND_IN_SET function call.

    Finds the position of a value in a SET column.

    Args:
        dialect: The MySQL dialect instance
        value: The value to find; always a string value, never a column
        set_column: Expression for the SET column to search

    Returns:
        A FunctionCall instance representing FIND_IN_SET

    Version: All MySQL versions
    """
    value_expr = core.Literal(dialect, value)
    return core.FunctionCall(dialect, "FIND_IN_SET", value_expr, set_column)


def elt(
    dialect: "MySQLDialect",
    index: int,
    *values: str,
) -> "core.FunctionCall":
    """
    Creates an ELT function call.

    Returns the N-th element from a list of strings.

    Args:
        dialect: The MySQL dialect instance
        index: 1-based index of the element to return
        *values: List of string values

    Returns:
        A FunctionCall instance representing ELT

    Version: All MySQL versions
    """
    index_expr = core.Literal(dialect, index)
    args = [index_expr]
    for v in values:
        args.append(core.Literal(dialect, v))
    return core.FunctionCall(dialect, "ELT", *args)


def field(
    dialect: "MySQLDialect",
    value: "bases.BaseExpression",
    *values: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a FIELD function call.

    Returns the index (position) of value in the list of values.
    Returns 0 if not found.

    Args:
        dialect: The MySQL dialect instance
        value: Expression for the value to search for
        *values: Expressions for the values to search within

    Returns:
        A FunctionCall instance representing FIELD

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "FIELD", value, *values)


__all__ = [
    "find_in_set",
    "elt",
    "field",
]
