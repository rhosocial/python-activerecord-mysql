# src/rhosocial/activerecord/backend/impl/mysql/expression/table_statement.py
"""MySQL TABLE statement and VALUES table-value constructor expressions.

MySQL 8.0.19+ supports two simplified query forms:

    TABLE <table> [ORDER BY ...] [LIMIT ...]
    VALUES ROW(...), ROW(...) [ORDER BY ...] [LIMIT ...]

``TABLE`` is a shortcut for ``SELECT * FROM <table>`` and ``VALUES`` lets a
row list be used as a table value constructor.
"""

from typing import Any, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLBaseTableStatement(BaseExpression):
    """Common base for the ``TABLE``/``VALUES`` simplified statements.

    This class owns the **clause** half of both statements: ``ORDER BY``,
    ``LIMIT`` and ``OFFSET``. Those belong to the statement, not to the thing
    being read -- a table has no ordering of its own, and ``LIMIT 10`` says
    something about the query rather than about the table. Keeping them here
    is what lets :class:`MySQLTableStatement` carry a bare relation object
    with no clause state bolted onto it.

    Attributes:
        order_by: Optional list of column names for the ORDER BY clause.
        limit: Optional LIMIT row count.
        offset: Optional OFFSET row count.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(dialect)
        self.order_by: List[str] = list(order_by or [])
        self.limit: Optional[int] = limit
        self.offset: Optional[int] = offset

    def _validate_common(self) -> None:
        if self.limit is not None and self.limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if self.offset is not None and self.offset < 0:
            raise ValueError("offset must be a non-negative integer")

    def _render_tail_clauses(self) -> str:
        """Render ``ORDER BY`` / ``LIMIT`` / ``OFFSET`` as one SQL fragment.

        The dialect formats the identifiers; this only assembles the clause
        order MySQL requires.
        """
        parts: List[str] = []
        if self.order_by:
            cols = ", ".join(self.format_identifier(c) for c in self.order_by)
            parts.append(f"ORDER BY {cols}")
        if self.limit is not None:
            parts.append(f"LIMIT {int(self.limit)}")
        if self.offset is not None:
            parts.append(f"OFFSET {int(self.offset)}")
        return " ".join(parts)


class MySQLTableStatement(MySQLBaseTableStatement):
    """The MySQL ``TABLE <table>`` simplified SELECT statement.

    The name is a :class:`~...expression.objects.Table`, so
    ``TABLE `db`.`users``` is expressible for the first time -- previously
    this statement held a bare string and could only ever name a table in the
    session's current database. The class used to be called
    ``MySQLTableExpression`` even though it was never a ``Table``;
    naming it after the statement it renders removes the ambiguity.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Table,
        *,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(
            dialect,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        self.table = table

    def validate(self, strict: bool = True) -> None:
        """Validate the target table and the clause bounds.

        Raises:
            TypeError: ``table`` is not a :class:`Table`. A bare string is
                rejected on purpose: it cannot say which database it belongs
                to, so it can only ever mean "the current one".
        """
        if not strict:
            return
        if not isinstance(self.table, Table):
            raise TypeError(
                f"table must be a Table object, got {type(self.table).__name__}; "
                f"pass Table(self.dialect, 'users', catalog_name='app') to qualify the name"
            )
        self._validate_common()

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_statement"


class MySQLValuesExpression(MySQLBaseTableStatement):
    """Represent the MySQL ``VALUES ROW(...), ...`` table value constructor."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        rows: List[List[Any]],
        *,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(
            dialect,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        self.rows: List[List[Any]] = [list(row) for row in rows]

    def validate(self, strict: bool = True) -> None:
        if not strict:
            return
        if not self.rows:
            raise ValueError("VALUES requires at least one ROW(...)")
        self._validate_common()

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_values_statement"