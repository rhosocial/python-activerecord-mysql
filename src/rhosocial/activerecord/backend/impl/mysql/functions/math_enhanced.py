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

from typing import TYPE_CHECKING, Any

from rhosocial.activerecord.backend.expression import bases, core
from rhosocial.activerecord.backend.expression.functions import aggregate
from rhosocial.activerecord.backend.expression.functions.math import (
    CeilFunction,
    FloorFunction,
    ModuloFunction,
    PowerFunction,
    RoundFunction,
    SquareRootFunction,
    TruncateFunction,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def _expression_arg(arg: Any, factory: str) -> "bases.BaseExpression":
    """Refuse a bare value where an expression is required.

    A string is a column name in this backend and a value is a ``Literal``,
    so the factories take expressions -- and a bare argument used to fail at
    render time with an ``AttributeError`` nobody could attribute to the
    call. The classed nodes lift bare numbers on their own, but accepting
    that here would loosen the factories' documented contract, and the lift
    would *parse* a numeric-looking string into the number it spells -- the
    exact silent guessing this backend refuses to reintroduce. The refusal
    is at construction now, and it names the factory.
    """
    if not isinstance(arg, bases.BaseExpression):
        raise TypeError(
            f"{factory} takes an expression -- a Column (or the "
            f"NumericColumn that says the argument is a number) to read a "
            f"column, a Literal to write a value -- not {type(arg).__name__}"
        )
    return arg


def round_(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
    precision: int = 0,
) -> "bases.BaseExpression":
    """
    Creates a ROUND function call.

    Rounds a numeric value to the specified number of decimal places.

    Usage:
        - round_(dialect, NumericColumn(dialect, "price")) -> ROUND(`price`, ?)
        - round_(dialect, NumericColumn(dialect, "price"), 2) -> ROUND(`price`, ?)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to round
        precision: Number of decimal places (default 0)

    Returns:
        A ``RoundFunction`` node -- ``RoundIntegerFunction`` when the operand
        is an integer column, because ROUND keeps a whole number whole

    Version: All MySQL versions
    """
    args = [_expression_arg(expr, "round_"), core.Literal(dialect, precision)]
    return RoundFunction.for_operand(dialect, type(expr), *args)


def pow(
    dialect: "SQLDialectBase",
    base: "bases.BaseExpression",
    exponent: "bases.BaseExpression",
) -> PowerFunction:
    """
    Creates a POWER function call.

    Returns the value of base raised to the power of exponent.

    Usage:
        - pow(dialect, Literal(dialect, 2), Literal(dialect, 3)) -> POWER(?, ?)
        - pow(dialect, NumericColumn(dialect, "x"), Literal(dialect, 2)) -> POWER(`x`, ?)

    Args:
        dialect: The SQL dialect instance
        base: The base expression
        exponent: The exponent expression

    Returns:
        A ``PowerFunction`` node. The classed entry point spells ``POWER``,
        which renders where ``POW`` used to; the two are synonyms on MySQL
        (both answer the same value), and the classed node carries the
        standard spelling.

    Version: All MySQL versions
    """
    return PowerFunction(
        dialect,
        _expression_arg(base, "pow"),
        _expression_arg(exponent, "pow"),
    )


def power(
    dialect: "SQLDialectBase",
    base: "bases.BaseExpression",
    exponent: "bases.BaseExpression",
) -> PowerFunction:
    """
    Creates a POWER function call (alias for POW).

    Returns the value of base raised to the power of exponent.

    Usage:
        - power(dialect, Literal(dialect, 2), Literal(dialect, 3)) -> POWER(?, ?)
        - power(dialect, NumericColumn(dialect, "x"), NumericColumn(dialect, "y"))
          -> POWER(`x`, `y`)

    Args:
        dialect: The SQL dialect instance
        base: The base expression
        exponent: The exponent expression

    Returns:
        A ``PowerFunction`` node

    Version: All MySQL versions
    """
    return PowerFunction(
        dialect,
        _expression_arg(base, "power"),
        _expression_arg(exponent, "power"),
    )


def sqrt(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> SquareRootFunction:
    """
    Creates a SQRT function call.

    Returns the square root of the argument.

    Usage:
        - sqrt(dialect, Literal(dialect, 16)) -> SQRT(?)
        - sqrt(dialect, NumericColumn(dialect, "value")) -> SQRT(`value`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A ``SquareRootFunction`` node

    Version: All MySQL versions
    """
    return SquareRootFunction(dialect, _expression_arg(expr, "sqrt"))


def mod(
    dialect: "SQLDialectBase",
    dividend: "bases.BaseExpression",
    divisor: "bases.BaseExpression",
) -> ModuloFunction:
    """
    Creates a MOD function call.

    Returns the remainder of dividend divided by divisor.

    Usage:
        - mod(dialect, Literal(dialect, 10), Literal(dialect, 3)) -> MOD(?, ?)
        - mod(dialect, NumericColumn(dialect, "total"), Literal(dialect, 10))
          -> MOD(`total`, ?)

    Args:
        dialect: The SQL dialect instance
        dividend: The dividend expression
        divisor: The divisor expression

    Returns:
        A ``ModuloFunction`` node

    Version: All MySQL versions
    """
    return ModuloFunction(
        dialect,
        _expression_arg(dividend, "mod"),
        _expression_arg(divisor, "mod"),
    )


def ceil(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """
    Creates a CEIL function call.

    Returns the smallest integer value not less than the argument.

    Usage:
        - ceil(dialect, Literal(dialect, 3.14)) -> CEIL(?)
        - ceil(dialect, NumericColumn(dialect, "price")) -> CEIL(`price`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A ``CeilFunction`` node -- ``CeilIntegerFunction`` when the operand
        is an integer column, because CEIL keeps a whole number whole

    Version: All MySQL versions (CEILING is also available as alias)
    """
    return CeilFunction.for_operand(
        dialect, type(expr), _expression_arg(expr, "ceil")
    )


def floor(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "bases.BaseExpression":
    """
    Creates a FLOOR function call.

    Returns the largest integer value not greater than the argument.

    Usage:
        - floor(dialect, Literal(dialect, 3.14)) -> FLOOR(?)
        - floor(dialect, NumericColumn(dialect, "price")) -> FLOOR(`price`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A ``FloorFunction`` node -- ``FloorIntegerFunction`` when the operand
        is an integer column, because FLOOR keeps a whole number whole

    Version: All MySQL versions
    """
    return FloorFunction.for_operand(
        dialect, type(expr), _expression_arg(expr, "floor")
    )


def trunc(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
    precision: int = 0,
) -> "bases.BaseExpression":
    """
    Creates a TRUNCATE function call.

    Returns the value truncated to the specified number of decimal places.

    Usage:
        - trunc(dialect, Literal(dialect, 3.14)) -> TRUNCATE(?, ?)
        - trunc(dialect, Literal(dialect, 3.14), 2) -> TRUNCATE(?, ?)
        - trunc(dialect, NumericColumn(dialect, "price"), 2) -> TRUNCATE(`price`, ?)

    Note:
        MySQL uses TRUNCATE, not TRUNC (which is used by some other databases).

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to truncate
        precision: Number of decimal places (default 0)

    Returns:
        A ``TruncateFunction`` node -- ``TruncateIntegerFunction`` when the
        operand is an integer column, because TRUNCATE keeps a whole number
        whole

    Version: All MySQL versions
    """
    args = [_expression_arg(expr, "trunc"), core.Literal(dialect, precision)]
    return TruncateFunction.for_operand(dialect, type(expr), *args)


def max_(
    dialect: "SQLDialectBase",
    *args: "bases.BaseExpression",
) -> "bases.BaseExpression":
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

    Only the aggregate half is a classed node: MAX is a standard function, so it
    is a ``MaxFunction``. GREATEST is a MySQL scalar with no standard node of
    its own and stays on the generic call -- the escape hatch.

    Args:
        dialect: The SQL dialect instance
        *args: The expressions to compare

    Returns:
        A MaxFunction for one argument, a FunctionCall for several

    Version: All MySQL versions
    """
    if len(args) == 1:
        return aggregate.MaxFunction(dialect, args[0])
    return core.FunctionCall(dialect, "GREATEST", *args)


def min_(
    dialect: "SQLDialectBase",
    *args: "bases.BaseExpression",
) -> "bases.BaseExpression":
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

    The aggregate half is a ``MinFunction`` and the scalar half stays on the
    generic call, for the reason given on :func:`max_`.

    Args:
        dialect: The SQL dialect instance
        *args: The expressions to compare

    Returns:
        A MinFunction for one argument, a FunctionCall for several

    Version: All MySQL versions
    """
    if len(args) == 1:
        return aggregate.MinFunction(dialect, args[0])
    return core.FunctionCall(dialect, "LEAST", *args)


def avg(
    dialect: "SQLDialectBase",
    expr: "bases.BaseExpression",
) -> "aggregate.AvgFunction":
    """
    Creates an AVG function call.

    Returns the average value of the argument.

    Usage:
        - avg(dialect, NumericColumn(dialect, "price")) -> AVG(`price`)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        An AvgFunction node

    Version: All MySQL versions
    """
    return aggregate.AvgFunction(dialect, expr)


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
