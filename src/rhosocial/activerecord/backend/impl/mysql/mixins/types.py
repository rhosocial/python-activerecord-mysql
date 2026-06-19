# src/rhosocial/activerecord/backend/impl/mysql/mixins/types.py
"""MySQL DataType formatting and parsing mixin."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Tuple, Type

from rhosocial.activerecord.backend.dialect.protocols import (
    TypeFormattingSupport,
    TypeParsingSupport,
)
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
    IntType,
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

if TYPE_CHECKING:
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


class MySQLTypeSupportMixin(TypeFormattingSupport, TypeParsingSupport):
    """MySQL DataType formatting and parsing.

    Implements both ``TypeFormattingSupport`` and ``TypeParsingSupport`` so
    the dialect can render ``DataType`` expressions to SQL strings and parse
    raw SQL type strings back into ``DataType`` instances.
    """

    # ------------------------------------------------------------------
    # TypeFormattingSupport
    # ------------------------------------------------------------------

    def render_type(self, data_type: DataType) -> str:
        for type_class, suffix in self.supports_data_types():
            if isinstance(data_type, type_class):
                formatter = getattr(self, f"format_data_type_{suffix}", None)
                if formatter is not None:
                    return formatter(data_type)
        return data_type._default_sql()

    def supports_data_types(self) -> List[Tuple[Type[DataType], str]]:
        return [
            # MySQL-specific types
            # (MySQLTinyBlobType, "tiny_blob"),
            # Integer family — MySQL overrides
            (MySQLTinyIntType, "tiny_int"),
            (MySQLSmallIntType, "small_int"),
            (MySQLIntType, "int"),
            (MySQLBigIntType, "big_int"),
            # BLOB variants
            (MySQLTinyBlobType, "tiny_blob"),
            (MySQLBlobType, "blob"),
            (MySQLMediumBlobType, "medium_blob"),
            (MySQLLongBlobType, "long_blob"),
            # TEXT variants
            (MySQLTinyTextType, "tiny_text"),
            (MySQLTextType, "text"),
            (MySQLMediumTextType, "medium_text"),
            (MySQLLongTextType, "long_text"),
            # Bit and binary
            (MySQLBitType, "bit"),
            (MySQLYearType, "year"),
            (MySQLBinaryType, "binary"),
            (MySQLVarBinaryType, "var_binary"),
            # ENUM / SET
            (MySQLEnumType, "enum"),
            (MySQLSetType, "set"),
            # Spatial
            (MySQLGeometryType, "geometry"),
            (MySQLPointType, "point"),
            (MySQLLineStringType, "line_string"),
            (MySQLPolygonType, "polygon"),
            (MySQLMultiPointType, "multi_point"),
            (MySQLMultiLineStringType, "multi_line_string"),
            (MySQLMultiPolygonType, "multi_polygon"),
            (MySQLGeometryCollectionType, "geometry_collection"),
            # Vector
            (MySQLVectorType, "vector"),
            # Core Integer family
            (TinyIntType, "tiny_int"),
            (SmallIntType, "small_int"),
            (IntType, "int"),
            (IntegerType, "integer"),
            (BigIntType, "big_int"),
            # Core Numeric family
            (FloatType, "float"),
            (RealType, "real"),
            (DoubleType, "double"),
            (DecimalType, "decimal"),
            # Core String family
            (CharType, "char"),
            (VarCharType, "var_char"),
            (TextType, "text"),
            # Boolean
            (BooleanType, "boolean"),
            # Binary
            (BlobType, "blob"),
            # Date/time
            (DateType, "date"),
            (TimeType, "time"),
            (TimeTzType, "time_tz"),
            (DateTimeType, "date_time"),
            (TimestampType, "timestamp"),
            (TimestampTzType, "timestamp_tz"),
            # JSON
            (JsonType, "json"),
            (JsonBType, "json_b"),
        ]

    # --- Integer formatters (MySQL with unsigned/zerofill) ---

    def format_data_type_tiny_int(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_small_int(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_int(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_big_int(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- BLOB variant formatters ---

    def format_data_type_tiny_blob(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_blob(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_medium_blob(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_long_blob(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- TEXT variant formatters ---

    def format_data_type_tiny_text(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_text(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_medium_text(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_long_text(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- Bit / Year / Binary formatters ---

    def format_data_type_bit(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_year(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_binary(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_var_binary(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- ENUM / SET formatters ---

    def format_data_type_enum(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_set(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- Spatial formatters ---

    def format_data_type_geometry(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_point(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_line_string(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_polygon(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_multi_point(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_multi_line_string(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_multi_polygon(self, data_type: DataType) -> str:
        return data_type._default_sql()

    def format_data_type_geometry_collection(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- Vector formatter ---

    def format_data_type_vector(self, data_type: DataType) -> str:
        return data_type._default_sql()

    # --- Core type formatters (MySQL specialized) ---

    def format_data_type_tiny_int(self, data_type: TinyIntType) -> str:
        return data_type._default_sql()

    def format_data_type_small_int(self, data_type: SmallIntType) -> str:
        return data_type._default_sql()

    def format_data_type_int(self, data_type: IntType) -> str:
        return data_type._default_sql()

    def format_data_type_integer(self, data_type: IntegerType) -> str:
        return data_type._default_sql()

    def format_data_type_big_int(self, data_type: BigIntType) -> str:
        return data_type._default_sql()

    def format_data_type_float(self, data_type: FloatType) -> str:
        return data_type._default_sql()

    def format_data_type_real(self, data_type: RealType) -> str:
        return "REAL"

    def format_data_type_double(self, data_type: DoubleType) -> str:
        return "DOUBLE"

    def format_data_type_decimal(self, data_type: DecimalType) -> str:
        return data_type._default_sql()

    def format_data_type_char(self, data_type: CharType) -> str:
        return data_type._default_sql()

    def format_data_type_var_char(self, data_type: VarCharType) -> str:
        return data_type._default_sql()

    def format_data_type_text(self, data_type: TextType) -> str:
        return data_type._default_sql()

    def format_data_type_boolean(self, data_type: BooleanType) -> str:
        return "TINYINT(1)"

    def format_data_type_blob(self, data_type: BlobType) -> str:
        return "BLOB"

    def format_data_type_date(self, data_type: DateType) -> str:
        return data_type._default_sql()

    def format_data_type_time(self, data_type: TimeType) -> str:
        return data_type._default_sql()

    def format_data_type_time_tz(self, data_type: TimeTzType) -> str:
        if data_type.precision is not None:
            return f"TIME({data_type.precision})"
        return "TIME"

    def format_data_type_date_time(self, data_type: DateTimeType) -> str:
        return data_type._default_sql()

    def format_data_type_timestamp(self, data_type: TimestampType) -> str:
        return data_type._default_sql()

    def format_data_type_timestamp_tz(self, data_type: TimestampTzType) -> str:
        if data_type.precision is not None:
            return f"TIMESTAMP({data_type.precision})"
        return "TIMESTAMP"

    def format_data_type_json(self, data_type: JsonType) -> str:
        return "JSON"

    def format_data_type_json_b(self, data_type: JsonBType) -> str:
        return "JSON"

    # ------------------------------------------------------------------
    # TypeParsingSupport
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
            return MySQLBitType(n)

        # Integer family
        if self._MYSQL_INTEGER_TYPES.match(upper):
            unsigned = "UNSIGNED" in upper
            zerofill = "ZEROFILL" in upper
            if upper.startswith("TINYINT"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MySQLTinyIntType
                t = MySQLTinyIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                # TINYINT(1) is commonly used as BOOLEAN
                if display_width == 1 and not unsigned and not zerofill:
                    return BooleanType()
                return t
            if upper.startswith("SMALLINT"):
                from ..expression.types import MySQLSmallIntType
                t = MySQLSmallIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            if upper.startswith("MEDIUMINT"):
                from ..expression.types import MySQLIntType
                t = MySQLIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            if upper.startswith("BIGINT"):
                from ..expression.types import MySQLBigIntType
                t = MySQLBigIntType()
                t.unsigned = unsigned
                t.zerofill = zerofill
                return t
            # INT / INTEGER
            from ..expression.types import MySQLIntType
            t = MySQLIntType()
            t.unsigned = unsigned
            t.zerofill = zerofill
            return t

        # Float family
        if self._MYSQL_FLOAT_TYPES.match(upper):
            if upper.startswith("DOUBLE"):
                return DoubleType()
            if upper.startswith("REAL"):
                return RealType()
            # FLOAT
            nums = re.findall(r"\d+", stripped)
            precision = int(nums[0]) if nums else None
            return FloatType(precision)

        # Decimal family
        if self._MYSQL_DECIMAL_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return DecimalType(int(nums[0]), int(nums[1]))
            if len(nums) == 1:
                return DecimalType(int(nums[0]))
            return DecimalType()

        # String family
        if self._MYSQL_STRING_TYPES.match(upper):
            if upper.startswith("TINYTEXT"):
                from ..expression.types import MySQLTinyTextType
                return MySQLTinyTextType()
            if upper.startswith("MEDIUMTEXT"):
                from ..expression.types import MySQLMediumTextType
                return MySQLMediumTextType()
            if upper.startswith("LONGTEXT"):
                from ..expression.types import MySQLLongTextType
                return MySQLLongTextType()
            if upper.startswith("TEXT"):
                from ..expression.types import MySQLTextType
                return MySQLTextType()
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
                return MySQLEnumType(values, charset=charset, collation=collation)
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
                return MySQLSetType(values, charset=charset, collation=collation)
            if upper.startswith("BINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MySQLBinaryType
                return MySQLBinaryType(length)
            if upper.startswith("VARBINARY"):
                nums = re.findall(r"\d+", stripped)
                length = int(nums[0]) if nums else None
                from ..expression.types import MySQLVarBinaryType
                return MySQLVarBinaryType(length)
            # CHAR / VARCHAR
            length_match = re.search(r"\((\d+)\)", stripped)
            length = int(length_match.group(1)) if length_match else None
            if upper.startswith("VARCHAR"):
                return VarCharType(length)
            return CharType(length)

        # BLOB family
        if self._MYSQL_BLOB_TYPES.match(upper):
            if upper.startswith("TINYBLOB"):
                from ..expression.types import MySQLTinyBlobType
                return MySQLTinyBlobType()
            if upper.startswith("MEDIUMBLOB"):
                from ..expression.types import MySQLMediumBlobType
                return MySQLMediumBlobType()
            if upper.startswith("LONGBLOB"):
                from ..expression.types import MySQLLongBlobType
                return MySQLLongBlobType()
            from ..expression.types import MySQLBlobType
            return MySQLBlobType()

        # Date/time family
        if self._MYSQL_DATE_TYPES.match(upper):
            if upper.startswith("YEAR"):
                nums = re.findall(r"\d+", stripped)
                display_width = int(nums[0]) if nums else None
                from ..expression.types import MySQLYearType
                return MySQLYearType(display_width)
            if upper.startswith("DATE"):
                if upper.strip() == "DATE":
                    return DateType()
                return DateTimeType()
            if upper.startswith("DATETIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                return DateTimeType(precision)
            if upper.startswith("TIMESTAMP"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(precision)
                return TimestampType(precision)
            if upper.startswith("TIME"):
                nums = re.findall(r"\d+", stripped)
                precision = int(nums[0]) if nums else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(precision)
                return TimeType(precision)

        # JSON
        if self._MYSQL_JSON_TYPES.match(upper):
            return JsonType()

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
                    return cls(srid)
            return MySQLGeometryType(srid)

        # Vector (MySQL 9.0+)
        if self._MYSQL_VECTOR_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            dim = int(nums[0]) if nums else 0
            from ..expression.types import MySQLVectorType
            return MySQLVectorType(dim)

        # Fallback
        from rhosocial.activerecord.backend.expression.types import CustomType
        return CustomType(stripped)
