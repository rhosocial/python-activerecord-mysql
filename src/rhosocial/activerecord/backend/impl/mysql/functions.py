# src/rhosocial/activerecord/backend/impl/mysql/functions.py
"""
MySQL-specific SQL function factories.

This module provides factory functions for creating MySQL-specific SQL expression
objects, including JSON functions, spatial functions, full-text search functions,
and SET type functions.

Usage Rules:
- All functions accept a dialect instance as the first argument
- For column references, pass Column objects or column name strings
- For literal values, pass the value directly (will be converted to Literal)
- Functions return appropriate expression objects (FunctionCall, RawSQLExpression, etc.)

Version Requirements:
- JSON functions: MySQL 5.7.8+
- Spatial functions: MySQL 5.7+
- GeoJSON functions: MySQL 5.7.5+
- Full-text search: MySQL 5.6+ (with some features requiring 5.7+)
- SET type: All MySQL versions
"""
from typing import Union, Optional, List, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from .dialect import MySQLDialect


def _convert_to_expression(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
                           handle_numeric_literals: bool = True) -> "bases.BaseExpression":
    """
    Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert
        handle_numeric_literals: Whether to treat numeric values as literals

    Returns:
        A BaseExpression instance
    """
    from rhosocial.activerecord.backend.expression import bases, core
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif handle_numeric_literals and isinstance(expr, (int, float)):
        return core.Literal(dialect, expr)
    else:
        return core.Column(dialect, expr)


# region JSON Function Factories

def json_extract(dialect: "MySQLDialect",
                 json_doc: Union[str, "bases.BaseExpression"],
                 path: str,
                 *paths: str) -> "core.FunctionCall":
    """
    Creates a JSON_EXTRACT function call.

    Extracts data from a JSON document at the specified path(s).

    Usage rules:
    - To extract from a column: json_extract(dialect, Column(dialect, "json_col"), "$.name")
    - To extract from a literal: json_extract(dialect, '{"a": 1}', "$.a")
    - Multiple paths: json_extract(dialect, col, "$.name", "$.age")

    Args:
        dialect: The MySQL dialect instance
        json_doc: JSON document (column or literal)
        path: First JSON path expression
        *paths: Additional JSON path expressions

    Returns:
        A FunctionCall instance representing JSON_EXTRACT

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    args = [doc_expr, path_expr]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_EXTRACT", *args)


def json_unquote(dialect: "MySQLDialect",
                 json_val: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a JSON_UNQUOTE function call.

    Unquotes a JSON value and returns the result as a string.

    Args:
        dialect: The MySQL dialect instance
        json_val: JSON value to unquote

    Returns:
        A FunctionCall instance representing JSON_UNQUOTE

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_UNQUOTE", val_expr)


def json_object(dialect: "MySQLDialect",
                *key_value_pairs: Any) -> "core.FunctionCall":
    """
    Creates a JSON_OBJECT function call.

    Creates a JSON object from key-value pairs.

    Usage rules:
    - Empty object: json_object(dialect)
    - With values: json_object(dialect, "name", "John", "age", 30)

    Args:
        dialect: The MySQL dialect instance
        *key_value_pairs: Alternating keys and values

    Returns:
        A FunctionCall instance representing JSON_OBJECT

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    if not key_value_pairs:
        return core.FunctionCall(dialect, "JSON_OBJECT")
    args = []
    for i, val in enumerate(key_value_pairs):
        args.append(core.Literal(dialect, val))
    return core.FunctionCall(dialect, "JSON_OBJECT", *args)


def json_array(dialect: "MySQLDialect",
                *values: Any) -> "core.FunctionCall":
    """
    Creates a JSON_ARRAY function call.

    Creates a JSON array from values.

    Usage rules:
    - Empty array: json_array(dialect)
    - With values: json_array(dialect, 1, 2, 3)

    Args:
        dialect: The MySQL dialect instance
        *values: Values to include in the array

    Returns:
        A FunctionCall instance representing JSON_ARRAY

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    if not values:
        return core.FunctionCall(dialect, "JSON_ARRAY")
    args = [core.Literal(dialect, v) for v in values]
    return core.FunctionCall(dialect, "JSON_ARRAY", *args)


def json_contains(dialect: "MySQLDialect",
                  target: Union[str, "bases.BaseExpression"],
                  candidate: Any,
                  path: Optional[str] = None) -> "core.FunctionCall":
    """
    Creates a JSON_CONTAINS function call.

    Checks if a JSON document contains a specific value.

    Args:
        dialect: The MySQL dialect instance
        target: Target JSON document or column
        candidate: Value to search for
        path: Optional path within the document

    Returns:
        A FunctionCall instance representing JSON_CONTAINS

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    target_expr = _convert_to_expression(dialect, target)
    candidate_expr = core.Literal(dialect, candidate)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_CONTAINS", target_expr, candidate_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_CONTAINS", target_expr, candidate_expr)


