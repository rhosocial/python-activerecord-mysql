# src/rhosocial/activerecord/backend/impl/mysql/expression/partition.py
"""MySQL partition DDL expressions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements import (
    PartitionClause,
    PartitionDefinition,
    SubpartitionDefinition,
)
from rhosocial.activerecord.backend.expression.objects import Table


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
class MySQLPartitionOptions:
    """Typed MySQL storage options for a partition or subpartition definition.

    Replaces the generic ``dialect_options`` bag with one attribute per MySQL
    ``PARTITION`` option keyword rendered by the MySQL formatter.

    Attributes:
        engine: Storage engine name (``ENGINE``).
        comment: Free-form comment (``COMMENT``).
        data_directory: Data directory path (``DATA DIRECTORY``).
        index_directory: Index directory path (``INDEX DIRECTORY``).
        max_rows: Maximum number of rows (``MAX_ROWS``).
        min_rows: Minimum number of rows (``MIN_ROWS``).
        tablespace: Tablespace name (``TABLESPACE``).
    """

    engine: Optional[str] = None
    comment: Optional[str] = None
    data_directory: Optional[str] = None
    index_directory: Optional[str] = None
    max_rows: Optional[int] = None
    min_rows: Optional[int] = None
    tablespace: Optional[str] = None


@dataclass
class MySQLSubpartitionDefinition(SubpartitionDefinition):
    """A single named subpartition within a partition definition.

    MySQL subpartitions carry no explicit boundary (the ``SUBPARTITION BY``
    template applies), so this subclass adds nothing beyond the base name and
    options. It exists as the MySQL-owned type derived from the generic
    :class:`~rhosocial.activerecord.backend.expression.statements.SubpartitionDefinition`.

    Raises:
        TypeError: if ``partition_options`` is not a :class:`MySQLPartitionOptions`
            when provided.
    """

    partition_options: Optional[MySQLPartitionOptions] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.partition_options is not None and not isinstance(
            self.partition_options, MySQLPartitionOptions
        ):
            raise TypeError(
                "partition_options must be a MySQLPartitionOptions value, "
                f"got {type(self.partition_options).__name__}"
            )


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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_subpartition_by"


if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MySQLDialect


class MySQLPartitionMaxValue(BaseExpression):
    """MySQL MAXVALUE partition boundary token."""

    def __init__(self, dialect: "MySQLDialect"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_value"



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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_value"



@dataclass
class MySQLPartitionDefinition(PartitionDefinition):
    """A MySQL ``PARTITION ... VALUES ...`` definition.

    Derives from the generic
    :class:`~rhosocial.activerecord.backend.expression.statements.PartitionDefinition`
    and tightens validation: MySQL requires exactly one boundary form.

    For single-column LIST COLUMNS, ``in_values`` accepts a flat sequence
    of ``BaseExpression`` (e.g. ``[val('a'), val('b')]`` → ``VALUES IN ('a', 'b')``).

    For multi-column LIST COLUMNS, ``in_values`` accepts a sequence where
    each element is itself a sequence of ``BaseExpression`` values, representing
    a row tuple (e.g. ``[(val('a'), val('x')), (val('b'), val('y'))]`` →
    ``VALUES IN (('a', 'x'), ('b', 'y'))``).

    When subpartitioning is used, ``subpartition_definitions`` optionally
    overrides the template from the ``SUBPARTITION BY`` clause for this
    specific partition. ``partition_options`` carries MySQL-only storage
    options typed on :class:`MySQLPartitionOptions`.

    Raises:
        ValueError: if both ``less_than`` and ``in_values`` are provided,
                    or if neither is provided.
        TypeError: if ``partition_options`` is not a
                   :class:`MySQLPartitionOptions` when provided.
    """

    subpartition_definitions: Optional[Sequence["MySQLSubpartitionDefinition"]] = None
    partition_options: Optional[MySQLPartitionOptions] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.partition_options is not None and not isinstance(
            self.partition_options, MySQLPartitionOptions
        ):
            raise TypeError(
                "partition_options must be a MySQLPartitionOptions value, "
                f"got {type(self.partition_options).__name__}"
            )
        if self.less_than is None and self.in_values is None:
            raise ValueError("partition definition requires less_than or in_values")


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


class MySQLPartitionTableExpression(BaseExpression):
    """Base for every ``ALTER TABLE ... <partition action>`` statement.

    All twelve of them name exactly one base table, and a base table is the
    only kind of relation MySQL accepts in that position: partitioning is a
    property of the table definition, so a view or a materialized view has
    none. The target is therefore a :class:`Table` rather than the broader
    :class:`~rhosocial.activerecord.backend.expression.objects.RelationObject`
    the whole-table maintenance statements take -- ``ANALYZE TABLE`` and
    ``OPTIMIZE TABLE`` do accept views, but ``ALTER TABLE ... ADD PARTITION``
    does not, and admitting a view here would emit SQL the server rejects.

    The object is required rather than coerced. A bare string says nothing
    about which database it belongs to, so accepting one would make
    ``ALTER TABLE `other_db`.`events``` inexpressible while every spelling that
    *was* accepted meant only the session's current database.
    """

    def __init__(self, dialect: "MySQLDialect", table: Table):
        """
        Args:
            dialect: SQL dialect.
            table: The table being altered, as a
                :class:`~rhosocial.activerecord.backend.expression.objects.Table`.

        Raises:
            TypeError: ``table`` is not a :class:`Table`. A bare string is
                refused rather than wrapped, because it cannot say which
                database it names and a dropped qualifier would address a
                different table than the caller meant.
        """
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"{type(self).__name__} target must be a Table object, got "
                f"{type(table).__name__}; pass "
                f"Table(dialect, 'users', catalog_name='app') to name a table "
                f"in another database"
            )
        self.table = table


class MySQLAddPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... ADD PARTITION``."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: Table,
        partitions: List[MySQLPartitionDefinition],
    ):
        super().__init__(dialect, table)
        self.partitions = partitions

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_add_partition_statement"



class MySQLDropPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... DROP PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_partition_statement"



class MySQLTruncatePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... TRUNCATE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_truncate_partition_statement"



class MySQLReorganizePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REORGANIZE PARTITION``."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: Table,
        partition: str,
        into: List[MySQLPartitionDefinition],
    ):
        super().__init__(dialect, table)
        self.partition = partition
        self.into = into

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_reorganize_partition_statement"



class MySQLExchangePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... EXCHANGE PARTITION``.

    The validation clause is a two-spelling alternative, so each spelling has
    its own parameter: ``with_validation`` spells ``WITH VALIDATION`` and
    ``without_validation`` spells ``WITHOUT VALIDATION``. Setting neither leaves
    the clause out, which is the server's default (``WITHOUT VALIDATION``);
    setting both is API misuse and raises ``ValueError`` at construction.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: Table,
        partition: str,
        exchange_table: Table,
        *,
        with_validation: bool = False,
        without_validation: bool = False,
    ):
        super().__init__(dialect, table)
        if with_validation and without_validation:
            raise ValueError(
                "with_validation and without_validation are mutually exclusive options"
            )
        self.partition = partition
        if not isinstance(exchange_table, Table):
            raise TypeError(
                "exchange_table must be a Table object, got "
                f"{type(exchange_table).__name__}; pass "
                f"Table(dialect, 'users', catalog_name='app') to name a table "
                f"in another database"
            )
        self.exchange_table = exchange_table
        self.with_validation = with_validation
        self.without_validation = without_validation

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_exchange_partition_statement"



class MySQLRemovePartitioningExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REMOVE PARTITIONING``."""

    def __init__(self, dialect: "MySQLDialect", table: Table):
        super().__init__(dialect, table)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_remove_partitioning_statement"



class MySQLCoalescePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... COALESCE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, count: int):
        if not isinstance(count, int) or count <= 0:
            raise ValueError("count must be a positive integer")
        super().__init__(dialect, table)
        self.count = count

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_coalesce_partition_statement"



class MySQLAnalyzePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... ANALYZE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_analyze_partition_statement"



class MySQLCheckPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... CHECK PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_check_partition_statement"



class MySQLOptimizePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... OPTIMIZE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_optimize_partition_statement"



class MySQLRebuildPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REBUILD PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rebuild_partition_statement"



class MySQLRepairPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REPAIR PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_repair_partition_statement"



class MySQLGetPartitionsExpression(BaseExpression):
    """Expression that queries ``information_schema.PARTITIONS`` for a table.

    Generates a SELECT statement retrieving partition name, method,
    expression, description, and storage statistics for the given table.
    Delegates SQL generation to the dialect's ``format_get_partitions_expression``.

    ``table_name`` stays a plain string here, and is matched against the
    ``TABLE_NAME`` *column* rather than used to name a relation: this is a
    catalogue lookup, not a statement acting on a table, so there is no
    object to build and no qualifier to lose.

    Raises:
        ValueError: if table_name is empty.
    """

    def __init__(self, dialect: "MySQLDialect", table_name: str):
        super().__init__(dialect)
        if not table_name or not table_name.strip():
            raise ValueError("table_name must not be empty")
        self.table_name = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_get_partitions_expression"

