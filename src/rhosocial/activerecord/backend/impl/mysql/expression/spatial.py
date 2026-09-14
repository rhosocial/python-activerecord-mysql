# src/rhosocial/activerecord/backend/impl/mysql/expression/spatial.py
"""
MySQL-specific spatial expression functions.

This module provides expression classes for MySQL spatial functions:
- MySQLSTGeomFromTextExpression
- MySQLSTDistanceExpression
- MySQLSTWithinExpression
- MySQLSTContainsExpression
- SpatialLiteralExpression
- STGeomFromWKBExpression
- STAsTextExpression
- STAsGeoJSONExpression
- CreateSpatialIndexExpression
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


class SpatialLiteralExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL spatial literal expression with optional SRID.

    Args:
        dialect: The SQL dialect.
        wkt: Well-Known Text representation of the geometry.
        srid: Optional Spatial Reference System Identifier.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        wkt: str,
        srid: Optional[int] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.wkt = wkt
        self.srid = srid
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_spatial_literal"


class STGeomFromWKBExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_GeomFromWKB expression.

    Creates a geometry value from WKB (Well-Known Binary).

    Args:
        dialect: The SQL dialect.
        wkb: Well-Known Binary representation of the geometry.
        srid: Optional Spatial Reference System Identifier.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        wkb: bytes,
        srid: Optional[int] = None,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.wkb = wkb
        self.srid = srid
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_geom_from_wkb"


class STAsTextExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_AsText expression.

    Converts a geometry value to its WKT (Well-Known Text) representation.

    Args:
        dialect: The SQL dialect.
        geom: Geometry column or expression to convert.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom = geom
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_as_text"


class STAsGeoJSONExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL ST_AsGeoJSON expression.

    Converts a geometry value to GeoJSON format (MySQL 5.7.5+).

    Args:
        dialect: The SQL dialect.
        geom: Geometry column or expression to convert.
        alias: Optional SQL alias.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        geom: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.geom = geom
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_st_as_geojson"


class CreateSpatialIndexExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    """MySQL CREATE SPATIAL INDEX expression.

    Args:
        dialect: The SQL dialect.
        index_name: Name of the index.
        table_name: Name of the table.
        column: Column to create the spatial index on.
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
        return "format_create_spatial_index"


__all__ = [
    "MySQLSTGeomFromTextExpression",
    "MySQLSTDistanceExpression",
    "MySQLSTWithinExpression",
    "MySQLSTContainsExpression",
    "SpatialLiteralExpression",
    "STGeomFromWKBExpression",
    "STAsTextExpression",
    "STAsGeoJSONExpression",
    "CreateSpatialIndexExpression",
]
