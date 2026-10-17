# src/rhosocial/activerecord/backend/impl/mysql/expression/dml.py
"""MySQL-specific DML expression classes."""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import InsertStatement

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLInsertExpression(InsertStatement):
    """A MySQL INSERT statement extending the generic one.

    MySQL supports ``REPLACE INTO`` and ``INSERT IGNORE`` which have no direct
    generic equivalent and different semantics from other backends. The flags
    live here as typed fields and are rendered by the MySQL
    ``format_insert_statement`` override, which reads them off this class --
    a plain :class:`InsertStatement` spells neither and renders a plain
    ``INSERT``.

    The mutual-exclusion rules are enforced here, where the node is built,
    rather than on every render: an invalid combination is a construction
    error, not a render-time surprise.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        into,
        source,
        columns=None,
        *,
        on_conflict=None,
        returning=None,
        replace: bool = False,
        ignore: bool = False,
    ):
        super().__init__(
            dialect,
            into=into,
            source=source,
            columns=columns,
            on_conflict=on_conflict,
            returning=returning,
        )
        if replace and ignore:
            raise ValueError("Cannot use both 'replace' and 'ignore' options together")
        if replace and self.on_conflict:
            raise ValueError("REPLACE INTO does not support ON CONFLICT clause")
        self.replace = replace
        self.ignore = ignore


__all__ = [
    "MySQLInsertExpression",
]
