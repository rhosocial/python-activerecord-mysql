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

from .load_data import MySQLLoadDataExpression, LoadDataOptions
from .json_table import MySQLJSONTableExpression, JSONTableColumn, NestedPath
from .json import (
    MySQLJSONExtractExpression,
    MySQLJSONObjectExpression,
    MySQLJSONArrayExpression,
    MySQLJSONContainsExpression,
)
from .spatial import (
    MySQLSTGeomFromTextExpression,
    MySQLSTDistanceExpression,
    MySQLSTWithinExpression,
    MySQLSTContainsExpression,
)
from .vector import (
    MySQLVectorExpression,
    MySQLDistanceEuclideanExpression,
    MySQLDistanceCosineExpression,
    MySQLDistanceDotExpression,
)
from .match_against import MySQLMatchAgainstExpression, MatchAgainstMode
from .locking import MySQLForUpdateClause, MySQLLockStrength

__all__ = [
    "MySQLLoadDataExpression",
    "LoadDataOptions",
    "MySQLJSONTableExpression",
    "JSONTableColumn",
    "NestedPath",
    "MySQLJSONExtractExpression",
    "MySQLJSONObjectExpression",
    "MySQLJSONArrayExpression",
    "MySQLJSONContainsExpression",
    "MySQLSTGeomFromTextExpression",
    "MySQLSTDistanceExpression",
    "MySQLSTWithinExpression",
    "MySQLSTContainsExpression",
    "MySQLVectorExpression",
    "MySQLDistanceEuclideanExpression",
    "MySQLDistanceCosineExpression",
    "MySQLDistanceDotExpression",
    "MySQLMatchAgainstExpression",
    "MatchAgainstMode",
    "MySQLForUpdateClause",
    "MySQLLockStrength",
]