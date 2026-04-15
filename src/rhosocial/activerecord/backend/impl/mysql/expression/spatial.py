# src/rhosocial/activerecord/backend/impl/mysql/expression/spatial.py
"""
MySQL-specific spatial expression functions.

This module provides expression classes for MySQL spatial functions:
- STGeomFromTextExpression
- STDistanceExpression
- STWithinExpression
- STContainsExpression
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import SQLQueryAndParams, SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class STGeomFromTextExpression(AliasableMixin, SQLValueExpression):
    """MySQL ST_GeomFromText expression.
    
    Creates a geometry value from WKT.
    
    Example:
        >>> expr = STGeomFromTextExpression(dialect, 'POINT(1 1)')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        wkt: str,
    ):
        super().__init__(dialect)
        self.wkt = wkt
        self.alias = None

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_geom_from_text(self.wkt)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class STDistanceExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_Distance expression.
    
    Returns the distance between two geometries.
    
    Example:
        >>> expr = STDistanceExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = None

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_distance(self.geom1, self.geom2)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class STWithinExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_Within expression.
    
    Returns whether one geometry is within another.
    
    Example:
        >>> expr = STWithinExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = None

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_within(self.geom1, self.geom2)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


class STContainsExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_Contains expression.
    
    Returns whether one geometry contains another.
    
    Example:
        >>> expr = STContainsExpression(dialect, 'geom1', 'geom2')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom1: str,
        geom2: str,
    ):
        super().__init__(dialect)
        self.geom1 = geom1
        self.geom2 = geom2
        self.alias = None

    def to_sql(self) -> "SQLQueryAndParams":
        sql, params = self.dialect.format_st_contains(self.geom1, self.geom2)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"
        return sql, params


__all__ = [
    "STGeomFromTextExpression",
    "STDistanceExpression",
    "STWithinExpression",
    "STContainsExpression",
]