def json_set(dialect: "MySQLDialect",
             json_doc: Union[str, "bases.BaseExpression"],
             path: str,
             value: Any,
             *path_value_pairs: Any) -> "core.FunctionCall":
    """
    Creates a JSON_SET function call.

    Inserts or updates data in a JSON document.

    Args:
        dialect: The MySQL dialect instance
        json_doc: JSON document or column
        path: JSON path expression
        value: Value to set
        *path_value_pairs: Additional path-value pairs

    Returns:
        A FunctionCall instance representing JSON_SET

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    args = [doc_expr, core.Literal(dialect, path), core.Literal(dialect, value)]
    for i in range(0, len(path_value_pairs), 2):
        if i + 1 < len(path_value_pairs):
            args.append(core.Literal(dialect, path_value_pairs[i]))
            args.append(core.Literal(dialect, path_value_pairs[i + 1]))
    return core.FunctionCall(dialect, "JSON_SET", *args)


def json_remove(dialect: "MySQLDialect",
                json_doc: Union[str, "bases.BaseExpression"],
                path: str,
                *paths: str) -> "core.FunctionCall":
    """
    Creates a JSON_REMOVE function call.

    Removes data from a JSON document.

    Args:
        dialect: The MySQL dialect instance
        json_doc: JSON document or column
        path: First JSON path expression
        *paths: Additional JSON path expressions

    Returns:
        A FunctionCall instance representing JSON_REMOVE

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    args = [doc_expr, core.Literal(dialect, path)]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_REMOVE", *args)


