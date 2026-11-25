# src/rhosocial/activerecord/backend/impl/mysql/suggestion/table_index_change_suggestion.py
"""MySQL's answer to the table-index-change migration decision point.

``supports_alter_table_index_actions()`` is True on every MySQL version, and
core's ``AddIndexAction`` / ``DropIndexAction`` render exactly the spellings the
server accepts: ``ADD INDEX <name> (<columns>)`` and ``DROP INDEX <name>``.
The frozen index projections carry the constructor parameters needed to rebuild
an ``IndexDefinition`` exactly; the enriched point also carries the live
``IndexDefinition`` declarations, which take precedence when present.

An option this ALTER path cannot spell (``USING``, partial/covering clauses,
``IF [NOT] EXISTS`` or ``CONCURRENTLY``) is declined instead of having that
option silently dropped -- the same is true of an expression column, which the
formatter would have to quote as an identifier. Each returned operation is a
separate action instance; a caller puts one action in one
``AlterTableStatement`` and no multi-action SQL string is ever built here.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from ....expression.objects import Index
from ....expression.statements.ddl_alter import AddIndexAction, DropIndexAction
from ....expression.statements.ddl_table import IndexDefinition
from ....suggestion import TableIndexChangeSuggestion
from ._change_projection import fingerprint, index_definition, index_name

__all__ = ["MySQLTableIndexChangeSuggestionMixin"]

#: (name, projected or live value, comparable form, source)
_Entry = Tuple[str, object, object, str]


def _entries(
    projections: Tuple[object, ...], declarations: Tuple[object, ...]
) -> Optional[List[_Entry]]:
    """Read one side of a point, preferring its live ``IndexDefinition``s."""
    entries: List[_Entry] = []
    seen = set()
    for value in declarations:
        name = index_name(value)
        if name is None or name in seen or not isinstance(value, IndexDefinition):
            return None
        seen.add(name)
        entries.append((name, value, fingerprint(value), "live"))
    for value in projections:
        name = index_name(value)
        if name is None:
            return None
        if name in seen:
            continue
        seen.add(name)
        source = "live" if isinstance(value, IndexDefinition) else "projection"
        entries.append((name, value, fingerprint(value), source))
    return entries


class MySQLTableIndexChangeSuggestionMixin:
    """Suggest ADD/DROP INDEX actions for an index-change point."""

    def suggest_table_index_change(
        self, point: TableIndexChangeSuggestion
    ) -> TableIndexChangeSuggestion:
        """Return one real action per added, removed or redefined index.

        A same-name redefinition becomes a drop followed by an add. An
        unreadable name, an index option the ALTER path cannot carry, or a
        dialect that refuses ALTER TABLE index actions answers explicit
        ``False``; an unchanged point answers ``None``.
        """
        if (
            not point.old_indexes
            and not point.new_indexes
            and not (point.old_index_declarations or point.new_index_declarations)
        ):
            return replace(point, operations=None)
        if not self.supports_alter_table_index_actions():
            return replace(point, operations=False)

        old_entries = _entries(point.old_indexes, point.old_index_declarations)
        new_entries = _entries(point.new_indexes, point.new_index_declarations)
        if old_entries is None or new_entries is None:
            return replace(point, operations=False)
        old_map: Dict[str, Tuple[object, object, str]] = {
            entry[0]: entry[1:] for entry in old_entries
        }
        new_map: Dict[str, Tuple[object, object, str]] = {
            entry[0]: entry[1:] for entry in new_entries
        }

        operations = []
        for name, (value, fp, source) in old_map.items():
            previous = new_map.get(name)
            if previous is not None and previous[2] == source and previous[1] == fp:
                continue
            index = value if isinstance(value, Index) else Index(self, name)
            operations.append(DropIndexAction(self, index))
        for name, (value, fp, source) in new_map.items():
            previous = old_map.get(name)
            if previous is not None and previous[2] == source and previous[1] == fp:
                continue
            definition = index_definition(self, value)
            if definition is None:
                return replace(point, operations=False)
            operations.append(AddIndexAction(self, definition))
        return replace(point, operations=tuple(operations) or None)
