# src/rhosocial/activerecord/backend/impl/mysql/suggestion/partition_build_suggestion.py
"""MySQL's partition build suggestion.

Suggests the inline ``PARTITION BY`` clause for CREATE TABLE as a real chain of
this backend's clause nodes. RANGE/LIST need keys and definitions; HASH/KEY take
a partition count (KEY may have no keys). An unknown strategy or an incomplete
plan answers explicit ``False``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....expression.bases import BaseExpression
from ....suggestion import PartitionBuildSuggestion
from ..expression.partition import (
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
)
from ._common import (
    _ALL_STRATEGIES,
    _HASH,
    _LIST,
    _RANGE,
    MySQLPartitionSuggestionBase,
    _get,
    _word,
)

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy

__all__ = ["MySQLPartitionBuildSuggestionMixin"]


class MySQLPartitionBuildSuggestionMixin(MySQLPartitionSuggestionBase):
    """Suggest the inline ``PARTITION BY`` clause for CREATE TABLE."""

    def suggest_partition_build(
        self, strategy: "PartitionStrategy", plan: object
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
