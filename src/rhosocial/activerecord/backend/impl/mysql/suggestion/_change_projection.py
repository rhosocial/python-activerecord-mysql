# src/rhosocial/activerecord/backend/impl/mysql/suggestion/_change_projection.py
"""Read the frozen context carried by the four migration change points.

``ChangePlan`` hands a backend *projections*, not live declarations: core's
``_freeze`` turns a node into ``("params", ((name, value), ...))`` so the plan
stays dialect-neutral and comparable. A suggestion that wants to return real
expression instances therefore has to read those projections back.

Only projections that can be rebuilt **without guessing** are read here:

* an index definition's constructor parameters are plain values, so it can be
  rebuilt exactly -- provided it carries no option the ALTER TABLE ``ADD INDEX``
  path cannot spell;
* a constraint's *name* is always readable, but a frozen branch that carries
  only ``columns`` is ambiguous between PRIMARY KEY and UNIQUE, so its kind is
  reported as ``None`` and the caller declines rather than invents one;
* a partition strategy's method and keys are readable as a generic clause.

Live expression instances are accepted too: a caller may build a point by hand
and pass the real nodes, in which case they are used as-is.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ....expression import Column
from ....expression.bases import BaseExpression
from ....expression.objects import Index
from ....expression.statements.ddl_partition import PartitionClause
from ....expression.statements.ddl_table import (
    IndexDefinition,
    TableCheckConstraint,
    TableConstraint,
    TableConstraintBranch,
    TableExcludeConstraint,
    TableForeignKeyConstraint,
)

__all__ = [
    "constraint_info",
    "index_definition",
    "index_name",
    "partition_strategy",
]


def _params(value: Any) -> Optional[Dict[str, Any]]:
    """The constructor parameters of a node or of a frozen ``params`` tuple."""
    if isinstance(value, tuple) and len(value) == 2 and value[0] == "params":
        pairs = value[1]
        if isinstance(pairs, (tuple, list)) and all(
            isinstance(pair, (tuple, list)) and len(pair) == 2 for pair in pairs
        ):
            return {str(key): item for key, item in pairs}
        return None
    getter = getattr(value, "get_params", None)
    if callable(getter):
        try:
            return dict(getter())
        except Exception:  # pragma: no cover - a node with a broken get_params
            return None
    return None


def _branch_kind(branch: Any) -> Optional[type]:
    """The branch class of a constraint branch, when the projection identifies it.

    ``{condition}``, ``{references, ...}`` and ``{operator, ...}`` each name one
    branch. ``{columns}`` alone does not: PRIMARY KEY and UNIQUE have the same
    constructor, so guessing between them would put a different constraint in
    the chain than the caller declared.
    """
    if isinstance(branch, TableConstraintBranch):
        return type(branch)
    params = _params(branch)
    if params is None:
        return None
    keys = set(params)
    if "condition" in keys:
        return TableCheckConstraint
    if "references" in keys:
        return TableForeignKeyConstraint
    if "operator" in keys or "index_method" in keys:
        return TableExcludeConstraint
    return None


def constraint_info(value: Any) -> Tuple[Optional[str], Optional[type], Optional[TableConstraint]]:
    """``(name, branch kind, live constraint)`` for a constraint projection."""
    if isinstance(value, TableConstraint):
        return value.name, type(value.branch), value
    params = _params(value)
    if params is None:
        return None, None, None
    name = params.get("name")
    if not isinstance(name, str) or not name:
        return None, None, None
    return name, _branch_kind(params.get("branch")), None


def _plain_index_options(params: Dict[str, Any]) -> bool:
    """Whether an index uses only what ALTER TABLE ``ADD INDEX`` can spell.

    Core renders ``ADD INDEX <name> (<columns>)``: no ``USING``, no partial or
    covering clauses, no idempotent qualifiers. A projection asking for one of
    those cannot be answered by an ``AddIndexAction`` without silently dropping
    the option, so the caller declines it.
    """
    return (
        params.get("type") is None
        and params.get("partial_condition") is None
        and params.get("include_columns") is None
        and params.get("tablespace") is None
        and not params.get("concurrent")
        and not params.get("if_not_exists")
        and not params.get("if_exists")
    )


def index_name(value: Any) -> Optional[str]:
    """The name of an index projection, used by ``DropIndexAction``."""
    if isinstance(value, (IndexDefinition, Index)):
        return value.name
    params = _params(value)
    if params is None:
        return None
    name = params.get("name")
    return name if isinstance(name, str) and name else None


def index_definition(dialect: Any, value: Any) -> Optional[IndexDefinition]:
    """Rebuild an ``IndexDefinition`` that ALTER TABLE ADD INDEX can render."""
    if isinstance(value, IndexDefinition):
        params = {
            "type": value.type,
            "partial_condition": value.partial_condition,
            "include_columns": value.include_columns,
            "tablespace": value.tablespace,
            "concurrent": value.concurrent,
            "if_not_exists": value.if_not_exists,
            "if_exists": value.if_exists,
        }
        if not _plain_index_options(params):
            return None
        return value
    params = _params(value)
    if params is None or not _plain_index_options(params):
        return None
    name, columns = params.get("name"), params.get("columns")
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(columns, (list, tuple)) or not columns:
        return None
    # core's ADD INDEX formatter quotes each column as an identifier, so an
    # expression column cannot be represented by this action.
    if not all(isinstance(column, str) and column for column in columns):
        return None
    return IndexDefinition(dialect, name, list(columns), unique=bool(params.get("unique", False)))


def partition_strategy(dialect: Any, value: Any) -> Optional[PartitionClause]:
    """Rebuild the generic partition clause carried by a partition projection."""
    if isinstance(value, PartitionClause):
        return value
    params = _params(value)
    if params is None:
        return None
    method, keys = params.get("method"), params.get("keys")
    if not isinstance(method, str) or not method.strip():
        return None
    if not isinstance(keys, (list, tuple)) or not keys:
        return None
    rebuilt = []
    for key in keys:
        if isinstance(key, BaseExpression):
            rebuilt.append(key)
            continue
        key_params = _params(key)
        if key_params is None or not isinstance(key_params.get("name"), str):
            return None
        rebuilt.append(Column(dialect, **key_params))
    return PartitionClause(dialect, method, rebuilt)
