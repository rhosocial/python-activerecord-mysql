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

from typing import List, Optional, Set

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

class MySQLIntType(IntegerType, backend="mysql"):
    """MySQL ``INTEGER`` / ``INT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType'}

    def _default_sql(self) -> str:
        sql = "INT"
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


class MySQLTinyIntType(TinyIntType, backend="mysql"):
    """MySQL ``TINYINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TinyIntType'}

    def _default_sql(self) -> str:
        sql = "TINYINT"
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


class MySQLSmallIntType(SmallIntType, backend="mysql"):
    """MySQL ``SMALLINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'SmallIntType'}

    def _default_sql(self) -> str:
        sql = "SMALLINT"
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


class MySQLBigIntType(BigIntType, backend="mysql"):
    """MySQL ``BIGINT`` with optional UNSIGNED / ZEROFILL."""

    unsigned: bool = False
    zerofill: bool = False

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.unsigned == other.unsigned and
                self.zerofill == other.zerofill)

    def __hash__(self) -> int:
        return hash((type(self), self.unsigned, self.zerofill))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BigIntType'}

    def _default_sql(self) -> str:
        sql = "BIGINT"
        if self.zerofill:
            return f"{sql} ZEROFILL"
        if self.unsigned:
            return f"{sql} UNSIGNED"
        return sql


# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MySQLTinyBlobType(BlobType, backend="mysql"):
    """MySQL ``TINYBLOB`` — maximum 255 bytes."""

    def _default_sql(self) -> str:
        return "TINYBLOB"


class MySQLBlobType(BlobType, backend="mysql"):
    """MySQL ``BLOB`` — maximum 65,535 bytes."""

    def _default_sql(self) -> str:
        return "BLOB"


class MySQLMediumBlobType(BlobType, backend="mysql"):
    """MySQL ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""

    def _default_sql(self) -> str:
        return "MEDIUMBLOB"


class MySQLLongBlobType(BlobType, backend="mysql"):
    """MySQL ``LONGBLOB`` — maximum 4,294,967,295 bytes."""

    def _default_sql(self) -> str:
        return "LONGBLOB"


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MySQLTinyTextType(TextType, backend="mysql"):
    """MySQL ``TINYTEXT`` — maximum 255 bytes."""

    def _default_sql(self) -> str:
        return "TINYTEXT"


class MySQLTextType(TextType, backend="mysql"):
    """MySQL ``TEXT`` — maximum 65,535 bytes."""

    def _default_sql(self) -> str:
        return "TEXT"


class MySQLMediumTextType(TextType, backend="mysql"):
    """MySQL ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""

    def _default_sql(self) -> str:
        return "MEDIUMTEXT"


class MySQLLongTextType(TextType, backend="mysql"):
    """MySQL ``LONGTEXT`` — maximum 4,294,967,295 bytes."""

    def _default_sql(self) -> str:
        return "LONGTEXT"


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MySQLBitType(DataType, backend="mysql"):
    """MySQL ``BIT[(n)]`` — bit-field type."""

    n: Optional[int] = None

    def __init__(self, n: Optional[int] = None):
        super().__init__()
        self.n = n

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.n == other.n

    def __hash__(self) -> int:
        return hash((type(self), self.n))

    def _default_sql(self) -> str:
        if self.n is not None:
            return f"BIT({self.n})"
        return "BIT"


# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MySQLYearType(DataType, backend="mysql"):
    """MySQL ``YEAR[(4)]`` — year type (``YEAR(4)`` is legacy)."""

    display_width: Optional[int] = None

    def __init__(self, display_width: Optional[int] = None):
        super().__init__()
        self.display_width = display_width

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.display_width == other.display_width

    def __hash__(self) -> int:
        return hash((type(self), self.display_width))

    def _default_sql(self) -> str:
        if self.display_width is not None:
            return f"YEAR({self.display_width})"
        return "YEAR"


# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MySQLBinaryType(DataType, backend="mysql"):
    """MySQL ``BINARY[(n)]`` — fixed-length binary."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None):
        super().__init__()
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"BINARY({self.length})"
        return "BINARY"


