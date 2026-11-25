# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_scheme_change_suggestion.py
"""MySQL's answer to the partition-scheme-change migration decision point.

Only one transition has a real migration-time chain on this server: dropping
partitioning from an already partitioned table. The existing
``suggest_partition_table_alter`` suggestion turns the old strategy into
``MySQLRemovePartitioningExpression``, rendered by this dialect as ``ALTER TABLE
<t> REMOVE PARTITIONING``; this point delegates to it rather than building DDL.

The other transitions have no such chain. Adding partitioning to an existing
table needs a table rebuild (``suggest_partition_build`` returns a CREATE TABLE
clause, not an ALTER action), and MySQL cannot change one scheme into another
in place -- REORGANIZE PARTITION only redistributes partitions within the
current scheme. Both are answered explicit ``False``; no partition DDL is
invented here.
"""

from __future__ import annotations

from dataclasses import replace

from ....suggestion import PartitionSchemeChangeSuggestion
from ._change_projection import partition_strategy

__all__ = ["MySQLPartitionSchemeChangeSuggestionMixin"]


class MySQLPartitionSchemeChangeSuggestionMixin:
    """Reuse the existing REMOVE PARTITIONING chain where it applies."""

    def suggest_partition_scheme_change(
        self, point: PartitionSchemeChangeSuggestion
    ) -> PartitionSchemeChangeSuggestion:
        """Return the remove-partitioning chain, ``False`` or ``None``.

        ``None`` means the old and new projections agree. A partitioned table
        becoming unpartitioned delegates to ``suggest_partition_table_alter``
        with mode ``"remove"``. An unreadable old strategy, a table gaining
        partitioning, or a scheme-to-scheme change answers explicit ``False``.
        """
        old, new = point.old_partition, point.new_partition
        if old == new:
            return replace(point, operations=None)
        if old is None:
            return replace(point, operations=False)
        strategy = partition_strategy(self, old)
        if strategy is None:
            return replace(point, operations=False)
        if new is not None:
            return replace(point, operations=False)
        answer = self.suggest_partition_table_alter(
            strategy, {"table": point.table_name, "mode": "remove"}
        )
        return replace(point, operations=answer.operations)
