# src/rhosocial/activerecord/backend/impl/mysql/mixins/set_type.py
from typing import List, Tuple


class MySQLSetTypeMixin:
    """MySQL SET type implementation."""

    def supports_set_type(self) -> bool:
        return True

    def format_set_literal(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLSetLiteralExpression` node."""
        from ..expression.set_type import MySQLSetLiteralExpression

        if not isinstance(expr, MySQLSetLiteralExpression):
            raise TypeError(
                f"format_set_literal expects MySQLSetLiteralExpression, got {type(expr).__name__}"
            )

        values = expr.values
        column_values = expr.column_values
        if len(values) > 64:
            raise ValueError("MySQL SET type supports maximum 64 members")

        if column_values is not None:
            invalid_values = [v for v in values if v not in column_values]
            if invalid_values:
                raise ValueError(f"Invalid SET values: {invalid_values}. Allowed values: {column_values}")

        if not values:
            return "'", ()

        sorted_values = sorted(values)
        literal = ",".join(sorted_values)
        sql = f"{self.get_parameter_placeholder()}"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, (literal,)

    def format_find_in_set(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLFindInSetExpression` node."""
        from ..expression.set_type import MySQLFindInSetExpression

        if not isinstance(expr, MySQLFindInSetExpression):
            raise TypeError(
                f"format_find_in_set expects MySQLFindInSetExpression, got {type(expr).__name__}"
            )

        sql = f"FIND_IN_SET(%s, {self.format_identifier(expr.set_column)}) > 0"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, (expr.value,)

    def format_set_contains(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLSetContainsExpression` node."""
        from ..expression.set_type import MySQLSetContainsExpression

        if not isinstance(expr, MySQLSetContainsExpression):
            raise TypeError(
                f"format_set_contains expects MySQLSetContainsExpression, got {type(expr).__name__}"
            )

        conditions = []
        params: List[str] = []

        for value in expr.values:
            conditions.append(f"FIND_IN_SET(%s, {self.format_identifier(expr.column)}) > 0")
            params.append(value)

        sql = " AND ".join(conditions)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(params)
