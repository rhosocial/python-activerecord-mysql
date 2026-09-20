# src/rhosocial/activerecord/backend/impl/mysql/expression/table_options.py
"""MySQL-specific CREATE TABLE options.

MySQL adds table-level options that have no generic equivalent:

* ``ENGINE=<name>`` — storage engine.
* ``DEFAULT CHARSET=<name>`` — table character set.
* ``COLLATE=<name>`` — table collation.

These live on ``MySQLCreateTableOptions`` (deriving the generic
``CreateTableOptions``) and are rendered by the MySQL
``format_create_table_statement`` override. MySQL does **not** share them with
any other backend.
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import CreateTableOptions

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MySQLCreateTableOptions",
]


class MySQLCreateTableOptions(CreateTableOptions):
    """A MySQL CREATE TABLE options declaration extending the generic one.

    Adds the MySQL-only ``engine`` / ``charset`` / ``collate`` table options.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        or_replace: bool = False,
        comment: Optional[str] = None,
        engine: Optional[str] = None,
        charset: Optional[str] = None,
        collate: Optional[str] = None,
    ):
        super().__init__(dialect, or_replace=or_replace, comment=comment)
        self.engine = engine
        self.charset = charset
        self.collate = collate
