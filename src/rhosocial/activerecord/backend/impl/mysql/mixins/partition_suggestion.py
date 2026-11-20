# src/rhosocial/activerecord/backend/impl/mysql/mixins/partition_suggestion.py
"""MySQLPartitionSuggestionMixin -- real MySQL answers for the 8 partition suggestions.

The eight ``suggest_partition_*`` methods turn a caller-supplied ``plan`` into
ordered chains of this backend's own expression nodes. Nothing here renders SQL:
every operation is a real statement/clause from ``...expression.partition`` (or
``DropTableStatement`` for the whole-table case), and the dialect formatter owns
the spelling exactly as it does for the maintenance helper.

``plan`` is opaque to the core protocol, so this mixin reads a small, documented
set of fields from either a mapping or an object with attributes:

* ``table``        -- target table name (``str``) or a ready ``Table`` object;
* ``keys``         -- build keys: ``BaseExpression`` nodes or column-name strings;
* ``definitions``  -- ``MySQLPartitionDefinition`` nodes (build/add/retention);
* ``partitions_count`` -- integer partition count for HASH/KEY build;
* ``subpartition_by``  -- optional ``MySQLSubpartitionClause`` for build;
* ``partition``    -- partition name to REORGANIZE/SPLIT;
* ``into``         -- replacement ``MySQLPartitionDefinition`` nodes for REORGANIZE;
* ``names``        -- partition name(s) to DROP;
* ``cutoff``       -- inclusive retention upper bound (RANGE only);
* ``mode``         -- table_alter ``"remove"`` (default) or ``"coalesce"``;
* ``count``        -- number of partitions to remove for ``"coalesce"``.

Tri-state result: a tuple of expressions when a real chain exists, ``False``
when MySQL has no such mechanism for the strategy/plan, ``None`` when nothing
needs doing. The capability probes on ``MySQLPartitionMixin`` gate every
mutating chain, so a dialect that withdraws a feature answers ``False`` rather
than emitting SQL the server would reject.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, List, Optional, TYPE_CHECKING

from ....expression import (
    Column,
    DropTableStatement,
    PartitionAddSuggestion,
    PartitionBuildSuggestion,
    PartitionDropSuggestion,
    PartitionMergeSuggestion,
    PartitionRetentionSuggestion,
    PartitionSplitSuggestion,
    PartitionTableAlterSuggestion,
    PartitionTableDropSuggestion,
)
from ....expression.bases import BaseExpression
from ....expression.objects import Table
from ..expression.partition import (
    MySQLAddPartitionExpression,
    MySQLCoalescePartitionExpression,
    MySQLDropPartitionExpression,
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
    MySQLPartitionDefinition,
    MySQLRemovePartitioningExpression,
    MySQLReorganizePartitionExpression,
)
from ..partition_maintenance import _MAXVALUE, _comparable, _compare, _upper_bound_value

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionSuggestionMixin"]

_RANGE = frozenset({"RANGE", "RANGE COLUMNS"})
_LIST = frozenset({"LIST", "LIST COLUMNS"})
_HASH = frozenset({"HASH", "LINEAR HASH"})
_KEY = frozenset({"KEY", "LINEAR KEY"})
_ALL_STRATEGIES = _RANGE | _LIST | _HASH | _KEY


def _get(plan: Any, name: str, default: Any = None) -> Any:
    """Read one field from a mapping-shaped or attribute-shaped plan."""
    if plan is None:
        return default
    if isinstance(plan, Mapping):
        return plan.get(name, default)
    return getattr(plan, name, default)


def _word(strategy: "PartitionStrategy") -> str:
    """Normalise a strategy member or its spelling to an upper-case word."""
    value = getattr(strategy, "value", strategy)
    return str(value).strip().upper()


class MySQLPartitionSuggestionMixin:
    """Suggest MySQL's real DDL action chains for partition lifecycle points."""

    # -- shared helpers --------------------------------------------------

    def _suggestion_table(self, plan: Any) -> Optional[Table]:
        target = _get(plan, "table")
        if isinstance(target, Table):
            return target
        if isinstance(target, str) and target.strip():
            return Table(self, target)
        return None

    def _suggestion_definitions(
        self,
        plan: Any,
        name: str = "definitions",
    ) -> Optional[List[MySQLPartitionDefinition]]:
        raw = _get(plan, name)
        if raw is None:
            return None
        values = list(raw)
        if not values or not all(isinstance(value, MySQLPartitionDefinition) for value in values):
            return None
        return values

    def _suggestion_keys(self, plan: Any) -> Optional[List[BaseExpression]]:
        raw = _get(plan, "keys")
        if raw is None:
            return None
        keys: List[BaseExpression] = []
        for key in raw:
            if isinstance(key, BaseExpression):
                keys.append(key)
            elif isinstance(key, str) and key.strip():
                keys.append(Column(self, key))
            else:
                return None
        return keys or None

    # -- 1. build --------------------------------------------------------

    def suggest_partition_build(
        self,
        strategy: "PartitionStrategy",
        plan: object,
    ) -> PartitionBuildSuggestion:
        """Suggest the inline ``PARTITION BY`` clause for CREATE TABLE."""
        word = _word(strategy)
        if word not in _ALL_STRATEGIES:
            return PartitionBuildSuggestion(False)
        subpartition_by = _get(plan, "subpartition_by")

        if word in _RANGE or word in _LIST:
            keys = self._suggestion_keys(plan)
            definitions = self._suggestion_definitions(plan)
            if not keys or not definitions:
                return PartitionBuildSuggestion(False)
            clause_class = {
                "RANGE": MySQLPartitionByRange,
                "RANGE COLUMNS": MySQLPartitionByRangeColumns,
                "LIST": MySQLPartitionByList,
                "LIST COLUMNS": MySQLPartitionByListColumns,
            }[word]
            clause = clause_class(
                self,
                keys,
                partitions=definitions,
                subpartition_by=subpartition_by,
            )
            return PartitionBuildSuggestion((clause,))

        count = _get(plan, "partitions_count")
        if count is not None and (not isinstance(count, int) or count <= 0):
            return PartitionBuildSuggestion(False)
        linear = word in {"LINEAR HASH", "LINEAR KEY"}
        if word in _HASH:
            keys = self._suggestion_keys(plan)
            if not keys:
                return PartitionBuildSuggestion(False)
            clause: BaseExpression = MySQLPartitionByHash(
                self,
                keys,
                partitions_count=count,
                linear=linear,
            )
        else:  # KEY / LINEAR KEY -- an empty key list is legal (KEY()).
            keys_or_none = self._suggestion_keys(plan)
            clause = MySQLPartitionByKey(
                self,
                keys_or_none,
                partitions_count=count,
                linear=linear,
            )
        return PartitionBuildSuggestion((clause,))

    # -- 2. table_drop ---------------------------------------------------

    def suggest_partition_table_drop(
        self,
        strategy: "PartitionStrategy",
        plan: object,
    ) -> PartitionTableDropSuggestion:
        """Suggest dropping the whole partitioned table (not REMOVE PARTITIONING)."""
        table = self._suggestion_table(plan)
        if table is None:
            return PartitionTableDropSuggestion(False)
        return PartitionTableDropSuggestion((DropTableStatement(self, table),))

    # -- 3. table_alter --------------------------------------------------

    def suggest_partition_table_alter(
        self,
        strategy: "PartitionStrategy",
        plan: object,
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

    # -- 4. add ----------------------------------------------------------

    def suggest_partition_add(
        self,
        strategy: "PartitionStrategy",
        plan: object,
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

    # -- 5. drop ---------------------------------------------------------

    def suggest_partition_drop(
        self,
        strategy: "PartitionStrategy",
        plan: object,
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

    # -- 6. split --------------------------------------------------------

    def suggest_partition_split(
        self,
        strategy: "PartitionStrategy",
        plan: object,
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

    # -- 7. merge --------------------------------------------------------

    def suggest_partition_merge(
        self,
        strategy: "PartitionStrategy",
        plan: object,
    ) -> PartitionMergeSuggestion:
        """MySQL has no MERGE PARTITION; COALESCE only shrinks HASH/KEY by count."""
        return PartitionMergeSuggestion(False)

    # -- 8. retention ----------------------------------------------------

    def suggest_partition_retention(
        self,
        strategy: "PartitionStrategy",
        plan: object,
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
