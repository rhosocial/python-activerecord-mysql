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
``columns`` is ambiguous between PRIMARY KEY and UNIQUE. Additions and changes
are answered only when the point carries live ``TableConstraint`` nodes; a
projection that cannot identify its branch kind is declined rather than guessed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, Optional, Tuple

from ....expression.statements.ddl_alter import (
    AddTableConstraintAction,
    DropTableConstraintAction,
)
from ....expression.statements.ddl_table import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from ....suggestion import TableConstraintChangeSuggestion
from ._change_projection import constraint_info

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


class MySQLTableConstraintChangeSuggestionMixin:
    """Suggest ADD/DROP CONSTRAINT actions for a constraint-change point."""

    def suggest_table_constraint_change(
        self, point: TableConstraintChangeSuggestion
    ) -> TableConstraintChangeSuggestion:
        """Return a chain of one-action-per-statement constraint actions.

        Drops are emitted first, then adds, so a name that is replaced can be
        re-created. A change to an existing name, an unaddressable PRIMARY KEY
        drop, an EXCLUDE kind, or a live node that cannot be identified is
        answered with explicit ``False``; an unchanged point is ``None``.
        """
        if not point.old_constraints and not point.new_constraints:
            return replace(point, operations=None)
        if not self.supports_add_constraint() or not self.supports_drop_constraint():
            return replace(point, operations=False)

        old_map: Dict[str, Tuple[Optional[type], object, object]] = {}
        new_map: Dict[str, Tuple[Optional[type], object, object]] = {}
        for values, target in (
            (point.old_constraints, old_map),
            (point.new_constraints, new_map),
        ):
            for value in values:
                name, kind, live = constraint_info(value)
                if name is None or name in target:
                    return replace(point, operations=False)
                target[name] = (kind, live, value)

        for name in set(old_map) & set(new_map):
            if old_map[name][2] != new_map[name][2]:
                # A same-name redefinition needs a drop and a faithful re-add;
                # a frozen branch cannot supply a trustworthy new node.
                return replace(point, operations=False)

        operations = []
        for name, (kind, _live, _value) in old_map.items():
            if name in new_map:
                continue
            if kind not in _DROPPABLE_BY_NAME:
                return replace(point, operations=False)
            operations.append(DropTableConstraintAction(self, name))
        for name, (kind, live, _value) in new_map.items():
            if name in old_map:
                continue
            if live is None or kind not in _ADDABLE:
                return replace(point, operations=False)
            operations.append(AddTableConstraintAction(self, live))
        return replace(point, operations=tuple(operations) or None)
