# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_rename_table.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.expression.objects import Table

from .object_kind import require_kind

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.expression.rename_table import (
        MySQLRenameTableExpression,
    )


class MySQLRenameTableMixin:
    """MySQL RENAME TABLE support.

    MySQL supports atomic multi-table renames:

        RENAME TABLE t1 TO t2 [, t3 TO t4, ...]
    """

    def supports_rename_table(self) -> bool:
        return True

    def supports_multi_table_rename(self) -> bool:
        return True

    def supports_cross_database_rename(self) -> bool:
        """Whether a single RENAME TABLE may span two databases.

        ``True``: MySQL accepts ``RENAME TABLE `a`.`t` TO `b`.`t`` and applies
        it atomically, as long as both databases live on the same server. That
        the server -- not the dialect -- draws the line is why this is a
        capability probe rather than a rendering decision.
        """
        return True

    def format_rename_table_statement(
        self,
        expr: "MySQLRenameTableExpression",
    ) -> Tuple[str, tuple]:
        """Format a MySQL ``RENAME TABLE ...`` statement.

        Both ends of every pair are schema objects that render themselves, so a
        cross-database rename renders as `` `from_db`.`t` TO `to_db`.`t` ``
        without this method having to know how a qualified name is spelled.

        Each end is checked as it is reached rather than in one pass first, so a
        pair whose second end is wrong reports that end and not the first.

        Raises:
            TypeError: Either end of a pair is not a Table. The check is here as
                well as in ``expr.validate`` because that runs under
                ``strict_validation`` and can be switched off, and a rename that
                quietly dropped a qualifier would move a table to a database the
                caller did not name.
        """
        expr.validate(strict=self.strict_validation)

        parts = ["RENAME TABLE"]
        pairs = []
        for position, (old_table, new_table) in enumerate(expr.renames):
            require_kind(
                old_table, Table, f"MySQLRenameTableExpression.renames old side at position {position}"
            )
            require_kind(
                new_table, Table, f"MySQLRenameTableExpression.renames new side at position {position}"
            )
            old_sql = old_table.to_sql()[0]
            new_sql = new_table.to_sql()[0]
            pairs.append(f"{old_sql} TO {new_sql}")
        parts.append(", ".join(pairs))
        return " ".join(parts), ()