# src/rhosocial/activerecord/backend/impl/mysql/expression/partition_lifecycle.py
"""MySQL partition lifecycle management helpers.

This module provides named expression helpers that compose the low-level
DDL expressions from :mod:`partition` into common partition management
operations: add, drop, coalesce, reorganize, and add subpartition.

All methods return ``BaseExpression`` subclasses ready for ``to_sql()``
or for use in a statement execution pipeline.
"""

from typing import List, Optional, Sequence, TYPE_CHECKING, Union

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
        MySQLAddPartitionExpression,
        MySQLDropPartitionExpression,
        MySQLCoalescePartitionExpression,
        MySQLReorganizePartitionExpression,
        MySQLPartitionDefinition,
        MySQLSubpartitionDefinition,
    )


def _import_partition_exprs():
    """Lazy import of partition expressions to avoid circular dependency."""
    from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
        MySQLAddPartitionExpression,
        MySQLCoalescePartitionExpression,
        MySQLDropPartitionExpression,
        MySQLPartitionDefinition,
        MySQLReorganizePartitionExpression,
    )
    return (
        MySQLAddPartitionExpression,
        MySQLCoalescePartitionExpression,
        MySQLDropPartitionExpression,
        MySQLPartitionDefinition,
        MySQLReorganizePartitionExpression,
    )


def _import_subpartition():
    """Lazy import of subpartition definitions."""
    from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
        MySQLSubpartitionDefinition,
    )
    return MySQLSubpartitionDefinition


class MySQLAddPartitionHelper(BaseExpression):
    """Helper that adds multiple partitions with generated names.

    .. code-block:: python

        expr = MySQLAddPartitionHelper(
            dialect, table="orders",
            partition_values=[2000, 2001, 2002],
            name_template="p{value}",
        )

    Args:
        dialect: MySQL dialect instance.
        table: Target table name.
        partition_values: Values for ``VALUES LESS THAN`` of each new partition.
        name_template: Format string for partition names (default ``"p{value}"``).
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partition_values: Sequence[Union[int, str]],
        name_template: str = "p{value}",
    ):
        super().__init__(dialect)
        self.table = table
        if not partition_values:
            raise ValueError("partition_values must not be empty")
        self.partition_values = list(partition_values)
        self.name_template = name_template

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_add_partition_helper"


class MySQLCoalescePartitionHelper(BaseExpression):
    """Helper that coalesces partitions with validation.

    Args:
        dialect: MySQL dialect instance.
        table: Target table name.
        target_count: Desired number of partitions after coalescing.
        current_count: Current number of partitions (for validation).
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        target_count: int,
        current_count: int,
    ):
        super().__init__(dialect)
        self.table = table
        if target_count <= 0:
            raise ValueError("target_count must be positive")
        self.target_count = target_count
        self.current_count = current_count

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_coalesce_partition_helper"


class MySQLDropOldestPartitionHelper(BaseExpression):
    """Helper that drops the oldest partition from a list of partition names.

    Sorts partitions by name and drops the first one (lexicographically oldest).

    Args:
        dialect: MySQL dialect instance.
        table: Target table name.
        partition_names: List of existing partition names.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partition_names: Sequence[str],
    ):
        super().__init__(dialect)
        self.table = table
        if not partition_names:
            raise ValueError("partition_names must not be empty")
        self.partition_names = list(partition_names)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_oldest_partition_helper"


class MySQLReorganizePartitionHelper(BaseExpression):
    """Helper that reorganizes a partition into multiple new partitions.

    Args:
        dialect: MySQL dialect instance.
        table: Target table name.
        partition: Existing partition name to reorganize.
        into: Definitions for the new partitions.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partition: str,
        into: List["MySQLPartitionDefinition"],
    ):
        super().__init__(dialect)
        self.table = table
        self.partition = partition
        self.into = into

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_reorganize_partition_helper"


class MySQLAddSubpartitionHelper(BaseExpression):
    """Helper that adds a partition with explicit subpartition definitions.

    Useful when a table already has a ``SUBPARTITION BY`` clause and you
    need to add a new partition together with its subpartitions.

    Args:
        dialect: MySQL dialect instance.
        table: Target table name.
        partition_name: Name for the new partition.
        less_than: ``VALUES LESS THAN`` bound(s) for the partition.
        subpartition_names: Names for the subpartitions.
        in_values: Optional ``VALUES IN`` values for LIST-based partitioning.
    """

    def __init__(
        self,
        dialect: "MySQLDialect",
        table: str,
        partition_name: str,
        less_than: Optional[Sequence] = None,
        subpartition_names: Optional[Sequence[str]] = None,
        in_values: Optional[Sequence] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.partition_name = partition_name
        self.less_than = list(less_than) if less_than else None
        self.in_values = list(in_values) if in_values else None
        self.subpartition_names = list(subpartition_names) if subpartition_names else None

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_add_subpartition_helper"
