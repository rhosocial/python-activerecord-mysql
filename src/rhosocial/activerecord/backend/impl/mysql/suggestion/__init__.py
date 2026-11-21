# src/rhosocial/activerecord/backend/impl/mysql/suggestion/__init__.py
"""Backend-owned DDL suggestion implementations for MySQL.

A suggestion is not an expression: the data classes and renderers live in core
``rhosocial.activerecord.backend.suggestion``. Only the per-backend answers
belong here, kept out of ``mixins`` so the two concerns stay separate.

There is one module per partition-lifecycle point, mirroring the SQLite
suggestion package. Shared plan-reading helpers and their common base live in
``_common.py``.
"""

from ._common import MySQLPartitionSuggestionBase
from .data_type_suggestions import MySQLDataTypeSuggestionsMixin
from .integer_auto_increment_column_suggestion import MySQLIntegerAutoIncrementColumnSuggestionMixin
from .partition_add_suggestion import MySQLPartitionAddSuggestionMixin
from .partition_build_suggestion import MySQLPartitionBuildSuggestionMixin
from .partition_drop_suggestion import MySQLPartitionDropSuggestionMixin
from .partition_merge_suggestion import MySQLPartitionMergeSuggestionMixin
from .partition_retention_suggestion import MySQLPartitionRetentionSuggestionMixin
from .partition_split_suggestion import MySQLPartitionSplitSuggestionMixin
from .partition_table_alter_suggestion import MySQLPartitionTableAlterSuggestionMixin
from .partition_table_drop_suggestion import MySQLPartitionTableDropSuggestionMixin

__all__ = [
    "MySQLPartitionSuggestionBase",
    "MySQLDataTypeSuggestionsMixin",
    "MySQLIntegerAutoIncrementColumnSuggestionMixin",
    "MySQLPartitionAddSuggestionMixin",
    "MySQLPartitionBuildSuggestionMixin",
    "MySQLPartitionDropSuggestionMixin",
    "MySQLPartitionMergeSuggestionMixin",
    "MySQLPartitionRetentionSuggestionMixin",
    "MySQLPartitionSplitSuggestionMixin",
    "MySQLPartitionTableAlterSuggestionMixin",
    "MySQLPartitionTableDropSuggestionMixin",
]
