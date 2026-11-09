# src/rhosocial/activerecord/backend/impl/mysql/partition_maintenance.py
"""Backend-level MySQL partition maintenance helpers.

The expression layer builds one statement at a time.  This module supplies the
four operations an application needs around that layer:

* ``ensure`` -- add the partitions a plan declares that the table does not have;
* ``list`` -- read ``information_schema.PARTITIONS`` into a small report;
* ``validate`` -- compare the catalogue with a plan without repairing anything;
* ``drop_before`` -- drop the partitions whose whole range is older than a
  caller-supplied cutoff, dry-run by default.

The module deliberately carries no table names, retention defaults, or
calendar vocabulary.  A plan is a caller-owned list of partition definitions,
so the application decides which partitions exist and how long they live.

MySQL notes that shape the API:

* RANGE partitions must be added in ascending order.  A partition missing
  above the current maximum is appended with ``ADD PARTITION``; one missing
  inside an existing range is created by reorganising the partition that
  contains it, because ``ADD PARTITION`` would be rejected.
* Adding after a ``MAXVALUE`` partition is impossible without reorganising
  that partition; ``ensure`` folds the new definitions into it and keeps a
  trailing ``MAXVALUE`` definition.
* When a catalogue boundary disagrees with the plan, or cannot be read as a
  RANGE bound, ``ensure`` refuses the change and reports every missing
  definition in ``skipped``.  A refusal is never silently turned into success.
* ``DROP PARTITION`` cannot remove the last partition of a table.  When the
  cutoff would remove every existing partition, the newest candidate is kept
  and reported.

These rules are reported, never silently worked around.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    FunctionCall,
    Literal,
    LogicalPredicate,
    OrderByClause,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.partition import PartitionInfo, PartitionReport

from .expression.partition import (
    MySQLAddPartitionExpression,
    MySQLDropPartitionExpression,
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
    MySQLReorganizePartitionExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.backend.async_backend import (
        AsyncMySQLBackend,
    )
    from rhosocial.activerecord.backend.impl.mysql.backend.backend import MySQLBackend

__all__ = [
    "MySQLPartitionInfo",
    "MySQLPartitionPlan",
    "MySQLPartitionReport",
    "MySQLPartitionChange",
    "MySQLPartitionMaintenance",
    "AsyncMySQLPartitionMaintenance",
    "plan_additions",
    "plan_changes",
    "select_drops",
]

#: Sentinel used when a plan's upper bound is ``MAXVALUE``.
_MAXVALUE = object()

# The report value objects come from the core contract. The module keeps its
# historical names so callers and tests do not depend on the import path.
MySQLPartitionInfo = PartitionInfo
MySQLPartitionReport = PartitionReport


@dataclass(frozen=True)
class MySQLPartitionPlan:
    """A caller-owned set of partition definitions.

    The plan does not say how to lay out a calendar; it only lists the
    definitions that must exist.  Definitions must carry unique names.  When
    all definitions use ``less_than`` (RANGE), they must also be in ascending
    order, because that is the order ``ALTER TABLE ... ADD PARTITION``
    executes them in.

    Attributes:
        table: Target table name.
        definitions: Partition definitions in declaration order.

    Raises:
        ValueError: if the table name is blank, the list is empty, names
            repeat, or RANGE definitions are not in ascending order.
    """

    table: str
    definitions: Tuple[MySQLPartitionDefinition, ...]

    def __post_init__(self) -> None:
        if not self.table or not self.table.strip():
            raise ValueError("table must be a non-empty string")
        if not self.definitions:
            raise ValueError("definitions must not be empty")

        names = [definition.name for definition in self.definitions]
        if len(set(names)) != len(names):
            raise ValueError("partition names in a plan must be unique")

        bounds = [_upper_bound_value(definition) for definition in self.definitions]
        if all(bound is not None for bound in bounds):
            previous = None
            for index, (definition, bound) in enumerate(zip(self.definitions, bounds)):
                if bound is _MAXVALUE:
                    if index != len(self.definitions) - 1:
                        raise ValueError(
                            "a MAXVALUE partition must be the last definition in a plan"
                        )
                    continue
                key = _comparable(bound)
                if previous is not None and _compare(key, previous) <= 0:
                    raise ValueError(
                        "RANGE partition definitions must be in ascending order: "
                        f"{definition.name} does not advance the upper bound"
                    )
                previous = key
        elif any(bound is not None for bound in bounds):
            raise ValueError(
                "a plan must use either less_than (RANGE) or in_values (LIST) "
                "definitions, not both"
            )


@dataclass(frozen=True)
class MySQLPartitionChange:
    """One partition statement ``ensure`` plans to run.

    Attributes:
        action: ``"add"`` for ``ALTER TABLE ... ADD PARTITION`` or
            ``"reorganize"`` for ``ALTER TABLE ... REORGANIZE PARTITION``.
        partition: The partition a ``REORGANIZE`` acts on; ``None`` for an
            ``ADD``.
        definitions: The partition definitions the statement carries, in the
            order the formatter renders them.  A ``REORGANIZE`` carries the
            definitions that replace the named partition, including the
            surviving name that closes the range.
    """

    action: str
    partition: Optional[str]
    definitions: Tuple[MySQLPartitionDefinition, ...]


@dataclass(frozen=True)
class _CatalogBound:
    """One top-level catalogue row reduced to its name, bound and method."""

    name: str
    bound: Any
    method: Optional[str]


def _upper_bound_value(definition: MySQLPartitionDefinition) -> Any:
    """Return the first ``less_than`` value, ``_MAXVALUE``, or ``None``."""
    if definition.less_than is None:
        return None
    first = definition.less_than[0]
    if isinstance(first, MySQLPartitionMaxValue):
        return _MAXVALUE
    return getattr(first, "value", first)


def _comparable(value: Any) -> Any:
    """Normalise a boundary value for ordering and cutoff comparisons."""
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
    """Compare two normalised values, refusing incomparable kinds."""
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


def _display_bound(value: Any) -> str:
    """Render one boundary value for a human-readable finding."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _split_bound_items(text: str) -> List[str]:
    """Split a catalogue boundary description on top-level commas."""
    items: List[str] = []
    current = ""
    depth = 0
    quote: Optional[str] = None
    for character in text:
        if quote is not None:
            current += character
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            current += character
            continue
        if character == "(":
            depth += 1
            current += character
            continue
        if character == ")":
            depth -= 1
            current += character
            continue
        if character == "," and depth == 0:
            items.append(current)
            current = ""
            continue
        current += character
    items.append(current)
    return items


