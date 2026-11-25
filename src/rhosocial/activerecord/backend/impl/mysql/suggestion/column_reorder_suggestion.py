# src/rhosocial/activerecord/backend/impl/mysql/suggestion/column_reorder_suggestion.py
"""MySQL's answer to the column-reorder migration decision point.

MySQL spells a positional change natively: a *new* column goes ``FIRST`` or
``AFTER <column>`` through this backend's ``MySQLAddColumn`` node, and an
*existing* column is restated with ``MODIFY COLUMN <definition> FIRST|AFTER
<column>`` through core's ``ModifyColumnAction``, which this backend's
``MySQLModifyColumnMixin`` formats itself.

The decision point does not carry enough information to use either node for a
reorder: it holds column *names* only. ``ModifyColumnAction`` needs a complete
``ColumnDefinition`` (a ``DataType`` plus every constraint and attribute) to
restate the existing column without changing it, and there is no name-only
reorder node in this backend. A drop+add chain would discard the column's data,
so this answer is an explicit ``False`` rather than a fabricated chain.
"""

from __future__ import annotations

from dataclasses import replace

from ....suggestion import ColumnReorderSuggestion

__all__ = ["MySQLColumnReorderSuggestionMixin"]


class MySQLColumnReorderSuggestionMixin:
    """Answer a column-reorder point, or decline when no safe chain exists."""

    def suggest_column_reorder(self, point: ColumnReorderSuggestion) -> ColumnReorderSuggestion:
        """Return ``None`` for an empty point, otherwise explicit ``False``.

        Available mechanisms, neither of which can be built from this point:
        ``MySQLAddColumn.first`` / ``after`` (renders ``ADD COLUMN ... FIRST``
        or ``... AFTER <column>`` on this dialect, but only for a new column)
        and core's ``ModifyColumnAction`` with ``first`` / ``after_column``
        (renders ``MODIFY COLUMN <definition> FIRST|AFTER <column>`` here, but
        needs a full ``ColumnDefinition`` -- name, ``DataType`` and every
        constraint and attribute -- which the point does not carry).

        Missing mechanism: a node that reorders an existing column by name
        alone. Without it there is no data-preserving chain to return, and a
        drop+add chain is refused because it loses the column's data.
        """
        if not point.reordered_columns:
            return replace(point, operations=None)
        return replace(point, operations=False)
