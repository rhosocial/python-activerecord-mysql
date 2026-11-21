# src/rhosocial/activerecord/backend/impl/mysql/suggestion/__init__.py
"""Backend-owned DDL suggestion implementations for MySQL.

A suggestion is not an expression: the data classes and renderers live in core
``rhosocial.activerecord.backend.suggestion``. Only the per-backend answers
belong here, kept out of ``mixins`` so the two concerns stay separate.
"""

from .data_types import MySQLDataTypeSuggestionsMixin
from .integer_auto_increment import MySQLIntegerAutoIncrementColumnSuggestionMixin
from .partition import MySQLPartitionSuggestionMixin

__all__ = [
    "MySQLIntegerAutoIncrementColumnSuggestionMixin",
    "MySQLPartitionSuggestionMixin",
    "MySQLDataTypeSuggestionsMixin",
]
