# src/rhosocial/activerecord/backend/impl/mysql/expression/types.py
"""MySQL-specific DataType subclasses.

Naming convention
-----------------
MySQL-specific types use the ``MySQL`` prefix to distinguish them from
the core types (which have no prefix).  This avoids ambiguity when both
core and backend types are used together.

Usage scope
-----------
These types are used **only** for MySQL backend DDL column definitions,
introspection result parsing, and schema comparison.  They should **not**
be used by application code directly — always use the core types for
DDL definition expressions (``ColumnDefinition.data_type``).
"""

from __future__ import annotations

from typing import ClassVar, List, Optional, Set, Tuple

from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    DataType,
    IntegerType,
    SmallIntType,
    TextType,
    TinyIntType,
)


# ---------------------------------------------------------------------------
# Integer variants with UNSIGNED / ZEROFILL
# ---------------------------------------------------------------------------

class MySQLIntType(IntegerType):
    """MySQL ``INTEGER`` / ``INT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def _type_params(self) -> Tuple:
        return (self.unsigned, self.zerofill)

    def _default_sql(self) -> str:
        sql = "INT"
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


class MySQLTinyIntType(TinyIntType):
    """MySQL ``TINYINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def _type_params(self) -> Tuple:
        return (self.unsigned, self.zerofill)

    def _default_sql(self) -> str:
        sql = super()._default_sql()
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


class MySQLSmallIntType(SmallIntType):
    """MySQL ``SMALLINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def _type_params(self) -> Tuple:
        return (self.unsigned, self.zerofill)

    def _default_sql(self) -> str:
        sql = super()._default_sql()
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


class MySQLBigIntType(BigIntType):
    """MySQL ``BIGINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def _type_params(self) -> Tuple:
        return (self.unsigned, self.zerofill)

    def _default_sql(self) -> str:
        sql = super()._default_sql()
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MySQLTinyBlobType(BlobType):
    """MySQL ``TINYBLOB`` — maximum 255 bytes."""

    def _default_sql(self) -> str:
        return "TINYBLOB"


class MySQLBlobType(BlobType):
    """MySQL ``BLOB`` — maximum 65,535 bytes."""

    def _default_sql(self) -> str:
        return "BLOB"


class MySQLMediumBlobType(BlobType):
    """MySQL ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""

    def _default_sql(self) -> str:
        return "MEDIUMBLOB"


class MySQLLongBlobType(BlobType):
    """MySQL ``LONGBLOB`` — maximum 4,294,967,295 bytes."""

    def _default_sql(self) -> str:
        return "LONGBLOB"


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MySQLTinyTextType(TextType):
    """MySQL ``TINYTEXT`` — maximum 255 bytes."""

    def _default_sql(self) -> str:
        return "TINYTEXT"


class MySQLTextType(TextType):
    """MySQL ``TEXT`` — maximum 65,535 bytes."""

    def _default_sql(self) -> str:
        return "TEXT"


class MySQLMediumTextType(TextType):
    """MySQL ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""

    def _default_sql(self) -> str:
        return "MEDIUMTEXT"


class MySQLLongTextType(TextType):
    """MySQL ``LONGTEXT`` — maximum 4,294,967,295 bytes."""

    def _default_sql(self) -> str:
        return "LONGTEXT"


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MySQLBitType(DataType):
    """MySQL ``BIT[(n)]`` — bit-field type."""

    n: Optional[int] = None

    def __init__(self, n: Optional[int] = None):
        super().__init__()
        self.n = n

    def _type_params(self) -> Tuple:
        return (self.n,)

    def _default_sql(self) -> str:
        if self.n is not None:
            return f"BIT({self.n})"
        return "BIT"


# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MySQLYearType(DataType):
    """MySQL ``YEAR[(4)]`` — year type (``YEAR(4)`` is legacy)."""

    display_width: Optional[int] = None

    def __init__(self, display_width: Optional[int] = None):
        super().__init__()
        self.display_width = display_width

    def _type_params(self) -> Tuple:
        return (self.display_width,)

    def _default_sql(self) -> str:
        if self.display_width is not None:
            return f"YEAR({self.display_width})"
        return "YEAR"


# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MySQLBinaryType(DataType):
    """MySQL ``BINARY[(n)]`` — fixed-length binary."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None):
        super().__init__()
        self.length = length

    def _type_params(self) -> Tuple:
        return (self.length,)

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"BINARY({self.length})"
        return "BINARY"


class MySQLVarBinaryType(DataType):
    """MySQL ``VARBINARY(n)`` — variable-length binary."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None):
        super().__init__()
        self.length = length

    def _type_params(self) -> Tuple:
        return (self.length,)

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"VARBINARY({self.length})"
        return "VARBINARY"


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MySQLEnumType(DataType):
    """MySQL ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE."""

    values: List[str]
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, values: List[str], charset: Optional[str] = None,
                 collation: Optional[str] = None):
        super().__init__()
        if not values:
            raise ValueError("ENUM must have at least one value")
        self.values = list(values)
        self.charset = charset
        self.collation = collation

    def _type_params(self) -> Tuple:
        return (tuple(self.values), self.charset, self.collation)

    def _default_sql(self) -> str:
        values_str = ",".join(f"'{v}'" for v in self.values)
        result = f"ENUM({values_str})"
        if self.charset:
            result += f" CHARACTER SET {self.charset}"
        if self.collation:
            result += f" COLLATE {self.collation}"
        return result

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MySQLSetType(DataType):
    """MySQL ``SET('val', ...)`` with optional CHARACTER SET / COLLATE."""

    values: List[str]
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, values: List[str], charset: Optional[str] = None,
                 collation: Optional[str] = None):
        super().__init__()
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = list(values)
        self.charset = charset
        self.collation = collation

    def _type_params(self) -> Tuple:
        return (tuple(self.values), self.charset, self.collation)

    def _default_sql(self) -> str:
        values_str = ",".join(f"'{v}'" for v in self.values)
        result = f"SET({values_str})"
        if self.charset:
            result += f" CHARACTER SET {self.charset}"
        if self.collation:
            result += f" COLLATE {self.collation}"
        return result

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MySQLGeometryType(DataType):
    """MySQL ``GEOMETRY`` with optional SRID."""

    srid: Optional[int] = None

    def __init__(self, srid: Optional[int] = None):
        super().__init__()
        self.srid = srid

    def _type_params(self) -> Tuple:
        return (self.srid,)

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"GEOMETRY SRID {self.srid}"
        return "GEOMETRY"


class MySQLPointType(MySQLGeometryType):
    """MySQL ``POINT`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"POINT SRID {self.srid}"
        return "POINT"


class MySQLLineStringType(MySQLGeometryType):
    """MySQL ``LINESTRING`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"LINESTRING SRID {self.srid}"
        return "LINESTRING"


class MySQLPolygonType(MySQLGeometryType):
    """MySQL ``POLYGON`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"POLYGON SRID {self.srid}"
        return "POLYGON"


class MySQLMultiPointType(MySQLGeometryType):
    """MySQL ``MULTIPOINT`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"MULTIPOINT SRID {self.srid}"
        return "MULTIPOINT"


class MySQLMultiLineStringType(MySQLGeometryType):
    """MySQL ``MULTILINESTRING`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"MULTILINESTRING SRID {self.srid}"
        return "MULTILINESTRING"


class MySQLMultiPolygonType(MySQLGeometryType):
    """MySQL ``MULTIPOLYGON`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"MULTIPOLYGON SRID {self.srid}"
        return "MULTIPOLYGON"


class MySQLGeometryCollectionType(MySQLGeometryType):
    """MySQL ``GEOMETRYCOLLECTION`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"GEOMETRYCOLLECTION SRID {self.srid}"
        return "GEOMETRYCOLLECTION"


# ---------------------------------------------------------------------------
# VECTOR type (MySQL 9.0+)
# ---------------------------------------------------------------------------

class MySQLVectorType(DataType):
    """MySQL ``VECTOR(n)`` — vector type (MySQL 9.0+)."""

    dim: int

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def _type_params(self) -> Tuple:
        return (self.dim,)

    def _default_sql(self) -> str:
        return f"VECTOR({self.dim})"


# ---------------------------------------------------------------------------
# Synonyms for registry
# ---------------------------------------------------------------------------

builtin_synonym_map: ClassVar[dict] = {}
