# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/test_adapters.py
"""Offline adapter round-trip coverage for the MySQL backend.

Each adapter is tested in both directions (to_database / from_database)
with None semantics and boundary values.
"""
import datetime
import uuid
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.impl.mysql.adapters import (
    MySQLBlobAdapter,
    MySQLBooleanAdapter,
    MySQLDateAdapter,
    MySQLDatetimeAdapter,
    MySQLDecimalAdapter,
    MySQLJSONAdapter,
    MySQLTimeAdapter,
    MySQLUUIDAdapter,
    MySQLUUIDBinaryAdapter,
    MySQLVectorAdapter,
)


@pytest.fixture
def blob(): return MySQLBlobAdapter()
@pytest.fixture
def json_a(): return MySQLJSONAdapter()
@pytest.fixture
def uuid_a(): return MySQLUUIDAdapter()
@pytest.fixture
def uuid_bin(): return MySQLUUIDBinaryAdapter()
@pytest.fixture
def bool_a(): return MySQLBooleanAdapter()
@pytest.fixture
def dec_a(): return MySQLDecimalAdapter()
@pytest.fixture
def date_a(): return MySQLDateAdapter()
@pytest.fixture
def time_a(): return MySQLTimeAdapter()
@pytest.fixture
def dt_a(): return MySQLDatetimeAdapter()
@pytest.fixture
def vec_a(): return MySQLVectorAdapter()


class TestBlob:
    def test_roundtrip(self, blob):
        assert blob.to_database(b"data", bytes) == b"data"
        assert blob.from_database(b"data", bytes) == b"data"
    def test_none(self, blob):
        assert blob.to_database(None, bytes) is None
        assert blob.from_database(None, bytes) is None

class TestJSON:
    def test_roundtrip(self, json_a):
        val = {"a": 1, "b": [2, 3]}
        result = json_a.to_database(val, str)
        assert isinstance(result, str)
        assert json_a.from_database(result, dict) == val
    def test_none(self, json_a):
        assert json_a.to_database(None, str) is None

class TestUUID:
    def test_roundtrip(self, uuid_a):
        u = uuid.uuid4()
        result = uuid_a.to_database(u, str)
        assert result == str(u)
        assert uuid_a.from_database(str(u), uuid.UUID) == u


class TestUUIDBinary:
    def test_roundtrip_binary(self, uuid_bin):
        u = uuid.uuid4()
        result = uuid_bin.to_database(u, bytes)
        assert isinstance(result, bytes)
        assert len(result) == 16
        assert uuid_bin.from_database(result, uuid.UUID) == u

    def test_roundtrip_equals_bytes(self, uuid_bin):
        u = uuid.uuid4()
        assert uuid_bin.to_database(u, bytes) == u.bytes

    def test_legacy_hex_string_fallback(self, uuid_bin):
        u = uuid.uuid4()
        assert uuid_bin.from_database(str(u), uuid.UUID) == u

    def test_wider_binary_padding(self, uuid_bin):
        u = uuid.uuid4()
        padded = u.bytes + b"\x00\x00\x00\x00"  # e.g. from BINARY(20)
        assert uuid_bin.from_database(padded, uuid.UUID) == u

    def test_none(self, uuid_bin):
        assert uuid_bin.to_database(None, bytes) is None
        assert uuid_bin.from_database(None, uuid.UUID) is None

class TestBoolean:
    def test_true(self, bool_a):
        assert bool_a.to_database(True, int) == 1
        assert bool_a.from_database(1, bool) is True
        assert bool_a.from_database(True, bool) is True

class TestDecimal:
    def test_roundtrip(self, dec_a):
        d = Decimal("123.45")
        assert dec_a.from_database(d, Decimal) == d
    def test_none(self, dec_a):
        assert dec_a.from_database(None, Decimal) is None

class TestDate:
    def test_roundtrip(self, date_a):
        d = datetime.date(2026, 8, 26)
        assert date_a.to_database(d, datetime.date) == "2026-08-26"
        assert date_a.from_database(d, datetime.date) == d

class TestTime:
    def test_roundtrip(self, time_a):
        t = datetime.time(14, 30, 0)
        s = time_a.to_database(t, str)
        assert isinstance(s, str)
        assert time_a.from_database(s, datetime.time) == t

class TestDatetime:
    def test_naive_roundtrip(self, dt_a):
        dt = datetime.datetime(2026, 8, 26, 14, 30, 0)
        result = dt_a.to_database(dt, str)
        assert result == dt  # naive datetime passes through for the driver

    def test_aware_normalizes_utc(self, dt_a):
        aware = datetime.datetime(2026, 8, 26, 14, 30, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        result = dt_a.to_database(aware, str)
        assert result == "2026-08-26T12:30:00"  # ISO 8601 UTC naive

    def test_none(self, dt_a):
        assert dt_a.to_database(None, str) is None

class TestVector:
    def test_roundtrip(self, vec_a):
        v = [1.0, 2.5, 3.0]
        s = vec_a.to_database(v, str)
        assert isinstance(s, str)
        assert vec_a.from_database(s, list) == v