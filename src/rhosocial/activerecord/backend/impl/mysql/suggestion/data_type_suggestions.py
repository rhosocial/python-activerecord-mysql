# src/rhosocial/activerecord/backend/impl/mysql/suggestion/data_type_suggestions.py
"""MySQL's **suggested data types**: what a bare field is declared as here.

The DDL half of the type answer; :mod:`.column_type` is the operation half.

Shapes this server forces:

* **a document's natural home is ``JSON``**, and the four sequence entries
  share it: MySQL has no array type, and its ``JSON`` column already holds an
  array, so ``list``/``tuple``/``set``/``frozenset`` all spend the same word.
* **a UUID is 16 raw bytes.** MySQL has no ``UUID`` type, so ``BINARY(16)``
  is the storage the backend's own adapter writes; a text form would waste
  four times the width and lose the fixed-length guarantee.
* **a bit string is text here.** The adapter writes the value as its digits
  (or bytes), so ``TEXT`` is the carrier a bare ``BitString`` round-trips
  through; ``BIT(n)`` would need a width the annotation does not carry.
* **a vector is text here.** MySQL 9's ``VECTOR`` needs a dimension, and the
  adapter's text form (``[1.0,2.0]``) round-trips through a text column.

The three parameter-carrying families (``Vector``, ``Range``, ``Multirange``)
therefore name text carriers, and a field that wants the server's native type
declares it with ``UseSqlType``. No key answers ``None``: a suggestion is what
a bare field gets, and taking the table away from the caller is not an answer.

Each call returns a fresh dict whose values are this module's read-only
templates; the derivation binds a dialect on a copy of the single entry it uses.
"""

from __future__ import annotations

from rhosocial.activerecord.backend.suggestion.definitions import (
    DataTypeSuggestion,
    ExtraDataTypeSuggestion,
)

import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional

from rhosocial.activerecord.backend.adapters import (
    AwareDatetime,
    BitString,
    Geometry,
    IPAddress,
    MacAddress,
    Multirange,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    JsonType,
    TextType,
    TimestampType,
    TimestampTzType,
    TimeType,
    VarCharType,
)

from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLBlobType,
    MySQLGeometryType,
    MySQLIntType,
    MySQLTextType,
    MySQLUUIDType,
)

#: MySQL's suggested declaration per framework-modelled Python type.
MYSQL_DATA_TYPE_SUGGESTIONS: Dict[Any, Optional[Any]] = {
    bool: BooleanType(),
    int: MySQLIntType(),
    float: DoubleType(),
    decimal.Decimal: DecimalType(),
    str: MySQLTextType(),
    bytes: MySQLBlobType(),
    bytearray: MySQLBlobType(),
    datetime.date: DateType(),
    datetime.time: TimeType(),
    # An instant: TIMESTAMP(p) is MySQL's tz-capable declaration, and a
    # precision of 3 (milliseconds) is the framework's timestamp default.
    AwareDatetime: TimestampTzType(precision=3),
    datetime.datetime: TimestampType(precision=3),
    # MySQL has no interval type; the value's text form is the carrier.
    datetime.timedelta: TextType(),
    uuid.UUID: MySQLUUIDType(),
    dict: JsonType(),
    list: JsonType(),
    tuple: JsonType(),
    set: JsonType(),
    frozenset: JsonType(),
    enum.Enum: VarCharType(length=255),
    # -- Complex families ------------------------------------------------
    Geometry: MySQLGeometryType(),
    # A dimension is column policy; the adapter's text form round-trips.
    Vector: TextType(),
    # BIT(n) needs a width the annotation does not carry; digits as text.
    BitString: TextType(),
    # The element type is column policy; the adapter writes JSON text.
    Range: TextType(),
    Multirange: TextType(),
    MacAddress: VarCharType(length=17),
    # IPv6's canonical text is up to 45 characters; no native IP type here.
    IPAddress: VarCharType(length=45),
}


class MySQLDataTypeSuggestionsMixin:
    """MySQL's answer to "what declaration does a bare field get here"."""

    def suggest_data_types(self) -> DataTypeSuggestion:
        return DataTypeSuggestion(table=dict(MYSQL_DATA_TYPE_SUGGESTIONS))

    def suggest_extra_data_types(self) -> ExtraDataTypeSuggestion:
        return ExtraDataTypeSuggestion(table={})


__all__ = ["MYSQL_DATA_TYPE_SUGGESTIONS", "MySQLDataTypeSuggestionsMixin"]
