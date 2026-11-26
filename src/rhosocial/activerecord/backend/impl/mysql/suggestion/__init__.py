# src/rhosocial/activerecord/backend/impl/mysql/suggestion/__init__.py
"""Backend-owned DDL suggestion implementations for MySQL.

A suggestion is not an expression: the data classes and renderers live in core
``rhosocial.activerecord.backend.suggestion``. Only the per-backend answers
belong here, kept out of ``mixins`` so the two concerns stay separate.

There is one module per partition-lifecycle point, mirroring the SQLite
suggestion package. Shared plan-reading helpers and their common base live in
``_common.py``; the four migration change points read their frozen projections
through ``_change_projection.py``.
"""

from ._common import MySQLPartitionSuggestionBase
from .column_reorder_suggestion import MySQLColumnReorderSuggestionMixin
from .data_type_suggestions import MySQLDataTypeSuggestionsMixin
from .general_suggestions import (
    MySQLCreateTableLayoutSuggestionMixin,
    MySQLJSONSuggestionMixin,
    MySQLStringConcatenationSuggestionMixin,
)
from .generated_value_suggestion import MySQLGeneratedValueSuggestionMixin
from .partition_add_suggestion import MySQLPartitionAddSuggestionMixin
from .partition_build_suggestion import MySQLPartitionBuildSuggestionMixin
from .partition_drop_suggestion import MySQLPartitionDropSuggestionMixin
from .partition_merge_suggestion import MySQLPartitionMergeSuggestionMixin
from .partition_retention_suggestion import MySQLPartitionRetentionSuggestionMixin
from .partition_scheme_change_suggestion import MySQLPartitionSchemeChangeSuggestionMixin
from .partition_split_suggestion import MySQLPartitionSplitSuggestionMixin
from .partition_table_alter_suggestion import MySQLPartitionTableAlterSuggestionMixin
from .partition_table_drop_suggestion import MySQLPartitionTableDropSuggestionMixin
from .table_constraint_change_suggestion import MySQLTableConstraintChangeSuggestionMixin
from .table_index_change_suggestion import MySQLTableIndexChangeSuggestionMixin
from .table_options_suggestion import (
    MySQLStorageEngineSuggestionMixin,
    MySQLTextEncodingSuggestionMixin,
)

__all__ = [
    "MySQLPartitionSuggestionBase",
    "MySQLColumnReorderSuggestionMixin",
    "MySQLDataTypeSuggestionsMixin",
    "MySQLCreateTableLayoutSuggestionMixin",
    "MySQLJSONSuggestionMixin",
    "MySQLStringConcatenationSuggestionMixin",
    "MySQLGeneratedValueSuggestionMixin",
    "MySQLPartitionAddSuggestionMixin",
    "MySQLPartitionBuildSuggestionMixin",
    "MySQLPartitionDropSuggestionMixin",
    "MySQLPartitionMergeSuggestionMixin",
    "MySQLPartitionRetentionSuggestionMixin",
    "MySQLPartitionSchemeChangeSuggestionMixin",
    "MySQLPartitionSplitSuggestionMixin",
    "MySQLPartitionTableAlterSuggestionMixin",
    "MySQLPartitionTableDropSuggestionMixin",
    "MySQLTableConstraintChangeSuggestionMixin",
    "MySQLTableIndexChangeSuggestionMixin",
    "MySQLStorageEngineSuggestionMixin",
    "MySQLTextEncodingSuggestionMixin",
]
