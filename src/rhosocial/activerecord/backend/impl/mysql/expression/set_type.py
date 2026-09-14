# src/rhosocial/activerecord/backend/impl/mysql/expression/set_type.py
"""MySQL SET type expression classes."""

from typing import TYPE_CHECKING, List, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLSetLiteralExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL SET literal value expression.

    Args:
        dialect: The SQL dialect.
        values: List of SET member values.
        column_values: Optional allowed column values for validation.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        values: List[str],
        column_values: Optional[List[str]] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.values = values
        self.column_values = column_values
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_literal"


class MySQLFindInSetExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL FIND_IN_SET expression.

    Args:
        dialect: The SQL dialect.
        value: Value to search for.
        set_column: Column containing the SET value.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: str,
        set_column: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.value = value
        self.set_column = set_column
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_find_in_set"


class MySQLSetContainsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL SET contains check expression.

    Args:
        dialect: The SQL dialect.
        column: Column containing the SET value.
        values: List of values to check for containment.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: str,
        values: List[str],
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.column = column
        self.values = values
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_contains"


__all__ = [
    "SetLiteralExpression",
    "FindInSetExpression",
    "SetContainsExpression",
]
