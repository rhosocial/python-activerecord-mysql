# src/rhosocial/activerecord/backend/impl/mysql/expression/__init__.py
"""
MySQL-specific expression classes.

This module provides expression classes that are specific to MySQL,
such as LOAD DATA INFILE, JSON_TABLE, and MATCH...AGAINST expressions.

Directory structure:
- load_data.py      - LOAD DATA INFILE expression
- json_table.py    - JSON_TABLE expression
- match_against.py - MATCH...AGAINST expression
"""

from .load_data import LoadDataExpression, LoadDataOptions
from .json_table import JSONTableExpression, JSONTableColumn, NestedPath
from .match_against import MatchAgainstExpression, MatchAgainstMode

__all__ = [
    "LoadDataExpression",
    "LoadDataOptions",
    "JSONTableExpression",
    "JSONTableColumn",
    "NestedPath",
    "MatchAgainstExpression",
    "MatchAgainstMode",
]