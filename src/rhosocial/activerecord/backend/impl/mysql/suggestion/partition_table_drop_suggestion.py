# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_table_drop_suggestion.py
"""MySQL's partition table-drop suggestion.

Suggests dropping the whole partitioned table with a real ``DropTableStatement``
rather than an inline ``REMOVE PARTITIONING``. A plan naming no table answers
explicit ``False``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....expression import DropTableStatement
from ....suggestion import PartitionTableDropSuggestion
from ._common import MySQLPartitionSuggestionBase

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause

__all__ = ["MySQLPartitionTableDropSuggestionMixin"]


class MySQLPartitionTableDropSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest dropping the whole partitioned table."""

    def suggest_partition_table_drop(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionTableDropSuggestion:
        """Suggest dropping the whole partitioned table (not REMOVE PARTITIONING)."""
        table = self._suggestion_table(plan)
        if table is None:
            return PartitionTableDropSuggestion(False)
        return PartitionTableDropSuggestion((DropTableStatement(self, table),))
