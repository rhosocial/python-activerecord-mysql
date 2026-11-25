# src/rhosocial/activerecord/backend/impl/mysql/suggestion/table_index_change_suggestion.py
"""MySQL's answer to the table-index-change migration decision point.

``supports_alter_table_index_actions()`` is True on every MySQL version, and
core's ``AddIndexAction`` / ``DropIndexAction`` render exactly the spellings the
server accepts: ``ADD INDEX <name> (<columns>)`` and ``DROP INDEX <name>``.
The frozen index projections carry the constructor parameters needed to rebuild
an ``IndexDefinition`` exactly; a projection asking for an option this ALTER
path cannot spell (``USING``, partial/covering clauses, ``IF [NOT] EXISTS`` or
``CONCURRENTLY``) is declined instead of having that option silently dropped.

Each returned operation is a separate action instance. A caller puts one action
in one ``AlterTableStatement``; no multi-action SQL string is ever built here.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict

from ....expression.objects import Index
from ....expression.statements.ddl_alter import AddIndexAction, DropIndexAction
from ....suggestion import TableIndexChangeSuggestion
from ._change_projection import index_definition, index_name

__all__ = ["MySQLTableIndexChangeSuggestionMixin"]


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
        if not point.old_indexes and not point.new_indexes:
            return replace(point, operations=None)
        if not self.supports_alter_table_index_actions():
            return replace(point, operations=False)

        old_map: Dict[str, object] = {}
        new_map: Dict[str, object] = {}
        for values, by_name in (
            (point.old_indexes, old_map),
            (point.new_indexes, new_map),
        ):
            for value in values:
                name = index_name(value)
                if name is None or name in by_name:
                    return replace(point, operations=False)
                by_name[name] = value

        operations = []
        for name, value in old_map.items():
            if name in new_map and old_map[name] == new_map[name]:
                continue
            index = value if isinstance(value, Index) else Index(self, name)
            operations.append(DropIndexAction(self, index))
        for name, value in new_map.items():
            if name in old_map and old_map[name] == value:
                continue
            definition = index_definition(self, value)
            if definition is None:
                return replace(point, operations=False)
            operations.append(AddIndexAction(self, definition))
        return replace(point, operations=tuple(operations) or None)