def json_type(dialect: "MySQLDialect",
              json_val: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a JSON_TYPE function call.

    Returns the type of a JSON value.

    Args:
        dialect: The MySQL dialect instance
        json_val: JSON value to check

    Returns:
        A FunctionCall instance representing JSON_TYPE

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_TYPE", val_expr)


def json_valid(dialect: "MySQLDialect",
               json_val: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a JSON_VALID function call.

    Validates whether a value is valid JSON.

    Args:
        dialect: The MySQL dialect instance
        json_val: Value to validate

    Returns:
        A FunctionCall instance representing JSON_VALID

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_VALID", val_expr)


def json_search(dialect: "MySQLDialect",
                json_doc: Union[str, "bases.BaseExpression"],
                search_str: str,
                path: Optional[str] = None,
                search_all: bool = False) -> "core.FunctionCall":
    """
    Creates a JSON_SEARCH function call.

    Searches for a string in a JSON document.

    Args:
        dialect: The MySQL dialect instance
        json_doc: JSON document or column
        search_str: String to search for
        path: Optional path to search within
        search_all: If True, returns all matches; otherwise returns first match

    Returns:
        A FunctionCall instance representing JSON_SEARCH

    Version: MySQL 5.7.8+
    """
    from rhosocial.activerecord.backend.expression import core
    doc_expr = _convert_to_expression(dialect, json_doc)
    one_or_all = "all" if search_all else "one"
    one_or_all_expr = core.Literal(dialect, one_or_all)
    search_expr = core.Literal(dialect, search_str)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_SEARCH", doc_expr, one_or_all_expr, search_expr,
                                  core.Literal(dialect, None), path_expr)
    return core.FunctionCall(dialect, "JSON_SEARCH", doc_expr, one_or_all_expr, search_expr)


# endregion JSON Function Factories


# region Spatial Function Factories

def st_geom_from_text(dialect: "MySQLDialect",
                      wkt: str,
                      srid: Optional[int] = None) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    wkt_expr = core.Literal(dialect, wkt)
    if srid is not None:
        srid_expr = core.Literal(dialect, srid)
        return core.FunctionCall(dialect, "ST_GeomFromText", wkt_expr, srid_expr)
    return core.FunctionCall(dialect, "ST_GeomFromText", wkt_expr)


def st_geom_from_wkb(dialect: "MySQLDialect",
                     wkb: bytes,
                     srid: Optional[int] = None) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    wkb_expr = core.Literal(dialect, wkb)
    if srid is not None:
        srid_expr = core.Literal(dialect, srid)
        return core.FunctionCall(dialect, "ST_GeomFromWKB", wkb_expr, srid_expr)
    return core.FunctionCall(dialect, "ST_GeomFromWKB", wkb_expr)


def st_as_text(dialect: "MySQLDialect",
               geom: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    geom_expr = _convert_to_expression(dialect, geom)
    return core.FunctionCall(dialect, "ST_AsText", geom_expr)


def st_as_geojson(dialect: "MySQLDialect",
                  geom: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    geom_expr = _convert_to_expression(dialect, geom)
    return core.FunctionCall(dialect, "ST_AsGeoJSON", geom_expr)


def st_distance(dialect: "MySQLDialect",
                geom1: Union[str, "bases.BaseExpression"],
                geom2: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Distance", geom1_expr, geom2_expr)


def st_within(dialect: "MySQLDialect",
              geom1: Union[str, "bases.BaseExpression"],
              geom2: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Within", geom1_expr, geom2_expr)


def st_contains(dialect: "MySQLDialect",
                geom1: Union[str, "bases.BaseExpression"],
                geom2: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Contains", geom1_expr, geom2_expr)


def st_intersects(dialect: "MySQLDialect",
                  geom1: Union[str, "bases.BaseExpression"],
                  geom2: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    from rhosocial.activerecord.backend.expression import core
    geom1_expr = _convert_to_expression(dialect, geom1)
    geom2_expr = _convert_to_expression(dialect, geom2)
    return core.FunctionCall(dialect, "ST_Intersects", geom1_expr, geom2_expr)


# endregion Spatial Function Factories


# region Full-Text Search Function Factories

def match_against(dialect: "MySQLDialect",
                  columns: Union[str, List[str], "bases.BaseExpression"],
                  search_string: str,
                  mode: Optional[str] = None) -> "operators.RawSQLExpression":
    """
    Creates a MATCH ... AGAINST expression for full-text search.

    Usage rules:
    - Natural language mode (default): match_against(dialect, "content", "search term")
    - Boolean mode: match_against(dialect, "content", "+term -exclude", mode="BOOLEAN")
    - Query expansion: match_against(dialect, "content", "search term", mode="QUERY_EXPANSION")

    Args:
        dialect: The MySQL dialect instance
        columns: Column name(s) to search
        search_string: Search string
        mode: Search mode - "NATURAL_LANGUAGE", "BOOLEAN", or "QUERY_EXPANSION"

    Returns:
        A RawSQLExpression instance representing MATCH ... AGAINST

    Version: MySQL 5.6+ (with parser option in 5.7+)
    """
    from rhosocial.activerecord.backend.expression import operators, core, bases
    if isinstance(columns, bases.BaseExpression):
        cols_sql, cols_params = columns.to_sql()
    elif isinstance(columns, list):
        cols_sql = ", ".join(dialect.format_identifier(c) for c in columns)
        cols_params = ()
    else:
        cols_sql = dialect.format_identifier(columns)
        cols_params = ()

    search_expr = core.Literal(dialect, search_string)
    search_sql, search_params = search_expr.to_sql()

    if mode is None or mode.upper() == "NATURAL_LANGUAGE":
        mode_str = "IN NATURAL LANGUAGE MODE"
    elif mode.upper() == "BOOLEAN":
        mode_str = "IN BOOLEAN MODE"
    elif mode.upper() == "QUERY_EXPANSION":
        mode_str = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
    else:
        mode_str = ""

    sql = f"MATCH({cols_sql}) AGAINST({search_sql} {mode_str})"
    return operators.RawSQLExpression(dialect, sql, search_params)


# endregion Full-Text Search Function Factories


# region SET Type Function Factories

def find_in_set(dialect: "MySQLDialect",
                value: str,
                set_column: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a FIND_IN_SET function call.

    Finds the position of a value in a SET column.

    Args:
        dialect: The MySQL dialect instance
        value: Value to find
        set_column: SET column name or expression

    Returns:
        A FunctionCall instance representing FIND_IN_SET

    Version: All MySQL versions
    """
    from rhosocial.activerecord.backend.expression import core
    value_expr = core.Literal(dialect, value)
    col_expr = _convert_to_expression(dialect, set_column)
    return core.FunctionCall(dialect, "FIND_IN_SET", value_expr, col_expr)


# endregion SET Type Function Factories


# region Enum Type Function Factories

def elt(dialect: "MySQLDialect",
        index: int,
        *values: str) -> "core.FunctionCall":
    """
    Creates an ELT function call.

    Returns the N-th element from a list of strings.

    Args:
        dialect: The MySQL dialect instance
        index: 1-based index of the element to return
        *values: List of string values

    Returns:
        A FunctionCall instance representing ELT

    Version: All MySQL versions
    """
    from rhosocial.activerecord.backend.expression import core
    index_expr = core.Literal(dialect, index)
    args = [index_expr]
    for v in values:
        args.append(core.Literal(dialect, v))
    return core.FunctionCall(dialect, "ELT", *args)


def field(dialect: "MySQLDialect",
          value: Any,
          *values: Any) -> "core.FunctionCall":
    """
    Creates a FIELD function call.

    Returns the index (position) of value in the list of values.
    Returns 0 if not found.

    Args:
        dialect: The MySQL dialect instance
        value: Value to search for
        *values: List of values to search in

    Returns:
        A FunctionCall instance representing FIELD

    Version: All MySQL versions
    """
    from rhosocial.activerecord.backend.expression import core
    value_expr = _convert_to_expression(dialect, value)
    args = [value_expr]
    for v in values:
        args.append(_convert_to_expression(dialect, v))
    return core.FunctionCall(dialect, "FIELD", *args)


# endregion Enum Type Function Factories


__all__ = [
    # JSON functions
    "json_extract",
    "json_unquote",
    "json_object",
    "json_array",
    "json_contains",
    "json_set",
    "json_remove",
    "json_type",
    "json_valid",
    "json_search",
    # Spatial functions
    "st_geom_from_text",
    "st_geom_from_wkb",
    "st_as_text",
    "st_as_geojson",
    "st_distance",
    "st_within",
    "st_contains",
    "st_intersects",
    # Full-text search
    "match_against",
    # SET type functions
    "find_in_set",
    # Enum type functions
    "elt",
    "field",
]
