# src/rhosocial/activerecord/backend/impl/mysql/expression/statements/alter_column.py
"""MySQL-specific ALTER TABLE column actions.

MySQL's ``ADD COLUMN`` accepts positional clauses that have no generic
equivalent:

* ``FIRST`` -- place the new column at the head of the table.
* ``AFTER <column>`` -- place the new column immediately after ``column``.

Both live on ``MySQLAddColumn`` (deriving the generic ``AddColumnAction``)
and are rendered by its own entry, ``format_mysql_add_column``. MySQL
does **not** share them with any other backend. The two clauses are
alternatives, not a combination; the formatter refuses an instance that
carries both.

This class only collects the parameters. The exclusivity check is a
formatter concern, so a constructor validates nothing beyond what the
generic base already does.
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

    Adds MySQL's ``first`` and ``after`` positional clauses. They name the
    same decision -- where the new column goes -- and requesting both is
    refused when the action is rendered.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: ColumnDefinition,
        *,
        if_not_exists: Optional[bool] = None,
        after: Optional[str] = None,
        first: Optional[bool] = None,
    ):
        super().__init__(dialect, column, if_not_exists=if_not_exists)
        self.after = after
        self.first = first

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_add_column"
