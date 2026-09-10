# src/rhosocial/activerecord/backend/impl/mysql/expression/spatial.py
"""
MySQL-specific spatial expression functions.

This module provides expression classes for MySQL spatial functions:
- MySQLSTGeomFromTextExpression
- MySQLSTDistanceExpression
- MySQLSTWithinExpression
- MySQLSTContainsExpression
"""

from typing import TYPE_CHECKING, Optional

from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLSTGeomFromTextExpression(AliasableMixin, SQLValueExpression):
    """MySQL ST_GeomFromText expression.

    Creates a geometry value from WKT.

    Example:
        >>> expr = MySQLSTGeomFromTextExpression(dialect, 'POINT(1 1)')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        wkt: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.wkt = wkt
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_geom_from_text"


class MySQLSTDistanceExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_Distance expression.

    Returns the distance between two geometries.

    Example:
        >>> expr = MySQLSTDistanceExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_distance"


class MySQLSTWithinExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_Within expression.

    Returns whether one geometry is within another.

    Example:
        >>> expr = MySQLSTWithinExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_within"


class MySQLSTContainsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_Contains expression.

    Returns whether one geometry contains another.

    Example:
        >>> expr = MySQLSTContainsExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_contains"


__all__ = [
    "MySQLSTGeomFromTextExpression",
    "MySQLSTDistanceExpression",
    "MySQLSTWithinExpression",
    "MySQLSTContainsExpression",
]
