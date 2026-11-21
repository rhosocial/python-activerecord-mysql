# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_add_suggestion.py
"""MySQL's partition add suggestion.

Suggests ADD PARTITION above the maximum, or REORGANIZE PARTITION inside a
RANGE/LIST partition when the plan names one and its replacements. HASH/KEY
growth has no expression node here, so it answers explicit ``False``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....suggestion import PartitionAddSuggestion
from ..expression.partition import (
    MySQLAddPartitionExpression,
    MySQLReorganizePartitionExpression,
)
from ._common import (
    _LIST,
    _RANGE,
    MySQLPartitionSuggestionBase,
    _get,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionAddSuggestionMixin"]


class MySQLPartitionAddSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest ADD PARTITION or REORGANIZE PARTITION for a RANGE/LIST table."""

    def suggest_partition_add(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionAddSuggestion:
        """Suggest ADD PARTITION above the maximum, or REORGANIZE inside a range."""
        table = self._suggestion_table(plan)
        if table is None:
            return PartitionAddSuggestion(False)
        word = _word(strategy)
        if word not in _RANGE | _LIST:
            # MySQL spells HASH/KEY growth as ``ADD PARTITION PARTITIONS n``, for
            # which this backend has no expression node; decline rather than fabricate SQL.
            return PartitionAddSuggestion(False)

        partition = _get(plan, "partition")
        into = self._suggestion_definitions(plan, "into")
        if partition is not None and into:
            if not self.supports_reorganize_partition():
                return PartitionAddSuggestion(False)
            reorganize = MySQLReorganizePartitionExpression(self, table, str(partition), into)
            return PartitionAddSuggestion((reorganize,))

        definitions = self._suggestion_definitions(plan)
        if definitions and self.supports_add_partition():
            return PartitionAddSuggestion((MySQLAddPartitionExpression(self, table, definitions),))
        return PartitionAddSuggestion(False)
