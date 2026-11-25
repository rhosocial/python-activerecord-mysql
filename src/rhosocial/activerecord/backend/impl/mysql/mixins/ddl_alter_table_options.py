# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_alter_table_options.py
"""MySQL ``ALTER TABLE ... <table options>`` support and formatter.

The option vocabulary is MySQL's own ``table_options`` production, the same one
``CREATE TABLE`` accepts; the ALTER path differs only in where it is spelled.
Values are checked against this dialect's existing vocabularies
(``validate_storage_engine_name`` / ``validate_charset_name`` /
``validate_collation_by_name`` and the shared ROW_FORMAT normaliser), and the
comment is a DDL literal, so it is quoted inline rather than bound.
"""

from typing import Tuple, TYPE_CHECKING

from ..expression.alter_table_options import MySQLAlterTableOptionsStatement
from ..expression.table_options import MySQLCreateTableOptions

if TYPE_CHECKING:  # pragma: no cover
    pass


class MySQLAlterTableOptionsMixin:
    """Formatter for the ALTER-time table options."""

    def format_mysql_alter_table_options_statement(
        self, expr: "MySQLAlterTableOptionsStatement"
    ) -> Tuple[str, tuple]:
        """Render ``ALTER TABLE <t> ENGINE=..., DEFAULT CHARSET=..., ...``.

        Validation lives here: the node must be the right class, the table name
        must be non-empty, at least one option must be supplied, and each value
        goes through this dialect's own vocabulary check. Options are emitted in
        grammar order so two equal declarations render the same bytes.
        """
        if not isinstance(expr, MySQLAlterTableOptionsStatement):
            raise TypeError(
                "format_mysql_alter_table_options_statement requires a "
                f"MySQLAlterTableOptionsStatement, got {type(expr).__name__}"
            )
        if not isinstance(expr.table, str) or not expr.table.strip():
            raise ValueError("ALTER TABLE options require a non-empty table name")

        parts = []
        if expr.engine is not None:
            engine = self.validate_storage_engine_name(expr.engine)
            parts.append(f"ENGINE={engine}")
        if expr.charset is not None:
            charset = self.validate_charset_name(expr.charset)
            parts.append(f"DEFAULT CHARSET={charset}")
        if expr.collate is not None:
            collate = self.validate_collation_by_name(expr.collate)
            parts.append(f"COLLATE={collate}")
        if expr.row_format is not None:
            row_format = MySQLCreateTableOptions._normalize_row_format(
                expr.row_format
            )
            parts.append(f"ROW_FORMAT={row_format}")
        if expr.auto_increment is not None:
            if isinstance(expr.auto_increment, bool) or not isinstance(
                expr.auto_increment, int
            ):
                raise TypeError(
                    "ALTER TABLE options auto_increment must be an int, got "
                    f"{type(expr.auto_increment).__name__}"
                )
            if expr.auto_increment < 1:
                raise ValueError(
                    "ALTER TABLE options auto_increment must be positive, got "
                    f"{expr.auto_increment}"
                )
            parts.append(f"AUTO_INCREMENT={expr.auto_increment}")
        if expr.comment is not None:
            if not isinstance(expr.comment, str):
                raise TypeError(
                    "ALTER TABLE options comment must be a string, got "
                    f"{type(expr.comment).__name__}"
                )
            comment = self.format_literal(expr.comment)  # type: ignore[attr-defined]
            parts.append(f"COMMENT={comment}")

        if not parts:
            raise ValueError(
                "ALTER TABLE options require at least one option: ENGINE, "
                "CHARSET, COLLATE, ROW_FORMAT, COMMENT or AUTO_INCREMENT"
            )

        from rhosocial.activerecord.backend.expression.objects import Table

        table_sql, _ = self.format_table_object(
            Table(self, expr.table, catalog_name=expr.database)
        )
        return f"ALTER TABLE {table_sql} " + ", ".join(parts), ()
