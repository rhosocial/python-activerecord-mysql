# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_table_statement.py
from typing import List, TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.expression.objects import Table

from .object_kind import require_kind

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.expression.table_statement import (
        MySQLTableStatement,
        MySQLValuesExpression,
    )


class MySQLTableStatementMixin:
    """MySQL TABLE statement and VALUES constructor support.

    ``TABLE table`` (8.0.19+) is a shortcut for ``SELECT * FROM table``.
    ``VALUES ROW(...), ...`` (8.0.19+) is a table value constructor.
    """

    def supports_table_statement(self) -> bool:
        """MySQL 8.0.19+ supports the TABLE statement."""
        return getattr(self, "version", None) is not None and self.version >= (8, 0, 19)

    def supports_values_table_constructor(self) -> bool:
        """MySQL 8.0.19+ supports VALUES as a table value constructor."""
        return getattr(self, "version", None) is not None and self.version >= (8, 0, 19)

    def format_table_statement(self, expr: "MySQLTableStatement") -> Tuple[str, tuple]:
        """Format ``TABLE <table> [ORDER BY ...] [LIMIT ...]``.

        The table is a schema object, so it renders itself and
        ``TABLE `db`.`users``` needs no hand-assembled prefix here.

        Raises:
            TypeError: ``expr.table`` is not a Table.
        """
        require_kind(expr.table, Table, "MySQLTableStatement.table")
        expr.validate(strict=self.strict_validation)
        table_sql = expr.table.to_sql()[0]
        parts = ["TABLE", table_sql]
        parts.extend(self._format_statement_clauses(expr))
        return " ".join(part for part in parts if part), ()

    def format_values_statement(self, expr: "MySQLValuesExpression") -> Tuple[str, tuple]:
        """Format ``VALUES ROW(...), ... [ORDER BY ...] [LIMIT ...]``."""
        expr.validate(strict=self.strict_validation)
        params = []
        row_parts = []
        for row in expr.rows:
            cell_parts = []
            for value in row:
                if hasattr(value, "to_sql"):
                    sql, p = value.to_sql()
                    cell_parts.append(sql)
                    params.extend(p)
                else:
                    cell_parts.append(self.get_parameter_placeholder())
                    params.append(value)
            row_parts.append(f"({', '.join(cell_parts)})")
        parts = ["VALUES", ", ".join(row_parts)]
        parts.extend(self._format_statement_clauses(expr))
        return " ".join(part for part in parts if part), tuple(params)

    def _format_statement_clauses(self, expr) -> List[str]:
        """Return the trailing ORDER BY / LIMIT / OFFSET fragments, in order.

        Kept here rather than shared with the expression because assembling
        clause order is the dialect's job: only the dialect knows the token
        order the engine accepts.
        """
        parts: List[str] = []
        if expr.order_by:
            cols = ", ".join(self.format_identifier(c) for c in expr.order_by)
            parts.append(f"ORDER BY {cols}")
        if expr.limit is not None:
            parts.append(f"LIMIT {int(expr.limit)}")
        if expr.offset is not None:
            parts.append(f"OFFSET {int(expr.offset)}")
        return parts