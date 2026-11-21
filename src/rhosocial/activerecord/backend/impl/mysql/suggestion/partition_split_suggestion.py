# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_split_suggestion.py
"""MySQL's partition split suggestion.

Suggests REORGANIZE PARTITION -- MySQL's way to split a RANGE/LIST partition
into the replacement definitions named by the plan. Every other strategy, or a
plan missing the partition or its replacements, answers explicit ``False``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....suggestion import PartitionSplitSuggestion
from ..expression.partition import MySQLReorganizePartitionExpression
from ._common import (
    _LIST,
    _RANGE,
    MySQLPartitionSuggestionBase,
    _get,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause

__all__ = ["MySQLPartitionSplitSuggestionMixin"]


class MySQLPartitionSplitSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest REORGANIZE PARTITION to split a RANGE/LIST partition."""

    def suggest_partition_split(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionSplitSuggestion:
        """Suggest REORGANIZE PARTITION -- MySQL's way to split a partition."""
        table = self._suggestion_table(plan)
        if table is None:
            return PartitionSplitSuggestion(False)
        if _word(strategy) not in _RANGE | _LIST:
            return PartitionSplitSuggestion(False)
        partition = _get(plan, "partition")
        into = self._suggestion_definitions(plan, "into")
        if not partition or not into or not self.supports_reorganize_partition():
            return PartitionSplitSuggestion(False)
        reorganize = MySQLReorganizePartitionExpression(self, table, str(partition), into)
        return PartitionSplitSuggestion((reorganize,))
