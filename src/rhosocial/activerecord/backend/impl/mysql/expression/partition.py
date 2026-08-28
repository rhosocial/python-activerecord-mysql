# src/rhosocial/activerecord/backend/impl/mysql/expression/partition.py
"""MySQL partition DDL expressions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING, Union

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


class MySQLSubpartitionStrategy(Enum):
    """MySQL subpartitioning strategies.

    MySQL restricts subpartitioning to HASH and KEY (and their LINEAR
    variants) only. RANGE and LIST cannot be used for subpartitioning.
    """

    HASH = "HASH"
    KEY = "KEY"
    LINEAR_HASH = "LINEAR HASH"
    LINEAR_KEY = "LINEAR KEY"


@dataclass
class MySQLSubpartitionDefinition:
    """A single named subpartition within a partition definition.

    Used when individual subpartitions need explicit names or distinct
    storage options. When omitted, MySQL applies the template from the
    ``SUBPARTITION BY`` clause automatically.

    Raises:
        ValueError: if name is empty or whitespace-only.
    """

    name: str
    dialect_options: Optional[Dict[str, Any]] = None


class MySQLSubpartitionClause(BaseExpression):
    """MySQL ``SUBPARTITION BY {HASH|KEY}(...) SUBPARTITIONS N`` clause.

    This clause appears after ``PARTITION BY ...`` and before the list
    of partition definitions in a ``CREATE TABLE`` statement.

    When ``definitions`` is provided, those explicit subpartition names
    override the template for each parent partition.

    Raises:
        TypeError: if strategy is not a MySQLSubpartitionStrategy.
        ValueError: if count is provided but is not a positive integer.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        strategy: MySQLSubpartitionStrategy,
        *,
        expression: Optional[BaseExpression] = None,
        count: Optional[int] = None,
        definitions: Optional[Sequence[MySQLSubpartitionDefinition]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(strategy, MySQLSubpartitionStrategy):
            raise TypeError(
                "strategy must be a MySQLSubpartitionStrategy value, "
                f"got {type(strategy).__name__}"
            )
        if count is not None and (not isinstance(count, int) or count <= 0):
            raise ValueError("count must be a positive integer when provided")
        self.strategy = strategy
        self.expression = expression
        self.count = count
        self.definitions = list(definitions) if definitions else None

    def to_sql(self) -> SQLQueryAndParams:
        """Delegate SQL generation to the dialect."""
        return self.dialect.format_subpartition_by(self)


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
    """A MySQL ``PARTITION ... VALUES ...`` definition.

    For single-column LIST COLUMNS, ``in_values`` accepts a flat sequence
    of ``BaseExpression`` (e.g. ``[val('a'), val('b')]`` → ``VALUES IN ('a', 'b')``).

    For multi-column LIST COLUMNS, ``in_values`` accepts a sequence where
    each element is itself a sequence of ``BaseExpression`` values, representing
    a row tuple (e.g. ``[(val('a'), val('x')), (val('b'), val('y'))]`` →
    ``VALUES IN (('a', 'x'), ('b', 'y'))``).

    When subpartitioning is used, ``subpartition_definitions`` optionally
    overrides the template from the ``SUBPARTITION BY`` clause for this
    specific partition.

    Raises:
        ValueError: if both ``less_than`` and ``in_values`` are provided,
                    or if neither is provided.
        TypeError: if ``dialect_options`` is not a dict when provided.
    """

    name: str
    less_than: Optional[Sequence[BaseExpression]] = None
    in_values: Optional[Sequence[Union[BaseExpression, Sequence[BaseExpression]]]] = None
    subpartition_definitions: Optional[Sequence["MySQLSubpartitionDefinition"]] = None
    dialect_options: Optional[dict] = None

    def __post_init__(self) -> None:
        if self.less_than is not None and self.in_values is not None:
            raise ValueError("less_than and in_values are mutually exclusive")
        if self.less_than is None and self.in_values is None:
            raise ValueError("partition definition requires less_than or in_values")
        if self.dialect_options is not None and not isinstance(self.dialect_options, dict):
            raise TypeError(
                "dialect_options must be dict or None, "
                f"got {type(self.dialect_options).__name__}"
            )


class MySQLPartitionClause(PartitionClause):
    """Base MySQL partition clause with MySQL-specific strategy enum."""

    strategy_type = MySQLPartitionStrategy


class MySQLPartitionByRange(MySQLPartitionClause):
    """MySQL PARTITION BY RANGE expression.

    When ``subpartition_by`` is provided, the generated DDL includes a
    ``SUBPARTITION BY`` clause. Each partition definition may also carry
    optional ``subpartition_definitions``.

    Raises:
        TypeError: if subpartition_by is not a MySQLSubpartitionClause.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.RANGE, keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MySQLPartitionByRangeColumns(MySQLPartitionClause):
    """MySQL PARTITION BY RANGE COLUMNS expression.

    Supports optional subpartitioning via ``subpartition_by``.

    Raises:
        TypeError: if subpartition_by is not a MySQLSubpartitionClause.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.RANGE_COLUMNS, keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MySQLPartitionByList(MySQLPartitionClause):
    """MySQL PARTITION BY LIST expression.

    Supports optional subpartitioning via ``subpartition_by``.

    Raises:
        TypeError: if subpartition_by is not a MySQLSubpartitionClause.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.LIST, keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


class MySQLPartitionByListColumns(MySQLPartitionClause):
    """MySQL PARTITION BY LIST COLUMNS expression.

    Supports optional subpartitioning via ``subpartition_by``.

    Raises:
        TypeError: if subpartition_by is not a MySQLSubpartitionClause.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Sequence[BaseExpression],
        *,
        partitions: Optional[Sequence[MySQLPartitionDefinition]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, MySQLPartitionStrategy.LIST_COLUMNS, keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by


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
    """MySQL PARTITION BY KEY expression.

    MySQL allows empty ``KEY()`` to use all primary key columns as the
    partition key. When ``keys`` is empty or ``None``, this expression
    bypasses the base class key validation (which requires at least one
    key expression) and produces ``PARTITION BY KEY()``.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        keys: Optional[Sequence[BaseExpression]] = None,
        *,
        partitions_count: Optional[int] = None,
        linear: bool = False,
    ):
        method = MySQLPartitionStrategy.LINEAR_KEY if linear else MySQLPartitionStrategy.KEY
        if keys:
            super().__init__(dialect, method, keys)
        else:
            BaseExpression.__init__(self, dialect)
            self.method = method.value
            self.keys = list(keys) if keys else []
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
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = partitions

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_add_partition_statement(self)


class MySQLDropPartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... DROP PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_drop_partition_statement(self)


class MySQLTruncatePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... TRUNCATE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
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
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partition = partition
        self.into = into

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_reorganize_partition_statement(self)


class MySQLExchangePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... EXCHANGE PARTITION``."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partition: str,
        exchange_table: str,
        *,
        with_validation: bool = True,
    ):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partition = partition
        if isinstance(exchange_table, TableExpression):
            self.exchange_table = exchange_table
        else:
            self.exchange_table = TableExpression(dialect, exchange_table)
        self.with_validation = with_validation

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_exchange_partition_statement(self)


class MySQLRemovePartitioningExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... REMOVE PARTITIONING``."""

    def __init__(self, dialect: "MySQLDialect", table: str):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_remove_partitioning_statement(self)


class MySQLCoalescePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... COALESCE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, count: int):
        super().__init__(dialect)
        if not isinstance(count, int) or count <= 0:
            raise ValueError("count must be a positive integer")
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.count = count

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_coalesce_partition_statement(self)


class MySQLAnalyzePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... ANALYZE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_analyze_partition_statement(self)


class MySQLCheckPartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... CHECK PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_check_partition_statement(self)


class MySQLOptimizePartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... OPTIMIZE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_optimize_partition_statement(self)


class MySQLRebuildPartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... REBUILD PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_rebuild_partition_statement(self)


class MySQLRepairPartitionExpression(BaseExpression):
    """Expression for ``ALTER TABLE ... REPAIR PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: str, partitions: Sequence[str]):
        super().__init__(dialect)
        if isinstance(table, TableExpression):
            self.table = table
        else:
            self.table = TableExpression(dialect, table)
        self.partitions = list(partitions)

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_repair_partition_statement(self)


class MySQLGetPartitionsExpression(BaseExpression):
    """Expression that queries ``information_schema.PARTITIONS`` for a table.

    Generates a SELECT statement retrieving partition name, method,
    expression, description, and storage statistics for the given table.
    Delegates SQL generation to the dialect's ``format_get_partitions_expression``.

    Raises:
        ValueError: if table_name is empty.
    """

    def __init__(self, dialect: "MySQLDialect", table_name: str):
        super().__init__(dialect)
        if not table_name or not table_name.strip():
            raise ValueError("table_name must not be empty")
        self.table_name = table_name

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_get_partitions_expression(self)
