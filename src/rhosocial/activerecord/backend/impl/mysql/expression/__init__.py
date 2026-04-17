# src/rhosocial/activerecord/backend/impl/mysql/expression/__init__.py
"""
MySQL-specific expression classes.

This module provides expression classes that are specific to MySQL, such as
LOAD DATA INFILE, JSON_TABLE, JSON functions, spatial functions, vector
functions, MATCH...AGAINST expressions, and row-level locking expressions.

Directory structure:
- load_data.py      - LOAD DATA INFILE expression
- json_table.py    - JSON_TABLE expression
- json.py           - JSON function expressions
- spatial.py         - Spatial function expressions
- vector.py          - Vector function expressions (MySQL 9.0+)
- match_against.py - MATCH...AGAINST expression
- locking.py        - Row-level locking expressions (FOR UPDATE, FOR SHARE)
"""

from .load_data import LoadDataExpression, LoadDataOptions
from .json_table import JSONTableExpression, JSONTableColumn, NestedPath
from .json import (
    JSONExtractExpression,
    JSONObjectExpression,
    JSONArrayExpression,
    JSONContainsExpression,
)
from .spatial import (
    STGeomFromTextExpression,
    STDistanceExpression,
    STWithinExpression,
    STContainsExpression,
)
from .vector import (
    VectorExpression,
    DistanceEuclideanExpression,
    DistanceCosineExpression,
    DistanceDotExpression,
)
from .match_against import MatchAgainstExpression, MatchAgainstMode
from .locking import MySQLForUpdateClause, MySQLLockStrength

__all__ = [
    "LoadDataExpression",
    "LoadDataOptions",
    "JSONTableExpression",
    "JSONTableColumn",
    "NestedPath",
    "JSONExtractExpression",
    "JSONObjectExpression",
    "JSONArrayExpression",
    "JSONContainsExpression",
    "STGeomFromTextExpression",
    "STDistanceExpression",
    "STWithinExpression",
    "STContainsExpression",
    "VectorExpression",
    "DistanceEuclideanExpression",
    "DistanceCosineExpression",
    "DistanceDotExpression",
    "MatchAgainstExpression",
    "MatchAgainstMode",
    "MySQLForUpdateClause",
    "MySQLLockStrength",
]