# src/rhosocial/activerecord/backend/impl/mysql/mixins/types.py
"""MySQL DataType formatting and parsing mixin."""

from __future__ import annotations

from typing import Optional, Tuple

from rhosocial.activerecord.backend.dialect.mixins.data_type import DataTypeMixin
from rhosocial.activerecord.backend.suggestion.definitions import (
    SubstituteAdviceSuggestion,
    SubstituteTypeSuggestion,
)
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    CustomType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    EnumType,
    FloatType,
    IntegerType,
    JsonBType,
    JsonType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
)
from ..expression.types.types import (
    MySQLBigIntType,
    MySQLBinaryType,
    MySQLBitType,
    MySQLBlobType,
    MySQLEnumType,
    MySQLGeometryCollectionType,
    MySQLGeometryType,
    MySQLIntType,
    MySQLLineStringType,
    MySQLLongBlobType,
    MySQLLongTextType,
    MySQLMediumBlobType,
    MySQLMediumIntType,
    MySQLMediumTextType,
    MySQLMultiLineStringType,
    MySQLMultiPointType,
    MySQLMultiPolygonType,
    MySQLPointType,
    MySQLPolygonType,
    MySQLSetType,
    MySQLSignedType,
    MySQLSmallIntType,
    MySQLTextType,
    MySQLTinyBlobType,
    MySQLTinyIntType,
    MySQLTinyTextType,
    MySQLUnsignedType,
    MySQLUUIDType,
    MySQLVarBinaryType,
    MySQLVectorType,
    MySQLYearType,
)


