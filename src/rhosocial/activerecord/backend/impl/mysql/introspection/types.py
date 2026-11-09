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
from typing import Optional, Tuple


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


@dataclass(frozen=True)
class MySQLRoutineParameter:
    """One argument of a MySQL stored routine.

    ``PARAMETERS`` reports a function's return value as ordinal zero with no
    mode, and the arguments as ordinals one upward with ``IN``/``OUT``/``INOUT``.
    The return value is lifted into :attr:`MySQLRoutineInfo.return_type`; this
    record therefore only ever describes arguments.

    Attributes:
        ordinal_position: 1-based argument position, in declaration order.
        mode: ``IN``, ``OUT`` or ``INOUT`` as the server reports it.
        name: The argument's name; ``None`` for an anonymous argument.
        data_type: The base type name, e.g. ``"int"`` or ``"varchar"``.
        data_type_full: The declared type with length or precision, e.g.
            ``"varchar(50)"``, when the server reports the DTD identifier.
    """

    ordinal_position: int
    mode: Optional[str] = None
    name: Optional[str] = None
    data_type: Optional[str] = None
    data_type_full: Optional[str] = None


@dataclass(frozen=True)
class MySQLRoutineInfo:
    """One stored procedure or function from ``information_schema``.

    Attributes:
        schema: The database the routine belongs to.
        name: The routine's name.
        kind: ``"PROCEDURE"`` or ``"FUNCTION"`` as the server reports it.
        parameters: The arguments in declaration order; empty for a routine
            with none. It is a tuple so a cached result cannot be edited in
            place.
        return_type: The function's return type, or ``None`` for a procedure.
        language: ``EXTERNAL_LANGUAGE`` when the server reports one, else the
            routine body language (``"SQL"``).
        is_deterministic: ``True``/``False`` from ``IS_DETERMINISTIC``; ``None``
            when the server does not report it.
        sql_data_access: ``NO SQL``, ``CONTAINS SQL``, ``READS SQL DATA`` or
            ``MODIFIES SQL DATA``.
        security_type: ``DEFINER`` or ``INVOKER``.
        comment: The routine's ``COMMENT``, empty string when unset.
        definer: The account the routine executes as.
        created: When the routine was created, as the server's text.
        last_altered: When the routine last changed, as the server's text.
        sql_mode: The SQL mode in effect when the routine was created.
    """

    schema: str
    name: str
    kind: str
    parameters: Tuple[MySQLRoutineParameter, ...] = ()
    return_type: Optional[str] = None
    language: Optional[str] = None
    is_deterministic: Optional[bool] = None
    sql_data_access: Optional[str] = None
    security_type: Optional[str] = None
    comment: Optional[str] = None
    definer: Optional[str] = None
    created: Optional[str] = None
    last_altered: Optional[str] = None
    sql_mode: Optional[str] = None


@dataclass(frozen=True)
class MySQLConstraintInfo:
    """One table constraint from ``information_schema.TABLE_CONSTRAINTS``.

    ``constraint_type`` is the server's own vocabulary: ``PRIMARY KEY``,
    ``UNIQUE``, ``FOREIGN KEY`` or ``CHECK``. Only ``CHECK`` constraints carry
    :attr:`expression`; only the column-bearing kinds carry :attr:`columns`.
    MySQL has no comment clause for constraints, so :attr:`comment` stays
    ``None`` rather than being fabricated.

    Attributes:
        schema: The constraint's schema (MySQL's database).
        table_name: The table the constraint belongs to.
        name: The constraint name.
        constraint_type: ``PRIMARY KEY``, ``UNIQUE``, ``FOREIGN KEY`` or
            ``CHECK``.
        columns: The constrained columns in ordinal order; empty for ``CHECK``.
        expression: The CHECK clause, only for a ``CHECK`` constraint.
        enforced: ``True``/``False`` from ``ENFORCED``; ``None`` when the
            server does not report it.
        comment: Always ``None``: MySQL stores no constraint comment.
    """

    schema: str
    table_name: str
    name: str
    constraint_type: str
    columns: Tuple[str, ...] = ()
    expression: Optional[str] = None
    enforced: Optional[bool] = None
    comment: Optional[str] = None
