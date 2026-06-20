# src/rhosocial/activerecord/backend/impl/mysql/mixins/types.py
"""MySQL DataType formatting and parsing mixin."""

from __future__ import annotations

import re

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import DDLTypeSupport
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    DoubleType,
    JsonBType,
    TimeTzType,
    TimestampTzType,
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

    # --- MySQL-specific type formatters (delegate to _default_sql) ---

    @DDLTypeMixin.handles(MySQLTinyIntType)
    def format_data_type_tiny_int(self, data_type: MySQLTinyIntType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLSmallIntType)
    def format_data_type_small_int(self, data_type: MySQLSmallIntType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLIntType)
    def format_data_type_int(self, data_type: MySQLIntType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLBigIntType)
    def format_data_type_big_int(self, data_type: MySQLBigIntType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLTinyBlobType)
    def format_data_type_tiny_blob(self, data_type: MySQLTinyBlobType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLBlobType)
    def format_data_type_blob(self, data_type: MySQLBlobType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLMediumBlobType)
    def format_data_type_medium_blob(self, data_type: MySQLMediumBlobType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLLongBlobType)
    def format_data_type_long_blob(self, data_type: MySQLLongBlobType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLTinyTextType)
    def format_data_type_tiny_text(self, data_type: MySQLTinyTextType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLTextType)
    def format_data_type_text(self, data_type: MySQLTextType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLMediumTextType)
    def format_data_type_medium_text(self, data_type: MySQLMediumTextType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLLongTextType)
    def format_data_type_long_text(self, data_type: MySQLLongTextType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLBitType)
    def format_data_type_bit(self, data_type: MySQLBitType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLYearType)
    def format_data_type_year(self, data_type: MySQLYearType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLBinaryType)
    def format_data_type_binary(self, data_type: MySQLBinaryType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLVarBinaryType)
    def format_data_type_var_binary(self, data_type: MySQLVarBinaryType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLEnumType)
    def format_data_type_enum(self, data_type: MySQLEnumType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLSetType)
    def format_data_type_set(self, data_type: MySQLSetType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLGeometryType)
    def format_data_type_geometry(self, data_type: MySQLGeometryType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLPointType)
    def format_data_type_point(self, data_type: MySQLPointType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLLineStringType)
    def format_data_type_line_string(self, data_type: MySQLLineStringType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLPolygonType)
    def format_data_type_polygon(self, data_type: MySQLPolygonType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLMultiPointType)
    def format_data_type_multi_point(self, data_type: MySQLMultiPointType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLMultiLineStringType)
    def format_data_type_multi_line_string(self, data_type: MySQLMultiLineStringType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLMultiPolygonType)
    def format_data_type_multi_polygon(self, data_type: MySQLMultiPolygonType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLGeometryCollectionType)
    def format_data_type_geometry_collection(self, data_type: MySQLGeometryCollectionType) -> str:
        return data_type._default_sql()

    @DDLTypeMixin.handles(MySQLVectorType)
    def format_data_type_vector(self, data_type: MySQLVectorType) -> str:
        return data_type._default_sql()

    # --- Core type overrides (MySQL-specific SQL) ---

    @DDLTypeMixin.handles(DoubleType)
    def format_data_type_double(self, data_type: DoubleType) -> str:
        return "DOUBLE"

    @DDLTypeMixin.handles(BooleanType)
    def format_data_type_boolean(self, data_type: BooleanType) -> str:
        return "TINYINT(1)"

    @DDLTypeMixin.handles(TimeTzType)
    def format_data_type_timetz(self, data_type: TimeTzType) -> str:
        return f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"

    @DDLTypeMixin.handles(TimestampTzType)
    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> str:
        return f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"

    @DDLTypeMixin.handles(JsonBType)
    def format_data_type_jsonb(self, data_type: JsonBType) -> str:
        return "JSON"

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
