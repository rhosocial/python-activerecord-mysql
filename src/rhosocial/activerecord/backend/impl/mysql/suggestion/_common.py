# src/rhosocial/activerecord/backend/impl/mysql/suggestion/_common.py
"""Shared helpers, constants and base class for MySQL's partition suggestions.

The eight partition suggestion mixins answer "how is each partition operation
done here" with expression nodes rather than SQL text. They all read the same
caller-owned, engine-neutral ``plan`` shape, so that shared knowledge lives
here: the normalisation/boundary helpers, the supported-strategy words, and
the plan-reading class methods carried by :class:`MySQLPartitionSuggestionBase`.

The clause/statement nodes come from this backend's ``expression.partition``
module; the suggestion value objects and the generic ``DROP TABLE`` statement
come from core. Each mixin keeps only its own ``suggest_partition_<x>()``
method plus that method's dedicated imports. Behaviour is unchanged by the
split.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional

from ....expression import Column
from ....expression.bases import BaseExpression
from ....expression.objects import Table
from ....expression.statements import PartitionDefinitionExpression
from ..expression.partition import MySQLPartitionMaxValue

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause

__all__ = ["MySQLPartitionSuggestionBase"]

# Boundary-comparison helpers live here so the suggestion mixins stay
# self-contained: with the partition-maintenance protocol retired, this layer
# is the single source for how MySQL performs each partition operation.
_MAXVALUE = object()


def _upper_bound_value(definition: "PartitionDefinitionExpression") -> Any:
    if definition.less_than is None:
        return None
    first = definition.less_than[0]
    if isinstance(first, MySQLPartitionMaxValue):
        return _MAXVALUE
    return getattr(first, "value", first)


def _comparable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        try:
            return datetime.combine(date.fromisoformat(text), time.min)
        except ValueError:
            return text
    if isinstance(value, (list, tuple)):
        return tuple(_comparable(item) for item in value)
    return value


def _compare(left: Any, right: Any) -> int:
    try:
        if left < right:
            return -1
        if left > right:
            return 1
        return 0
    except TypeError as error:
        raise ValueError(
            f"partition bound value {left!r} is not comparable to {right!r}"
        ) from error


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


def _word(strategy: "PartitionByClause") -> str:
    """Normalise a strategy clause (or a legacy str Enum) to an upper-case word.

    A strategy clause carries its word on ``.word`` (the artifact form) and
    ``.method`` (what the formatters read). A legacy str Enum instead carries
    ``.value``; accepting it keeps older callers working while the annotation
    moves to the expression node.
    """
    value = getattr(strategy, "word", None)
    if value is None:
        value = getattr(strategy, "method", None)
    if value is None:
        value = getattr(strategy, "value", strategy)
    return str(value).strip().upper()


class MySQLPartitionSuggestionBase:
    """Common base for MySQL's eight partition suggestion mixins.

    It carries the plan-reading helpers shared by every suggestion so all eight
    read the same caller-owned ``plan`` shape. It adds no protocol methods of
    its own; behaviour lives in the per-operation mixins.
    """

    def _suggestion_table(self, plan: Any) -> Optional[Table]:
        target = _get(plan, "table")
        if isinstance(target, Table):
            return target
        if isinstance(target, str) and target.strip():
            return Table(self, target)
        return None

    def _suggestion_definitions(
        self, plan: Any, name: str = "definitions"
    ) -> Optional[List[PartitionDefinitionExpression]]:
        raw = _get(plan, name)
        if raw is None:
            return None
        values = list(raw)
        if not values or not all(
            isinstance(value, PartitionDefinitionExpression) for value in values
        ):
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
