# src/rhosocial/activerecord/backend/impl/mysql/expression/partition.py
"""MySQL partition DDL expressions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression, SQLQueryAndParams
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements import PartitionClause


class MySQLPartitionStrategy(Enum):
    """MySQL table partitioning strategies supported by MySQLPartitionMixin."""

    RANGE = "RANGE"
    RANGE_COLUMNS = "RANGE COLUMNS"
    LIST = "LIST"
    LIST_COLUMNS = "LIST COLUMNS"
    HASH = "HASH"
    LINEAR_HASH = "LINEAR HASH"
    KEY = "KEY"
    LINEAR_KEY = "LINEAR KEY"

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MySQLDialect


class MySQLPartitionMaxValue(BaseExpression):
    """MySQL MAXVALUE partition boundary token."""

    def __init__(self, dialect: "MySQLDialect"):
        super().__init__(dialect)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_partition_value(self)


class MySQLPartitionValue(BaseExpression):
    """Literal value used in MySQL partition boundary definitions."""

    def __init__(self, dialect: "MySQLDialect", value: Any):
        super().__init__(dialect)
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("partition value float must be finite")
        if not isinstance(value, (str, int, float, Decimal, type(None))):
            from datetime import date, datetime

            if not isinstance(value, (date, datetime)):
                raise TypeError(
                    "partition value must be str, int, float, Decimal, "
                    f"date, datetime, or None, got {type(value).__name__}"
                )
        self.value = value

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_partition_value(self)


@dataclass
class MySQLPartitionDefinition:
    """A MySQL ``PARTITION ... VALUES ...`` definition."""

    name: str
    less_than: Optional[Sequence[BaseExpression]] = None
    in_values: Optional[Sequence[BaseExpression]] = None
    dialect_options: Optional[dict] = None

    def __post_init__(self) -> None:
        if self.less_than is not None and self.in_values is not None:
            raise ValueError("less_than and in_values are mutually exclusive")
        if self.less_than is None and self.in_values is None:
            raise ValueError("partition definition requires less_than or in_values")


class MySQLPartitionClause(PartitionClause):
    """Base MySQL partition clause with MySQL-specific strategy enum."""

    strategy_type = MySQLPartitionStrategy


class MySQLPartitionByRange(MySQLPartitionClause):
    """MySQL PARTITION BY RANGE expression."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.RANGE, keys)
        self.partitions = list(partitions or [])


class MySQLPartitionByRangeColumns(MySQLPartitionClause):
    """MySQL PARTITION BY RANGE COLUMNS expression."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.RANGE_COLUMNS, keys)
        self.partitions = list(partitions or [])


class MySQLPartitionByList(MySQLPartitionClause):
    """MySQL PARTITION BY LIST expression."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.LIST, keys)
        self.partitions = list(partitions or [])


class MySQLPartitionByListColumns(MySQLPartitionClause):
    """MySQL PARTITION BY LIST COLUMNS expression."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.LIST_COLUMNS, keys)
        self.partitions = list(partitions or [])


class MySQLPartitionByHash(MySQLPartitionClause):
    """MySQL PARTITION BY HASH expression."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions_count: Optional[int] = None,
        linear: bool = False,
    ):
        method = MySQLPartitionStrategy.LINEAR_HASH if linear else MySQLPartitionStrategy.HASH
        super().__init__(dialect, method, keys)
        self.partitions_count = partitions_count
        self.linear = linear


class MySQLPartitionByKey(MySQLPartitionClause):
    """MySQL PARTITION BY KEY expression."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions_count: Optional[int] = None,
        linear: bool = False,
    ):
        method = MySQLPartitionStrategy.LINEAR_KEY if linear else MySQLPartitionStrategy.KEY
        super().__init__(dialect, method, keys)
        self.partitions_count = partitions_count
        self.linear = linear


class MySQLAddPartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... ADD PARTITION``."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partitions: List[MySQLPartitionDefinition],
    ):
        super().__init__(dialect)
        self.table = TableExpression(dialect, table)
        self.partitions = partitions

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_add_partition_statement(self)


class MySQLDropPartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... DROP PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_drop_partition_statement(self)


class MySQLTruncatePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... TRUNCATE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_truncate_partition_statement(self)


class MySQLReorganizePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... REORGANIZE PARTITION``."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partition: str,
        into: List[MySQLPartitionDefinition],
    ):
        super().__init__(dialect)
        self.table = TableExpression(dialect, table)
        self.partition = partition
        self.into = into

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_reorganize_partition_statement(self)
