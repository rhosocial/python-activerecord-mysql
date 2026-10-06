# src/rhosocial/activerecord/backend/impl/mysql/mixins/truncate.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Table

from .object_kind import require_kind

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
        TruncateExpression,
    )


class MySQLTruncateMixin:
    """MySQL TRUNCATE TABLE support.

    MySQL 8.0 syntax is ``TRUNCATE [TABLE] tbl_name``. Unlike PostgreSQL,
    MySQL does not support RESTART IDENTITY or CASCADE, and a successful
    TRUNCATE always resets AUTO_INCREMENT counters.
    """

    def supports_truncate(self) -> bool:
        return True

    def supports_truncate_table_keyword(self) -> bool:
        return True

    def supports_truncate_restart_identity(self) -> bool:
        return False

    def supports_truncate_cascade(self) -> bool:
        return False

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format MySQL ``TRUNCATE [TABLE] tbl_name``.

        Raises:
            TypeError: ``expr.table`` is not a Table. TRUNCATE empties a table,
                so a View or a Sequence in that slot would render a statement
                emptying something else.
        """
        require_kind(expr.table, Table, "TruncateExpression.table")
        if expr.restart_identity:
            raise UnsupportedFeatureError(
                self.name,
                "TRUNCATE ... RESTART IDENTITY",
                suggestion="MySQL TRUNCATE always resets AUTO_INCREMENT; drop the option.",
            )
        if expr.cascade:
            raise UnsupportedFeatureError(
                self.name,
                "TRUNCATE ... CASCADE",
                suggestion="MySQL does not support CASCADE on TRUNCATE.",
            )
        sql = f"TRUNCATE TABLE {expr.table.to_sql()[0]}"
        return sql, ()