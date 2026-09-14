# src/rhosocial/activerecord/backend/impl/mysql/expression/table_expr.py
"""MySQL table DDL expression classes."""

from typing import TYPE_CHECKING, Any, Dict, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class InlineIndexExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL inline INDEX definition within CREATE TABLE.

    Args:
        dialect: The SQL dialect.
        idx_def: The IndexDefinition object containing index details.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        idx_def: Any,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.idx_def = idx_def
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_inline_index"


class StorageOptionsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL table storage options expression (ENGINE, CHARSET, etc.).

    Args:
        dialect: The SQL dialect.
        storage_options: Dictionary of storage option key-value pairs.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        storage_options: Dict[str, Any],
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.storage_options = storage_options
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_storage_options"


__all__ = [
    "InlineIndexExpression",
    "StorageOptionsExpression",
]
