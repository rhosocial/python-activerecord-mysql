# src/rhosocial/activerecord/backend/impl/mysql/expression/vector.py
"""
MySQL-specific vector expression functions.

This module provides expression classes for MySQL vector functions:
- MySQLVectorExpression
- MySQLDistanceEuclideanExpression
- MySQLDistanceCosineExpression
- MySQLDistanceDotExpression
- StringToVectorExpression
- VectorToStringExpression
- VectorDimExpression
- CreateVectorIndexExpression

Note: Vector support requires MySQL 9.0+
"""

from typing import TYPE_CHECKING, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLVectorExpression(AliasableMixin, SQLValueExpression):
    """MySQL vector literal expression.

    Creates a vector value from array string.

    Example:
        >>> expr = MySQLVectorExpression(dialect, '[1,2,3]')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vector: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vector = vector
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_vector_literal"


class MySQLDistanceEuclideanExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL Euclidean distance expression.

    Example:
        >>> expr = MySQLDistanceEuclideanExpression(dialect, 'vec1', 'vec2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vec1: str,
        vec2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vec1 = vec1
        self.vec2 = vec2
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_distance_euclidean"


class MySQLDistanceCosineExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL Cosine distance expression.

    Example:
        >>> expr = MySQLDistanceCosineExpression(dialect, 'vec1', 'vec2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vec1: str,
        vec2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vec1 = vec1
        self.vec2 = vec2
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_distance_cosine"


class MySQLDistanceDotExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL Dot product distance expression.

    Example:
        >>> expr = MySQLDistanceDotExpression(dialect, 'vec1', 'vec2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vec1: str,
        vec2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vec1 = vec1
        self.vec2 = vec2
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_distance_dot"


class StringToVectorExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL STRING_TO_VECTOR expression.

    Converts a string representation to a VECTOR value.

    Args:
        dialect: The SQL dialect.
        vector_str: String representation of the vector.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vector_str: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vector_str = vector_str
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_string_to_vector"


class VectorToStringExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL VECTOR_TO_STRING expression.

    Converts a VECTOR value to its string representation.

    Args:
        dialect: The SQL dialect.
        vector_col: Vector column or expression.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vector_col: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vector_col = vector_col
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_vector_to_string"


class VectorDimExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL VECTOR_DIM expression.

    Returns the dimension of a VECTOR value.

    Args:
        dialect: The SQL dialect.
        vector_col: Vector column or expression.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        vector_col: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.vector_col = vector_col
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_vector_dim"


class CreateVectorIndexExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL CREATE VECTOR INDEX expression.

    Args:
        dialect: The SQL dialect.
        index_name: Name of the index.
        table_name: Name of the table.
        column: Column to create the vector index on.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table_name: str,
        column: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.index_name = index_name
        self.table_name = table_name
        self.column = column
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_vector_index"


__all__ = [
    "MySQLVectorExpression",
    "MySQLDistanceEuclideanExpression",
    "MySQLDistanceCosineExpression",
    "MySQLDistanceDotExpression",
    "StringToVectorExpression",
    "VectorToStringExpression",
    "VectorDimExpression",
    "CreateVectorIndexExpression",
]
