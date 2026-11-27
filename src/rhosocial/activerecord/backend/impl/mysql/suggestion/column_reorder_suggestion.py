# src/rhosocial/activerecord/backend/impl/mysql/suggestion/column_reorder_suggestion.py
"""MySQL's answer to the column-reorder migration decision point.

MySQL spells a positional change natively: a *new* column goes ``FIRST`` or
``AFTER <column>`` through ``MySQLAddColumn``, and an *existing* column is
restated with ``MODIFY COLUMN <definition> FIRST|AFTER <column>`` through core's
``ModifyColumnAction``, which ``MySQLModifyColumnMixin`` formats itself.

The minimal point carries column *names* only. ``ModifyColumnAction`` needs a
complete ``ColumnDefinition`` (a ``DataType`` plus every constraint and
attribute) to restate the column without changing it, and there is no name-only
reorder node in this backend. A drop+add chain would discard the column's data,
so that point is answered explicit ``False``. The enriched point carries full
typed definitions in ``new_fields``: each moved column can then be restated in
place, with ``after_column`` naming its predecessor (or ``first`` for the head),
one single-action statement per moved column and no data loss.
"""

from __future__ import annotations

from dataclasses import replace

from ....expression.objects import Table
from ....expression.statements.ddl_alter import AlterTableStatement, ModifyColumnAction
from ....expression.statements.ddl_table import ColumnDefinition
from ....suggestion import ColumnReorderSuggestion

__all__ = ["MySQLColumnReorderSuggestionMixin"]


class MySQLColumnReorderSuggestionMixin:
    """Answer a column-reorder point, or decline when no safe chain exists."""

    def suggest_column_reorder(self, point: ColumnReorderSuggestion) -> ColumnReorderSuggestion:
        """One ``MODIFY COLUMN ... FIRST|AFTER`` statement per moved column.

        ``MySQLAddColumn`` already spells ``FIRST``/``AFTER`` for a *new*
        column, but a moved column needs core's ``ModifyColumnAction``: it
        restates a complete ``ColumnDefinition`` (a ``DataType`` plus every
        constraint and attribute) and this backend formats it itself. The
        enriched point supplies those definitions in ``new_fields``, so each
        moved column is restated with ``after_column`` naming its predecessor
        in ``new_order`` (or ``first`` for the head). Columns that did not move
        are left alone.

        ``False`` is kept for a point without usable definitions (a moved
        column missing from ``new_fields``, a moved name absent from
        ``new_order``) or a dialect that refuses MODIFY COLUMN. An unchanged
        point answers ``None``; a drop+add chain is never built because it
        would lose data.
        """
        if not point.reordered_columns:
            return replace(point, operations=None)
        if not self.supports_modify_column():
            return replace(point, operations=False)

        new_order = point.new_order
        moved = set(point.reordered_columns)
        if not new_order or not moved <= set(new_order):
            return replace(point, operations=False)

        table = Table(self, point.table_name)
        operations = []
        previous = None
        for name in new_order:
            if name not in moved:
                previous = name
                continue
            column = point.new_fields.get(name)
            if not isinstance(column, ColumnDefinition):
                return replace(point, operations=False)
            operations.append(
                AlterTableStatement(
                    self,
                    table,
                    ModifyColumnAction(
                            self,
                            column,
                            first=previous is None,
                            after_column=previous,
                        ),
                )
            )
            previous = name
        return replace(point, operations=tuple(operations) or None)
