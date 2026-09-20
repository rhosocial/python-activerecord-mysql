# src/rhosocial/activerecord/backend/impl/mysql/expression/column.py
"""MySQL-specific column definition expressions.

MySQL extends the standard column definition with per-column attributes that
have no generic equivalent:

* ``CHARACTER SET <name>`` — column character set.
* ``COLLATE <name>`` — column collation (rendered via the collate clause).
* ``COLUMN_FORMAT {FIXED|DYNAMIC|DEFAULT}`` — NDB column format.
* ``STORAGE {DISK|MEMORY|DEFAULT}`` — NDB storage type.
* ``INVISIBLE`` — column hidden from ``SELECT *``.

These live on ``MySQLColumnDefinition`` (deriving the generic
``ColumnDefinition``) and are rendered by the MySQL
``format_column_definition`` override. They are declared through
``MySQLColumnOptions`` (deriving the generic ``ColumnOptions``).
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.base.ddl.options import ColumnOptions

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


__all__ = [
    "MySQLColumnFormat",
    "MySQLColumnStorage",
    "MySQLColumnDefinition",
    "MySQLColumnOptions",
]


class MySQLColumnFormat(Enum):
    """MySQL NDB ``COLUMN_FORMAT`` values."""

    FIXED = "FIXED"
    DYNAMIC = "DYNAMIC"
    DEFAULT = "DEFAULT"


class MySQLColumnStorage(Enum):
    """MySQL NDB ``STORAGE`` values."""

    DISK = "DISK"
    MEMORY = "MEMORY"
    DEFAULT = "DEFAULT"


class MySQLColumnDefinition(ColumnDefinition):
    """A MySQL column definition extending the generic one.

    Adds MySQL-only typed attributes: ``character_set``, ``column_format``,
    ``storage`` and ``invisible``. The MySQL ``format_column_definition``
    renders these alongside the generic parts.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        data_type,
        constraints=None,
        comment: Optional[str] = None,
        generated_expression=None,
        identity: Optional[str] = None,
        identity_start: Optional[int] = None,
        identity_increment: Optional[int] = None,
        identity_clause=None,
        *,
        character_set: Optional[str] = None,
        column_format: Optional[MySQLColumnFormat] = None,
        storage: Optional[MySQLColumnStorage] = None,
        invisible: Optional[bool] = None,
    ):
        super().__init__(
            dialect,
            name,
            data_type,
            constraints=constraints,
            comment=comment,
            generated_expression=generated_expression,
            identity=identity,
            identity_start=identity_start,
            identity_increment=identity_increment,
            identity_clause=identity_clause,
        )
        if column_format is not None and not isinstance(column_format, MySQLColumnFormat):
            raise TypeError(
                "column_format must be a MySQLColumnFormat value, "
                f"got {type(column_format).__name__}"
            )
        if storage is not None and not isinstance(storage, MySQLColumnStorage):
            raise TypeError(
                "storage must be a MySQLColumnStorage value, "
                f"got {type(storage).__name__}"
            )
        self.character_set = character_set
        self.column_format = column_format
        self.storage = storage
        self.invisible = invisible


class MySQLColumnOptions(ColumnOptions):
    """MySQL per-column options declaration.

    Carries MySQL-only typed attributes; the deriver builds a
    ``MySQLColumnDefinition`` and this declaration transfers its fields onto
    it via :meth:`apply_to`.
    """

    def __init__(
        self,
        *,
        identity_start: Optional[int] = None,
        identity_increment: Optional[int] = None,
        character_set: Optional[str] = None,
        column_format: Optional[MySQLColumnFormat] = None,
        storage: Optional[MySQLColumnStorage] = None,
        invisible: Optional[bool] = None,
    ):
        super().__init__(
            identity_start=identity_start,
            identity_increment=identity_increment,
        )
        if column_format is not None and not isinstance(column_format, MySQLColumnFormat):
            raise TypeError(
                "column_format must be a MySQLColumnFormat value, "
                f"got {type(column_format).__name__}"
            )
        if storage is not None and not isinstance(storage, MySQLColumnStorage):
            raise TypeError(
                "storage must be a MySQLColumnStorage value, "
                f"got {type(storage).__name__}"
            )
        self.character_set = character_set
        self.column_format = column_format
        self.storage = storage
        self.invisible = invisible

    def column_definition_class(self):
        """Build a ``MySQLColumnDefinition`` for these options."""
        return MySQLColumnDefinition

    def apply_to(self, column) -> None:
        """Transfer the MySQL-only fields onto the column definition."""
        if not isinstance(column, MySQLColumnDefinition):
            raise TypeError(
                "MySQLColumnOptions.apply_to requires a MySQLColumnDefinition, "
                f"got {type(column).__name__}"
            )
        column.character_set = self.character_set
        column.column_format = self.column_format
        column.storage = self.storage
        column.invisible = self.invisible