class MySQLVarBinaryType(DataType, backend="mysql"):
    """MySQL ``VARBINARY(n)`` — variable-length binary."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None):
        super().__init__()
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"VARBINARY({self.length})"
        return "VARBINARY"


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MySQLEnumType(DataType, backend="mysql"):
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

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.values == other.values and
                self.charset == other.charset and
                self.collation == other.collation)

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.values), self.charset, self.collation))

    def _default_sql(self) -> str:
        values_str = ",".join(f"'{v}'" for v in self.values)
        result = f"ENUM({values_str})"
        if self.charset:
            result += f" CHARACTER SET {self.charset}"
        if self.collation:
            result += f" COLLATE {self.collation}"
        return result

    def __str__(self) -> str:
        return self._default_sql()

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MySQLSetType(DataType, backend="mysql"):
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

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.values == other.values and
                self.charset == other.charset and
                self.collation == other.collation)

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.values), self.charset, self.collation))

    def _default_sql(self) -> str:
        values_str = ",".join(f"'{v}'" for v in self.values)
        result = f"SET({values_str})"
        if self.charset:
            result += f" CHARACTER SET {self.charset}"
        if self.collation:
            result += f" COLLATE {self.collation}"
        return result

    def __str__(self) -> str:
        return self._default_sql()

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MySQLGeometryType(DataType, backend="mysql"):
    """MySQL ``GEOMETRY`` with optional SRID."""

    srid: Optional[int] = None

    def __init__(self, srid: Optional[int] = None):
        super().__init__()
        self.srid = srid

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.srid == other.srid

    def __hash__(self) -> int:
        return hash((type(self), self.srid))

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"GEOMETRY SRID {self.srid}"
        return "GEOMETRY"


class MySQLPointType(MySQLGeometryType, backend="mysql"):
    """MySQL ``POINT`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"POINT SRID {self.srid}"
        return "POINT"


class MySQLLineStringType(MySQLGeometryType, backend="mysql"):
    """MySQL ``LINESTRING`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"LINESTRING SRID {self.srid}"
        return "LINESTRING"


class MySQLPolygonType(MySQLGeometryType, backend="mysql"):
    """MySQL ``POLYGON`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"POLYGON SRID {self.srid}"
        return "POLYGON"


class MySQLMultiPointType(MySQLGeometryType, backend="mysql"):
    """MySQL ``MULTIPOINT`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"MULTIPOINT SRID {self.srid}"
        return "MULTIPOINT"


class MySQLMultiLineStringType(MySQLGeometryType, backend="mysql"):
    """MySQL ``MULTILINESTRING`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"MULTILINESTRING SRID {self.srid}"
        return "MULTILINESTRING"


class MySQLMultiPolygonType(MySQLGeometryType, backend="mysql"):
    """MySQL ``MULTIPOLYGON`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"MULTIPOLYGON SRID {self.srid}"
        return "MULTIPOLYGON"


class MySQLGeometryCollectionType(MySQLGeometryType, backend="mysql"):
    """MySQL ``GEOMETRYCOLLECTION`` with optional SRID."""

    def _default_sql(self) -> str:
        if self.srid is not None:
            return f"GEOMETRYCOLLECTION SRID {self.srid}"
        return "GEOMETRYCOLLECTION"


# ---------------------------------------------------------------------------
# VECTOR type (MySQL 9.0+)
# ---------------------------------------------------------------------------

class MySQLVectorType(DataType, backend="mysql"):
    """MySQL ``VECTOR(n)`` — vector type (MySQL 9.0+)."""

    dim: int

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.dim == other.dim

    def __hash__(self) -> int:
        return hash((type(self), self.dim))

    def _default_sql(self) -> str:
        return f"VECTOR({self.dim})"



