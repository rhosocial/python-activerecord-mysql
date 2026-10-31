# src/rhosocial/activerecord/backend/impl/mysql/introspection/types.py
"""MySQL-specific introspection result types.

The core introspection types describe what every backend can answer about
tables, columns and indexes. MySQL can answer two further questions that
have no cross-backend shape: what a table's *storage* options are (engine,
row format, collation, comment, self-managed auto-increment counter), and
how it is *partitioned*. Both are reported here as frozen dataclasses so a
result cannot be edited in place after the cache handed it out.

Units are stated on the fields rather than implied: MySQL reports
``DATA_LENGTH`` and ``INDEX_LENGTH`` in bytes, and those are the values
carried here unchanged. They are the server's own accounting, which for
InnoDB is an estimate from the tablespace rather than an exact byte count,
so they are reported as the server said them and not recomputed.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MySQLTableOptions:
    """Storage options of one MySQL table.

    Mirrors the ``information_schema.TABLES`` columns of the same names.
    Every field but the identity is optional: a view has no engine, a
    table without a self-managed counter has no auto-increment value, and
    the server may not report a field at all on an older release.

    Attributes:
        schema: The database (MySQL's catalog/schema slot) the table lives in.
        table_name: The table's name.
        engine: Storage engine, e.g. ``"InnoDB"``.
        row_format: Physical row format, e.g. ``"Dynamic"``.
        table_collation: Default collation for the table's character columns.
        auto_increment: Next value the self-managed counter will hand out;
            ``None`` when the table has no AUTO_INCREMENT column or has not
            been written to yet.
        table_comment: The table's ``COMMENT``, empty string when unset.
        create_options: Extra options as the server echoes them in
            ``SHOW CREATE TABLE`` (e.g. ``"partitioned"``).
        data_length: Bytes the server accounts to the table's rows. For
            InnoDB this is an estimate from the tablespace, not an exact
            sum of row sizes.
        index_length: Bytes the server accounts to the table's indexes;
            same caveat about being an estimate for InnoDB.
    """

    schema: str
    table_name: str
    engine: Optional[str] = None
    row_format: Optional[str] = None
    table_collation: Optional[str] = None
    auto_increment: Optional[int] = None
    table_comment: Optional[str] = None
    create_options: Optional[str] = None
    data_length: Optional[int] = None
    index_length: Optional[int] = None

    @property
    def total_length(self) -> Optional[int]:
        """Data plus index bytes, or ``None`` if neither is reported.

        A convenience only: the two components stay available separately
        because they answer different questions (row storage vs index
        storage) and summing them here does not change that.
        """
        if self.data_length is None and self.index_length is None:
            return None
        return (self.data_length or 0) + (self.index_length or 0)


@dataclass(frozen=True)
class MySQLPartitionInfo:
    """One row of ``information_schema.PARTITIONS`` for a table.

    A subpartitioned table reports one row per (partition, subpartition)
    pair, which is why the subpartition identity is carried too: without
    it two rows of the same partition would be indistinguishable.

    Attributes:
        schema: The database the table lives in.
        table_name: The partitioned table's name.
        partition_name: The partition's name, or ``None`` for a
            non-partitioned table (those rows are filtered out before
            parsing, so this is a plain string in practice).
        partition_method: ``RANGE``, ``LIST``, ``HASH``, ``KEY`` or
            ``LINEAR`` as reported by the server.
        partition_expression: The expression the method was applied to,
            e.g. ``"YEAR(`created_at`)"``; ``None`` for ``KEY`` partitions.
        partition_description: The boundary value for RANGE/LIST
            partitions; ``None`` for HASH/KEY.
        partition_ordinal_position: 1-based position of the partition.
        subpartition_name: The subpartition's name, ``None`` when the table
            is not subpartitioned.
        subpartition_ordinal_position: 1-based position within the
            partition, ``None`` when not subpartitioned.
        table_rows: Rows the server estimates the partition holds.
        data_length: Bytes the server accounts to this partition's rows.
        index_length: Bytes the server accounts to this partition's
            indexes.
    """

    schema: str
    table_name: str
    partition_name: Optional[str] = None
    partition_method: Optional[str] = None
    partition_expression: Optional[str] = None
    partition_description: Optional[str] = None
    partition_ordinal_position: Optional[int] = None
    subpartition_name: Optional[str] = None
    subpartition_ordinal_position: Optional[int] = None
    table_rows: Optional[int] = None
    data_length: Optional[int] = None
    index_length: Optional[int] = None
