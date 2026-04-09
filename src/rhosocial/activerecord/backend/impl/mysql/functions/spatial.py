# src/rhosocial/activerecord/backend/impl/mysql/functions/spatial.py
"""
MySQL spatial function factories.

Functions: st_geom_from_text, st_geom_from_wkb, st_as_text, st_as_geojson,
st_distance, st_within, st_contains, st_intersects
"""

from typing import Union, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from .dialect import MySQLDialect


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    handle_numeric_literals: bool = True,
) -> "bases.BaseExpression":
    """
    Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert
        handle_numeric_literals: Whether to treat numeric values as literals

    Returns:
        A BaseExpression instance
    """
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif handle_numeric_literals and isinstance(expr, (int, float)):
        return core.Literal(dialect, expr)
    else:
        return core.Column(dialect, expr)


def st_geom_from_text(
    dialect: "MySQLDialect",
    wkt: str,
    srid: Optional[int] = None,
) -> "core.FunctionCall":
    """
    Creates an ST_GeomFromText function call.

    Constructs a geometry value from a WKT (Well-Known Text) representation.

    Args:
        dialect: The MySQL dialect instance
        wkt: Well-Known Text string
        srid: Optional SRID (Spatial Reference System Identifier)

    Returns:
        A FunctionCall instance representing ST_GeomFromText

    Version: MySQL 5.7+
    """
    wkt_expr = core.Literal(dialect, wkt)
    if srid is not None:
        srid_expr = core.Literal(dialect, srid)
        return core.FunctionCall(dialect, "ST_GeomFromText", wkt_expr, srid_expr)
    return core.FunctionCall(dialect, "ST_GeomFromText", wkt_expr)


def st_geom_from_wkb(
    dialect: "MySQLDialect",
    wkb: bytes,
    srid: Optional[int] = None,
) -> "core.FunctionCall":
    """
    Creates an ST_GeomFromWKB function call.

    Constructs a geometry value from a WKB (Well-Known Binary) representation.

    Args:
        dialect: The MySQL dialect instance
        wkb: Well-Known Binary data
        srid: Optional SRID (Spatial Reference System Identifier)

    Returns:
        A FunctionCall instance representing ST_GeomFromWKB

    Version: MySQL 5.7+
    """
    wkb_expr = core.Literal(dialect, wkb)
    if srid is not None:
        srid_expr = core.Literal(dialect, srid)
        return core.FunctionCall(dialect, "ST_GeomFromWKB", wkb_expr, srid_expr)
    return core.FunctionCall(dialect, "ST_GeomFromWKB", wkb_expr)


def st_as_text(
    dialect: "MySQLDialect",
    geom: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an ST_AsText function call.

    Returns the WKT (Well-Known Text) representation of a geometry.

    Args:
        dialect: The MySQL dialect instance
        geom: Geometry value or column

    Returns:
        A FunctionCall instance representing ST_AsText

    Version: MySQL 5.7+
    """
    geom_expr = _convert_to_expression(dialect, geom)
    return core.FunctionCall(dialect, "ST_AsText", geom_expr)


def st_as_geojson(
    dialect: "MySQLDialect",
    geom: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an ST_AsGeoJSON function call.

    Returns the GeoJSON representation of a geometry.

    Args:
        dialect: The MySQL dialect instance
        geom: Geometry value or column

    Returns:
        A FunctionCall instance representing ST_AsGeoJSON

    Version: MySQL 5.7.5+
    """
    geom_expr = _convert_to_expression(dialect, geom)
    return core.FunctionCall(dialect, "ST_AsGeoJSON", geom_expr)


def st_distance(
    dialect: "MySQLDialect",
    geom1: Union[str, "bases.BaseExpression"],
    geom2: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an ST_Distance function call.

    Returns the distance between two geometries.

    Args:
        dialect: The MySQL dialect instance
        geom1: First geometry
        geom2: Second geometry

    Returns:
        A FunctionCall instance representing ST_Distance

    Version: MySQL 5.7+
    """
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Distance", geom1_expr, geom2_expr)


def st_within(
    dialect: "MySQLDialect",
    geom1: Union[str, "bases.BaseExpression"],
    geom2: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an ST_Within function call.

    Checks if geom1 is spatially within geom2.

    Args:
        dialect: The MySQL dialect instance
        geom1: First geometry
        geom2: Second geometry

    Returns:
        A FunctionCall instance representing ST_Within

    Version: MySQL 5.7+
    """
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Within", geom1_expr, geom2_expr)


def st_contains(
    dialect: "MySQLDialect",
    geom1: Union[str, "bases.BaseExpression"],
    geom2: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an ST_Contains function call.

    Checks if geom1 spatially contains geom2.

    Args:
        dialect: The MySQL dialect instance
        geom1: First geometry
        geom2: Second geometry

    Returns:
        A FunctionCall instance representing ST_Contains

    Version: MySQL 5.7+
    """
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Contains", geom1_expr, geom2_expr)


def st_intersects(
    dialect: "MySQLDialect",
    geom1: Union[str, "bases.BaseExpression"],
    geom2: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an ST_Intersects function call.

    Checks if two geometries spatially intersect.

    Args:
        dialect: The MySQL dialect instance
        geom1: First geometry
        geom2: Second geometry

    Returns:
        A FunctionCall instance representing ST_Intersects

    Version: MySQL 5.7+
    """
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Intersects", geom1_expr, geom2_expr)


__all__ = [
    "st_geom_from_text",
    "st_geom_from_wkb",
    "st_as_text",
    "st_as_geojson",
    "st_distance",
    "st_within",
    "st_contains",
    "st_intersects",
]