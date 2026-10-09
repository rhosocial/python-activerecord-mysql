# src/rhosocial/activerecord/backend/impl/mysql/functions/math_enhanced.py
"""
MySQL enhanced math function factories.

Additional mathematical functions beyond the basic math module.
Includes: round, pow, power, sqrt, mod, ceil, floor, truncate, max, min, avg

Functions: round_, pow, power, sqrt, mod, ceil, floor, trunc, max_, min_, avg

Every value argument is an expression: a ``Column`` -- or the ``NumericColumn``
that says the argument is a number -- to read a column, and a ``Literal`` to
write a value.  Those arguments used to be accepted as bare strings and numbers,
and the factory decided at run time which was which -- including parsing a
numeric-looking string into the number it spelled, so ``sqrt(dialect, "16")``
computed sqrt(16)=4.0 instead of reading a column called ``16``.  A string is a
column name here, as it is everywhere else in this backend; a value is a
``Literal``, which also reaches the server as a bound parameter rather than as
quoted SQL text.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def round_(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
    precision: int = 0,
) -> "core.FunctionCall":
    """
    Creates a ROUND function call.

    Rounds a numeric value to the specified number of decimal places.

    Usage:
        - round_(dialect, NumericColumn(dialect, "price")) -> ROUND(`price`, 0)
        - round_(dialect, NumericColumn(dialect, "price"), 2) -> ROUND(`price`, 2)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to round
        precision: Number of decimal places (default 0)

    Returns:
        A FunctionCall instance representing the ROUND function

    Version: All MySQL versions
    """
    precision_expr = core.Literal(dialect, precision)
    return core.FunctionCall(dialect, "ROUND", expr, precision_expr)


def pow(
    dialect: "SQLDialectBase",
    base: "bases.BaseExpression",
    exponent: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a POW function call.

    Returns the value of base raised to the power of exponent.

    Usage:
        - pow(dialect, Literal(dialect, 2), Literal(dialect, 3)) -> POW(2, 3)
        - pow(dialect, NumericColumn(dialect, "x"), Literal(dialect, 2)) -> POW(`x`, 2)

    Args:
        dialect: The SQL dialect instance
        base: The base expression
        exponent: The exponent expression

    Returns:
        A FunctionCall instance representing the POW function

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "POW", base, exponent)


def power(
    dialect: "SQLDialectBase",
    base: "bases.BaseExpression",
    exponent: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a POWER function call (alias for POW).

    Returns the value of base raised to the power of exponent.

    Usage:
        - power(dialect, Literal(dialect, 2), Literal(dialect, 3)) -> POWER(2, 3)
        - power(dialect, NumericColumn(dialect, "x"), NumericColumn(dialect, "y"))
          -> POWER(`x`, `y`)

    Args:
        dialect: The SQL dialect instance
        base: The base expression
        exponent: The exponent expression

    Returns:
        A FunctionCall instance representing the POWER function

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "POWER", base, exponent)


def sqrt(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a SQRT function call.

    Returns the square root of the argument.

    Usage:
        - sqrt(dialect, Literal(dialect, 16)) -> SQRT(16)
        - sqrt(dialect, NumericColumn(dialect, "value")) -> SQRT(`value`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SQRT function

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "SQRT", expr)


def mod(
    dialect: "SQLDialectBase",
    dividend: "bases.BaseExpression",
    divisor: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a MOD function call.

    Returns the remainder of dividend divided by divisor.

    Usage:
        - mod(dialect, Literal(dialect, 10), Literal(dialect, 3)) -> MOD(10, 3)
        - mod(dialect, NumericColumn(dialect, "total"), Literal(dialect, 10))
          -> MOD(`total`, 10)

    Args:
        dialect: The SQL dialect instance
        dividend: The dividend expression
        divisor: The divisor expression

    Returns:
        A FunctionCall instance representing the MOD function

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "MOD", dividend, divisor)


def ceil(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a CEIL function call.

    Returns the smallest integer value not less than the argument.

    Usage:
        - ceil(dialect, Literal(dialect, 3.14)) -> CEIL(3.14)
        - ceil(dialect, NumericColumn(dialect, "price")) -> CEIL(`price`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the CEIL function

    Version: All MySQL versions (CEILING is also available as alias)
    """
    return core.FunctionCall(dialect, "CEIL", expr)


