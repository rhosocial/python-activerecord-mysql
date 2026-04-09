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
]