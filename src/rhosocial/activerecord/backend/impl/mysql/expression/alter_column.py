# src/rhosocial/activerecord/backend/impl/mysql/expression/alter_column.py
"""MySQL-specific ALTER TABLE column actions.

MySQL's ``ADD COLUMN`` accepts a positional clause that has no generic
equivalent:

* ``AFTER <column>`` — place the new column immediately after ``column``.

It lives on ``MySQLAddColumn`` (deriving the generic ``AddColumnAction``)
and is rendered by its own entry, ``format_mysql_add_column``. MySQL
does **not** share it with any other backend.
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import (
    AddColumnAction,
    ColumnDefinition,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MySQLAddColumn",
]


class MySQLAddColumn(AddColumnAction):
    """A MySQL ``ADD COLUMN`` action extending the generic one.

    Adds the MySQL-only ``after`` positional clause.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: ColumnDefinition,
        *,
        if_not_exists: Optional[bool] = None,
        after: Optional[str] = None,
    ):
        super().__init__(dialect, column, if_not_exists=if_not_exists)
        self.after = after

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_add_column"
