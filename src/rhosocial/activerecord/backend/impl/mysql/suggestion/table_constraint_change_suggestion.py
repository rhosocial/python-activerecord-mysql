# src/rhosocial/activerecord/backend/impl/mysql/suggestion/table_constraint_change_suggestion.py
"""MySQL's answer to the table-constraint-change migration decision point.

The capability probes in ``MySQLConstraintMixin`` were measured against a live
MySQL 26.7.0 server:

* ``ALTER TABLE ADD CONSTRAINT`` is accepted for CHECK, PRIMARY KEY, UNIQUE and
  FOREIGN KEY, and refused for EXCLUDE (1064). An ``AddTableConstraintAction``
  carrying any of the first four is therefore an honest chain.
* ``ALTER TABLE DROP CONSTRAINT`` addresses UNIQUE, FOREIGN KEY and CHECK by
  name (a missing CHECK name answers 3940, while ``DROP CHECK`` answers 3821).
  It does **not** address a PRIMARY KEY: MySQL discards the ``CONSTRAINT``
  symbol for a primary key, so ``DROP CONSTRAINT <pk>`` answers 3940 and the
  working spelling is ``DROP PRIMARY KEY``, which no existing node here emits.

A frozen projection identifies a constraint's name, but a branch carrying only
``columns`` is ambiguous between PRIMARY KEY and UNIQUE, and a projection can
never supply the live node ``AddTableConstraintAction`` needs. The enriched
point carries the model's own ``TableConstraint`` declarations, whose ``branch``
keeps the kind. They take precedence over the projections; a name covered only
by a projection stays subject to the old, conservative rules. EXCLUDE, an
unnameable or unidentifiable constraint, and a PRIMARY KEY drop remain
explicit ``False``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from ....expression.statements.ddl_alter import (
    AddTableConstraintAction,
    DropTableConstraintAction,
)
from ....expression.statements.ddl_table import (
    TableCheckConstraint,
    TableConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from ....suggestion import TableConstraintChangeSuggestion
from ._change_projection import constraint_info, fingerprint

__all__ = ["MySQLTableConstraintChangeSuggestionMixin"]

_ADDABLE = frozenset(
    {
        TablePrimaryKeyConstraint,
        TableUniqueConstraint,
        TableForeignKeyConstraint,
        TableCheckConstraint,
    }
)
_DROPPABLE_BY_NAME = frozenset(
    {
        TableUniqueConstraint,
        TableForeignKeyConstraint,
        TableCheckConstraint,
    }
)

#: (name, branch kind, live declaration or None, comparable form, source)
_Entry = Tuple[str, Optional[type], Optional[TableConstraint], object, str]


def _entries(
    projections: Tuple[object, ...], declarations: Tuple[object, ...]
) -> Optional[List[_Entry]]:
    """Read one side of a point, preferring its live declarations.

    Names are unique across both sources; a duplicate or an unreadable name is
    ambiguous and returns ``None``. A projection is consulted only for a name
    no live declaration covers, so the richer source never gets overridden.
    The source is kept so a projection is never mistaken for an unchanged live
    declaration just because the two happen to freeze to the same shape.
    """
    entries: List[_Entry] = []
    seen = set()
    for value in declarations:
        name, kind, live = constraint_info(value)
        if name is None or name in seen or not isinstance(live, TableConstraint):
            return None
        seen.add(name)
        entries.append((name, kind, live, fingerprint(live), "live"))
    for value in projections:
        name, kind, live = constraint_info(value)
        if name is None:
            return None
        if name in seen:
            continue
        seen.add(name)
        source = "live" if isinstance(value, TableConstraint) else "projection"
        entries.append((name, kind, live, fingerprint(value), source))
    return entries


class MySQLTableConstraintChangeSuggestionMixin:
    """Suggest ADD/DROP CONSTRAINT actions for a constraint-change point."""

    def suggest_table_constraint_change(
        self, point: TableConstraintChangeSuggestion
    ) -> TableConstraintChangeSuggestion:
        """Return one real action per statement, drops before adds.

        Live declarations let the kinds MySQL can spell become real
        ``AddTableConstraintAction`` chains, including a same-name redefinition
        (drop the old name, add the new declaration). A PRIMARY KEY drop, an
        EXCLUDE add, a name that cannot be identified, or a new constraint with
        no live node is answered explicit ``False``; nothing changed is ``None``.
        """
        if (
            not point.old_constraints
            and not point.new_constraints
            and not (point.old_constraint_declarations or point.new_constraint_declarations)
        ):
            return replace(point, operations=None)
        if not self.supports_add_constraint() or not self.supports_drop_constraint():
            return replace(point, operations=False)

        old_entries = _entries(point.old_constraints, point.old_constraint_declarations)
        new_entries = _entries(point.new_constraints, point.new_constraint_declarations)
        if old_entries is None or new_entries is None:
            return replace(point, operations=False)
        old_map: Dict[str, Tuple[Optional[type], Optional[TableConstraint], object, str]] = {
            entry[0]: entry[1:] for entry in old_entries
        }
        new_map: Dict[str, Tuple[Optional[type], Optional[TableConstraint], object, str]] = {
            entry[0]: entry[1:] for entry in new_entries
        }

        drops = []
        adds = []
        for name, (kind, _live, _fp, _source) in old_map.items():
            if name in new_map:
                continue
            if kind not in _DROPPABLE_BY_NAME:
                return replace(point, operations=False)
            drops.append(DropTableConstraintAction(self, name))
        for name, (kind, live, fp, source) in new_map.items():
            previous = old_map.get(name)
            if previous is not None and previous[3] == source and previous[2] == fp:
                continue
            if live is None or kind not in _ADDABLE:
                return replace(point, operations=False)
            if previous is not None:
                # Redefinition: only a name droppable by name can be recreated.
                if previous[0] not in _DROPPABLE_BY_NAME:
                    return replace(point, operations=False)
                drops.append(DropTableConstraintAction(self, name))
            adds.append(AddTableConstraintAction(self, live))
        return replace(point, operations=tuple(drops + adds) or None)
