# src/rhosocial/activerecord/backend/impl/mysql/ddl_spec.py
"""MySQL-specific DDL feature specs.

Each spec is a plain declaration object (no dialect at definition time)
recognized by the MySQL dialect's ``build_spec`` via ``isinstance``.
Only the MySQL dialect claims these specs; every other backend silently
ignores them (``build_spec`` returns ``None``).
"""

from typing import Optional, Sequence, Union

from rhosocial.activerecord.backend.expression.statements.ddl_spec import (
    ColumnTypeSpec,
    PartitionSpec,
)


class MySQLPartitionBound:
    """A single partition boundary in a MySQL ``PARTITION`` definition.

    ``value`` is a plain scalar (str / int / float / Decimal / date /
    datetime) or ``None``; the special ``"MAXVALUE"`` marker renders as
    ``MAXVALUE``.
    """

    __slots__ = ("value",)

    def __init__(self, value: Union[str, int, float, "object", None] = None):
        if isinstance(value, str) and value.upper() == "MAXVALUE":
            value = "MAXVALUE"
        self.value = value

    def __repr__(self) -> str:
        return f"MySQLPartitionBound({self.value!r})"


class MySQLPartitionDefinitionSpec:
    """A ``PARTITION <name> ...`` entry for a MySQL partition spec.

    ``less_than`` and ``in_values`` are mutually exclusive:

    - RANGE / RANGE COLUMNS: ``less_than=[bound, ...]`` → ``VALUES LESS THAN (...)``
    - LIST / LIST COLUMNS: ``in_values=[value, ...]`` → ``VALUES IN (...)``
    """

    __slots__ = ("name", "less_than", "in_values")

    def __init__(
        self,
        name: str,
        *,
        less_than: Optional[Sequence[MySQLPartitionBound]] = None,
        in_values: Optional[Sequence[Union[MySQLPartitionBound, "object"]]] = None,
    ):
        if less_than is not None and in_values is not None:
            raise ValueError("less_than and in_values are mutually exclusive")
        if less_than is None and in_values is None:
            raise ValueError("a partition definition requires less_than or in_values")
        self.name = name
        self.less_than = list(less_than) if less_than is not None else None
        self.in_values = list(in_values) if in_values is not None else None


class MySQLRangePartition(PartitionSpec):
    """MySQL ``PARTITION BY RANGE`` declaration.

    Example::

        MySQLRangePartition(
            column="created_at",
            partitions=[
                MySQLPartitionDefinitionSpec("p2026", less_than=[MySQLPartitionBound(2027)]),
                MySQLPartitionDefinitionSpec("p_max", less_than=[MySQLPartitionBound("MAXVALUE")]),
            ],
        )
    """

    __slots__ = ("column", "partitions")

    def __init__(
        self,
        column: str,
        partitions: Sequence[MySQLPartitionDefinitionSpec],
    ):
        if not column:
            raise ValueError("MySQLRangePartition requires a partition column")
        if not partitions:
            raise ValueError("MySQLRangePartition requires at least one partition")
        self.column = column
        self.partitions = list(partitions)


class MySQLListPartition(PartitionSpec):
    """MySQL ``PARTITION BY LIST`` declaration."""

    __slots__ = ("column", "partitions")

    def __init__(
        self,
        column: str,
        partitions: Sequence[MySQLPartitionDefinitionSpec],
    ):
        if not column:
            raise ValueError("MySQLListPartition requires a partition column")
        if not partitions:
            raise ValueError("MySQLListPartition requires at least one partition")
        self.column = column
        self.partitions = list(partitions)


class MySQLHashPartition(PartitionSpec):
    """MySQL ``PARTITION BY HASH`` declaration."""

    __slots__ = ("column", "partitions")

    def __init__(
        self,
        column: str,
        partitions: int,
    ):
        if not column:
            raise ValueError("MySQLHashPartition requires a partition column")
        if partitions <= 0:
            raise ValueError("MySQLHashPartition requires a positive partition count")
        self.column = column
        self.partitions = partitions


class MySQLVectorColumnSpec(ColumnTypeSpec):
    """A MySQL ``VECTOR(dim)`` column (MySQL 9.0+)."""

    __slots__ = ("dim",)

    def __init__(self, column: str, dim: int):
        super().__init__(column)
        if dim <= 0:
            raise ValueError("MySQLVectorColumnSpec requires a positive dimension")
        self.dim = dim


class MySQLSpatialColumnSpec(ColumnTypeSpec):
    """A MySQL spatial column (GEOMETRY / POINT / LINESTRING / POLYGON / ...)."""

    __slots__ = ("kind", "srid")

    def __init__(self, column: str, kind: str = "GEOMETRY", *, srid: Optional[int] = None):
        super().__init__(column)
        kind = (kind or "GEOMETRY").upper()
        valid = {
            "GEOMETRY", "POINT", "LINESTRING", "POLYGON",
            "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON",
            "GEOMETRYCOLLECTION",
        }
        if kind not in valid:
            raise ValueError(
                f"Invalid MySQL spatial kind {kind!r}; expected one of {sorted(valid)}"
            )
        self.kind = kind
        self.srid = srid


class MySQLSetColumnSpec(ColumnTypeSpec):
    """A MySQL ``SET('a','b',...)`` column."""

    __slots__ = ("values",)

    def __init__(self, column: str, values: Sequence[str]):
        super().__init__(column)
        if not values:
            raise ValueError("MySQLSetColumnSpec requires at least one value")
        self.values = list(values)