def _parse_catalog_scalar(text: str) -> Any:
    """Turn one catalogue value back into a comparable Python value."""
    value = text.strip()
    while len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        if value[0] in value[1:-1]:
            break
        value = value[1:-1].strip()
    value = value.replace("''", "'")
    if not value:
        return value
    if value.upper() == "MAXVALUE":
        return _MAXVALUE
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return Decimal(value)
    except (ArithmeticError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.combine(date.fromisoformat(value), time.min)
    except ValueError:
        return value


def _strip_bound_quotes(text: Optional[str]) -> Optional[str]:
    """Strip a single quoted literal, leaving a multi-value list intact."""
    if text is None:
        return None
    value = text.strip()
    if value.upper() == "MAXVALUE":
        return "MAXVALUE"
    if (
        len(value) >= 2
        and value[0] in {"'", '"'}
        and value[-1] == value[0]
        and value[0] not in value[1:-1]
    ):
        return value[1:-1].strip()
    return value


def _catalog_bound_value(text: Optional[str]) -> Any:
    """Parse a catalogue ``PARTITION_DESCRIPTION`` into a comparable value."""
    value = _strip_bound_quotes(text)
    if value is None:
        return None
    if value.upper() == "MAXVALUE":
        return _MAXVALUE
    if value.startswith("(") and value.endswith(")"):
        items = _split_bound_items(value[1:-1])
        return tuple(_parse_catalog_scalar(item) for item in items)
    return _parse_catalog_scalar(value)


def _range_bound_key(definition: MySQLPartitionDefinition) -> Any:
    """Return the plan's RANGE upper bound as a comparable scalar or tuple."""
    values = definition.less_than or ()
    if any(isinstance(value, MySQLPartitionMaxValue) for value in values):
        return _MAXVALUE
    parts = [_comparable(getattr(value, "value", value)) for value in values]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else tuple(parts)


def _list_bound_key(definition: MySQLPartitionDefinition) -> Tuple[Any, ...]:
    """Return the plan's LIST boundary values as comparable tuple rows."""
    rows: List[Any] = []
    for item in definition.in_values or ():
        if isinstance(item, (list, tuple)):
            rows.append(tuple(_comparable(getattr(value, "value", value)) for value in item))
        else:
            rows.append(_comparable(getattr(item, "value", item)))
    return tuple(rows)


def _plan_boundary_text(definition: MySQLPartitionDefinition) -> str:
    """Render the plan's boundary in a form a finding can quote."""
    if definition.less_than is not None:
        values = definition.less_than
        if any(isinstance(value, MySQLPartitionMaxValue) for value in values):
            return "MAXVALUE"
        parts = [_display_bound(getattr(value, "value", value)) for value in values]
        return parts[0] if len(parts) == 1 else "(" + ", ".join(parts) + ")"
    rows = []
    for item in definition.in_values or ():
        if isinstance(item, (list, tuple)):
            inner = ", ".join(_display_bound(getattr(value, "value", value)) for value in item)
            rows.append(f"({inner})")
        else:
            rows.append(_display_bound(getattr(item, "value", item)))
    return ", ".join(rows)


def _plan_method(definition: MySQLPartitionDefinition) -> str:
    """Return the strategy family a plan definition declares."""
    return "RANGE" if definition.less_than is not None else "LIST"


def _method_matches(reported: Optional[str], expected: str) -> bool:
    """Return whether a catalogue method word belongs to the expected family."""
    word = (reported or "").strip().upper()
    if not word:
        return False
    return word.startswith(expected)


def _catalog_method_matches(definition: MySQLPartitionDefinition, reported: Optional[str]) -> bool:
    """Return whether the catalogue method agrees with the plan definition."""
    return _method_matches(reported, _plan_method(definition))


def _range_bound_matches(definition: MySQLPartitionDefinition, catalog_value: Any) -> bool:
    """Return whether a parsed catalogue bound equals the plan's RANGE bound."""
    expected = _range_bound_key(definition)
    if expected is _MAXVALUE or catalog_value is _MAXVALUE:
        return expected is _MAXVALUE and catalog_value is _MAXVALUE
    if catalog_value is None:
        return False
    if (
        isinstance(catalog_value, tuple)
        and len(catalog_value) == 1
        and not isinstance(expected, tuple)
    ):
        catalog_value = catalog_value[0]
    return expected == catalog_value


def _list_bound_matches(definition: MySQLPartitionDefinition, catalog_value: Any) -> bool:
    """Return whether a parsed catalogue bound equals the plan's LIST row set."""
    expected = _list_bound_key(definition)
    if not isinstance(catalog_value, tuple):
        return False
    actual = catalog_value
    if (
        len(actual) == 1
        and isinstance(actual[0], tuple)
        and expected
        and not isinstance(expected[0], tuple)
    ):
        actual = actual[0]
    return actual == expected


def _catalog_list_value(text: Optional[str]) -> Any:
    """Parse a LIST ``PARTITION_DESCRIPTION`` into comparable tuple rows."""
    value = _strip_bound_quotes(text)
    if value is None:
        return None
    if value.upper() == "MAXVALUE":
        return None
    rows: List[Any] = []
    for item in _split_bound_items(value):
        stripped = item.strip()
        if stripped.startswith("(") and stripped.endswith(")"):
            inner = _split_bound_items(stripped[1:-1])
            rows.append(tuple(_parse_catalog_scalar(part) for part in inner))
        else:
            rows.append(_parse_catalog_scalar(stripped))
    return tuple(rows)


def _catalog_bound_matches(definition: MySQLPartitionDefinition, text: Optional[str]) -> bool:
    """Return whether a catalogue description agrees with a plan definition."""
    if definition.less_than is not None:
        return _range_bound_matches(definition, _catalog_bound_value(text))
    return _list_bound_matches(definition, _catalog_list_value(text))


def _top_level_infos(report: MySQLPartitionReport) -> List[PartitionInfo]:
    """Return the report's first-level partitions."""
    return [info for info in report.partitions if info.parent is None]


def _bound_sort_key(bound: Any) -> Tuple[int, Any]:
    """Sort finite bounds ascending and MAXVALUE last."""
    if bound is _MAXVALUE:
        return (1, 0)
    return (0, bound)


def _ordered_definitions(plan: MySQLPartitionPlan) -> List[MySQLPartitionDefinition]:
    """Return RANGE definitions in plan order; refuse LIST plans."""
    if any(definition.less_than is None for definition in plan.definitions):
        raise ValueError(
            "drop_before applies only to RANGE plans (definitions with less_than)"
        )
    return list(plan.definitions)


def plan_additions(
    plan: MySQLPartitionPlan,
    existing_names: Sequence[str],
) -> Tuple[List[MySQLPartitionDefinition], List[Tuple[str, str]]]:
    """Return the definitions an append-only ``ADD PARTITION`` may carry.

    This helper answers only the append question: it never plans
    ``REORGANIZE PARTITION``.  ``ensure`` uses :func:`plan_changes`, which
    folds a trailing ``MAXVALUE`` and fills intermediate gaps.  A caller that
    wants the complete plan should use that function too.

    Args:
        plan: Caller-owned plan.
        existing_names: Top-level partition names currently on the table.

    Returns:
        ``(additions, skipped)``.  ``additions`` are in plan order and can be
        sent in one ``ALTER TABLE ... ADD PARTITION`` statement.  ``skipped``
        pairs a definition name with the reason it cannot be appended.

    Raises:
        ValueError: if the plan mixes RANGE and LIST definitions, or an
            existing partition is not named by the plan (its bound is then
            unknown, so no safe insertion point exists).
    """
    existing = set(existing_names)
    missing = [definition for definition in plan.definitions if definition.name not in existing]
    if not missing:
        return [], []

    bounds = [_upper_bound_value(definition) for definition in plan.definitions]
    is_range = all(bound is not None for bound in bounds)
    if not is_range and any(bound is not None for bound in bounds):
        raise ValueError(
            "a plan must use either less_than (RANGE) or in_values (LIST) "
            "definitions, not both"
        )

    if not is_range:
        # LIST values are independent, so missing definitions can simply be added.
        return missing, []

    skipped: List[Tuple[str, str]] = []
    existing_definitions = [
        definition for definition in plan.definitions if definition.name in existing
    ]
    unknown = existing - {definition.name for definition in existing_definitions}
    if unknown:
        for definition in missing:
            skipped.append(
                (
                    definition.name,
                    "existing partition(s) not named by the plan make the "
                    "current upper bound unknown; include them in the plan",
                )
            )
        return [], skipped

    current_max = None
    for definition in existing_definitions:
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            for candidate in missing:
                skipped.append(
                    (
                        candidate.name,
                        "the table already has a MAXVALUE partition; "
                        "REORGANIZE PARTITION is required",
                    )
                )
            return [], skipped
        key = _comparable(bound)
        if current_max is None or _compare(key, current_max) > 0:
            current_max = key

    additions: List[MySQLPartitionDefinition] = []
    for definition in missing:
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            additions.append(definition)
            current_max = None
            continue
        key = _comparable(bound)
        if current_max is not None and _compare(key, current_max) <= 0:
            skipped.append(
                (
                    definition.name,
                    "upper bound is not above the current maximum; "
                    "REORGANIZE PARTITION is required",
                )
            )
            continue
        additions.append(definition)
        current_max = key

    return additions, skipped


def _definition_from_bound(
    dialect: Any,
    name: str,
    bound: Any,
) -> MySQLPartitionDefinition:
    """Build a definition for an existing partition the plan does not name."""
    if bound is _MAXVALUE:
        return MySQLPartitionDefinition(name, less_than=[MySQLPartitionMaxValue(dialect)])
    if isinstance(bound, tuple):
        return MySQLPartitionDefinition(
            name,
            less_than=[MySQLPartitionValue(dialect, part) for part in bound],
        )
    return MySQLPartitionDefinition(
        name,
        less_than=[MySQLPartitionValue(dialect, bound)],
    )


def plan_changes(
    plan: MySQLPartitionPlan,
    report: MySQLPartitionReport,
    dialect: Any,
) -> Tuple[List[MySQLPartitionChange], List[Tuple[str, str]]]:
    """Plan the statements ``ensure`` needs to reconcile a plan with a report.

    The catalog bounds decide where each missing definition belongs:

    * a missing bound above every finite catalogue bound is appended with
      ``ADD PARTITION``;
    * a missing bound inside an existing partition's range is created by
      ``REORGANIZE PARTITION`` on that partition, preserving its upper bound;
    * a missing bound above the last finite partition while a ``MAXVALUE``
      partition exists is folded into that ``MAXVALUE`` partition, which is
      redefined last so the range stays closed.

    A catalogue method or boundary that disagrees with the plan makes every
    split point uncertain, so the whole request is refused.  A bound that
    cannot be read, a range already covered by another partition, and a
    second ``MAXVALUE`` partition are refused individually.

    Args:
        plan: Caller-owned plan.
        report: Current catalogue report, as returned by ``list``.
        dialect: MySQL dialect used to build definitions for orphan partitions.

    Returns:
        ``(changes, skipped)``.  ``changes`` are statements to run in order;
        ``skipped`` pairs a definition name with the reason it was refused.

    Raises:
        ValueError: if the plan mixes RANGE and LIST definitions.
    """
    existing = set(report.partition_names)
    missing = [
        definition for definition in plan.definitions if definition.name not in existing
    ]
    if not missing:
        return [], []

    bounds = [_upper_bound_value(definition) for definition in plan.definitions]
    is_range = all(bound is not None for bound in bounds)
    if not is_range:
        if any(bound is not None for bound in bounds):
            raise ValueError(
                "a plan must use either less_than (RANGE) or in_values (LIST) "
                "definitions, not both"
            )
        return [MySQLPartitionChange("add", None, tuple(missing))], []

    catalog = _top_level_infos(report)
    if not catalog:
        return [], [
            (
                definition.name,
                "the table has no partitions; ADD PARTITION cannot partition "
                "a non-partitioned table",
            )
            for definition in missing
        ]

    for info in catalog:
        if not _method_matches(info.method, "RANGE"):
            return [], [
                (
                    definition.name,
                    f"the catalogue reports method {info.method or 'unknown'} "
                    "but the plan declares RANGE",
                )
                for definition in missing
            ]

    entries: List[_CatalogBound] = []
    unknown: List[str] = []
    for info in catalog:
        parsed = _catalog_bound_value(info.bound)
        if parsed is None:
            unknown.append(info.name)
        else:
            entries.append(_CatalogBound(info.name, parsed, info.method))
    if unknown:
        reason = (
            f"the boundary of existing partition {unknown[0]} cannot be read "
            "as a RANGE bound"
        )
        return [], [(definition.name, reason) for definition in missing]

    plan_by_name = {definition.name: definition for definition in plan.definitions}
    for entry in entries:
        definition = plan_by_name.get(entry.name)
        if definition is None:
            continue
        if not _catalog_method_matches(definition, entry.method):
            reason = (
                f"existing partition {entry.name} uses method "
                f"{entry.method or 'unknown'} but the plan declares "
                f"{_plan_method(definition)}"
            )
            return [], [(candidate.name, reason) for candidate in missing]
        if not _range_bound_matches(definition, entry.bound):
            reason = (
                f"existing partition {entry.name} ends at "
                f"{_display_bound(entry.bound)} but the plan declares "
                f"{_plan_boundary_text(definition)}"
            )
            return [], [(candidate.name, reason) for candidate in missing]

    try:
        entries.sort(key=lambda entry: _bound_sort_key(entry.bound))
    except TypeError:
        reason = "catalogue RANGE bounds are not mutually comparable"
        return [], [(definition.name, reason) for definition in missing]

    maxvalues = [entry for entry in entries if entry.bound is _MAXVALUE]
    if len(maxvalues) > 1:
        reason = "the catalogue reports more than one MAXVALUE partition"
        return [], [(definition.name, reason) for definition in missing]

    skipped: List[Tuple[str, str]] = []
    groups: Dict[str, Dict[str, Any]] = {}
    group_order: List[str] = []
    appends: List[MySQLPartitionDefinition] = []
    missing_maxvalue: List[MySQLPartitionDefinition] = []

    for definition in missing:
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            missing_maxvalue.append(definition)
            continue
        key = _comparable(bound)
        successor: Optional[_CatalogBound] = None
        lower: Any = None
        lower_name: Optional[str] = None
        try:
            for entry in entries:
                if entry.bound is _MAXVALUE:
                    successor = entry
                    break
                if _compare(entry.bound, key) > 0:
                    successor = entry
                    break
                lower = entry.bound
                lower_name = entry.name
        except (TypeError, ValueError) as error:
            skipped.append(
                (
                    definition.name,
                    f"bound {_plan_boundary_text(definition)} cannot be compared "
                    f"with the catalogue: {error}",
                )
            )
            continue

        if successor is None:
            appends.append(definition)
            continue
        if lower is not None and _compare(key, lower) <= 0:
            skipped.append(
                (
                    definition.name,
                    f"the range is already covered: existing partition "
                    f"{lower_name} ends at {_display_bound(lower)} and "
                    f"{definition.name} ends at {_display_bound(key)}",
                )
            )
            continue

        if successor.name not in groups:
            groups[successor.name] = {"entry": successor, "missing": []}
            group_order.append(successor.name)
        groups[successor.name]["missing"].append(definition)

    existing_maxvalue = maxvalues[0] if maxvalues else None
    for definition in missing_maxvalue:
        if existing_maxvalue is not None:
            skipped.append(
                (
                    definition.name,
                    f"the table already has MAXVALUE partition "
                    f"{existing_maxvalue.name}; MySQL refuses a second "
                    "MAXVALUE partition",
                )
            )
            continue
        appends.append(definition)

    changes: List[MySQLPartitionChange] = []
    for name in group_order:
        group = groups[name]
        successor = group["entry"]
        closing = plan_by_name.get(successor.name) or _definition_from_bound(
            dialect,
            successor.name,
            successor.bound,
        )
        changes.append(
            MySQLPartitionChange(
                "reorganize",
                successor.name,
                tuple(group["missing"]) + (closing,),
            )
        )

    if appends:
        append_names = {definition.name for definition in appends}
        ordered = [
            definition
            for definition in plan.definitions
            if definition.name in append_names
        ]
        changes.append(MySQLPartitionChange("add", None, tuple(ordered)))

    return changes, skipped


def _change_expression(
    dialect: Any,
    table: str,
    change: MySQLPartitionChange,
) -> Any:
    """Build the expression for one planned partition change."""
    target = Table(dialect, table)
    if change.action == "add":
        return MySQLAddPartitionExpression(dialect, target, list(change.definitions))
    if change.action == "reorganize":
        if change.partition is None:
            raise ValueError("a reorganize change requires a partition name")
        return MySQLReorganizePartitionExpression(
            dialect,
            target,
            change.partition,
            list(change.definitions),
        )
    raise ValueError(f"unknown partition change action {change.action!r}")


def select_drops(
    plan: MySQLPartitionPlan,
    existing_names: Sequence[str],
    cutoff: Any,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Return the partitions ``drop_before`` may drop and the skipped ones.

    A partition is a candidate when its whole range is older than ``cutoff``:
    its upper bound (the first column, for multi-column RANGE) is less than or
    equal to the cutoff.  The newest candidate is kept when dropping all
    existing partitions would make the table non-partitioned, because MySQL
    refuses to drop the last partition.

    Returns:
        ``(dropped, skipped)``.

    Raises:
        ValueError: if the plan is not RANGE, or a bound and the cutoff are
            not comparable.
    """
    existing = set(existing_names)
    ordered = _ordered_definitions(plan)
    threshold = _comparable(cutoff)

    candidates: List[MySQLPartitionDefinition] = []
    for definition in ordered:
        if definition.name not in existing:
            continue
        bound = _upper_bound_value(definition)
        if bound is _MAXVALUE:
            continue
        if _compare(_comparable(bound), threshold) <= 0:
            candidates.append(definition)

    skipped: List[Tuple[str, str]] = []
    if candidates and len(candidates) == len(existing):
        keep = candidates[-1]
        candidates = candidates[:-1]
        skipped.append(
            (
                keep.name,
                "keeping the newest partition; MySQL cannot drop the last "
                "partition of a table",
            )
        )

    return [definition.name for definition in candidates], skipped


def _metadata_expression(dialect: Any, table: str) -> QueryStatement:
    """Build the ``information_schema.PARTITIONS`` query for one table."""
    partitions = Table(dialect, "PARTITIONS", catalog_name="information_schema")
    return QueryStatement(
        dialect,
        select=[
            Column(dialect, "PARTITION_NAME", alias="name"),
            Column(dialect, "SUBPARTITION_NAME", alias="subname"),
            Column(dialect, "PARTITION_METHOD", alias="method"),
            Column(dialect, "SUBPARTITION_METHOD", alias="submethod"),
            Column(dialect, "PARTITION_DESCRIPTION", alias="description"),
            Column(dialect, "TABLE_ROWS", alias="table_rows"),
            Column(dialect, "DATA_LENGTH", alias="data_length"),
            Column(dialect, "INDEX_LENGTH", alias="index_length"),
        ],
        from_=partitions,
        where=LogicalPredicate(
            dialect,
            "AND",
            ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "TABLE_SCHEMA"),
                FunctionCall(dialect, "DATABASE"),
            ),
            ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "TABLE_NAME"),
                Literal(dialect, table),
            ),
            Column(dialect, "PARTITION_NAME").is_not_null(),
        ),
        order_by=OrderByClause(
            dialect,
            [
                (Column(dialect, "PARTITION_NAME"), "ASC"),
                (Column(dialect, "SUBPARTITION_NAME"), "ASC"),
            ],
        ),
    )


def build_report(table: str, rows: Sequence[Any]) -> MySQLPartitionReport:
    """Turn ``information_schema.PARTITIONS`` rows into a partition tree.

    Args:
        table: Table name.
        rows: Mapping-like rows with the aliases used by
            :func:`_metadata_expression`.

    Returns:
        A report whose ``partitions`` are top-level entries first, each
        carrying its children, followed by the child entries themselves.
    """
    groups: Dict[str, List[Any]] = {}
    for row in rows:
        name = row["name"]
        groups.setdefault(name, []).append(row)

    infos: List[MySQLPartitionInfo] = []
    for name, group in groups.items():
        subnames = [row["subname"] for row in group if row["subname"] is not None]
        method = group[0]["method"]
        description = group[0]["description"]

        def _sum(key: str, group: List[Any] = group) -> Optional[int]:
            values = [row[key] for row in group if row[key] is not None]
            return sum(int(value) for value in values) if values else None

        infos.append(
            PartitionInfo(
                name=name,
                level=1,
                method=method,
                bound=str(description) if description is not None else None,
                row_count=_sum("table_rows"),
                size_bytes=(
                    (_sum("data_length") or 0) + (_sum("index_length") or 0)
                    if any(
                        row["data_length"] is not None or row["index_length"] is not None
                        for row in group
                    )
                    else None
                ),
                is_partitioned=bool(subnames),
                extras={"children": tuple(subnames)},
            )
        )
        for row in group:
            if row["subname"] is None:
                continue
            infos.append(
                PartitionInfo(
                    name=row["subname"],
                    parent=name,
                    level=2,
                    method=row["submethod"],
                    row_count=(
                        int(row["table_rows"]) if row["table_rows"] is not None else None
                    ),
                    size_bytes=(
                        int(row["data_length"] or 0) + int(row["index_length"] or 0)
                        if row["data_length"] is not None
                        or row["index_length"] is not None
                        else None
                    ),
                )
            )
    return PartitionReport(target=table, partitions=tuple(infos))


def _with_plan(
    report: MySQLPartitionReport,
    plan: MySQLPartitionPlan,
) -> MySQLPartitionReport:
    """Fill ``missing`` and ``orphans`` on a catalogue report from a plan."""
    known = {definition.name for definition in plan.definitions}
    missing = [
        definition.name
        for definition in plan.definitions
        if definition.name not in report.partition_names
    ]
    orphans = [name for name in report.partition_names if name not in known]
    return replace(report, missing=tuple(missing), orphans=tuple(orphans))


def _validate_plan(
    plan: MySQLPartitionPlan,
    report: MySQLPartitionReport,
) -> Tuple[str, ...]:
    """Return read-only findings for a plan against a catalogue report."""
    infos = {info.name: info for info in _top_level_infos(report)}
    issues: List[str] = []
    for definition in plan.definitions:
        info = infos.get(definition.name)
        if info is None:
            continue
        if not _catalog_method_matches(definition, info.method):
            issues.append(
                f"partition {definition.name} method is "
                f"{info.method or 'unknown'} but the plan declares "
                f"{_plan_method(definition)}"
            )
        if not _catalog_bound_matches(definition, info.bound):
            issues.append(
                f"partition {definition.name} boundary is "
                f"{info.bound if info.bound is not None else 'unknown'} but "
                f"the plan declares {_plan_boundary_text(definition)}"
            )
    return tuple(issues)


class MySQLPartitionMaintenance:
    """Run partition maintenance against one MySQL backend.

    Args:
        backend: A connected synchronous MySQL backend.

    Example:
        >>> maintenance = MySQLPartitionMaintenance(backend)
        >>> report = maintenance.ensure(plan)
        >>> report = maintenance.validate(plan)
        >>> report = maintenance.drop_before(plan, cutoff, dry_run=True)
    """

    def __init__(self, backend: "MySQLBackend"):
        self.backend = backend
        self.dialect = backend.dialect

    def list(
        self,
        table: str,
        *,
        plan: Optional[MySQLPartitionPlan] = None,
    ) -> MySQLPartitionReport:
        """Read the partition tree for ``table``.

        Args:
            table: Table name.
            plan: Optional plan used to fill ``missing`` with the definitions
                the catalogue does not hold and to mark existing partitions
                the plan does not name as ``orphans``.

        Returns:
            A report with the current partition tree.
        """
        if not table or not table.strip():
            raise ValueError("table must be a non-empty string")
        rows = self.backend.fetch_all(
            *_metadata_expression(self.dialect, table).to_sql()
        )
        report = build_report(table, rows)
        if plan is not None:
            report = _with_plan(report, plan)
        return report

    def ensure(
        self,
        plan: MySQLPartitionPlan,
        *,
        dry_run: bool = False,
    ) -> MySQLPartitionReport:
        """Create the plan's missing partitions, appending or reorganising.

        ``ADD PARTITION`` carries definitions above the current maximum.  A
        missing definition inside an existing range, or above a ``MAXVALUE``
        partition, is created with ``REORGANIZE PARTITION``.  Every missing
        definition that cannot be placed safely is reported in ``skipped``
        with the reason, and no statement claims it was added.

        Args:
            plan: Caller-owned plan.
            dry_run: Report what would be added without executing DDL.

        Returns:
            The pre-action snapshot plus ``missing``, ``added`` and ``skipped``.
        """
        report = self.list(plan.table, plan=plan)
        changes, skipped = plan_changes(plan, report, self.dialect)
        added_names = {
            definition.name
            for change in changes
            for definition in change.definitions
        }
        missing = tuple(report.missing)
        added = tuple(name for name in missing if name in added_names)

        if changes and not dry_run:
            for change in changes:
                expression = _change_expression(self.dialect, plan.table, change)
                self.backend.execute(*expression.to_sql())

        return replace(
            report,
            missing=missing,
            added=added,
            skipped=tuple(skipped),
            dry_run=dry_run,
        )

    def validate(self, plan: MySQLPartitionPlan) -> MySQLPartitionReport:
        """Compare the catalogue with ``plan`` without changing anything.

        ``missing`` and ``orphans`` come from the catalogue comparison.  Each
        partition present on both sides is checked for method drift
        (``PARTITION_METHOD``) and boundary drift (``PARTITION_DESCRIPTION``),
        and every finding is reported in ``issues``.  No DDL is executed and
        nothing is repaired.

        Args:
            plan: Caller-owned plan.

        Returns:
            The catalogue report plus ``issues``.
        """
        report = self.list(plan.table, plan=plan)
        return replace(report, issues=_validate_plan(plan, report), dry_run=True)

    def drop_before(
        self,
        plan: MySQLPartitionPlan,
        cutoff: Any,
        *,
        dry_run: bool = True,
    ) -> MySQLPartitionReport:
        """Drop the plan's partitions whose whole range is older than ``cutoff``.

        A partition qualifies when its upper bound is less than or equal to the
        cutoff, so a partition ending exactly at the cutoff is fully older than
        it.  The last partition is always kept.

        Args:
            plan: Caller-owned RANGE plan.
            cutoff: Inclusive upper threshold for retention.  Values must be
                comparable with the plan's ``less_than`` values.
            dry_run: Default ``True``; set ``False`` to execute the DDL.

        Returns:
            The pre-action snapshot plus ``dropped`` and ``skipped``.
        """
        report = self.list(plan.table, plan=plan)
        dropped, skipped = select_drops(plan, report.partition_names, cutoff)

        if dropped and not dry_run:
            expression = MySQLDropPartitionExpression(
                self.dialect,
                Table(self.dialect, plan.table),
                dropped,
            )
            self.backend.execute(*expression.to_sql())

        return replace(
            report,
            dropped=tuple(dropped),
            skipped=tuple(skipped),
            dry_run=dry_run,
        )


class AsyncMySQLPartitionMaintenance:
    """Asynchronously run partition maintenance against one MySQL backend.

    The planning rules are shared with :class:`MySQLPartitionMaintenance`;
    only the two backend calls are awaited.

    Args:
        backend: A connected asynchronous MySQL backend.

    Example:
        >>> maintenance = AsyncMySQLPartitionMaintenance(async_backend)
        >>> report = await maintenance.ensure(plan)
        >>> report = await maintenance.validate(plan)
        >>> report = await maintenance.drop_before(plan, cutoff)
    """

    def __init__(self, backend: "AsyncMySQLBackend"):
        self.backend = backend
        self.dialect = backend.dialect

    async def list(
        self,
        table: str,
        *,
        plan: Optional[MySQLPartitionPlan] = None,
    ) -> MySQLPartitionReport:
        """Read the partition tree for ``table`` asynchronously."""
        if not table or not table.strip():
            raise ValueError("table must be a non-empty string")
        rows = await self.backend.fetch_all(
            *_metadata_expression(self.dialect, table).to_sql()
        )
        report = build_report(table, rows)
        if plan is not None:
            report = _with_plan(report, plan)
        return report

    async def ensure(
        self,
        plan: MySQLPartitionPlan,
        *,
        dry_run: bool = False,
    ) -> MySQLPartitionReport:
        """Create the plan's missing partitions asynchronously.

        The append, reorganise, MAXVALUE-fold and refusal rules are identical
        to the synchronous executor.
        """
        report = await self.list(plan.table, plan=plan)
        changes, skipped = plan_changes(plan, report, self.dialect)
        added_names = {
            definition.name
            for change in changes
            for definition in change.definitions
        }
        missing = tuple(report.missing)
        added = tuple(name for name in missing if name in added_names)

        if changes and not dry_run:
            for change in changes:
                expression = _change_expression(self.dialect, plan.table, change)
                await self.backend.execute(*expression.to_sql())

        return replace(
            report,
            missing=missing,
            added=added,
            skipped=tuple(skipped),
            dry_run=dry_run,
        )

    async def validate(self, plan: MySQLPartitionPlan) -> MySQLPartitionReport:
        """Compare the catalogue with ``plan`` asynchronously, read-only."""
        report = await self.list(plan.table, plan=plan)
        return replace(report, issues=_validate_plan(plan, report), dry_run=True)

    async def drop_before(
        self,
        plan: MySQLPartitionPlan,
        cutoff: Any,
        *,
        dry_run: bool = True,
    ) -> MySQLPartitionReport:
        """Drop old partitions asynchronously; dry-run by default.

        A partition qualifies when its upper bound is less than or equal to the
        cutoff, and the last partition is always kept, exactly as in the
        synchronous executor.
        """
        report = await self.list(plan.table, plan=plan)
        dropped, skipped = select_drops(plan, report.partition_names, cutoff)

        if dropped and not dry_run:
            expression = MySQLDropPartitionExpression(
                self.dialect,
                Table(self.dialect, plan.table),
                dropped,
            )
            await self.backend.execute(*expression.to_sql())

        return replace(
            report,
            dropped=tuple(dropped),
            skipped=tuple(skipped),
            dry_run=dry_run,
        )
