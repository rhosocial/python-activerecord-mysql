# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_table_alter_suggestion.py
"""MySQL's partition table-alter suggestion.

Suggests REMOVE PARTITIONING (the default ``"remove"`` mode), or COALESCE
PARTITION for HASH/KEY when the plan asks for ``"coalesce"`` with a positive
count. Every mutating chain is gated by the dialect's capability probes; an
unsupported mode or strategy answers explicit ``False``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....suggestion import PartitionTableAlterSuggestion
from ..expression.partition import (
    MySQLCoalescePartitionExpression,
    MySQLRemovePartitioningExpression,
)
from ._common import (
    _HASH,
    _KEY,
    MySQLPartitionSuggestionBase,
    _get,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionTableAlterSuggestionMixin"]


class MySQLPartitionTableAlterSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest REMOVE PARTITIONING or COALESCE for a partitioned table."""

    def suggest_partition_table_alter(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionTableAlterSuggestion:
        """Suggest REMOVE PARTITIONING, or COALESCE for HASH/KEY when requested."""
        table = self._suggestion_table(plan)
        if table is None:
            return PartitionTableAlterSuggestion(False)
        mode = str(_get(plan, "mode", "remove")).strip().lower()
        if mode == "remove":
            if not self.supports_remove_partitioning():
                return PartitionTableAlterSuggestion(False)
            return PartitionTableAlterSuggestion((MySQLRemovePartitioningExpression(self, table),))
        if mode == "coalesce":
            if _word(strategy) not in _HASH | _KEY or not self.supports_coalesce_partition():
                return PartitionTableAlterSuggestion(False)
            count = _get(plan, "count")
            if not isinstance(count, int) or count <= 0:
                return PartitionTableAlterSuggestion(False)
            return PartitionTableAlterSuggestion(
                (MySQLCoalescePartitionExpression(self, table, count),)
            )
        return PartitionTableAlterSuggestion(False)
