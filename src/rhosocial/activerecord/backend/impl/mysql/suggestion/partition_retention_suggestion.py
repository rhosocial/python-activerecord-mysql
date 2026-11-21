# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_retention_suggestion.py
"""MySQL's partition retention suggestion.

Suggests a DROP PARTITION chain for RANGE partitions whose upper bound is at or
below the plan's inclusive ``cutoff``. The newest partition is always kept,
because MySQL refuses to drop the last partition of a table. Tri-state: a real
chain, ``False`` when the strategy/plan cannot be answered, or ``None`` when
nothing needs dropping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from ....suggestion import PartitionRetentionSuggestion
from ..expression.partition import MySQLDropPartitionExpression
from ._common import (
    _MAXVALUE,
    _RANGE,
    MySQLPartitionSuggestionBase,
    _comparable,
    _compare,
    _get,
    _upper_bound_value,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionRetentionSuggestionMixin"]


class MySQLPartitionRetentionSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest DROP PARTITION for RANGE partitions older than a cutoff."""

    def suggest_partition_retention(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionRetentionSuggestion:
        """Suggest a DROP PARTITION chain for RANGE partitions older than the cutoff."""
        table = self._suggestion_table(plan)
        if table is None or _word(strategy) not in _RANGE:
            return PartitionRetentionSuggestion(False)
        definitions = self._suggestion_definitions(plan)
        cutoff = _get(plan, "cutoff")
        if not definitions or cutoff is None:
            return PartitionRetentionSuggestion(False)
        if not self.supports_drop_partition():
            return PartitionRetentionSuggestion(False)

        try:
            threshold = _comparable(cutoff)
            candidates: List[str] = []
            for definition in definitions:
                if definition.less_than is None:
                    return PartitionRetentionSuggestion(False)
                bound = _upper_bound_value(definition)
                if bound is _MAXVALUE:
                    continue
                if _compare(_comparable(bound), threshold) <= 0:
                    candidates.append(definition.name)
        except (TypeError, ValueError):
            return PartitionRetentionSuggestion(False)

        if not candidates:
            return PartitionRetentionSuggestion(None)
        if len(candidates) == len(definitions):
            # MySQL refuses to drop the last partition of a table.
            candidates = candidates[:-1]
            if not candidates:
                return PartitionRetentionSuggestion(None)
        drop = MySQLDropPartitionExpression(self, table, candidates)
        return PartitionRetentionSuggestion((drop,))
