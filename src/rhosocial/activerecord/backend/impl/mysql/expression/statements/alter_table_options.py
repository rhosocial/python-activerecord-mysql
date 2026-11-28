# src/rhosocial/activerecord/backend/impl/mysql/expression/statements/alter_table_options.py
"""MySQL ``ALTER TABLE ... <table options>`` statement.

MySQL's ``ALTER TABLE`` grammar accepts ``table_options`` as an alter
specification, so an existing table's engine, character set, collation, row
format, comment and auto-increment counter can be changed in place::

    ALTER TABLE t ENGINE=InnoDB, DEFAULT CHARSET=utf8mb4, COMMENT='orders'

The option vocabulary is the one ``CREATE TABLE`` uses, but core models table
options only for creation (``CreateTableOptions``) and has no ALTER-time
carrier. This node is therefore owned by this backend and is never re-exported
from core.

The constructor collects parameters and validates nothing; the dialect formatter
owns the value checks, literal quoting and every refusal.
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import MySQLDialect

__all__ = ["MySQLAlterTableOptionsStatement"]


class MySQLAlterTableOptionsStatement(BaseExpression):
    """``ALTER TABLE <table> <engine/charset/collate/row-format/comment>``.

    Args:
        dialect: The MySQL dialect, or ``None`` for a later binding.
        table: Target table name.
        engine: Storage engine, e.g. ``"InnoDB"``.
        charset: Character set, rendered as ``DEFAULT CHARSET=...``.
        collate: Collation name.
        row_format: Row format word, e.g. ``"DYNAMIC"``.
        comment: Table comment text; empty string removes it.
        auto_increment: Next auto-increment value.
        database: Optional database name.
    """

    def __init__(
        self,
        dialect: Optional["MySQLDialect"],
        table: str,
        *,
        engine: Optional[object] = None,
        charset: Optional[object] = None,
        collate: Optional[str] = None,
        row_format: Optional[object] = None,
        comment: Optional[str] = None,
        auto_increment: Optional[int] = None,
        database: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.engine = engine
        self.charset = charset
        self.collate = collate
        self.row_format = row_format
        self.comment = comment
        self.auto_increment = auto_increment
        self.database = database

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this statement."""
        return "format_mysql_alter_table_options_statement"
