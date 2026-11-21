# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_drop_suggestion.py
"""MySQL's partition drop suggestion.

Suggests DROP PARTITION for one or more named partitions of a RANGE/LIST
table. HASH/KEY shrink via COALESCE PARTITION (table_alter), so they answer
explicit ``False``; a plan naming no partitions answers ``None``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....suggestion import PartitionDropSuggestion
from ..expression.partition import MySQLDropPartitionExpression
from ._common import (
    _LIST,
    _RANGE,
    MySQLPartitionSuggestionBase,
    _get,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionDropSuggestionMixin"]


class MySQLPartitionDropSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest DROP PARTITION for named RANGE/LIST partitions."""

    def suggest_partition_drop(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionDropSuggestion:
        """Suggest DROP PARTITION for one or more named partitions."""
        table = self._suggestion_table(plan)
        if table is None:
            return PartitionDropSuggestion(False)
        if _word(strategy) not in _RANGE | _LIST:
            # HASH/KEY shrink via COALESCE PARTITION (table_alter), not DROP PARTITION.
            return PartitionDropSuggestion(False)
        raw = _get(plan, "names")
        if raw is None:
            single = _get(plan, "partition")
            raw = [single] if single else None
        if not raw or not self.supports_drop_partition():
            return PartitionDropSuggestion(None if not raw else False)
        names = [str(name) for name in raw]
        return PartitionDropSuggestion((MySQLDropPartitionExpression(self, table, names),))
