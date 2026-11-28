# src/rhosocial/activerecord/backend/impl/mysql/expression/value_types/set_type.py
"""MySQL SET literal value expression."""

from typing import TYPE_CHECKING, List, Optional

from rhosocial.activerecord.backend.expression.bases.bases import SQLValue
from rhosocial.activerecord.backend.expression.bases.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLSetLiteralExpression(AliasableMixin, ComparisonMixin, SQLValue):
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
        return "format_mysql_set_literal_expression"


__all__ = [
    "MySQLSetLiteralExpression",
]
