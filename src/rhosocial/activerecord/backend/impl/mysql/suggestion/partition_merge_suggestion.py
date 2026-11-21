# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_merge_suggestion.py
"""MySQL's partition merge suggestion.

MySQL has no MERGE PARTITION statement; COALESCE only shrinks HASH/KEY by
count (a table_alter), so the answer is the explicit unsupported state
``False`` for every strategy. Unconditional, consults no probe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....suggestion import PartitionMergeSuggestion
from ._common import MySQLPartitionSuggestionBase

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionMergeSuggestionMixin"]


class MySQLPartitionMergeSuggestionMixin(MySQLPartitionSuggestionBase):
    """Answer MySQL's lack of MERGE PARTITION explicitly."""

    def suggest_partition_merge(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionMergeSuggestion:
        """MySQL has no MERGE PARTITION; COALESCE only shrinks HASH/KEY by count."""
        return PartitionMergeSuggestion(False)
