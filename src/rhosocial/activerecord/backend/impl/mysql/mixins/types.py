# src/rhosocial/activerecord/backend/impl/mysql/mixins/types.py
"""MySQL DataType formatting and parsing mixin."""

from __future__ import annotations

import re
from typing import Optional, Tuple

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import (
    DDLTypeMixin,
    DDLTypeSuggestionMixin,
)
from rhosocial.activerecord.backend.dialect.protocols import DDLTypeSupport
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    JsonBType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
)
from ..expression.types import (
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
    MySQLMediumTextType,
    MySQLMultiLineStringType,
    MySQLMultiPointType,
    MySQLMultiPolygonType,
    MySQLPointType,
    MySQLPolygonType,
    MySQLSetType,
    MySQLSmallIntType,
    MySQLTextType,
    MySQLTinyBlobType,
    MySQLTinyIntType,
    MySQLTinyTextType,
    MySQLVarBinaryType,
    MySQLVectorType,
    MySQLYearType,
)


class MySQLTypeSupportMixin(DDLTypeMixin, DDLTypeSupport):
    """MySQL DataType formatting and parsing.

    Implements ``DDLTypeSupport`` so the dialect can render ``DataType``
    expressions to SQL strings and parse raw SQL type strings back into
    ``DataType`` instances.
    """

    # ------------------------------------------------------------------
    # DDLTypeSupport — formatting
    # ------------------------------------------------------------------

    # --- MySQL-specific type formatters ---

    @DDLTypeMixin.handles(MySQLTinyIntType)
    def format_data_type_tiny_int(self, data_type: MySQLTinyIntType) -> Tuple[str, tuple]:
        sql = "TINYINT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MySQLSmallIntType)
    def format_data_type_small_int(self, data_type: MySQLSmallIntType) -> Tuple[str, tuple]:
        sql = "SMALLINT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MySQLIntType)
    def format_data_type_int(self, data_type: MySQLIntType) -> Tuple[str, tuple]:
        sql = "INT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MySQLBigIntType)
    def format_data_type_big_int(self, data_type: MySQLBigIntType) -> Tuple[str, tuple]:
        sql = "BIGINT"
        if data_type.zerofill:
            return f"{sql} ZEROFILL", ()
        if data_type.unsigned:
            return f"{sql} UNSIGNED", ()
        return sql, ()

    @DDLTypeMixin.handles(MySQLTinyBlobType)
    def format_data_type_tiny_blob(self, data_type: MySQLTinyBlobType) -> Tuple[str, tuple]:
        return "TINYBLOB", ()

    @DDLTypeMixin.handles(MySQLBlobType)
    def format_data_type_blob(self, data_type: MySQLBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    @DDLTypeMixin.handles(MySQLMediumBlobType)
    def format_data_type_medium_blob(self, data_type: MySQLMediumBlobType) -> Tuple[str, tuple]:
        return "MEDIUMBLOB", ()

    @DDLTypeMixin.handles(MySQLLongBlobType)
    def format_data_type_long_blob(self, data_type: MySQLLongBlobType) -> Tuple[str, tuple]:
        return "LONGBLOB", ()

    @DDLTypeMixin.handles(MySQLTinyTextType)
    def format_data_type_tiny_text(self, data_type: MySQLTinyTextType) -> Tuple[str, tuple]:
        return "TINYTEXT", ()

    @DDLTypeMixin.handles(MySQLTextType)
    def format_data_type_text(self, data_type: MySQLTextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    @DDLTypeMixin.handles(MySQLMediumTextType)
    def format_data_type_medium_text(self, data_type: MySQLMediumTextType) -> Tuple[str, tuple]:
        return "MEDIUMTEXT", ()

    @DDLTypeMixin.handles(MySQLLongTextType)
    def format_data_type_long_text(self, data_type: MySQLLongTextType) -> Tuple[str, tuple]:
        return "LONGTEXT", ()

    @DDLTypeMixin.handles(MySQLBitType)
    def format_data_type_bit(self, data_type: MySQLBitType) -> Tuple[str, tuple]:
        if data_type.n is not None:
            return f"BIT({data_type.n})", ()
        return "BIT", ()

    @DDLTypeMixin.handles(MySQLYearType)
    def format_data_type_year(self, data_type: MySQLYearType) -> Tuple[str, tuple]:
        if data_type.display_width is not None:
            return f"YEAR({data_type.display_width})", ()
        return "YEAR", ()

    @DDLTypeMixin.handles(MySQLBinaryType)
    def format_data_type_binary(self, data_type: MySQLBinaryType) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"BINARY({data_type.length})", ()
        return "BINARY", ()

    @DDLTypeMixin.handles(MySQLVarBinaryType)
    def format_data_type_var_binary(self, data_type: MySQLVarBinaryType) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"VARBINARY({data_type.length})", ()
        return "VARBINARY", ()

    @DDLTypeMixin.handles(MySQLEnumType)
    def format_data_type_enum(self, data_type: MySQLEnumType) -> Tuple[str, tuple]:
        values_str = ",".join(f"'{v}'" for v in data_type.values)
        result = f"ENUM({values_str})"
        if data_type.charset:
            result += f" CHARACTER SET {data_type.charset}"
        if data_type.collation:
            result += f" COLLATE {data_type.collation}"
        return result, ()

    @DDLTypeMixin.handles(MySQLSetType)
    def format_data_type_set(self, data_type: MySQLSetType) -> Tuple[str, tuple]:
        values_str = ",".join(f"'{v}'" for v in data_type.values)
        result = f"SET({values_str})"
        if data_type.charset:
            result += f" CHARACTER SET {data_type.charset}"
        if data_type.collation:
            result += f" COLLATE {data_type.collation}"
        return result, ()

    @DDLTypeMixin.handles(MySQLGeometryType)
    def format_data_type_geometry(self, data_type: MySQLGeometryType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"GEOMETRY SRID {data_type.srid}", ()
        return "GEOMETRY", ()

    @DDLTypeMixin.handles(MySQLPointType)
    def format_data_type_point(self, data_type: MySQLPointType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"POINT SRID {data_type.srid}", ()
        return "POINT", ()

    @DDLTypeMixin.handles(MySQLLineStringType)
    def format_data_type_line_string(self, data_type: MySQLLineStringType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"LINESTRING SRID {data_type.srid}", ()
        return "LINESTRING", ()

    @DDLTypeMixin.handles(MySQLPolygonType)
    def format_data_type_polygon(self, data_type: MySQLPolygonType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"POLYGON SRID {data_type.srid}", ()
        return "POLYGON", ()

    @DDLTypeMixin.handles(MySQLMultiPointType)
    def format_data_type_multi_point(self, data_type: MySQLMultiPointType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"MULTIPOINT SRID {data_type.srid}", ()
        return "MULTIPOINT", ()

    @DDLTypeMixin.handles(MySQLMultiLineStringType)
    def format_data_type_multi_line_string(self, data_type: MySQLMultiLineStringType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"MULTILINESTRING SRID {data_type.srid}", ()
        return "MULTILINESTRING", ()

    @DDLTypeMixin.handles(MySQLMultiPolygonType)
    def format_data_type_multi_polygon(self, data_type: MySQLMultiPolygonType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"MULTIPOLYGON SRID {data_type.srid}", ()
        return "MULTIPOLYGON", ()

    @DDLTypeMixin.handles(MySQLGeometryCollectionType)
    def format_data_type_geometry_collection(self, data_type: MySQLGeometryCollectionType) -> Tuple[str, tuple]:
        if data_type.srid is not None:
            return f"GEOMETRYCOLLECTION SRID {data_type.srid}", ()
        return "GEOMETRYCOLLECTION", ()

    @DDLTypeMixin.handles(MySQLVectorType)
    def format_data_type_vector(self, data_type: MySQLVectorType) -> Tuple[str, tuple]:
        return f"VECTOR({data_type.dim})", ()

    # --- Core type overrides (MySQL-specific SQL) ---

    @DDLTypeMixin.handles(DoubleType)
    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
        return "DOUBLE", ()

    @DDLTypeMixin.handles(BooleanType)
    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        return "TINYINT(1)", ()

    @DDLTypeMixin.handles(TimeTzType)
    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    @DDLTypeMixin.handles(TimestampTzType)
    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @DDLTypeMixin.handles(JsonBType)
    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "JSON", ()

    # --- Core type handlers (render standard types to MySQL SQL) ---

    @DDLTypeMixin.handles(IntegerType)
    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        return "INT", ()

    @DDLTypeMixin.handles(BigIntType)
    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
        return "BIGINT", ()

    @DDLTypeMixin.handles(SmallIntType)
    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        return "SMALLINT", ()

    @DDLTypeMixin.handles(TinyIntType)
    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:
        return "TINYINT", ()

    @DDLTypeMixin.handles(VarCharType)
    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    @DDLTypeMixin.handles(CharType)
    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        return (f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"), ()

    @DDLTypeMixin.handles(TextType)
    def format_data_type_text_core(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    @DDLTypeMixin.handles(DateTimeType)
    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        return (f"DATETIME({data_type.precision})" if data_type.precision is not None else "DATETIME"), ()

    @DDLTypeMixin.handles(DateType)
    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    @DDLTypeMixin.handles(TimeType)
    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    @DDLTypeMixin.handles(TimestampType)
    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @DDLTypeMixin.handles(FloatType)
    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
        return (f"FLOAT({data_type.precision})" if data_type.precision is not None else "FLOAT"), ()

    @DDLTypeMixin.handles(RealType)
    def format_data_type_real(self, data_type: RealType) -> Tuple[str, tuple]:
        return "REAL", ()

    @DDLTypeMixin.handles(DecimalType)
    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision}, {data_type.scale})", ()
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})", ()
        return "DECIMAL", ()

    @DDLTypeMixin.handles(JsonType)
    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    @DDLTypeMixin.handles(BlobType)
    def format_data_type_blob_core(self, data_type: BlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    # ------------------------------------------------------------------
    # DDLTypeSupport — parsing
    # ------------------------------------------------------------------

    _MYSQL_INTEGER_TYPES = re.compile(
        r"^(?:TINYINT|SMALLINT|MEDIUMINT|INT|INTEGER|BIGINT)\b",
        re.IGNORECASE,
    )
    _MYSQL_FLOAT_TYPES = re.compile(
        r"^(?:FLOAT|REAL|DOUBLE)\b",
        re.IGNORECASE,
    )
    _MYSQL_DECIMAL_TYPES = re.compile(
        r"^(?:DECIMAL|NUMERIC|FIXED)\b",
        re.IGNORECASE,
    )
    _MYSQL_STRING_TYPES = re.compile(
        r"^(?:CHAR|VARCHAR|TEXT|TINYTEXT|MEDIUMTEXT|LONGTEXT|"
        r"ENUM|SET|BINARY|VARBINARY)\b",
        re.IGNORECASE,
    )
    _MYSQL_BLOB_TYPES = re.compile(
        r"^(?:BLOB|TINYBLOB|MEDIUMBLOB|LONGBLOB)\b",
        re.IGNORECASE,
    )
    _MYSQL_DATE_TYPES = re.compile(
        r"^(?:DATE|DATETIME|TIMESTAMP|TIME|YEAR)\b",
        re.IGNORECASE,
    )
    _MYSQL_JSON_TYPES = re.compile(
        r"^(?:JSON)\b",
        re.IGNORECASE,
    )
    _MYSQL_SPATIAL_TYPES = re.compile(
        r"^(?:GEOMETRY|POINT|LINESTRING|POLYGON|"
        r"MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)\b",
        re.IGNORECASE,
    )
    _MYSQL_BIT_TYPES = re.compile(
        r"^(?:BIT)\b",
        re.IGNORECASE,
    )
    _MYSQL_VECTOR_TYPES = re.compile(
        r"^(?:VECTOR)\b",
        re.IGNORECASE,
    )

    def parse_type(self, raw: str) -> DataType:
        stripped = raw.strip()
        upper = stripped.upper()

        # BIT type
        if self._MYSQL_BIT_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            n = int(nums[0]) if nums else None
            from ..expression.types import MySQLBitType
            return MySQLBitType(dialect=self, n=n)

        # Integer family
        if self._MYSQL_INTEGER_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            zerofill = "ZEROFILL" in upper
            if upper.startswith("TINYINT"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MySQLTinyIntType
                t = MySQLTinyIntType(dialect=self)
                t.unsigned = unsigned
                t.zerofill = zerofill
                # TINYINT(1) is commonly used as BOOLEAN
                if display_width == 1 and not unsigned and not zerofill:
                    return BooleanType(dialect=self)
                return t
            if upper.startswith("SMALLINT"):
                from ..expression.types import MySQLSmallIntType
                t = MySQLSmallIntType(dialect=self)
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            if upper.startswith("MEDIUMINT"):
                from ..expression.types import MySQLIntType
                t = MySQLIntType(dialect=self)
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            if upper.startswith("BIGINT"):
                from ..expression.types import MySQLBigIntType
                t = MySQLBigIntType(dialect=self)
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            # INT / INTEGER
            from ..expression.types import MySQLIntType
            t = MySQLIntType(dialect=self)
            t.unsigned = unsigned
            t.zerofill = zerofill
            return t

        # Float family
        if self._MYSQL_FLOAT_TYPES.match(upper):
            if upper.startswith("DOUBLE"):
                return DoubleType(dialect=self)
            if upper.startswith("REAL"):
                return RealType(dialect=self)
            # FLOAT
            nums = re.findall(r"\d+", stripped)
            precision = int(nums[0]) if nums else None
            return FloatType(dialect=self, precision=precision)

        # Decimal family
        if self._MYSQL_DECIMAL_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return DecimalType(dialect=self, precision=int(nums[0]), scale=int(nums[1]))
            if len(nums) == 1:
                return DecimalType(dialect=self, precision=int(nums[0]))
            return DecimalType(dialect=self)

        # String family
        if self._MYSQL_STRING_TYPES.match(upper):
            if upper.startswith("TINYTEXT"):
                from ..expression.types import MySQLTinyTextType
                return MySQLTinyTextType(dialect=self)
            if upper.startswith("MEDIUMTEXT"):
                from ..expression.types import MySQLMediumTextType
                return MySQLMediumTextType(dialect=self)
            if upper.startswith("LONGTEXT"):
                from ..expression.types import MySQLLongTextType
                return MySQLLongTextType(dialect=self)
            if upper.startswith("TEXT"):
                from ..expression.types import MySQLTextType
                return MySQLTextType(dialect=self)
            if upper.startswith("ENUM"):
                from ..expression.types import MySQLEnumType
                values = re.findall(r"'([^']*)'", stripped)
                charset = None
                collation = None
                cs_match = re.search(r"CHARACTER\s+SET\s+(\w+)", upper)
                if cs_match:
                    charset = cs_match.group(1)
                col_match = re.search(r"COLLATE\s+(\w+)", upper)
                if col_match:
                    collation = col_match.group(1)
                return MySQLEnumType(dialect=self, values=values, charset=charset, collation=collation)
            if upper.startswith("SET"):
                from ..expression.types import MySQLSetType
                values = re.findall(r"'([^']*)'", stripped)
                charset = None
                collation = None
                cs_match = re.search(r"CHARACTER\s+SET\s+(\w+)", upper)
                if cs_match:
                    charset = cs_match.group(1)
                col_match = re.search(r"COLLATE\s+(\w+)", upper)
                if col_match:
                    collation = col_match.group(1)
                return MySQLSetType(dialect=self, values=values, charset=charset, collation=collation)
            if upper.startswith("BINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MySQLBinaryType
                return MySQLBinaryType(dialect=self, length=length)
            if upper.startswith("VARBINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MySQLVarBinaryType
                return MySQLVarBinaryType(dialect=self, length=length)
            # CHAR / VARCHAR
            length_match = re.search(r"\((\d+)\)", stripped)
            length = int(length_match.group(1)) if length_match else None
            if upper.startswith("VARCHAR"):
                return VarCharType(dialect=self, length=length)
            return CharType(dialect=self, length=length)

        # BLOB family
        if self._MYSQL_BLOB_TYPES.match(upper):
            if upper.startswith("TINYBLOB"):
                from ..expression.types import MySQLTinyBlobType
                return MySQLTinyBlobType(dialect=self)
            if upper.startswith("MEDIUMBLOB"):
                from ..expression.types import MySQLMediumBlobType
                return MySQLMediumBlobType(dialect=self)
            if upper.startswith("LONGBLOB"):
                from ..expression.types import MySQLLongBlobType
                return MySQLLongBlobType(dialect=self)
            from ..expression.types import MySQLBlobType
            return MySQLBlobType(dialect=self)

        # Date/time family
        if self._MYSQL_DATE_TYPES.match(upper):
            if upper.startswith("YEAR"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MySQLYearType
                return MySQLYearType(dialect=self, display_width=display_width)
            if upper.startswith("DATE"):
                if upper.strip() == "DATE":
                    return DateType(dialect=self)
                return DateTimeType(dialect=self)
            if upper.startswith("DATETIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                return DateTimeType(dialect=self, precision=precision)
            if upper.startswith("TIMESTAMP"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(dialect=self, precision=precision)
                return TimestampType(dialect=self, precision=precision)
            if upper.startswith("TIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(dialect=self, precision=precision)
                return TimeType(dialect=self, precision=precision)

        # JSON
        if self._MYSQL_JSON_TYPES.match(upper):
            return JsonType(dialect=self)

        # Spatial
        if self._MYSQL_SPATIAL_TYPES.match(upper):
            srid = None
            srid_match = re.search(r"SRID\s+(\d+)", upper)
            if srid_match:
                srid = int(srid_match.group(1))
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
            for name, cls in spatial_map.items():
                if upper.startswith(name):
                    return cls(dialect=self, srid=srid)
            return MySQLGeometryType(dialect=self, srid=srid)

        # Vector (MySQL 9.0+)
        if self._MYSQL_VECTOR_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            dim = int(nums[0]) if nums else 0
            from ..expression.types import MySQLVectorType
            return MySQLVectorType(dialect=self, dim=dim)

        # Fallback
        from rhosocial.activerecord.backend.expression.types import CustomType
        return CustomType(dialect=self, raw=stripped)

class MySQLTypeSuggestionMixin(DDLTypeSuggestionMixin):
    """MySQL-native ``suggest_column_type()``.

    Provides MySQL-specific default ``DataType`` suggestions for DDL
    generation. Version-gated types follow the backend server version:

    - ``dict`` / ``list`` → ``JsonType`` on MySQL 5.7+; ``MySQLLongTextType``
      on older servers. When *version* is unknown, no guess is made and the
      caller falls back (per the ``ColumnTypeSuggestion`` contract).
    - ``uuid.UUID`` → ``MySQLBinaryType(16)`` (binary storage, matching the
      ``MySQLUUIDBinaryAdapter`` default value conversion).

    All other mappings mirror the backend-neutral defaults but select the
    MySQL-native ``DataType`` subclass where one exists.
    """

    def suggest_column_type(
        self, python_type: type, version: "Optional[Tuple[int, int, int]]" = None
    ) -> "Optional[DataType]":
        import datetime as _dt
        import decimal as _dec
        import enum as _enum
        import uuid as _uuid

        # When the caller does not supply a version, fall back to the dialect's
        # own configured server version (None if never introspected/adapted).
        if version is None:
            version = getattr(self, "_version", None)

        mapping = {
            str: MySQLTextType,
            int: MySQLIntType,
            bool: MySQLTinyIntType,
            float: DoubleType,
            bytes: MySQLBlobType,
            _dt.datetime: DateTimeType,
            _dt.date: DateType,
            _dt.time: TimeType,
            _dec.Decimal: DecimalType,
            _uuid.UUID: MySQLBinaryType,
            _enum.Enum: VarCharType,
        }
        factory = mapping.get(python_type)
        if factory is not None:
            if python_type is _uuid.UUID:
                return MySQLBinaryType(dialect=self, length=16)
            if python_type is _enum.Enum:
                return VarCharType(dialect=self, length=64)
            return factory(dialect=self)

        if python_type in (dict, list):
            if version is None:
                # Per the contract: do not silently guess the version.
                return None
            if version >= (5, 7, 0):
                return JsonType(dialect=self)
            return MySQLLongTextType(dialect=self)

        return super().suggest_column_type(python_type, version)
