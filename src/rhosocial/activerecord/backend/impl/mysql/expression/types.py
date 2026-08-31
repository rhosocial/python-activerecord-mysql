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

class MySQLIntType(IntegerType):
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


class MySQLTinyIntType(TinyIntType):
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


class MySQLSmallIntType(SmallIntType):
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


class MySQLBigIntType(BigIntType):
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


# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MySQLTinyBlobType(BlobType):
    """MySQL ``TINYBLOB`` — maximum 255 bytes."""


class MySQLBlobType(BlobType):
    """MySQL ``BLOB`` — maximum 65,535 bytes."""


class MySQLMediumBlobType(BlobType):
    """MySQL ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""


class MySQLLongBlobType(BlobType):
    """MySQL ``LONGBLOB`` — maximum 4,294,967,295 bytes."""


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MySQLTinyTextType(TextType):
    """MySQL ``TINYTEXT`` — maximum 255 bytes."""


class MySQLTextType(TextType):
    """MySQL ``TEXT`` — maximum 65,535 bytes."""


class MySQLMediumTextType(TextType):
    """MySQL ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""


class MySQLLongTextType(TextType):
    """MySQL ``LONGTEXT`` — maximum 4,294,967,295 bytes."""


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MySQLBitType(DataType):
    """MySQL ``BIT[(n)]`` — bit-field type."""

    n: Optional[int] = None

    def __init__(self, dialect=None, *, n: Optional[int] = None):
        super().__init__(dialect)
        self.n = n

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.n == other.n

    def __hash__(self) -> int:
        return hash((type(self), self.n))


# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MySQLYearType(DataType):
    """MySQL ``YEAR[(4)]`` — year type (``YEAR(4)`` is legacy)."""

    display_width: Optional[int] = None

    def __init__(self, dialect=None, *, display_width: Optional[int] = None):
        super().__init__(dialect)
        self.display_width = display_width

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.display_width == other.display_width

    def __hash__(self) -> int:
        return hash((type(self), self.display_width))


# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MySQLBinaryType(DataType):
    """MySQL ``BINARY[(n)]`` — fixed-length binary."""

    length: Optional[int] = None

    def __init__(self, dialect=None, *, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))


class MySQLVarBinaryType(DataType):
    """MySQL ``VARBINARY(n)`` — variable-length binary."""

    length: Optional[int] = None

    def __init__(self, dialect=None, *, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MySQLEnumType(DataType):
    """MySQL ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE."""

    values: List[str]
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, *, values: List[str],
                 charset: Optional[str] = None, collation: Optional[str] = None):
        super().__init__(dialect)
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

    def __init__(self, dialect=None, *, values: List[str],
                 charset: Optional[str] = None, collation: Optional[str] = None):
        super().__init__(dialect)
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

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MySQLGeometryType(DataType):
    """MySQL ``GEOMETRY`` with optional SRID."""

    srid: Optional[int] = None

    def __init__(self, dialect=None, *, srid: Optional[int] = None):
        super().__init__(dialect)
        self.srid = srid

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.srid == other.srid

    def __hash__(self) -> int:
        return hash((type(self), self.srid))


class MySQLPointType(MySQLGeometryType):
    """MySQL ``POINT`` with optional SRID."""


class MySQLLineStringType(MySQLGeometryType):
    """MySQL ``LINESTRING`` with optional SRID."""


class MySQLPolygonType(MySQLGeometryType):
    """MySQL ``POLYGON`` with optional SRID."""


class MySQLMultiPointType(MySQLGeometryType):
    """MySQL ``MULTIPOINT`` with optional SRID."""


class MySQLMultiLineStringType(MySQLGeometryType):
    """MySQL ``MULTILINESTRING`` with optional SRID."""


class MySQLMultiPolygonType(MySQLGeometryType):
    """MySQL ``MULTIPOLYGON`` with optional SRID."""


class MySQLGeometryCollectionType(MySQLGeometryType):
    """MySQL ``GEOMETRYCOLLECTION`` with optional SRID."""


# ---------------------------------------------------------------------------
# VECTOR type (MySQL 9.0+)
# ---------------------------------------------------------------------------

class MySQLVectorType(DataType):
    """MySQL ``VECTOR(n)`` — vector type (MySQL 9.0+)."""

    dim: int

    def __init__(self, dialect=None, *, dim: int):
        super().__init__(dialect)
        self.dim = dim

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.dim == other.dim

    def __hash__(self) -> int:
        return hash((type(self), self.dim))