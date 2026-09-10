# src/rhosocial/activerecord/backend/impl/mysql/expression/vector.py
"""
MySQL-specific vector expression functions.

This module provides expression classes for MySQL vector functions:
- MySQLVectorExpression
- MySQLDistanceEuclideanExpression
- MySQLDistanceCosineExpression
- MySQLDistanceDotExpression

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


__all__ = [
    "MySQLVectorExpression",
    "MySQLDistanceEuclideanExpression",
    "MySQLDistanceCosineExpression",
    "MySQLDistanceDotExpression",
]
