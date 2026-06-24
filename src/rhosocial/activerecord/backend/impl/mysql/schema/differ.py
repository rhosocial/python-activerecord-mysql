# src/rhosocial/activerecord/backend/impl/mysql/schema/differ.py
"""MySQL schema differ — column order is significant."""

from rhosocial.activerecord.backend.schema.differ import SchemaDiffer


class MySQLSchemaDiffer(SchemaDiffer):
    """MySQL schema differ.

    MySQL column order matters: adding a column in the middle shifts
    all subsequent columns. ``_columns_equivalent`` additionally checks
    ``ordinal_position`` to detect re-orderings.
    """

    def _columns_equivalent(self, old_col, new_col) -> bool:
        if not super()._columns_equivalent(old_col, new_col):
            return False
        return old_col.ordinal_position == new_col.ordinal_position
