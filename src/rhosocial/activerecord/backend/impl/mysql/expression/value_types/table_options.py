# src/rhosocial/activerecord/backend/impl/mysql/expression/value_types/table_options.py
"""MySQL table-option value nodes."""

from enum import Enum


class MySQLRowFormat(str, Enum):
    """MySQL ``ROW_FORMAT`` table option values."""
    #: A member *is* the word it carries; see `SortDirection.__str__`.
    __str__ = str.__str__


    DEFAULT = "DEFAULT"
    DYNAMIC = "DYNAMIC"
    FIXED = "FIXED"
    COMPRESSED = "COMPRESSED"
    REDUNDANT = "REDUNDANT"
    COMPACT = "COMPACT"


__all__ = [
    "MySQLRowFormat",
]
