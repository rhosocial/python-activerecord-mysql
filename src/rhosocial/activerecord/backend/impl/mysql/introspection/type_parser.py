# src/rhosocial/activerecord/backend/impl/mysql/introspection/type_parser.py
"""MySQL's type-spelling parser (read direction, introspection-only).

Parsing a server-reported ``COLUMN_TYPE`` string back into a ``DataType`` is
an introspection concern, not a dialect capability: the dialect protocol no
longer declares ``parse_type``. This helper lives under introspection and is
used only when reading back a column's declared type.
"""
from __future__ import annotations

from typing import Any

from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    CharType,
    CustomType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    JsonType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    VarCharType,
)

from .._scan import (
    digit_runs,
    digits_after,
    first_digit_run,
    leading_upper_run,
    parenthesized_digits,
    quoted_values,
    starts_with_word,
    word_after,
)
from ..expression.types import MySQLUUIDType


class MySQLTypeParser:
    """Parse a raw MySQL type spelling into a DataType, bound to a dialect."""

    def __init__(self, dialect: Any):
        self.dialect = dialect

    #: Leading words that open the integer family. Every entry is a whole
    #: identifier: ``INTEGER`` must not be read as ``INT`` plus a boundary, and
    #: ``INT8`` must not be read as ``INT`` plus the digit ``8``.
    _MYSQL_INTEGER_TYPES = (
        "TINYINT",
        "INT1",
        "SMALLINT",
        "INT2",
        "MEDIUMINT",
        "INT",
        "INTEGER",
        "BIGINT",
        "INT8",
    )
    _MYSQL_FLOAT_TYPES = (
        "FLOAT",
        "REAL",
        "DOUBLE",
    )
    # ``DECIMAL`` / ``NUMERIC`` / ``DEC`` are the three spellings of the core
    # concept. MySQL's historical fourth synonym, ``FIXED``, is deliberately
    # absent: it is not in the closed ``SPELLINGS`` list, and mapping it onto
    # the concept with a spelling the concept never declared would make the
    # list decorative. (information_schema never reports ``fixed`` anyway.)
    _MYSQL_DECIMAL_TYPES = (
        "DECIMAL",
        "NUMERIC",
        "DEC",
    )
    _MYSQL_STRING_TYPES = (
        "CHAR",
        "VARCHAR",
        "TEXT",
        "TINYTEXT",
        "MEDIUMTEXT",
        "LONGTEXT",
        "ENUM",
        "SET",
        "BINARY",
        "VARBINARY",
    )
    _MYSQL_BLOB_TYPES = (
        "BLOB",
        "TINYBLOB",
        "MEDIUMBLOB",
        "LONGBLOB",
    )
    _MYSQL_DATE_TYPES = (
        "DATE",
        "DATETIME",
        "TIMESTAMP",
        "TIME",
        "YEAR",
    )
    _MYSQL_JSON_TYPES = ("JSON",)
    _MYSQL_SPATIAL_TYPES = (
        "GEOMETRY",
        "POINT",
        "LINESTRING",
        "POLYGON",
        "MULTIPOINT",
        "MULTILINESTRING",
        "MULTIPOLYGON",
        "GEOMETRYCOLLECTION",
    )
    _MYSQL_BIT_TYPES = ("BIT",)
    _MYSQL_VECTOR_TYPES = ("VECTOR",)

    def parse(self, raw: str) -> DataType:
        """Turn a MySQL type string back into the ``DataType`` it came from.

        Canonical in the D8 sense: each of a concept's closed ``SPELLINGS``
        entries that MySQL writes maps to that concept's one class, with the
        word that was used carried on the instance as ``spelling``. So
        ``"int8"`` and ``"bigint"`` both give a :class:`MySQLBigIntType` and
        differ only in ``spelling``; ``"character varying(10)"``, ``"clob"``
        and ``"bytea"`` give :class:`CustomType`, because MySQL has no such
        types and pretending otherwise would make the differ report a change
        that was never made.
        """
        stripped = raw.strip()
        upper = stripped.upper()

        # BIT type
        if starts_with_word(upper, self._MYSQL_BIT_TYPES):
            digits = first_digit_run(stripped)
            n = int(digits) if digits is not None else None
            from ..expression.types import MySQLBitType

            return MySQLBitType(self.dialect, n)

        # BOOLEAN / BOOL — MySQL's documented aliases for TINYINT(1), so both
        # spellings of the core concept reach it.
        if upper.startswith("BOOLEAN"):
            return BooleanType(dialect=self.dialect, spelling="boolean")
        if upper.startswith("BOOL"):
            return BooleanType(dialect=self.dialect, spelling="bool")

        # Integer family
        if starts_with_word(upper, self._MYSQL_INTEGER_TYPES):
            unsigned = "UNSIGNED" in upper
            zerofill = "ZEROFILL" in upper
            if upper.startswith("TINYINT") or upper.startswith("INT1"):
                # Read the width out of ``(n)`` only. The digits of the
                # ``INT1`` synonym are part of the *name*, so a bare scan over
                # the whole string would read ``INT1`` as width 1 and hand back
                # a boolean.
                width = parenthesized_digits(stripped, allow_blanks=True)
                display_width = int(width) if width is not None else None
                from ..expression.types import MySQLTinyIntType

                spelling = "int1" if upper.startswith("INT1") else "tinyint"
                t = MySQLTinyIntType(
                    dialect=self.dialect,
                    unsigned=unsigned,
                    zerofill=zerofill,
                    spelling=spelling,
                )
                # TINYINT(1) is commonly used as BOOLEAN
                if display_width == 1 and not unsigned and not zerofill:
                    return BooleanType(self.dialect)
                return t
            if upper.startswith("SMALLINT") or upper.startswith("INT2"):
                from ..expression.types import MySQLSmallIntType
                spelling = "int2" if upper.startswith("INT2") else "smallint"
                return MySQLSmallIntType(dialect=self.dialect, unsigned=unsigned,
                                         zerofill=zerofill, spelling=spelling)
            if upper.startswith("MEDIUMINT"):
                # ``information_schema`` reports ``mediumint`` verbatim (and
                # ``mediumint(8) unsigned zerofill`` for a zero-padded one), so
                # this branch really is reached for MEDIUMINT columns and the
                # width has to be named by its own class.
                from ..expression.types import MySQLMediumIntType
                return MySQLMediumIntType(dialect=self.dialect, unsigned=unsigned,
                                          zerofill=zerofill)
            if upper.startswith("BIGINT") or upper.startswith("INT8"):
                from ..expression.types import MySQLBigIntType
                spelling = "int8" if upper.startswith("INT8") else "bigint"
                return MySQLBigIntType(dialect=self.dialect, unsigned=unsigned,
                                       zerofill=zerofill, spelling=spelling)
            # INT / INTEGER — the two spellings of the 4-byte concept. Both
            # render as ``INT``, but which word was declared is kept so a diff
            # does not report a change that was never made.
            from ..expression.types import MySQLIntType
            spelling = "integer" if upper.startswith("INTEGER") else "int"
            return MySQLIntType(dialect=self.dialect, unsigned=unsigned,
                                zerofill=zerofill, spelling=spelling)

        # Float family
        if starts_with_word(upper, self._MYSQL_FLOAT_TYPES):
            # ``UNSIGNED`` is read here for the same reason it is read for the
            # integers above: MySQL writes ``FLOAT[(M,D)] [UNSIGNED]``,
            # ``FLOAT(p) [UNSIGNED]`` and ``DOUBLE[(M,D)] [UNSIGNED]``, so an
            # introspected ``double unsigned`` used to come back as a signed
            # ``DoubleType`` and a declared unsigned column compared equal to
            # the signed column the server had actually changed. ``ZEROFILL``
            # is deliberately not read: the core concepts carry no such field,
            # and MySQL documents that specifying it "adds the UNSIGNED
            # attribute to the column", so the signedness this branch recovers
            # is the whole of what the column's storage changed.
            #
            # ``REAL`` and ``DOUBLE PRECISION`` are the server's documented
            # synonyms for ``DOUBLE`` (the manual groups all three on one line),
            # so both canonicalise to :class:`DoubleType` -- the storage the
            # column actually has. ``REAL_AS_FLOAT`` is the mode-dependent
            # exception, under which REAL means FLOAT; a live column made under
            # that mode is not reported as ``real`` but as ``float``, which
            # reaches the FLOAT branch below. The catalog never writes the word
            # ``real``, which is why the dialect refuses RealType and suggests
            # DoubleType for it (see ``suggest_substitute_advice`` and
            # ``suggest_substitute_types``).
            # https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html
            unsigned = "UNSIGNED" in upper
            if upper.startswith("DOUBLE"):
                return DoubleType(dialect=self.dialect, unsigned=unsigned)
            if upper.startswith("REAL"):
                return DoubleType(dialect=self.dialect, unsigned=unsigned)
            # FLOAT. The manual says what the parentheses mean: "If p is from 0
            # to 24, the data type becomes FLOAT with no M or D values. If p is
            # from 25 to 53, the data type becomes DOUBLE with no M or D
            # values." A single argument is therefore read as that p and
            # canonicalised to the class it selects: p<=24 is 4-byte FLOAT
            # storage, so it stays FloatType and p itself is dropped (the
            # catalog does not record it); p>=25 is DOUBLE storage, so it
            # becomes DoubleType.
            #
            # The deprecated two-argument ``FLOAT(M,D)`` is read differently,
            # because its first number is M (total *decimal* digits), not p
            # (bits): measured on the wired servers, ``FLOAT(25,17)`` and
            # ``FLOAT(53,17)`` both store single-precision values
            # (1.2345678806304932, against ``DOUBLE``'s 1.2345678901234567) and
            # both report ``NUMERIC_PRECISION = M``, while one-argument
            # ``FLOAT(25)`` resolves to ``double``. The column is therefore the
            # 4-byte concept, and FloatType is returned with the (M,D) display
            # spec dropped -- FloatType carries no scale, and this dialect now
            # refuses a precision it cannot round-trip.
            nums = digit_runs(stripped)
            if len(nums) >= 2:
                return FloatType(self.dialect, unsigned=unsigned)
            precision = int(nums[0]) if nums else None
            if precision is not None and precision >= 25:
                return DoubleType(self.dialect, unsigned=unsigned)
            return FloatType(self.dialect, unsigned=unsigned)

        # Decimal family
        if starts_with_word(upper, self._MYSQL_DECIMAL_TYPES):
            # One concept, three words: MySQL's manual calls DECIMAL, NUMERIC
            # and DEC synonyms, so all three reach DecimalType and the word that
            # was used is recorded rather than lost.
            #
            # ``UNSIGNED`` is read here too, for the same reason it is read for
            # the integers and the floats above: MySQL writes
            # ``DECIMAL[(M[,D])] [UNSIGNED] [ZEROFILL]`` (and the same for the
            # DEC / NUMERIC / FIXED synonyms), and an introspected
            # ``decimal(10,2) unsigned zerofill`` used to come back as a signed
            # ``DecimalType(10, 2)`` -- the signedness simply gone, so a column
            # the server had changed to unsigned compared equal to its own
            # declaration and the differ reported no change.
            # https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html
            unsigned = "UNSIGNED" in upper
            if upper.startswith("NUMERIC"):
                spelling = "numeric"
            elif upper.startswith("DEC") and not upper.startswith("DECIMAL"):
                spelling = "dec"
            else:
                spelling = "decimal"
            nums = digit_runs(stripped)
            if len(nums) >= 2:
                return DecimalType(self.dialect, int(nums[0]), int(nums[1]),
                                   unsigned=unsigned, spelling=spelling)
            if len(nums) == 1:
                return DecimalType(self.dialect, int(nums[0]), unsigned=unsigned,
                                   spelling=spelling)
            return DecimalType(self.dialect, unsigned=unsigned, spelling=spelling)

        # String family
        if starts_with_word(upper, self._MYSQL_STRING_TYPES):
            if upper.startswith("TINYTEXT"):
                from ..expression.types import MySQLTinyTextType
                return MySQLTinyTextType(self.dialect)
            if upper.startswith("MEDIUMTEXT"):
                from ..expression.types import MySQLMediumTextType
                return MySQLMediumTextType(self.dialect)
            if upper.startswith("LONGTEXT"):
                from ..expression.types import MySQLLongTextType
                return MySQLLongTextType(self.dialect)
            if upper.startswith("TEXT"):
                from ..expression.types import MySQLTextType
                return MySQLTextType(self.dialect)
            if upper.startswith("ENUM"):
                from ..expression.types import MySQLEnumType

                values = quoted_values(stripped)
                charset = word_after(upper, "CHARACTER", "SET")
                collation = word_after(upper, "COLLATE")
                return MySQLEnumType(self.dialect, values, charset=charset, collation=collation)
            if upper.startswith("SET"):
                from ..expression.types import MySQLSetType

                values = quoted_values(stripped)
                charset = word_after(upper, "CHARACTER", "SET")
                collation = word_after(upper, "COLLATE")
                return MySQLSetType(self.dialect, values, charset=charset, collation=collation)
            if upper.startswith("BINARY"):
                digits = first_digit_run(stripped)
                length = int(digits) if digits is not None else None
                # ``BINARY(16)`` is this backend's UUID storage, so it is read back
                # as the UUID type: a UUID is 128 bits with no other width, so
                # the column width *is* the identity, and reading it as a
                # plain byte string would leave the declared UUID type unequal
                # to its own column in any schema diff. This is what makes the
                # substitute round-trip — ``MySQLUUIDType`` renders
                # ``BINARY(16)`` and this hands back an equal value object —
                # and it is the same width-specific reading the framework
                # already applies to ``TINYINT(1)`` -> ``BooleanType``. A plain
                # 16-byte column that is not meant to be a UUID is now named
                # ``mysql_uuid`` on introspection; the storage is identical
                # either way, only the framework's name for it differs.
                if length == MySQLUUIDType.BYTE_LENGTH:
                    return MySQLUUIDType(self.dialect)
                from ..expression.types import MySQLBinaryType
                return MySQLBinaryType(self.dialect, length)
            if upper.startswith("VARBINARY"):
                digits = first_digit_run(stripped)
                length = int(digits) if digits is not None else None
                # A bare ``VARBINARY`` cannot reach here from a live server:
                # ``CREATE TABLE t (c VARBINARY)`` is a syntax error, so the
                # server never reports one. It is still refused rather than
                # guessed at, so a hand-written string gets the same answer a
                # constructor call would.
                if length is None:
                    return CustomType(self.dialect, raw=stripped)
                from ..expression.types import MySQLVarBinaryType
                return MySQLVarBinaryType(self.dialect, length)
            # CHAR / VARCHAR
            length_digits = parenthesized_digits(stripped)
            length = int(length_digits) if length_digits is not None else None
            if upper.startswith("VARCHAR"):
                return VarCharType(self.dialect, length)
            return CharType(self.dialect, length)

        # BLOB family
        if starts_with_word(upper, self._MYSQL_BLOB_TYPES):
            if upper.startswith("TINYBLOB"):
                from ..expression.types import MySQLTinyBlobType
                return MySQLTinyBlobType(self.dialect)
            if upper.startswith("MEDIUMBLOB"):
                from ..expression.types import MySQLMediumBlobType
                return MySQLMediumBlobType(self.dialect)
            if upper.startswith("LONGBLOB"):
                from ..expression.types import MySQLLongBlobType
                return MySQLLongBlobType(self.dialect)
            from ..expression.types import MySQLBlobType
            return MySQLBlobType(self.dialect)

        # Date/time family
        if starts_with_word(upper, self._MYSQL_DATE_TYPES):
            if upper.startswith("YEAR"):
                digits = first_digit_run(stripped)
                display_width = int(digits) if digits is not None else None
                from ..expression.types import MySQLYearType

                return MySQLYearType(self.dialect, display_width)
            if upper.startswith("DATE"):
                if upper.strip() == "DATE":
                    return DateType(self.dialect)
                return DateTimeType(self.dialect)
            if upper.startswith("DATETIME"):
                digits = first_digit_run(stripped)
                precision = int(digits) if digits is not None else None
                return DateTimeType(self.dialect, precision)
            if upper.startswith("TIMESTAMP"):
                digits = first_digit_run(stripped)
                precision = int(digits) if digits is not None else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(self.dialect, precision)
                return TimestampType(self.dialect, precision)
            if upper.startswith("TIME"):
                digits = first_digit_run(stripped)
                precision = int(digits) if digits is not None else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(self.dialect, precision)
                return TimeType(self.dialect, precision)

        # JSON
        if starts_with_word(upper, self._MYSQL_JSON_TYPES):
            return JsonType(self.dialect)

        # Spatial
        if starts_with_word(upper, self._MYSQL_SPATIAL_TYPES):
            srid_digits = digits_after(upper, "SRID")
            srid = int(srid_digits) if srid_digits is not None else None
            from ..expression.types import (
                MySQLGeometryCollectionType,
                MySQLGeometryType,
                MySQLLineStringType,
                MySQLMultiLineStringType,
                MySQLMultiPointType,
                MySQLMultiPolygonType,
                MySQLPointType,
                MySQLPolygonType,
            )
            spatial_map = {
                "GEOMETRY": MySQLGeometryType,
                "POINT": MySQLPointType,
                "LINESTRING": MySQLLineStringType,
                "POLYGON": MySQLPolygonType,
                "MULTIPOINT": MySQLMultiPointType,
                "MULTILINESTRING": MySQLMultiLineStringType,
                "MULTIPOLYGON": MySQLMultiPolygonType,
                "GEOMETRYCOLLECTION": MySQLGeometryCollectionType,
            }
            # Dispatch on the leading **word**, not on a prefix scanned in
            # declaration order. ``GEOMETRYCOLLECTION`` begins with
            # ``GEOMETRY``, and dict order put ``GEOMETRY`` first, so the
            # ``startswith`` loop read a collection column as the generic
            # geometry type -- the same defect MariaDB's branch of this
            # family fixed, measured there on all fifteen wired servers:
            # ``CREATE TABLE t (c GEOMETRYCOLLECTION)`` introspected as the
            # generic geometry type, which made the differ report *no*
            # change between two columns MySQL can certainly tell apart.
            # Every one of the eight words is a single identifier, so the
            # leading word is the whole name and the map needs no ordering
            # discipline to stay correct.
            name = leading_upper_run(upper) or upper
            return spatial_map.get(name, MySQLGeometryType)(self.dialect, srid)

        # Vector (MySQL 9.0+)
        if starts_with_word(upper, self._MYSQL_VECTOR_TYPES):
            dim_digits = first_digit_run(stripped)
            dim = int(dim_digits) if dim_digits is not None else 0
            from ..expression.types import MySQLVectorType

            return MySQLVectorType(self.dialect, dim)

        # Fallback: an honest "I do not model this type" rather than a guess.
        return CustomType(self.dialect, raw=stripped)
