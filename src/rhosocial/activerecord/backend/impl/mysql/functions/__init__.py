# src/rhosocial/activerecord/backend/impl/mysql/functions/__init__.py
"""
MySQL-specific SQL function factories.

This module provides factory functions for creating MySQL-specific SQL expression
objects, organized into submodules by category:

- json: JSON functions (json_extract, json_object, etc.)
- spatial: Spatial/geometric functions (st_geom_from_text, st_distance, etc.)
- fulltext: Full-text search functions (match_against)
- enum_set: SET and Enum type functions (find_in_set, elt, field)
- math_enhanced: Enhanced math functions (round, pow, sqrt, ceil, floor, etc.)

Usage:
    from rhosocial.activerecord.backend.impl.mysql.functions import json_extract
    from rhosocial.activerecord.backend.impl.mysql.functions import st_distance
    from rhosocial.activerecord.backend.impl.mysql.functions import match_against
    from rhosocial.activerecord.backend.impl.mysql.functions import round_

Or import directly from submodules:
    from rhosocial.activerecord.backend.impl.mysql.functions.json import json_extract
    from rhosocial.activerecord.backend.impl.mysql.functions.spatial import st_distance
    from rhosocial.activerecord.backend.impl.mysql.functions.fulltext import match_against
    from rhosocial.activerecord.backend.impl.mysql.functions.math_enhanced import round_

Value arguments:
    Every value argument is an expression, so the caller states what it has:
    a ``Column`` (or the typed column that matches the parameter, such as
    ``NumericColumn``) to read a column and a ``Literal`` to write a value.
    Data that is not a number or a string -- a geometry given as WKT or WKB --
    is turned into an expression by a named constructor here
    (``st_geom_from_text``, ``st_geom_from_wkb``), not by the function that
    consumes it.  ``find_in_set``'s searched value and ``elt``'s index and
    values are the exception: they are plain Python values and are always sent
    as bound parameters.

Version Requirements:
- JSON functions: MySQL 5.7.8+
- Spatial functions: MySQL 5.7+
- GeoJSON functions: MySQL 5.7.5+
- Full-text search: MySQL 5.6+ (with some features requiring 5.7+)
- SET type: All MySQL versions
- Math functions: All MySQL versions
"""

from .json import (
    json_extract,
    json_unquote,
    json_object,
    json_array,
    json_contains,
    json_set,
    json_remove,
    json_type,
    json_valid,
    json_search,
)

from .math_enhanced import (
    round_,
    pow,
    power,
    sqrt,
    mod,
    ceil,
    floor,
    trunc,
    max_,
    min_,
    avg,
)

from .spatial import (
    st_geom_from_text,
    st_geom_from_wkb,
    st_as_text,
    st_as_geojson,
    st_distance,
    st_within,
    st_contains,
    st_intersects,
)

from .fulltext import (
    match_against,
)

from .enum_set import (
    find_in_set,
    elt,
    field,
)

from .bitwise import (
    bit_and,
    bit_or,
    bit_xor,
    bit_count,
    bit_get_bit,
    bit_shift_left,
    bit_shift_right,
)

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
    # Math enhanced functions
    "round_",
    "pow",
    "power",
    "sqrt",
    "mod",
    "ceil",
    "floor",
    "trunc",
    "max_",
    "min_",
    "avg",
    # Bitwise functions
    "bit_and",
    "bit_or",
    "bit_xor",
    "bit_count",
    "bit_get_bit",
    "bit_shift_left",
    "bit_shift_right",
]
