# src/rhosocial/activerecord/backend/impl/mysql/expression/alter_table_modifiers.py
"""MySQL's ``ALTER TABLE`` execution modifiers as a proprietary statement node.

The MySQL 8.0 Reference Manual (§15.1.9, ``ALTER TABLE``) gives the grammar::

    ALTER TABLE tbl_name [alter_option [, alter_option] ...] [partition_options]

    alter_option: {
        ...
      | ALGORITHM [=] {DEFAULT | INSTANT | INPLACE | COPY}
      | LOCK [=] {DEFAULT | NONE | SHARED | EXCLUSIVE}
      ...
    }

``ALGORITHM`` and ``LOCK`` are *alter_options*: they sit in the same
comma-separated list as the ordinary actions, and MySQL's own online-DDL
chapter (§17.12) shows them written after an action, e.g.
``ALTER TABLE t ADD PRIMARY KEY (c), ALGORITHM=INPLACE``. Core has no
counterpart for either clause, so this backend owns the node that carries
them. It is a wrapper, not a new action: the actions remain the core
``AlterTableAction`` objects the rest of the library already builds.

Only the parameters are collected here (§3.1). Version gates, the allowed
word sets, and the INSTANT/LOCK conflict are the formatter's business, and
no SQL is assembled in this constructor. With both modifiers omitted the
node renders byte-identically to a plain core ``AlterTableStatement``.
"""

from typing import List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterTableAction,
    AlterTableStatement,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from rhosocial.activerecord.backend.expression.objects import Table


__all__ = [
    "MySQLAlterTableStatement",
    "MYSQL_ALGORITHM_WORDS",
    "MYSQL_LOCK_WORDS",
]


#: The closed vocabulary of ``ALGORITHM`` words in §15.1.9. Data for the
#: formatter, not a constructor gate: a word the server does not know is
#: refused by name when the statement is rendered.
MYSQL_ALGORITHM_WORDS = ("DEFAULT", "INSTANT", "INPLACE", "COPY")

#: The closed vocabulary of ``LOCK`` words in §15.1.9.
MYSQL_LOCK_WORDS = ("DEFAULT", "NONE", "SHARED", "EXCLUSIVE")


class MySQLAlterTableStatement(AlterTableStatement):
    """A core ``ALTER TABLE`` plus MySQL's two execution modifiers.

    ``algorithm`` and ``lock`` are optional words; ``None`` means the clause
    is omitted entirely, which is what keeps an unmodified instance
    indistinguishable in SQL from core's ``AlterTableStatement``. Passing
    ``"DEFAULT"`` explicitly *does* render the clause -- MySQL spells
    ``ALGORITHM=DEFAULT`` and ``LOCK=DEFAULT`` and they are not the same text
    as omitting them, even though the server treats them as equivalent.

    The words are plain strings on purpose: the constructor collects values
    only, and the formatter decides which words this server understands.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        action: AlterTableAction,
        *,
        algorithm: Optional[str] = None,
        lock: Optional[str] = None,
    ) -> None:
        super().__init__(dialect, table, action)
        self.algorithm = algorithm
        self.lock = lock

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_alter_table_statement"
