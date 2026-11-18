import datetime
import decimal
import enum
import uuid

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLBitType,
    MySQLGeometryType,
    MySQLVectorType,
    MySQLUUIDType,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    IntegerType,
    DoubleType,
    DecimalType,
    TextType,
    BlobType,
    DateType,
    TimeType,
    TimestampType,
    JsonType,
    VarCharType,
    CharType,
)

TABLE = {
    bool: BooleanType(),
    int: IntegerType(),
    float: DoubleType(),
    decimal.Decimal: DecimalType(),
    str: TextType(),
    bytes: BlobType(),
    bytearray: BlobType(),
    datetime.date: DateType(),
    datetime.time: TimeType(),
    datetime.datetime: TimestampType(precision=3),
    uuid.UUID: MySQLUUIDType(),
    dict: JsonType(),
    list: JsonType(),
    tuple: JsonType(),
    set: JsonType(),
    frozenset: JsonType(),
    enum.Enum: VarCharType(length=255),
}

d = MySQLDialect()
for k, v in TABLE.items():
    if v is None:
        print(getattr(k, "__name__", k), "-> None")
        continue
    try:
        print(getattr(k, "__name__", k), "->", d.format_data_type(v)[0])
    except Exception as e:
        print(getattr(k, "__name__", k), "!!", type(e).__name__, e)

for name, factory in (
    ("mysql_geometry", lambda: MySQLGeometryType()),
    ("mysql_vector", lambda: MySQLVectorType(dim=1536)),
    ("mysql_bit", lambda: MySQLBitType()),
    ("mac char17", lambda: CharType(length=17)),
    ("timedelta int", lambda: IntegerType()),
):
    try:
        v = factory()
        print(name, "->", d.format_data_type(v)[0])
    except Exception as e:
        print(name, "!!", type(e).__name__, e)