def floor(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a FLOOR function call.

    Returns the largest integer value not greater than the argument.

    Usage:
        - floor(dialect, Literal(dialect, 3.14)) -> FLOOR(3.14)
        - floor(dialect, NumericColumn(dialect, "price")) -> FLOOR(`price`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the FLOOR function

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "FLOOR", expr)


def trunc(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
    precision: int = 0,
) -> "core.FunctionCall":
    """
    Creates a TRUNCATE function call.

    Returns the value truncated to the specified number of decimal places.

    Usage:
        - trunc(dialect, Literal(dialect, 3.14)) -> TRUNCATE(3.14, 0)
        - trunc(dialect, Literal(dialect, 3.14), 2) -> TRUNCATE(3.14, 2)
        - trunc(dialect, NumericColumn(dialect, "price"), 2) -> TRUNCATE(`price`, 2)

    Note:
        MySQL uses TRUNCATE, not TRUNC (which is used by some other databases).

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to truncate
        precision: Number of decimal places (default 0)

    Returns:
        A FunctionCall instance representing the TRUNCATE function

    Version: All MySQL versions
    """
    precision_expr = core.Literal(dialect, precision)
    return core.FunctionCall(dialect, "TRUNCATE", expr, precision_expr)


def max_(
    dialect: "SQLDialectBase",
    *args: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a GREATEST or MAX function call.

    Returns the maximum value from the arguments.

    Usage:
        - max_(dialect, Literal(dialect, 1), Literal(dialect, 5)) -> GREATEST(1, 5)
        - max_(dialect, NumericColumn(dialect, "a"), NumericColumn(dialect, "b"))
          -> GREATEST(`a`, `b`)

    Note:
        When called with a single argument, uses MAX (aggregate).
        When called with multiple arguments, uses GREATEST (scalar).

    Args:
        dialect: The SQL dialect instance
        *args: The expressions to compare

    Returns:
        A FunctionCall instance representing GREATEST or MAX

    Version: All MySQL versions
    """
    if len(args) == 1:
        return core.FunctionCall(dialect, "MAX", args[0])
    return core.FunctionCall(dialect, "GREATEST", *args)


def min_(
    dialect: "SQLDialectBase",
    *args: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates a LEAST or MIN function call.

    Returns the minimum value from the arguments.

    Usage:
        - min_(dialect, Literal(dialect, 1), Literal(dialect, 5)) -> LEAST(1, 5)
        - min_(dialect, NumericColumn(dialect, "a"), NumericColumn(dialect, "b"))
          -> LEAST(`a`, `b`)

    Note:
        When called with a single argument, uses MIN (aggregate).
        When called with multiple arguments, uses LEAST (scalar).

    Args:
        dialect: The SQL dialect instance
        *args: The expressions to compare

    Returns:
        A FunctionCall instance representing LEAST or MIN

    Version: All MySQL versions
    """
    if len(args) == 1:
        return core.FunctionCall(dialect, "MIN", args[0])
    return core.FunctionCall(dialect, "LEAST", *args)


def avg(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "core.FunctionCall":
    """
    Creates an AVG function call.

    Returns the average value of the argument.

    Usage:
        - avg(dialect, NumericColumn(dialect, "price")) -> AVG(`price`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the AVG function

    Version: All MySQL versions
    """
    return core.FunctionCall(dialect, "AVG", expr)


__all__ = [
    "round_",
    "pow",
    "power",
    "sqrt",
    "mod",
    "ceil",
    "floor",
    "trunc",
    "max_",
    "min_",
    "avg",
]
