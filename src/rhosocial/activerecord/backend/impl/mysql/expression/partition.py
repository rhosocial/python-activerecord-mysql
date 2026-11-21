# src/rhosocial/activerecord/backend/impl/mysql/expression/partition.py
"""MySQL partition DDL expressions."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements import (
    PartitionClause,
    PartitionDefinitionExpression,
    SubpartitionDefinitionExpression,
)
from rhosocial.activerecord.backend.expression.objects import Table


#: The strategy words MySQL spells. A strategy is now expressed by a core
#: ``PartitionBy*Clause`` node, so the words travel as plain strings that an
#: artifact can round-trip; this frozenset is only the vocabulary a dialect
#: checks a clause word against.
MYSQL_PARTITION_WORDS = frozenset(
    {
        "RANGE",
        "RANGE COLUMNS",
        "LIST",
        "LIST COLUMNS",
        "HASH",
        "LINEAR HASH",
        "KEY",
        "LINEAR KEY",
    }
)


class MySQLSubpartitionStrategy(str, Enum):
    """MySQL subpartitioning strategies.

    MySQL restricts subpartitioning to HASH and KEY (and their LINEAR
    variants) only. RANGE and LIST cannot be used for subpartitioning.
    """

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    HASH = "HASH"
    KEY = "KEY"
    LINEAR_HASH = "LINEAR HASH"
    LINEAR_KEY = "LINEAR KEY"


def _normalize_subpartition_strategy(
    dialect: "MySQLDialect",
    strategy: Any,
) -> MySQLSubpartitionStrategy:
    """Return the strategy member, refusing RANGE/LIST by name.

    MySQL and MariaDB restrict subpartitioning to HASH and KEY (and their
    LINEAR variants). ``SUBPARTITION BY RANGE`` cannot be silently downgraded
    to HASH: the caller asked for a feature the server does not have, so the
    refusal names that feature instead of producing valid-but-wrong SQL.
    """
    try:
        return MySQLSubpartitionStrategy(strategy)
    except ValueError as error:
        word = str(strategy).strip().upper()
        if word in {"RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"}:
            raise UnsupportedFeatureError(
                getattr(dialect, "name", "MySQL"),
                f"SUBPARTITION BY {word}",
                "MySQL and MariaDB support only HASH and KEY subpartitioning.",
            ) from error
        raise


class MySQLSubpartitionClause(BaseExpression):
    """MySQL ``SUBPARTITION BY {HASH|KEY}(...) SUBPARTITIONS N`` clause.

    This clause appears after ``PARTITION BY ...`` and before the list
    of partition definitions in a ``CREATE TABLE`` statement.

    When ``definitions`` is provided, those explicit subpartition names
    override the template for each parent partition.

    Raises:
        ValueError: if strategy is not a MySQLSubpartitionStrategy word.
        UnsupportedFeatureError: if strategy names RANGE or LIST subpartitioning.
        ValueError: if ``expression`` is missing; MySQL requires a column list
            for every SUBPARTITION BY HASH/KEY form, including LINEAR variants.
        ValueError: if count is provided but is not a positive integer.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        strategy: MySQLSubpartitionStrategy,
        *,
        expression: Optional[BaseExpression] = None,
        count: Optional[int] = None,
        definitions: Optional[Sequence[SubpartitionDefinitionExpression]] = None,
    ):
        super().__init__(dialect)
        # The member or the word it spells (§10: wide entry, normalised
        # storage): an artifact carries the word, and the formatter reads
        # ``.value``, which only the member has. A word this enum does not
        # name is refused here, where the caller can still see which
        # strategy was meant.
        self.strategy = _normalize_subpartition_strategy(dialect, strategy)
        if expression is None:
            raise ValueError(
                "SUBPARTITION BY %s requires an expression (column list)"
                % self.strategy.value
            )
        if count is not None and (not isinstance(count, int) or count <= 0):
            raise ValueError("count must be a positive integer when provided")
        self.expression = expression
        self.count = count
        self.definitions = list(definitions) if definitions else None

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_subpartition_clause"


if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import MySQLDialect


