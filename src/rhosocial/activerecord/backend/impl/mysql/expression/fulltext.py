# src/rhosocial/activerecord/backend/impl/mysql/expression/fulltext.py
"""MySQL FULLTEXT index expression classes."""

from rhosocial.activerecord.backend.expression.core import _validate_schema_name
from typing import TYPE_CHECKING, List, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLFulltextIndexOptionsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL FULLTEXT index options expression for CREATE TABLE / ALTER TABLE.

    Args:
        dialect: The SQL dialect.
        index_name: Name of the FULLTEXT index.
        columns: List of column names to index.
        index_type: Optional index type (e.g., 'FULLTEXT').
        parser_name: Optional parser name (e.g., 'ngram').
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        columns: List[str],
        index_type: Optional[str] = None,
        parser_name: Optional[str] = None,
        *,
        alias: Optional[str] = None,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            schema_name: Namespace to qualify the index with, e.g. ``app``.
                None leaves the name unqualified. An empty string raises
                ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.index_name = index_name
        self.schema_name = _validate_schema_name(schema_name, type(self).__name__)
        self.columns = columns
        self.index_type = index_type
        self.parser_name = parser_name
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_fulltext_index_options"


__all__ = [
    "FulltextIndexOptionsExpression",
]
