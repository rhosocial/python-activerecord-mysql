# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/native_models.py
"""Models for the MySQL native-type tests.

One model per native family table; each field's Python type is the adapter's
neutral type where one exists, so the backend's suggestion table selects the
adapter.  The tables themselves are declared by the definition classes at the
end of this module, built from MySQL's own type classes.

Where the default suggestion is not the right *driver* target for a native
column, the field declares it with ``UseAdapter``:

* ``BIT(n)`` is a bit string, and the adapter's default target (``str``) is for
  text carriers.  A native ``BIT`` column takes ``int`` or ``bytes``; the width
  must be declared because a ``BIT`` value carries no length metadata.
* ``BINARY(16)`` holds the raw 16 bytes, so the UUID field binds ``bytes`` while
  the ``CHAR(36)`` field keeps the default canonical text.
"""

from enum import Enum
from typing import Optional, Set
from uuid import UUID

import sys

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from pydantic import ConfigDict

from rhosocial.activerecord.backend.adapters.bitstring import BitString
from rhosocial.activerecord.backend.adapters.geometry import Geometry, Point
from rhosocial.activerecord.backend.adapters.vector import Vector
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint as Constraint,
    ColumnDefinition as Column,
    CreateTableStatement as CreateTable,
    DropTableStatement as DropTable,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint as PrimaryKey,
)
from rhosocial.activerecord.backend.expression.types import (
    CharType as Char,
    IntegerType as Int,
    JsonType as Json,
)
from rhosocial.activerecord.backend.impl.mysql.adapters import (
    MySQLBitStringAdapter,
    MySQLUUIDAdapter,
)
from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLBinaryType,
    MySQLBitType,
    MySQLEnumType,
    MySQLGeometryType,
    MySQLPointType,
    MySQLSetType,
    MySQLVectorType,
    MySQLYearType,
)
from rhosocial.activerecord.base import UseAdapter
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.testsuite.feature.query.fixtures.definitions import supports_drop_if_exists


class Shade(str, Enum):
    """The ENUM labels of ``native_set_enum.label``."""

    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class NativeBit(ActiveRecord):
    """``BIT(8)``, ``BIT(13)`` and a 13-bit column bound as raw bytes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_bit"

    id: Optional[int] = None
    bits8: Annotated[
        Optional[BitString], UseAdapter(MySQLBitStringAdapter(bit_length=8), int)
    ] = None
    bits13: Annotated[
        Optional[BitString], UseAdapter(MySQLBitStringAdapter(bit_length=13), int)
    ] = None
    bits_bytes: Annotated[
        Optional[BitString], UseAdapter(MySQLBitStringAdapter(bit_length=13), bytes)
    ] = None


class NativeSetEnum(ActiveRecord):
    """``SET``, ``ENUM`` and ``YEAR`` columns."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_set_enum"

    id: Optional[int] = None
    flags: Optional[Set[str]] = None
    label: Optional[Shade] = None
    year: Optional[int] = None


class NativeJSON(ActiveRecord):
    """A native ``JSON`` column (the driver hands back text)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_json"

    id: Optional[int] = None
    payload: Optional[dict] = None


class NativeUUID(ActiveRecord):
    """The two UUID carriers side by side: ``CHAR(36)`` and ``BINARY(16)``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_uuid"

    id: Optional[int] = None
    u_char: Optional[UUID] = None
    u_bin: Annotated[Optional[UUID], UseAdapter(MySQLUUIDAdapter(), bytes)] = None


class NativeGeometry(ActiveRecord):
    """A generic ``GEOMETRY`` column and a ``POINT`` column."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_geometry"

    id: Optional[int] = None
    shape: Optional[Geometry] = None
    spot: Optional[Point] = None


class NativeVector(ActiveRecord):
    """A ``VECTOR(3)`` column (MySQL 9.0+)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_vector"

    id: Optional[int] = None
    embedding: Optional[Vector] = None


# --- L1 fixture definitions ---------------------------------------------------
# A definition class receives only a ``dialect``: it holds the DDL its table
# needs and knows nothing about backends, databases, or execution.  Which
# statements run, and when, is decided by the L2 fixtures in the directory.
#
# MySQL's native families (``SET``/``ENUM``/``YEAR``, a real ``JSON`` document,
# ``BIT`` bit strings, ``GEOMETRY``, and optionally ``VECTOR``) each have their
# own type class in ``rhosocial.activerecord.backend.impl.mysql.expression``,
# so the tables are built from those classes rather than from raw SQL.


class Definition:
    """Base class for this directory's table definitions."""

    model = None
    table_name = ""

    def __init__(self, dialect):
        self.dialect = dialect
        self.name = type(self).table_name
        self.create_table = CreateTable(
            self.dialect,
            table=Table(self.dialect, self.name),
            columns=self.columns(),
        )
        self.drop_table = DropTable(
            self.dialect,
            table=Table(self.dialect, self.name),
            if_exists=supports_drop_if_exists(self.dialect),
        )

    def columns(self):
        raise NotImplementedError

    def column(self, name, sql_type, constraints=None):
        return Column(self.dialect, name, sql_type, constraints=constraints or [])

    def auto_pk(self, name="id"):
        return self.column(
            name,
            Int(self.dialect),
            [
                Constraint(
                    self.dialect,
                    branch=PrimaryKey(self.dialect, is_auto_increment=True),
                )
            ],
        )


class NativeBitDefinition(Definition):
    """``BIT(8)``, ``BIT(13)`` and a 13-bit column bound as raw bytes."""

    model = NativeBit
    table_name = "native_bit"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("bits8", MySQLBitType(self.dialect, 8)),
            self.column("bits13", MySQLBitType(self.dialect, 13)),
            self.column("bits_bytes", MySQLBitType(self.dialect, 13)),
        ]


class NativeSetEnumDefinition(Definition):
    """``SET``, ``ENUM`` and ``YEAR`` columns."""

    model = NativeSetEnum
    table_name = "native_set_enum"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("flags", MySQLSetType(self.dialect, ["a", "b", "c"])),
            self.column("label", MySQLEnumType(self.dialect, ["red", "green", "blue"])),
            self.column("year", MySQLYearType(self.dialect)),
        ]


class NativeJsonDefinition(Definition):
    """A native ``JSON`` column (the driver hands back text)."""

    model = NativeJSON
    table_name = "native_json"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("payload", Json(self.dialect)),
        ]


class NativeUuidDefinition(Definition):
    """The two UUID carriers side by side: ``CHAR(36)`` and ``BINARY(16)``."""

    model = NativeUUID
    table_name = "native_uuid"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("u_char", Char(self.dialect, 36)),
            self.column("u_bin", MySQLBinaryType(self.dialect, 16)),
        ]


class NativeGeometryDefinition(Definition):
    """A generic ``GEOMETRY`` column and a ``POINT`` column."""

    model = NativeGeometry
    table_name = "native_geometry"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("shape", MySQLGeometryType(self.dialect)),
            self.column("spot", MySQLPointType(self.dialect)),
        ]


class NativeVectorDefinition(Definition):
    """A ``VECTOR(3)`` column (MySQL 9.0+)."""

    model = NativeVector
    table_name = "native_vector"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("embedding", MySQLVectorType(self.dialect, 3)),
        ]
