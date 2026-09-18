# src/rhosocial/activerecord/backend/impl/mysql/expression/types.py
"""MySQL-specific DataType subclasses.

Naming convention
-----------------
MySQL-specific types use the ``MySQL`` class-name prefix and a
``mysql_``-prefixed generic type ``name`` (the protocol dispatch key) to
distinguish them from the core types (which own pure names such as
``integer`` or ``varchar``).  This keeps the
``format_data_type_<name>`` dispatch families of core and backend
isolated and avoids ambiguity when both type families are used together.

Usage scope
-----------
These types are used **only** for MySQL backend DDL column definitions,
introspection result parsing, and schema comparison.  They should **not**
be used by application code directly — always use the core types for
DDL definition expressions (``ColumnDefinition.data_type``).

Value-object semantics
----------------------
Equality/hash live on the core ``DataType`` base (via ``_type_params``);
subclasses only declare their semantic parameters through
``_type_params()`` and must **not** hand-write ``__eq__``/``__hash__``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BinaryType,
    BlobType,
    DataType,
    EnumType,
    IntegerType,
    SmallIntType,
    TextType,
    TinyIntType,
    VarBinaryType,
)


# ---------------------------------------------------------------------------
# Integer variants with UNSIGNED / ZEROFILL
# ---------------------------------------------------------------------------

class MySQLIntType(IntegerType):
    """MySQL ``INTEGER`` / ``INT`` with optional UNSIGNED / ZEROFILL."""

    name = "mysql_int"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType'}


class MySQLTinyIntType(TinyIntType):
    """MySQL ``TINYINT`` with optional UNSIGNED / ZEROFILL."""

    name = "mysql_tinyint"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TinyIntType'}


class MySQLSmallIntType(SmallIntType):
    """MySQL ``SMALLINT`` with optional UNSIGNED / ZEROFILL."""

    name = "mysql_smallint"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'SmallIntType'}


class MySQLBigIntType(BigIntType):
    """MySQL ``BIGINT`` with optional UNSIGNED / ZEROFILL."""

    name = "mysql_bigint"

    unsigned: bool = False
    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.unsigned = unsigned
        self.zerofill = zerofill

    def _type_params(self) -> tuple:
        return (self.unsigned, self.zerofill)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BigIntType'}


# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MySQLTinyBlobType(BlobType):
    """MySQL ``TINYBLOB`` — maximum 255 bytes."""

    name = "mysql_tinyblob"


class MySQLBlobType(BlobType):
    """MySQL ``BLOB`` — maximum 65,535 bytes."""

    name = "mysql_blob"


class MySQLMediumBlobType(BlobType):
    """MySQL ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""

    name = "mysql_mediumblob"


class MySQLLongBlobType(BlobType):
    """MySQL ``LONGBLOB`` — maximum 4,294,967,295 bytes."""

    name = "mysql_longblob"


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MySQLTinyTextType(TextType):
    """MySQL ``TINYTEXT`` — maximum 255 bytes."""

    name = "mysql_tinytext"


class MySQLTextType(TextType):
    """MySQL ``TEXT`` — maximum 65,535 bytes."""

    name = "mysql_text"


class MySQLMediumTextType(TextType):
    """MySQL ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""

    name = "mysql_mediumtext"


class MySQLLongTextType(TextType):
    """MySQL ``LONGTEXT`` — maximum 4,294,967,295 bytes."""

    name = "mysql_longtext"


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MySQLBitType(DataType):
    """MySQL ``BIT[(n)]`` — bit-field type."""

    name = "mysql_bit"

    n: Optional[int] = None

    def __init__(self, dialect=None, n: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.n = n

    def _type_params(self) -> tuple:
        return (self.n,)


# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MySQLYearType(DataType):
    """MySQL ``YEAR[(4)]`` — year type (``YEAR(4)`` is legacy)."""

    name = "mysql_year"

    display_width: Optional[int] = None

    def __init__(self, dialect=None, display_width: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.display_width = display_width

    def _type_params(self) -> tuple:
        return (self.display_width,)


# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MySQLBinaryType(BinaryType):
    """MySQL ``BINARY[(n)]`` — fixed-length binary."""

    name = "mysql_binary"

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length


class MySQLVarBinaryType(VarBinaryType):
    """MySQL ``VARBINARY(n)`` — variable-length binary."""

    name = "mysql_varbinary"

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MySQLEnumType(EnumType):
    """MySQL ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE.

    Inherits the core ``EnumType`` (values validation and value-object
    semantics); the MySQL rendering (including charset/collation
    extensions) lives in the dialect's ``format_data_type_mysql_enum``.
    """

    name = "mysql_enum"

    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        if values is None:
            raise ValueError("MySQLEnumType requires values")
        if not values:
            raise ValueError("ENUM must have at least one value")
        super().__init__(dialect, values=values, dialect_options=dialect_options)
        self.charset = charset
        self.collation = collation

    def _type_params(self) -> tuple:
        return (self.values, self.charset, self.collation)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MySQLSetType(DataType):
    """MySQL ``SET('val', ...)`` with optional CHARACTER SET / COLLATE.

    Deliberately **not** an ``EnumType`` subclass: SET renders as
    ``SET(...)``, not ``ENUM(...)``, and accepts multi-value membership —
    a different generic type with its own ``mysql_set`` dispatch key.
    """

    name = "mysql_set"

    values: Tuple[str, ...] = ()
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        if values is None:
            raise ValueError("MySQLSetType requires values")
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = tuple(values)
        self.charset = charset
        self.collation = collation

    def _type_params(self) -> tuple:
        return (self.values, self.charset, self.collation)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MySQLGeometryType(DataType):
    """MySQL ``GEOMETRY`` with optional SRID."""

    name = "mysql_geometry"

    srid: Optional[int] = None

    def __init__(self, dialect=None, srid: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.srid = srid

    def _type_params(self) -> tuple:
        return (self.srid,)


class MySQLPointType(MySQLGeometryType):
    """MySQL ``POINT`` with optional SRID."""

    name = "mysql_point"


class MySQLLineStringType(MySQLGeometryType):
    """MySQL ``LINESTRING`` with optional SRID."""

    name = "mysql_linestring"


class MySQLPolygonType(MySQLGeometryType):
    """MySQL ``POLYGON`` with optional SRID."""

    name = "mysql_polygon"


class MySQLMultiPointType(MySQLGeometryType):
    """MySQL ``MULTIPOINT`` with optional SRID."""

    name = "mysql_multipoint"


class MySQLMultiLineStringType(MySQLGeometryType):
    """MySQL ``MULTILINESTRING`` with optional SRID."""

    name = "mysql_multilinestring"


class MySQLMultiPolygonType(MySQLGeometryType):
    """MySQL ``MULTIPOLYGON`` with optional SRID."""

    name = "mysql_multipolygon"


class MySQLGeometryCollectionType(MySQLGeometryType):
    """MySQL ``GEOMETRYCOLLECTION`` with optional SRID."""

    name = "mysql_geometrycollection"


# ---------------------------------------------------------------------------
# VECTOR type (MySQL 9.0+)
# ---------------------------------------------------------------------------

class MySQLVectorType(DataType):
    """MySQL ``VECTOR(n)`` — vector type (MySQL 9.0+)."""

    name = "mysql_vector"

    dim: Optional[int] = None

    def __init__(self, dialect=None, dim: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        if dim is None:
            raise ValueError("MySQLVectorType requires dim")
        self.dim = dim

    def _type_params(self) -> tuple:
        return (self.dim,)