class MySQLPartitionMaxValue(BaseExpression):
    """MySQL MAXVALUE partition boundary token."""

    def __init__(self, dialect: "MySQLDialect"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_max_value"



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
        return "format_mysql_partition_value"



class MySQLPartitionClause(PartitionClause):
    """Base MySQL partition clause; the strategy is a fixed word, not an enum.

    Core's :class:`~...statements.PartitionClause` validates ``method`` against
    its own narrow vocabulary (RANGE/LIST/HASH). MySQL spells eight words, so
    this override stores the word directly while keeping the same key checks.
    Both ``.method`` (what the formatters read) and ``.word`` (the artifact form)
    carry it.
    """

    def __init__(self, dialect: "MySQLDialect", method: str, keys: Sequence[BaseExpression]):
        BaseExpression.__init__(self, dialect)
        word = getattr(method, "value", method)
        self.method = str(word).strip().upper()
        self.word = self.method
        if not keys:
            raise ValueError("keys are required")
        for key in keys:
            if not isinstance(key, BaseExpression):
                raise TypeError(
                    f"keys must contain BaseExpression instances, got {type(key).__name__}"
                )
        self.keys = list(keys)


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
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, "RANGE", keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_by_range"


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
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, "RANGE COLUMNS", keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_by_range_columns"


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
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, "LIST", keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_by_list"


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
        partitions: Optional[Sequence[PartitionDefinitionExpression]] = None,
        subpartition_by: Optional[MySQLSubpartitionClause] = None,
    ):
        super().__init__(dialect, "LIST COLUMNS", keys)
        if subpartition_by is not None and not isinstance(subpartition_by, MySQLSubpartitionClause):
            raise TypeError("subpartition_by must be a MySQLSubpartitionClause")
        self.partitions = list(partitions or [])
        self.subpartition_by = subpartition_by

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_by_list_columns"


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
        method = "LINEAR HASH" if linear else "HASH"
        super().__init__(dialect, method, keys)
        self.partitions_count = partitions_count
        self.linear = linear

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_by_hash"


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
        method = "LINEAR KEY" if linear else "KEY"
        if keys:
            super().__init__(dialect, method, keys)
        else:
            BaseExpression.__init__(self, dialect)
            self.method = method
            self.word = method
            self.keys = []
        self.partitions_count = partitions_count
        self.linear = linear

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_partition_by_key"


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
        partitions: List[PartitionDefinitionExpression],
    ):
        super().__init__(dialect, table)
        self.partitions = partitions

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_add_partition_expression"



class MySQLDropPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... DROP PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_drop_partition_expression"



class MySQLTruncatePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... TRUNCATE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_truncate_partition_expression"



class MySQLReorganizePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REORGANIZE PARTITION``."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: Table,
        partition: str,
        into: List[PartitionDefinitionExpression],
    ):
        super().__init__(dialect, table)
        self.partition = partition
        self.into = into

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_reorganize_partition_expression"



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
        return "format_mysql_exchange_partition_expression"



class MySQLRemovePartitioningExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REMOVE PARTITIONING``."""

    def __init__(self, dialect: "MySQLDialect", table: Table):
        super().__init__(dialect, table)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_remove_partitioning_expression"



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
        return "format_mysql_coalesce_partition_expression"



class MySQLAnalyzePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... ANALYZE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_analyze_partition_expression"



class MySQLCheckPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... CHECK PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_check_partition_expression"



class MySQLOptimizePartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... OPTIMIZE PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_optimize_partition_expression"



class MySQLRebuildPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REBUILD PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_rebuild_partition_expression"



class MySQLRepairPartitionExpression(MySQLPartitionTableExpression):
    """Expression for ``ALTER TABLE ... REPAIR PARTITION``."""

    def __init__(self, dialect: "MySQLDialect", table: Table, partitions: Sequence[str]):
        super().__init__(dialect, table)
        self.partitions = list(partitions)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_repair_partition_expression"



class MySQLGetPartitionsExpression(BaseExpression):
    """Expression that queries ``information_schema.PARTITIONS`` for a table.

    Generates a SELECT statement retrieving partition name, method,
    expression, description, and storage statistics for the given table.
    Delegates SQL generation to the dialect's ``format_mysql_get_partitions_expression``.

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
        return "format_mysql_get_partitions_expression"

