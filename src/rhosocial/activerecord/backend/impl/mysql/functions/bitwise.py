# src/rhosocial/activerecord/backend/impl/mysql/functions/bitwise.py
"""
MySQL Bitwise function factories.

Functions: bit_and, bit_or, bit_xor, bit_count, bit_get_bit,
           bit_shift_left, bit_shift_right

Note: MySQL 9.6 does not support BIT_GET_BIT, BIT_SHIFT_LEFT, BIT_SHIFT_RIGHT
as functions. These are implemented using native bitwise operators.
"""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core, NumericColumn
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MySQLDialect


def bit_and(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
    *values: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Returns the bitwise AND of values.

    Note: MySQL's BIT_AND() is an aggregate function. For scalar bitwise AND,
    this function returns (value & values[0] & values[1] ...).

    Args:
        dialect: The MySQL dialect instance
        value: First value
        *values: Additional values to AND

    Returns:
        An expression representing bitwise AND

    Version: MySQL 5.0.12+ (aggregate), native operators available in all versions
    """
    result = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    for v in values:
        v_expr = (
            v if isinstance(v, bases.BaseExpression)
            else core.Literal(dialect, v) if isinstance(v, (int, float))
            else NumericColumn(dialect, v)
        )
        result = BinaryArithmeticExpression(dialect, "&", result, v_expr)
    return result


def bit_or(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
    *values: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Returns the bitwise OR of values.

    Note: MySQL's BIT_OR() is an aggregate function. For scalar bitwise OR,
    this function returns (value | values[0] | values[1] ...).

    Args:
        dialect: The MySQL dialect instance
        value: First value
        *values: Additional values to OR

    Returns:
        An expression representing bitwise OR

    Version: MySQL 5.0.12+ (aggregate), native operators available in all versions
    """
    result = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    for v in values:
        v_expr = (
            v if isinstance(v, bases.BaseExpression)
            else core.Literal(dialect, v) if isinstance(v, (int, float))
            else NumericColumn(dialect, v)
        )
        result = BinaryArithmeticExpression(dialect, "|", result, v_expr)
    return result


def bit_xor(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
    *values: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Returns the bitwise XOR of values.

    Note: MySQL's BIT_XOR() is an aggregate function. For scalar bitwise XOR,
    this function returns (value ^ values[0] ^ values[1] ...).

    Args:
        dialect: The MySQL dialect instance
        value: First value
        *values: Additional values to XOR

    Returns:
        An expression representing bitwise XOR

    Version: MySQL 5.0.12+ (aggregate), native operators available in all versions
    """
    result = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    for v in values:
        v_expr = (
            v if isinstance(v, bases.BaseExpression)
            else core.Literal(dialect, v) if isinstance(v, (int, float))
            else NumericColumn(dialect, v)
        )
        result = BinaryArithmeticExpression(dialect, "^", result, v_expr)
    return result


def bit_count(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Returns the number of bits set to 1 in the binary representation.

    Args:
        dialect: The MySQL dialect instance
        value: Column or expression to count bits

    Returns:
        A FunctionCall instance representing BIT_COUNT(expr)

    Version: MySQL 5.0.12+
    """
    value_expr = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    return core.FunctionCall(dialect, "BIT_COUNT", value_expr)


def bit_get_bit(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
    bit: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Returns the value of a specific bit (0 or 1).

    Note: MySQL does not have a BIT_GET_BIT function in all versions.
    This is implemented as ((value >> bit) & 1).

    Args:
        dialect: The MySQL dialect instance
        value: The value to get the bit from
        bit: The bit position (0-indexed)

    Returns:
        An expression representing the bit value (0 or 1)

    Version: Native operators available in all MySQL versions
    """
    value_expr = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    bit_expr = (
        bit if isinstance(bit, bases.BaseExpression)
        else core.Literal(dialect, bit) if isinstance(bit, (int, float))
        else NumericColumn(dialect, bit)
    )
    # (value >> bit) & 1
    shifted = BinaryArithmeticExpression(dialect, ">>", value_expr, bit_expr)
    return BinaryArithmeticExpression(dialect, "&", shifted, core.Literal(dialect, 1))


def bit_shift_left(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
    count: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Returns the value left-shifted by count bits.

    Note: MySQL does not have BIT_SHIFT_LEFT function in all versions.
    This is implemented using the native << operator.

    Args:
        dialect: The MySQL dialect instance
        value: The value to shift
        count: Number of positions to shift

    Returns:
        An expression representing the left-shifted value

    Version: Native operators available in all MySQL versions
    """
    value_expr = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    count_expr = (
        count if isinstance(count, bases.BaseExpression)
        else core.Literal(dialect, count) if isinstance(count, (int, float))
        else NumericColumn(dialect, count)
    )
    return BinaryArithmeticExpression(dialect, "<<", value_expr, count_expr)


def bit_shift_right(
    dialect: "MySQLDialect",
    value: Union[str, int, "bases.BaseExpression"],
    count: Union[str, int, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Returns the value right-shifted by count bits.

    Note: MySQL does not have BIT_SHIFT_RIGHT function in all versions.
    This is implemented using the native >> operator.

    Args:
        dialect: The MySQL dialect instance
        value: The value to shift
        count: Number of positions to shift

    Returns:
        An expression representing the right-shifted value

    Version: Native operators available in all MySQL versions
    """
    value_expr = (
        value if isinstance(value, bases.BaseExpression)
        else core.Literal(dialect, value) if isinstance(value, (int, float))
        else NumericColumn(dialect, value)
    )
    count_expr = (
        count if isinstance(count, bases.BaseExpression)
        else core.Literal(dialect, count) if isinstance(count, (int, float))
        else NumericColumn(dialect, count)
    )
    return BinaryArithmeticExpression(dialect, ">>", value_expr, count_expr)


__all__ = [
    "bit_and",
    "bit_or",
    "bit_xor",
    "bit_count",
    "bit_get_bit",
    "bit_shift_left",
    "bit_shift_right",
]
