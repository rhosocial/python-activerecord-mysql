# src/rhosocial/activerecord/backend/impl/mysql/expression/maintenance.py
"""MySQL table maintenance statement expressions.

MySQL supports table maintenance statements that operate at the whole-table
level (as opposed to the partition-level variants in ``partition.py``):

    ANALYZE TABLE [NO_WRITE_TO_BINLOG | LOCAL] table [, table ...]
    CHECK TABLE table [, table ...] [FOR UPGRADE] [QUICK] [FAST] [MEDIUM] [EXTENDED] [CHANGED]
    CHECKSUM TABLE table [, table ...] [QUICK | EXTENDED]
    OPTIMIZE TABLE [NO_WRITE_TO_BINLOG | LOCAL] table [, table ...]
    REPAIR TABLE [NO_WRITE_TO_BINLOG | LOCAL] table [, table ...] [QUICK] [EXTENDED] [USE_FRM]
"""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import RelationObject

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class NoWriteToBinlogOption(Enum):
    """NO_WRITE_TO_BINLOG / LOCAL synonym selector."""

    NONE = ""
    NO_WRITE_TO_BINLOG = "NO_WRITE_TO_BINLOG"
    LOCAL = "LOCAL"


class CheckTableOption(Enum):
    """CHECK TABLE optional modes."""

    FOR_UPGRADE = "FOR UPGRADE"
    QUICK = "QUICK"
    FAST = "FAST"
    MEDIUM = "MEDIUM"
    EXTENDED = "EXTENDED"
    CHANGED = "CHANGED"


class ChecksumTableOption(Enum):
    """CHECKSUM TABLE optional modes."""

    QUICK = "QUICK"
    EXTENDED = "EXTENDED"


class RepairTableOption(Enum):
    """REPAIR TABLE optional modes."""

    QUICK = "QUICK"
    EXTENDED = "EXTENDED"
    USE_FRM = "USE_FRM"


class MySQLTableMaintenanceExpression(BaseExpression):
    """Base class for whole-table maintenance statements.

    Attributes:
        operation: Statement keyword (ANALYZE / CHECK / CHECKSUM / OPTIMIZE / REPAIR).
        tables: List of target relations, as
            :class:`~rhosocial.activerecord.backend.expression.objects.RelationObject`
            instances. Each carries its own database, so
            ``ANALYZE TABLE `app`.`users``` needs no separate qualifier
            argument -- and a qualifier can no longer be supplied in a form
            that silently disagrees with the name.
        no_write_to_binlog: NO_WRITE_TO_BINLOG / LOCAL selector (where supported).
    """

    operation: str = ""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        tables: List[RelationObject],
        *,
        no_write_to_binlog: "NoWriteToBinlogOption" = NoWriteToBinlogOption.NONE,
    ):
        super().__init__(dialect)
        self.tables: List[RelationObject] = list(tables)
        self.no_write_to_binlog: NoWriteToBinlogOption = no_write_to_binlog

    def validate(self, strict: bool = True) -> None:
        """Validate table list.

        Raises:
            ValueError: If the table list is empty.
            TypeError: If an entry is not a relation object. A ``(schema,
                table)`` tuple is refused outright rather than being accepted
                and unpacked: a tuple cannot say which part is the database and
                which is the name, which is exactly the ambiguity a schema
                object removes.
        """
        if not strict:
            return
        if not self.tables:
            raise ValueError(f"{self.operation} TABLE requires at least one table")
        for table in self.tables:
            if not isinstance(table, RelationObject):
                raise TypeError(
                    f"{self.operation} TABLE expects relation objects "
                    f"(Table, View, MaterializedView, ForeignTable), got "
                    f"{type(table).__name__}; pass "
                    f"Table(self.dialect, 'users', catalog_name='app') to qualify the name"
                )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_maintenance_statement"



class MySQLAnalyzeTableExpression(MySQLTableMaintenanceExpression):
    """Represent ``ANALYZE TABLE``."""

    operation: str = "ANALYZE"


class MySQLCheckTableExpression(MySQLTableMaintenanceExpression):
    """Represent ``CHECK TABLE`` with optional modes."""

    operation: str = "CHECK"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        tables: List[RelationObject],
        *,
        options: Optional[List[CheckTableOption]] = None,
    ):
        super().__init__(
            dialect,
            tables,
            no_write_to_binlog=NoWriteToBinlogOption.NONE,
        )
        self.options: List[CheckTableOption] = list(options or [])

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_maintenance_statement"



class MySQLChecksumTableExpression(MySQLTableMaintenanceExpression):
    """Represent ``CHECKSUM TABLE`` with optional mode."""

    operation: str = "CHECKSUM"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        tables: List[RelationObject],
        *,
        option: Optional[ChecksumTableOption] = None,
    ):
        super().__init__(
            dialect,
            tables,
            no_write_to_binlog=NoWriteToBinlogOption.NONE,
        )
        self.option: Optional[ChecksumTableOption] = option

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_maintenance_statement"



class MySQLOptimizeTableExpression(MySQLTableMaintenanceExpression):
    """Represent ``OPTIMIZE TABLE``."""

    operation: str = "OPTIMIZE"


class MySQLRepairTableExpression(MySQLTableMaintenanceExpression):
    """Represent ``REPAIR TABLE`` with optional modes."""

    operation: str = "REPAIR"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        tables: List[RelationObject],
        *,
        no_write_to_binlog: "NoWriteToBinlogOption" = NoWriteToBinlogOption.NONE,
        options: Optional[List[RepairTableOption]] = None,
    ):
        super().__init__(
            dialect,
            tables,
            no_write_to_binlog=no_write_to_binlog,
        )
        self.options: List[RepairTableOption] = list(options or [])

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_maintenance_statement"