class MySQLTypeSupportMixin(DataTypeMixin):
    """MySQL DataType formatting and parsing.

    Implements ``DataTypeSupport`` so the dialect can render ``DataType``
    expressions to SQL strings and parse raw SQL type strings back into
    ``DataType`` instances.

    Formatting dispatches by the type instance's ``name`` through the
    naming-convention ``format_data_type_<name>`` methods (see
    ``DataTypeMixin``). MySQL-specific types carry ``mysql_``-prefixed
    names; core types render their real MySQL SQL.
    """

    # ------------------------------------------------------------------
    # DataTypeSupport — formatting
    # ------------------------------------------------------------------

    # --- MySQL-specific type formatters (dispatch key = type name) ---

    def format_data_type_mysql_signed(self, expr: MySQLSignedType) -> Tuple[str, tuple]:
        """``CAST(x AS SIGNED)`` -- MySQL's spelling of a signed integer.

        Not an alias for INTEGER: the server treats the two as different types
        and rejects a CAST that names the wrong one. The word is the name of
        the cast *target*, not of a column type, so there is no spelling to
        choose here.
        """
        return "SIGNED", ()

    def format_data_type_mysql_unsigned(self, expr: MySQLUnsignedType) -> Tuple[str, tuple]:
        """``CAST(x AS UNSIGNED)`` -- the unsigned counterpart.

        A cast target like ``SIGNED``, not an unsigned column type: see
        :class:`MySQLUnsignedType`. ``unsigned`` as a *column* attribute is the
        field on :class:`MySQLIntType` and friends.
        """
        return "UNSIGNED", ()

    def _check_unsigned(self, data_type: DataType) -> None:
        """Raise ``TypeError`` unless ``unsigned`` is a real ``bool``.

        ``unsigned`` is a *field* on every numeric concept here and every reader
        below turns it into the ``UNSIGNED`` word of the rendered DDL. The
        expressions collect it without judging it — a value is not a wrong value
        until a backend has to honour it, and this is that backend — so the
        judgement belongs at this end, which is why each reader calls this before
        it reads.

        Without it a truthy non-bool renders silently: ``unsigned="yes"`` writes
        ``INT UNSIGNED`` and reports success for a column nobody declared. That is
        the same silent loss the dummy dialect's ``_refuse_unsigned`` names when
        it refuses the flag outright, arriving from the opposite direction.

        The attribute is read directly rather than through ``getattr(..., False)``:
        the field is part of every concept routed to a reader here, and probing
        for it would turn "caller passed the wrong class" into the same silent
        render this guard exists to prevent.

        Raises:
            TypeError: naming the type actually supplied.
        """
        unsigned = data_type.unsigned
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )

    def _format_mysql_integer(self, sql: str, data_type: DataType) -> Tuple[str, tuple]:
        """Append the ``UNSIGNED`` / ``ZEROFILL`` attributes in MySQL's order.

        MySQL's grammar for every integer type is ``TYPE[(M)] [UNSIGNED]
        [ZEROFILL]`` — both attributes, ``UNSIGNED`` first — and the server
        writes both back that way, so this is the one spelling that agrees with
        ``SHOW CREATE TABLE`` and with the ``COLUMN_TYPE`` string that
        introspection feeds to the backend's ``MySQLTypeParser``.

        Both attributes are emitted independently rather than as an either/or.
        ``unsigned`` is part of the type's identity (core puts it in
        ``PARAMETERS``, and the differ compares with ``!=``), so a type carrying
        ``unsigned=True`` has to say so in its DDL; and ``zerofill`` is
        orthogonal to it, a display attribute that says nothing about the
        range. Treating the second as a replacement for the first would make the
        rendered SQL depend on the order of two independent booleans.

        Note that MySQL would *infer* ``UNSIGNED`` from a bare ``ZEROFILL``
        ("If you specify ZEROFILL for a numeric column, MySQL automatically
        adds the UNSIGNED attribute"), so the stored column would have the
        unsigned range either way — but the emitted DDL would then no longer
        describe the type object that produced it, and parsing the emitted SQL
        back would give ``unsigned=False``, a different value object than the
        one the caller declared. Emitting both is what makes
        ``parser.parse(t.to_sql()[0]) == t`` hold for every combination.
        """
        self._check_unsigned(data_type)
        if data_type.unsigned:
            sql = f"{sql} UNSIGNED"
        if data_type.zerofill:
            sql = f"{sql} ZEROFILL"
        return sql, ()

    def format_data_type_mysql_tinyint(self, expr: MySQLTinyIntType) -> Tuple[str, tuple]:
        """MySQL ``TINYINT``.

        Both spellings of the concept are accepted — MySQL's own manual lists
        ``TINYINT`` and ``INT1`` as names for the same 1-byte type — and the
        rendered word is MySQL's own canonical one, since ``TINYINT`` is what
        the server reports back from ``SHOW CREATE TABLE``.
        """
        self._check_spelling(expr, MySQLTinyIntType)
        return self._format_mysql_integer("TINYINT", expr)

    def format_data_type_mysql_smallint(self, expr: MySQLSmallIntType) -> Tuple[str, tuple]:
        """MySQL ``SMALLINT``.

        ``SMALLINT`` and ``INT2`` are both MySQL words for the 2-byte type, so
        both are accepted and MySQL's own word is rendered.
        """
        self._check_spelling(expr, MySQLSmallIntType)
        return self._format_mysql_integer("SMALLINT", expr)

    def format_data_type_mysql_mediumint(self, expr: MySQLMediumIntType) -> Tuple[str, tuple]:
        """MySQL ``MEDIUMINT`` — 3 bytes, ``-8388608``..``16777215``.

        MySQL spells this width with exactly one word, so there is no spelling
        to choose and none is taken; ``SPELLINGS`` is narrowed to that single
        word so the class does not inherit the 4-byte concept's ``int`` /
        ``integer`` list it does not share.

        ``MEDIUMINT`` is a MySQL *extension* to SQL: the manual lists only
        ``INTEGER``/``INT`` and ``SMALLINT`` as the standard's integer types and
        names ``TINYINT``, ``MEDIUMINT`` and ``BIGINT`` as extensions. There is
        no core 3-byte concept to render or inherit, which is why this is a
        ``mysql_``-namespaced class rather than a spelling of an existing one.
        """
        self._check_spelling(expr, MySQLMediumIntType)
        return self._format_mysql_integer("MEDIUMINT", expr)

    def format_data_type_mysql_int(self, expr: MySQLIntType) -> Tuple[str, tuple]:
        """MySQL ``INT`` with the MySQL-only attributes.

        ``INT`` and ``INTEGER`` are both MySQL words for the 4-byte type, so
        both are accepted; ``INT`` is rendered because that is the form MySQL
        itself writes back. The ``mysql_int`` dispatch key exists so that a
        column carrying ``UNSIGNED`` / ``ZEROFILL`` stays distinguishable from a
        plain ``integer`` in a schema diff — the word ``INT`` is the same.
        """
        self._check_spelling(expr, MySQLIntType)
        return self._format_mysql_integer("INT", expr)

    def format_data_type_mysql_bigint(self, expr: MySQLBigIntType) -> Tuple[str, tuple]:
        """MySQL ``BIGINT``.

        ``BIGINT`` and ``INT8`` are both MySQL words for the 8-byte type (the
        manual's own table lists ``INT8``), so both are accepted and MySQL's
        canonical word is rendered.
        """
        self._check_spelling(expr, MySQLBigIntType)
        return self._format_mysql_integer("BIGINT", expr)

    def format_data_type_mysql_tinyblob(self, expr: MySQLTinyBlobType) -> Tuple[str, tuple]:
        """``TINYBLOB`` — max 255 bytes.

        Same spelling gate as the unbounded concept it derives from: the
        size variants inherit the core ``BlobType`` spelling list, and MySQL
        writes ``BLOB``, not ``BYTEA``, in every one of them.
        """
        self._check_spelling(expr, ("blob",))
        return "TINYBLOB", ()

    def format_data_type_mysql_blob(self, expr: MySQLBlobType) -> Tuple[str, tuple]:
        """``BLOB`` — max 65,535 bytes. ``BYTEA`` refused; see ``mysql_tinyblob``."""
        self._check_spelling(expr, ("blob",))
        return "BLOB", ()

    def format_data_type_mysql_mediumblob(self, expr: MySQLMediumBlobType) -> Tuple[str, tuple]:
        """``MEDIUMBLOB`` — max 16,777,215 bytes. ``BYTEA`` refused."""
        self._check_spelling(expr, ("blob",))
        return "MEDIUMBLOB", ()

    def format_data_type_mysql_longblob(self, expr: MySQLLongBlobType) -> Tuple[str, tuple]:
        """``LONGBLOB`` — max 4,294,967,295 bytes. ``BYTEA`` refused."""
        self._check_spelling(expr, ("blob",))
        return "LONGBLOB", ()

    def format_data_type_mysql_tinytext(self, expr: MySQLTinyTextType) -> Tuple[str, tuple]:
        """``TINYTEXT`` — max 255 bytes.

        The size variants inherit the core ``TextType`` spelling list, and
        MySQL has no CLOB in any of them, so ``clob`` is refused here exactly
        as it is for the unbounded ``text``.
        """
        self._check_spelling(expr, ("text",))
        return "TINYTEXT", ()

    def format_data_type_mysql_text(self, expr: MySQLTextType) -> Tuple[str, tuple]:
        """``TEXT`` — max 65,535 bytes. ``CLOB`` refused; see ``mysql_tinytext``."""
        self._check_spelling(expr, ("text",))
        return "TEXT", ()

    def format_data_type_mysql_mediumtext(self, expr: MySQLMediumTextType) -> Tuple[str, tuple]:
        """``MEDIUMTEXT`` — max 16,777,215 bytes. ``CLOB`` refused."""
        self._check_spelling(expr, ("text",))
        return "MEDIUMTEXT", ()

    def format_data_type_mysql_longtext(self, expr: MySQLLongTextType) -> Tuple[str, tuple]:
        """``LONGTEXT`` — max 4,294,967,295 bytes. ``CLOB`` refused."""
        self._check_spelling(expr, ("text",))
        return "LONGTEXT", ()

    def format_data_type_mysql_bit(self, expr: MySQLBitType) -> Tuple[str, tuple]:
        if expr.n is not None:
            return f"BIT({expr.n})", ()
        return "BIT", ()

    def format_data_type_mysql_year(self, expr: MySQLYearType) -> Tuple[str, tuple]:
        if expr.display_width is not None:
            return f"YEAR({expr.display_width})", ()
        return "YEAR", ()

    def format_data_type_mysql_binary(self, expr: MySQLBinaryType) -> Tuple[str, tuple]:
        """``BINARY`` / ``BINARY(n)``.

        Omitting the length is *legal here* and means one byte: "If omitted,
        *M* defaults to 1" (manual §13.3.1), which every scenario server
        reports as ``binary(1)`` in ``information_schema``. So this
        formatter keeps honouring a missing length rather than inventing one —
        but a concept whose own width is fixed must not come through here
        unparameterised, which is why :class:`MySQLUUIDType` is its own class
        rather than a lengthless ``MySQLBinaryType``.
        """
        if expr.length is not None:
            return f"BINARY({expr.length})", ()
        return "BINARY", ()

    def format_data_type_mysql_varbinary(self, expr: MySQLVarBinaryType) -> Tuple[str, tuple]:
        """``VARBINARY(n)`` — always with its length.

        Unlike ``BINARY``, there is no lengthless form to fall back on:
        MySQL's grammar is ``VARBINARY(M)`` with *M* mandatory, so
        ``CREATE TABLE t (c VARBINARY)`` is a syntax error (1064). The
        constructor rejects the missing length rather than the formatter
        emitting SQL the server refuses.
        """
        return f"VARBINARY({expr.length})", ()

    def format_data_type_mysql_uuid(self, expr: MySQLUUIDType) -> Tuple[str, tuple]:
        """``BINARY(16)`` — a UUID as the 16 raw bytes it is.

        MySQL has no UUID type, so this is what it renders instead. The width
        comes from the *class constant* rather than from an instance field, so
        the rendered SQL cannot drift away from the value object's identity —
        ``PARAMETERS`` is empty, so a field would not be part of what equality
        compares. ``BINARY`` on its own is ``BINARY(1)`` (manual §13.3.1) and a
        one-byte column cannot hold a UUID. See the class docstring for why
        fixed-width ``BINARY`` and variable-width ``VARBINARY`` are not
        interchangeable here.
        """
        return f"BINARY({MySQLUUIDType.BYTE_LENGTH})", ()

    def format_data_type_enum(self, expr: EnumType) -> Tuple[str, tuple]:
        """Render the core ``EnumType``.

        MySQL has a native ENUM, so the generic type is renderable here rather
        than something to substitute. ``MySQLEnumType`` stays for the cases
        that need the charset and collation this form does not carry.
        """
        values_str = ",".join(self.format_literal(value) for value in expr.values)
        return f"ENUM({values_str})", ()

    def format_data_type_mysql_enum(self, expr: MySQLEnumType) -> Tuple[str, tuple]:
        values_str = ",".join(self.format_literal(v) for v in expr.values)
        result = f"ENUM({values_str})"
        if expr.charset:
            result += f" CHARACTER SET {expr.charset}"
        if expr.collation:
            result += f" COLLATE {expr.collation}"
        return result, ()

    def format_data_type_mysql_set(self, expr: MySQLSetType) -> Tuple[str, tuple]:
        values_str = ",".join(self.format_literal(v) for v in expr.values)
        result = f"SET({values_str})"
        if expr.charset:
            result += f" CHARACTER SET {expr.charset}"
        if expr.collation:
            result += f" COLLATE {expr.collation}"
        return result, ()

    def format_data_type_mysql_geometry(self, expr: MySQLGeometryType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"GEOMETRY SRID {expr.srid}", ()
        return "GEOMETRY", ()

    def format_data_type_mysql_point(self, expr: MySQLPointType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"POINT SRID {expr.srid}", ()
        return "POINT", ()

    def format_data_type_mysql_linestring(self, expr: MySQLLineStringType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"LINESTRING SRID {expr.srid}", ()
        return "LINESTRING", ()

    def format_data_type_mysql_polygon(self, expr: MySQLPolygonType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"POLYGON SRID {expr.srid}", ()
        return "POLYGON", ()

    def format_data_type_mysql_multipoint(self, expr: MySQLMultiPointType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"MULTIPOINT SRID {expr.srid}", ()
        return "MULTIPOINT", ()

    def format_data_type_mysql_multilinestring(self, expr: MySQLMultiLineStringType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"MULTILINESTRING SRID {expr.srid}", ()
        return "MULTILINESTRING", ()

    def format_data_type_mysql_multipolygon(self, expr: MySQLMultiPolygonType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"MULTIPOLYGON SRID {expr.srid}", ()
        return "MULTIPOLYGON", ()

    def format_data_type_mysql_geometrycollection(self, expr: MySQLGeometryCollectionType) -> Tuple[str, tuple]:
        if expr.srid is not None:
            return f"GEOMETRYCOLLECTION SRID {expr.srid}", ()
        return "GEOMETRYCOLLECTION", ()

    def format_data_type_mysql_vector(self, expr: MySQLVectorType) -> Tuple[str, tuple]:
        return f"VECTOR({expr.dim})", ()

    def _validate_fsp(self, label: str, precision: Optional[int]) -> None:
        """Validate fractional-seconds precision (dialect-specific range).

        MySQL allows 0-6 digits of fractional seconds on DATETIME /
        TIMESTAMP / TIME.  Structural checks happen at construction; this
        is the dialect-specific range check the type contract requires.
        """
        if precision is not None and not 0 <= precision <= 6:
            raise ValueError(
                f"MySQL {label} fractional seconds precision must be "
                f"between 0 and 6, got {precision}."
            )

    # --- Core types (pure names) rendered to real MySQL SQL ---

    def format_data_type_integer(self, expr: IntegerType) -> Tuple[str, tuple]:
        """``INT``.

        MySQL writes this concept both ways (``INT`` and ``INTEGER``) and
        accepts both, so both are accepted here; the rendered word is MySQL's
        own, which is also what the server echoes back in ``SHOW CREATE
        TABLE``. ``INT4`` is *not* accepted: MySQL does use it as a synonym in
        its integer-type table, but the concept's closed spelling list is
        ``("integer", "int")``, and inventing a third word here would make that
        list decorative.

        ``unsigned`` is honoured rather than dropped: MySQL *has* unsigned
        integers, so writing the attribute is possible and a declared unsigned
        column that renders as a signed one is a different column than the
        caller asked for. The backend's own width classes go through
        :meth:`_format_mysql_integer`, which also handles ``ZEROFILL``; core's
        integer concepts have no ``zerofill`` field -- it is MySQL's display
        attribute, not part of the concept -- so only ``UNSIGNED`` is appended
        here.
        https://dev.mysql.com/doc/refman/8.4/en/numeric-type-syntax.html
        """
        self._check_spelling(expr, IntegerType)
        self._check_unsigned(expr)
        return ("INT UNSIGNED" if expr.unsigned else "INT"), ()

    def format_data_type_bigint(self, expr: BigIntType) -> Tuple[str, tuple]:
        """``BIGINT`` — ``BIGINT`` and MySQL's ``INT8`` synonym both accepted.

        ``unsigned`` is honoured rather than dropped: MySQL *has* unsigned
        integers, so writing the attribute is possible and a declared unsigned
        column that renders as a signed one is a different column than the
        caller asked for. The backend's own width classes go through
        :meth:`_format_mysql_integer`, which also handles ``ZEROFILL``; core's
        integer concepts have no ``zerofill`` field -- it is MySQL's display
        attribute, not part of the concept -- so only ``UNSIGNED`` is appended
        here.
        https://dev.mysql.com/doc/refman/8.4/en/numeric-type-syntax.html
        """
        self._check_spelling(expr, BigIntType)
        self._check_unsigned(expr)
        return ("BIGINT UNSIGNED" if expr.unsigned else "BIGINT"), ()

    def format_data_type_smallint(self, expr: SmallIntType) -> Tuple[str, tuple]:
        """``SMALLINT`` — ``SMALLINT`` and MySQL's ``INT2`` synonym both accepted.

        ``unsigned`` is honoured rather than dropped: MySQL *has* unsigned
        integers, so writing the attribute is possible and a declared unsigned
        column that renders as a signed one is a different column than the
        caller asked for. The backend's own width classes go through
        :meth:`_format_mysql_integer`, which also handles ``ZEROFILL``; core's
        integer concepts have no ``zerofill`` field -- it is MySQL's display
        attribute, not part of the concept -- so only ``UNSIGNED`` is appended
        here.
        https://dev.mysql.com/doc/refman/8.4/en/numeric-type-syntax.html
        """
        self._check_spelling(expr, SmallIntType)
        self._check_unsigned(expr)
        return ("SMALLINT UNSIGNED" if expr.unsigned else "SMALLINT"), ()

    def format_data_type_tinyint(self, expr: TinyIntType) -> Tuple[str, tuple]:
        """``TINYINT`` — ``TINYINT`` and MySQL's ``INT1`` synonym both accepted.

        ``unsigned`` is honoured rather than dropped: MySQL *has* unsigned
        integers, so writing the attribute is possible and a declared unsigned
        column that renders as a signed one is a different column than the
        caller asked for. The backend's own width classes go through
        :meth:`_format_mysql_integer`, which also handles ``ZEROFILL``; core's
        integer concepts have no ``zerofill`` field -- it is MySQL's display
        attribute, not part of the concept -- so only ``UNSIGNED`` is appended
        here.
        https://dev.mysql.com/doc/refman/8.4/en/numeric-type-syntax.html
        """
        self._check_spelling(expr, TinyIntType)
        self._check_unsigned(expr)
        return ("TINYINT UNSIGNED" if expr.unsigned else "TINYINT"), ()

    def format_data_type_varchar(self, expr: VarCharType) -> Tuple[str, tuple]:
        """``VARCHAR`` only.

        ``CHARACTER VARYING`` is the SQL standard's long form, but MySQL has no
        such keyword: ``CHARACTER`` in a column definition is the character-set
        clause (``CHARACTER SET``), and ``CREATE TABLE t (c CHARACTER VARYING
        (10))`` is a syntax error. So that spelling is refused rather than
        quietly rewritten into something MySQL did not ask for.

        A missing length is refused too, and this is MySQL's grammar rather
        than the concept's: ``length`` stays optional on the core class because
        PostgreSQL's bare ``VARCHAR`` is legal, so it is the dialect's job to say
        whether it can do without one. MySQL cannot -- ``VARCHAR(M)`` has a
        mandatory *M*, and ``CREATE TABLE t (c VARCHAR)`` is error 1064. Emitting
        the bare word would hand the server a statement it rejects, at a point
        where the caller has no way to tell that from success.
        https://dev.mysql.com/doc/refman/8.4/en/string-type-syntax.html
        """
        self._check_spelling(expr, ("varchar",))
        if expr.length is None:
            raise ValueError(
                "MySQL's grammar is VARCHAR(M) with M mandatory, so a VarCharType "
                "declared without a length cannot be rendered here "
                "(CREATE TABLE t (c VARCHAR) is a syntax error). Declare a length."
            )
        return f"VARCHAR({expr.length})", ()

    def format_data_type_char(self, expr: CharType) -> Tuple[str, tuple]:
        """``CHAR`` only.

        As with ``VARCHAR``: MySQL has no ``CHARACTER`` column type — the word
        belongs to the character-set clause — so the standard's long form is
        refused rather than rewritten. (MySQL's national-character-set forms
        ``NCHAR`` / ``NVARCHAR`` are deliberately absent from the concept's
        spelling list too: this framework treats a character set as a *field*,
        not as a type.)
        """
        self._check_spelling(expr, ("char",))
        return (f"CHAR({expr.length})" if expr.length is not None else "CHAR"), ()

    def format_data_type_text(self, expr: TextType) -> Tuple[str, tuple]:
        """``TEXT`` only.

        MySQL has no CLOB type, so ``clob`` is refused. The default spelling
        still renders — a backend may write the concept under its own name but
        must not refuse the spelling every plain ``TextType(d)`` carries.
        """
        self._check_spelling(expr, ("text",))
        return "TEXT", ()

    def format_data_type_boolean(self, expr: BooleanType) -> Tuple[str, tuple]:
        """``TINYINT(1)``.

        MySQL has no BOOLEAN/BOOL *storage* type: both words are documented
        aliases for ``TINYINT(1)``, so both are accepted, and the backend's own
        word is rendered. The truth value is then the byte — which is exactly
        why :class:`MySQLBitType` is a separate concept: a BIT string is not a
        boolean even at width 1.
        """
        self._check_spelling(expr, BooleanType)
        return "TINYINT(1)", ()

    def format_data_type_date(self, expr: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    def format_data_type_datetime(self, expr: DateTimeType) -> Tuple[str, tuple]:
        self._validate_fsp("DATETIME", expr.precision)
        return (f"DATETIME({expr.precision})" if expr.precision is not None else "DATETIME"), ()

    def format_data_type_time(self, expr: TimeType) -> Tuple[str, tuple]:
        self._validate_fsp("TIME", expr.precision)
        return (f"TIME({expr.precision})" if expr.precision is not None else "TIME"), ()

    def format_data_type_timetz(self, expr: TimeTzType) -> Tuple[str, tuple]:
        self._validate_fsp("TIME", expr.precision)
        return (f"TIME({expr.precision})" if expr.precision is not None else "TIME"), ()

    def format_data_type_timestamp(self, expr: TimestampType) -> Tuple[str, tuple]:
        self._validate_fsp("TIMESTAMP", expr.precision)
        return (f"TIMESTAMP({expr.precision})" if expr.precision is not None else "TIMESTAMP"), ()

    def format_data_type_timestamptz(self, expr: TimestampTzType) -> Tuple[str, tuple]:
        self._validate_fsp("TIMESTAMP", expr.precision)
        return (f"TIMESTAMP({expr.precision})" if expr.precision is not None else "TIMESTAMP"), ()

    def format_data_type_float(self, expr: FloatType) -> Tuple[str, tuple]:
        """``FLOAT`` only; ``UNSIGNED`` honoured in MySQL's documented slot.

        MySQL's numeric-type syntax writes this concept as
        ``FLOAT[(M,D)] [UNSIGNED] [ZEROFILL]``, so the attribute goes after the
        type word — the same slot the integer widths put it in, because it is
        the same attribute.
        https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html

        **``precision`` is refused, because ``FLOAT(p)`` cannot round-trip.**
        The manual states what *p* does: "If *p* is from 0 to 24, the data type
        becomes ``FLOAT`` with no *M* or *D* values. If *p* is from 25 to 53,
        the data type becomes ``DOUBLE`` with no *M* or *D* values." *p* is
        consumed to choose the storage class and is recorded nowhere: measured
        on the wired servers (5.6.51 through 26.7.0),
        ``CREATE TABLE t (c FLOAT(24))`` reports ``COLUMN_TYPE = 'float'`` and
        ``FLOAT(25)`` / ``FLOAT(53)`` report ``'double'``. A declared
        ``FloatType(precision=24)`` would therefore be introspected back as a
        precision-free ``FloatType``, and ``FloatType(precision=53)`` as a
        ``DoubleType`` — the second is a different storage class, not a
        different spelling of one, and the first is a parameter silently gone.
        The caller is told which class to declare for each range instead of
        being handed a declaration the catalog contradicts.

        ``precision=None`` — the bare ``FLOAT`` — round-trips: it renders
        ``FLOAT``, the server stores 4-byte single precision, and the catalog
        reports ``float``.

        ``UNSIGNED`` is honoured rather than dropped, and MySQL says so of this
        concept in as many words: "Floating point and fixed-point types also can
        be ``UNSIGNED``. As with integer types, this attribute prevents negative
        values from being stored in the column. Unlike the integer types, the
        upper range of column values remains the same."
        https://dev.mysql.com/doc/refman/9.7/en/numeric-type-attributes.html
        The same page deprecates the attribute on ``FLOAT``, ``DOUBLE`` and
        ``DECIMAL`` ("and any synonyms"), but it is still the documented
        grammar, and a dialect that quietly stopped writing it would hand the
        caller a signed column and report success. ``ZEROFILL`` has no field on
        the concept and is not read.

        :raises ValueError: if ``precision`` is set — see above for the two
            ranges and the class to declare for each.
        """
        if expr.precision is not None:
            raise ValueError(
                "MySQL cannot round-trip FLOAT(p): the catalog records FLOAT "
                "without p, and p chooses the storage class. p 0..24 creates "
                "single-precision FLOAT storage — declare FloatType(dialect) "
                "with no precision; p 25..53 creates double-precision DOUBLE "
                f"storage — declare DoubleType(dialect). "
                f"Got precision={expr.precision}."
            )
        self._check_unsigned(expr)
        return ("FLOAT UNSIGNED" if expr.unsigned else "FLOAT"), ()

    def format_data_type_double(self, expr: DoubleType) -> Tuple[str, tuple]:
        """``DOUBLE``; both of the concept's spellings accepted, ``UNSIGNED``
        honoured in MySQL's documented slot.

        ``DOUBLE`` and ``DOUBLE PRECISION`` are synonyms on this server. The
        manual puts them on one line with ``REAL``: "``DOUBLE PRECISION[(M,D)]
        [UNSIGNED] [ZEROFILL]``, ``REAL[(M,D)] [UNSIGNED] [ZEROFILL]`` -- These
        types are synonyms for ``DOUBLE``. Exception: If the ``REAL_AS_FLOAT``
        SQL mode is enabled, ``REAL`` is a synonym for ``FLOAT`` rather than
        ``DOUBLE``." Both spellings are therefore accepted, and both render
        ``DOUBLE`` -- the word the catalog writes back, which is what makes the
        rendered form parse back to the same class.
        https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html

        (This formatter previously refused ``double precision`` on the claim
        that MySQL rejects the spelling. That claim was false: measured on every
        wired server, 5.6.51 through 26.7.0,
        ``CREATE TABLE t (c DOUBLE PRECISION)`` is accepted and
        ``information_schema.COLUMNS`` reports ``double``.)

        ``REAL`` is deliberately not a third spelling here even though the
        server treats it as one. It is mode-dependent storage -- ``DOUBLE``
        normally, ``FLOAT`` under ``REAL_AS_FLOAT`` -- and the catalog never
        writes the word ``real`` back (it reports ``double``, or ``float`` under
        the mode). A ``RealType`` therefore cannot round-trip, so this dialect
        substitutes it; see :meth:`suggest_substitute_advice` and
        :meth:`suggest_substitute_types`.

        The numeric-type syntax writes the concept as ``DOUBLE[(M,D)] [UNSIGNED]
        [ZEROFILL]``, so the attribute follows the type word in the same slot the
        integers use; see :meth:`format_data_type_float` for why MySQL's own
        deprecation of ``UNSIGNED`` on ``FLOAT``, ``DOUBLE`` and ``DECIMAL`` is
        honoured rather than routed around.
        https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html
        """
        self._check_spelling(expr, DoubleType)
        self._check_unsigned(expr)
        return ("DOUBLE UNSIGNED" if expr.unsigned else "DOUBLE"), ()

    def format_data_type_decimal(self, expr: DecimalType) -> Tuple[str, tuple]:
        """``DECIMAL`` — all three of the concept's spellings accepted.

        MySQL's manual states that ``DECIMAL``, ``NUMERIC`` and ``DEC`` are
        synonyms for one fixed-point type, so all three are accepted and
        ``DECIMAL`` is rendered (the word MySQL itself writes back).
        ``FIXED``, MySQL's fourth historical synonym, is not accepted: it is
        not in the concept's closed spelling list, and pretending otherwise
        would make the list meaningless.

        ``unsigned`` is honoured rather than dropped. MySQL writes this concept
        as ``DECIMAL[(M[,D])] [UNSIGNED] [ZEROFILL]`` (and the same for ``DEC``,
        ``NUMERIC`` and ``FIXED``, its three synonyms), so the attribute goes
        **after** the ``(M[,D])`` group — the position the grammar gives it and
        the position the catalog reports it in, which is what makes
        the backend's introspection parser able to read this backend's own
        output back.
        https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html

        "Floating point and fixed-point types also can be ``UNSIGNED``. As with
        integer types, this attribute prevents negative values from being stored
        in the column. Unlike the integer types, the upper range of column values
        remains the same." — MySQL's own words, which is why this is a field on
        one class rather than a second ``DecimalType``: the range does not
        double, the reachable values do change, and the schema differ has to see
        that change. MySQL also deprecates it here ("Consider using a simple
        ``CHECK`` constraint instead for such columns"); see
        :meth:`format_data_type_float` for why that does not change the answer.
        https://dev.mysql.com/doc/refman/9.7/en/numeric-type-attributes.html

        The precision and scale bounds below are MySQL's and are untouched by
        this: ``unsigned`` sits after the ``(M, D)`` group, so a request that is
        out of range is still a ``ValueError`` and is still refused before any
        attribute is appended.
        """
        self._check_spelling(expr, DecimalType)
        if expr.precision is not None and not 1 <= expr.precision <= 65:
            raise ValueError(
                f"MySQL DECIMAL precision must be between 1 and 65, "
                f"got {expr.precision}."
            )
        if expr.scale is not None and not 0 <= expr.scale <= 30:
            raise ValueError(
                f"MySQL DECIMAL scale must be between 0 and 30, "
                f"got {expr.scale}."
            )
        if (expr.precision is not None and expr.scale is not None
                and expr.scale > expr.precision):
            raise ValueError(
                f"MySQL DECIMAL scale ({expr.scale}) cannot exceed "
                f"precision ({expr.precision})."
            )
        if expr.precision is not None and expr.scale is not None:
            base = f"DECIMAL({expr.precision}, {expr.scale})"
        elif expr.precision is not None:
            base = f"DECIMAL({expr.precision})"
        else:
            base = "DECIMAL"
        self._check_unsigned(expr)
        return (f"{base} UNSIGNED" if expr.unsigned else base), ()

    def format_data_type_json(self, expr: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    def format_data_type_jsonb(self, expr: JsonBType) -> Tuple[str, tuple]:
        return "JSON", ()

    def format_data_type_blob(self, expr: BlobType) -> Tuple[str, tuple]:
        """``BLOB`` only.

        ``BYTEA`` is PostgreSQL's name for this concept and is not a MySQL type
        at all, so it is refused here. ``BLOB`` — the concept's default
        spelling, and the word MySQL writes — always renders.
        """
        self._check_spelling(expr, ("blob",))
        return "BLOB", ()

    def format_data_type_custom(self, expr: CustomType) -> Tuple[str, tuple]:
        return expr.raw, ()

    # ------------------------------------------------------------------
    # DataTypeSupport — per-type support declarations
    #
    # MySQL declares support for exactly the format_data_type_* family
    # above (1:1 correspondence contract): every type this mixin renders
    # is genuinely storable in MySQL, so support is honest ``True`` for
    # each, and honestly absent for everything else (e.g. ``xml``,
    # ``array``, ``interval`` — see ``substitute_data_types()``).
    # ------------------------------------------------------------------

    def supports_data_type_mysql_tinyint(self) -> bool:
        return True

    def supports_data_type_mysql_smallint(self) -> bool:
        return True

    def supports_data_type_mysql_signed(self) -> bool:
        return True

    def supports_data_type_mysql_unsigned(self) -> bool:
        return True

    def supports_data_type_mysql_mediumint(self) -> bool:
        return True

    def supports_data_type_mysql_int(self) -> bool:
        return True

    def supports_data_type_mysql_bigint(self) -> bool:
        return True

    def supports_data_type_mysql_tinyblob(self) -> bool:
        return True

    def supports_data_type_mysql_blob(self) -> bool:
        return True

    def supports_data_type_mysql_mediumblob(self) -> bool:
        return True

    def supports_data_type_mysql_longblob(self) -> bool:
        return True

    def supports_data_type_mysql_tinytext(self) -> bool:
        return True

    def supports_data_type_mysql_text(self) -> bool:
        return True

    def supports_data_type_mysql_mediumtext(self) -> bool:
        return True

    def supports_data_type_mysql_longtext(self) -> bool:
        return True

    def supports_data_type_mysql_bit(self) -> bool:
        return True

    def supports_data_type_mysql_year(self) -> bool:
        return True

    def supports_data_type_mysql_binary(self) -> bool:
        return True

    def supports_data_type_mysql_varbinary(self) -> bool:
        return True

    def supports_data_type_mysql_uuid(self) -> bool:
        """Whether the UUID substitute — the 16 raw bytes — is supported.

        Always true: it is a ``BINARY(16)`` column, and this backend renders
        ``BINARY``. MySQL itself has no UUID type, which is why the concept is
        substituted rather than rendered under its own name.
        """
        return True

    def supports_data_type_enum(self) -> bool:
        return True

    def supports_data_type_mysql_enum(self) -> bool:
        return True

    def supports_data_type_mysql_set(self) -> bool:
        return True

    def supports_data_type_mysql_geometry(self) -> bool:
        return True

    def supports_data_type_mysql_point(self) -> bool:
        return True

    def supports_data_type_mysql_linestring(self) -> bool:
        return True

    def supports_data_type_mysql_polygon(self) -> bool:
        return True

    def supports_data_type_mysql_multipoint(self) -> bool:
        return True

    def supports_data_type_mysql_multilinestring(self) -> bool:
        return True

    def supports_data_type_mysql_multipolygon(self) -> bool:
        return True

    def supports_data_type_mysql_geometrycollection(self) -> bool:
        return True

    def supports_data_type_mysql_vector(self) -> bool:
        return True

    def supports_data_type_integer(self) -> bool:
        return True

    def supports_data_type_bigint(self) -> bool:
        return True

    def supports_data_type_smallint(self) -> bool:
        return True

    def supports_data_type_tinyint(self) -> bool:
        return True

    def supports_data_type_varchar(self) -> bool:
        return True

    def supports_data_type_char(self) -> bool:
        return True

    def supports_data_type_text(self) -> bool:
        return True

    def supports_data_type_boolean(self) -> bool:
        return True

    def supports_data_type_date(self) -> bool:
        return True

    def supports_data_type_datetime(self) -> bool:
        return True

    def supports_data_type_time(self) -> bool:
        return True

    def supports_data_type_timetz(self) -> bool:
        return True

    def supports_data_type_timestamp(self) -> bool:
        return True

    def supports_data_type_timestamptz(self) -> bool:
        return True

    def supports_data_type_float(self) -> bool:
        return True

    def supports_data_type_double(self) -> bool:
        return True

    def supports_data_type_decimal(self) -> bool:
        return True

    def supports_data_type_json(self) -> bool:
        return True

    def supports_data_type_jsonb(self) -> bool:
        return True

    def supports_data_type_blob(self) -> bool:
        return True

    def supports_data_type_custom(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # DataTypeSupport — cross-backend type suggestions
    # ------------------------------------------------------------------

    def suggest_substitute_advice(self, name: str) -> SubstituteAdviceSuggestion:
        """State what MySQL's substitution for *name* gives up, in the error.

        The default message says "It suggests X instead, which is what this
        backend uses" without claiming the substitute means the same thing;
        this hook is where a backend that has something specific to add says
        it. For ``real`` there is exactly that to add: the concept cannot
        round-trip, and the reason is a vendor synonym rule rather than a
        storage choice this framework made.
        """
        if name == "real":
            advice = (
                "MySQL's ``REAL`` is a synonym for ``DOUBLE`` in this server's "
                "grammar (the manual lists ``DOUBLE PRECISION`` and ``REAL`` as "
                "synonyms of ``DOUBLE``); only under the ``REAL_AS_FLOAT`` SQL "
                "mode does it mean ``FLOAT``. Every wired server reports a "
                "``REAL`` column as ``double`` (``float`` under that mode) and "
                "never as ``real`` in ``information_schema``, so the "
                "single-precision concept cannot round-trip. Declare "
                "``DoubleType``, or ``FloatType`` for 4-byte single precision."
            )
            return SubstituteAdviceSuggestion(advice=advice)
        return SubstituteAdviceSuggestion(advice="")

    def suggest_substitute_types(self) -> SubstituteTypeSuggestion:
        """Cross-backend type-consistency suggestions for MySQL.

        Every core concept this dialect cannot spell is named here rather than
        left in silence: the caller who asks for one is told what MySQL stores
        instead, which is a usable answer, and the keys stay disjoint from
        ``supports_data_types()`` because a type that is rendered needs no
        substitute.

        ``real``
            MySQL documents ``REAL`` as a synonym of ``DOUBLE`` — and, "if the
            ``REAL_AS_FLOAT`` SQL mode is enabled, ``REAL`` is a synonym for
            ``FLOAT`` rather than ``DOUBLE``". Every wired server reports a
            ``REAL`` column as ``double`` (``float`` under that mode) and never
            writes the word ``real`` back, so the concept cannot round-trip
            through the introspection ``MySQLTypeParser``: the class is the single-precision
            concept on paper, while the column the server builds is the 8-byte
            double (or 4-byte float under the mode). The substitute is
            ``DoubleType`` — what the column actually is in the default mode —
            and :meth:`suggest_substitute_advice` carries the same fact into the error
            a caller sees.

        ``uuid``
            MySQL has no UUID type — its data-types chapter is a closed list of
            categories ("numeric types, date and time types, string (character
            and byte) types, spatial types, and the JSON data type", manual
            §13) and ``UUID`` is in none of them. What MySQL *does* document is
            the binary UUID as 16 bytes: ``UUID_TO_BIN()`` "return[s] [the]
            binary UUID [as] a ``VARBINARY(16)`` value" (§14.23). The substitute
            is therefore the 16 raw bytes as a fixed-length column —
            :class:`~...expression.types.types.MySQLUUIDType`, which renders
            ``BINARY(16)``.

            The width is baked into that class rather than left to the caller,
            and it has to be: the mapping names a *class*, and the generic
            ``UUIDType`` carries no length to hand over. Naming the general
            byte-string class instead — as this used to — yields a substitute
            that renders ``BINARY``, and the manual defines that as
            ``BINARY(1)``: "An optional length *M* represents the column length
            in bytes. **If omitted, *M* defaults to 1.**" (§13.3.1). Every
            scenario server agrees: ``CREATE TABLE t (c BINARY)`` reports
            ``binary(1)``, and a 16-byte UUID then fails with error 1406 or is
            truncated to its first byte. A one-byte column silently handed to
            someone who asked for a UUID is the defect this fixes.

            ``BINARY(16)`` rather than ``VARBINARY(16)``: a UUID is *always* 16
            bytes, so the width is a length and not a ceiling, and the padding
            concern that usually argues for ``VARBINARY`` cannot arise. See
            :class:`~...expression.types.types.MySQLUUIDType` for the full
            argument, the storage figures and the manual sections.

        ``binary`` / ``varbinary``
            MySQL *does* have ``BINARY(n)`` and ``VARBINARY(n)``, but the
            framework reaches them through the ``mysql_``-namespaced types,
            which carry the length MySQL requires and get their own dispatch
            keys. Those are therefore the suggested classes for the core
            concepts — a mapping that says "the byte string you want is this
            backend's own type", not a claim that MySQL lacks byte strings.

            The difference from ``uuid`` above is where the length comes from.
            These two core concepts carry a ``length`` field for the caller to
            fill in, so the substitute is a class that *takes* the width; the
            UUID concept carries none, so the substitute is a class that *is*
            the width. That is the whole rule: a substitute must be able to say
            the size on its own when the concept fixes it.

            One asymmetry is MySQL's own grammar, not a choice made here.
            ``BINARY[(M)]`` lets *M* be omitted and defines the omission as
            ``BINARY(1)``, so ``MySQLBinaryType()`` renders ``BINARY`` and is
            genuinely a one-byte column — a legal column, and a legal answer
            for a caller who asked for a one-byte byte string. ``VARBINARY(M)``
            has no optional form: ``CREATE TABLE t (c VARBINARY)`` is a syntax
            error (1064, on every server checked), so ``MySQLVarBinaryType``
            requires its length rather than rendering SQL the server refuses.

        ``xml``
            MySQL has no XML type and no XML validation: an XML document is
            stored as a character string, so ``TextType`` is what this backend
            actually holds. This is not a compromise.

        ``array``
            MySQL has no array type. A list of values is stored as a JSON
            document, so ``JsonType`` is the substitute.

        ``interval``
            MySQL's ``INTERVAL`` is not a column type at all — it is a
            date-arithmetic *keyword*, and ``CREATE TABLE t (c INTERVAL)`` is a
            syntax error. The value it takes is a plain integer count of a unit
            (``DATE_ADD(d, INTERVAL 30 DAY)``), so the number is what a column
            holding a duration stores and ``IntegerType`` is the honest
            substitute; the unit travels with the expression, not with the type.
            ``INT`` has no width that MySQL would fill in differently — its *M*
            is a *display width*, not a storage size — so this one has no
            hidden default to get wrong.
        """
        from ..expression.types.types import (
            MySQLBinaryType,
            MySQLVarBinaryType,
        )

        return SubstituteTypeSuggestion(
            mapping={
                "uuid": MySQLUUIDType,
                "binary": MySQLBinaryType,
                "varbinary": MySQLVarBinaryType,
                "real": DoubleType,
                "xml": TextType,
                "array": JsonType,
                "interval": IntegerType,
            }
        )
