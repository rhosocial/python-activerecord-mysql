# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/test_adapter_refusals.py
"""The MySQL adapters' refusals, pass-throughs and option guards.

The round-trip tests pin what each adapter produces for a good value; this file
pins what it does with a value it should not accept, and with a value that is
already in the right shape. Two families behave differently and the tests keep
that difference visible:

* the legacy adapters derive from ``SQLTypeAdapter`` and raise the plain
  ``TypeError``/``ValueError`` their docstrings describe;
* the neutral-family adapters derive from the core bases, which wrap a hook's
  failure into ``TypeConversionError``.
"""

import datetime
import uuid
from decimal import Decimal
from enum import Enum

import pytest

from rhosocial.activerecord.backend.adapters import (
    BitString,
    Geometry,
    MacAddress,
    Multirange,
    Point,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.impl.mysql.adapters import (
    MySQLBitStringAdapter,
    MySQLBooleanAdapter,
    MySQLDatetimeAdapter,
    MySQLDecimalAdapter,
    MySQLEnumAdapter,
    MySQLGeometryAdapter,
    MySQLNeutralVectorAdapter,
    MySQLRangeAdapter,
    MySQLSetAdapter,
    MySQLTimeAdapter,
    MySQLVectorAdapter,
    MySQLMacAddressAdapter,
    MySQLUUIDAdapter,
)


class Colour(Enum):
    RED = "red"
    BLUE = "blue"


# ---------------------------------------------------------------------------
# Legacy adapters: plain exceptions
# ---------------------------------------------------------------------------


class TestUUIDAdapterRefusals:
    def test_a_uuid_is_carried_through_on_read(self):
        adapter = MySQLUUIDAdapter()
        value = uuid.uuid4()
        assert adapter.from_database(value, uuid.UUID) is value


class TestBooleanAdapterRefusals:
    def test_absence_passes_through(self):
        adapter = MySQLBooleanAdapter()
        assert adapter.to_database(None, int) is None
        assert adapter.from_database(None, bool) is None


class TestDecimalAdapterRefusals:
    def test_every_write_target(self):
        adapter = MySQLDecimalAdapter()
        value = Decimal("1.50")

        assert adapter.to_database(None, Decimal) is None
        assert adapter.to_database(value, Decimal) is value
        assert adapter.to_database(value, float) == 1.5
        assert adapter.to_database(value, str) == "1.50"

        with pytest.raises(TypeError, match="Cannot convert"):
            adapter.to_database(value, int)

    def test_a_driver_number_is_read_through_text(self):
        """``Decimal(str(value))`` for every driver shape: a float directly
        would reintroduce the precision loss the adapter exists to prevent."""
        adapter = MySQLDecimalAdapter()

        assert adapter.from_database("1.50", Decimal) == Decimal("1.50")
        assert adapter.from_database(2, Decimal) == Decimal("2")
        assert adapter.from_database(1.5, Decimal) == Decimal("1.5")


class TestTimeAdapterRefusals:
    def test_absence_and_the_text_wire_form(self):
        adapter = MySQLTimeAdapter()

        assert adapter.to_database(None, str) is None
        assert adapter.to_database(datetime.time(1, 2, 3), str) == "01:02:03.000000"

    def test_all_three_read_shapes(self):
        adapter = MySQLTimeAdapter()

        assert adapter.from_database(None, datetime.time) is None

        value = datetime.time(1, 2)
        assert adapter.from_database(value, datetime.time) is value

        # mysql-connector returns a TIME column as a timedelta.
        converted = adapter.from_database(
            datetime.timedelta(hours=1, minutes=2, seconds=3), datetime.time
        )
        assert converted == datetime.time(1, 2, 3)

        assert adapter.from_database("01:02:03", datetime.time) == datetime.time(1, 2, 3)


class TestDatetimeAdapterRefusals:
    def test_the_old_server_spelling_for_an_aware_value(self):
        """Below 5.7.8 the ISO text is not accepted, so the aware value is
        rendered in the traditional form (and normalised to UTC first)."""
        adapter = MySQLDatetimeAdapter(mysql_version=(5, 7, 0))
        aware = datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))

        assert adapter.to_database(aware, str) == "2024-01-01 10:00:00.000000"

    def test_every_read_shape_gets_a_utc_aware_value(self):
        adapter = MySQLDatetimeAdapter()

        assert adapter.from_database(None, datetime.datetime) is None

        naive = datetime.datetime(2024, 1, 1, 12, 0)
        assert adapter.from_database(naive, datetime.datetime).tzinfo is datetime.timezone.utc

        aware = datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        assert adapter.from_database(aware, datetime.datetime) is aware

        assert adapter.from_database("2024-01-01T12:00:00", datetime.datetime).tzinfo is (
            datetime.timezone.utc
        )
        assert adapter.from_database("2024-01-01T12:00:00+00:00", datetime.datetime) == aware

        # Anything else goes through ``str()`` first; a date is such a value.
        fallback = adapter.from_database(datetime.date(2024, 1, 1), datetime.datetime)
        assert fallback == aware.replace(hour=0, minute=0)


class TestEnumAdapterRefusals:
    def test_a_value_that_is_neither_text_nor_an_index_is_named(self):
        adapter = MySQLEnumAdapter()

        with pytest.raises(TypeError, match="Cannot convert"):
            adapter.from_database(object(), Colour)


class TestSetAdapterRefusals:
    def test_the_target_must_be_text(self):
        adapter = MySQLSetAdapter()

        with pytest.raises(TypeError, match="only supports str target type"):
            adapter.to_database({"a"}, int)

    def test_at_most_sixty_four_members(self):
        adapter = MySQLSetAdapter()

        with pytest.raises(ValueError, match="maximum 64 members"):
            adapter.to_database([str(index) for index in range(65)], str)

    def test_a_member_outside_the_declaration_is_named(self):
        adapter = MySQLSetAdapter(allowed_values=["a"])

        with pytest.raises(ValueError, match="Invalid SET values"):
            adapter.to_database(["b"], str)

    def test_an_unreadable_value_is_named(self):
        adapter = MySQLSetAdapter()

        with pytest.raises(TypeError, match="Cannot convert"):
            adapter.from_database(object(), set)


class TestLegacyVectorAdapterRefusals:
    def test_the_declared_pairs(self):
        assert MySQLVectorAdapter().supported_types == {list: [bytes, str]}

    def test_absence_passes_through_both_ways(self):
        adapter = MySQLVectorAdapter()

        assert adapter.to_database(None, str) is None
        assert adapter.from_database(None, list) is None

    def test_the_maximum_dimension_is_enforced(self):
        adapter = MySQLVectorAdapter()
        too_many = [0.0] * (adapter.MAX_VECTOR_DIMENSION + 1)

        with pytest.raises(ValueError, match="exceeds maximum supported dimension"):
            adapter.to_database(too_many, str)

    def test_a_declared_dimension_is_enforced(self):
        adapter = MySQLVectorAdapter(dimension=2)

        with pytest.raises(ValueError, match="doesn't match expected dimension"):
            adapter.to_database([1.0], str)

    def test_a_component_must_be_a_number(self):
        adapter = MySQLVectorAdapter()

        with pytest.raises(TypeError, match="is not a number"):
            adapter.to_database([1.0, "x"], str)

    def test_the_read_target_must_be_a_list(self):
        adapter = MySQLVectorAdapter()

        with pytest.raises(TypeError, match="only supports list target type"):
            adapter.from_database("[1.0]", str)

    def test_a_list_is_normalised_to_floats(self):
        adapter = MySQLVectorAdapter()

        assert adapter.from_database([1, 2.5], list) == [1.0, 2.5]

    def test_an_unreadable_value_is_named(self):
        adapter = MySQLVectorAdapter()

        with pytest.raises(TypeError, match="to vector"):
            adapter.from_database(object(), list)


# ---------------------------------------------------------------------------
# Neutral-family adapters: the base wraps failures as TypeConversionError
# ---------------------------------------------------------------------------


class TestGeometryAdapterRefusals:
    def test_an_unusable_srid_option_is_refused(self):
        adapter = MySQLGeometryAdapter()

        with pytest.raises(TypeConversionError, match="srid option must be int or None"):
            adapter.to_database(Point(1, 2), str, {"srid": "epsg:4326"})
        with pytest.raises(TypeConversionError, match="srid must be non-negative"):
            adapter.to_database(Point(1, 2), str, {"srid": -1})

    def test_a_neutral_geometry_is_carried_through_on_read(self):
        adapter = MySQLGeometryAdapter()
        value = Point(1, 2)

        assert adapter.from_database(value, Geometry) is value

    def test_an_unreadable_geometry_is_named(self):
        """The adapter reads WKT text only; the server's internal binary
        geometry is not WKT and must be selected as ``ST_AsText(col)``."""
        adapter = MySQLGeometryAdapter()

        with pytest.raises(TypeConversionError, match="expected WKT str or UTF-8 bytes"):
            adapter.from_database(42, Geometry)


class TestNeutralVectorAdapterRefusals:
    def test_a_neutral_vector_is_carried_through_on_read(self):
        adapter = MySQLNeutralVectorAdapter()
        value = Vector((1.0, 2.0))

        assert adapter.from_database(value, Vector) is value


class TestBitStringAdapterRefusals:
    def test_a_neutral_bit_string_is_carried_through_on_read(self):
        adapter = MySQLBitStringAdapter()
        value = BitString.from_bits("101")

        assert adapter.from_database(value, BitString) is value

    def test_a_declared_width_must_be_a_positive_integer(self):
        """The constructor validates its own argument; the per-call option is
        validated at the point it is read."""
        adapter = MySQLBitStringAdapter()

        with pytest.raises(TypeConversionError, match="bit_length option must be int"):
            adapter.from_database(b"\x01", BitString, {"bit_length": True})
        with pytest.raises(TypeConversionError, match="bit_length option must be at least 1"):
            adapter.from_database(b"\x01", BitString, {"bit_length": 0})

    def test_a_negative_integer_is_refused(self):
        adapter = MySQLBitStringAdapter()

        with pytest.raises(TypeConversionError, match="must be non-negative"):
            adapter.from_database(-1, BitString, {"bit_length": 8})

    def test_an_unreadable_value_is_named(self):
        adapter = MySQLBitStringAdapter(bit_length=8)

        with pytest.raises(TypeConversionError, match="expected bytes, int or bit text"):
            adapter.from_database(object(), BitString)


class TestRangeAdapterRefusals:
    def test_a_neutral_range_is_carried_through_on_read(self):
        adapter = MySQLRangeAdapter()
        value = Range(1, 2, "[)")

        assert adapter.from_database(value, Range) is value

    def test_bytes_must_be_utf8(self):
        adapter = MySQLRangeAdapter()

        with pytest.raises(TypeConversionError, match="is not UTF-8"):
            adapter.from_database(b"\xff\xfe", Range)

    def test_an_unreadable_json_shape_is_named(self):
        adapter = MySQLRangeAdapter()

        with pytest.raises(TypeConversionError, match="expected range JSON object or array"):
            adapter.from_database(42, str)


class TestMacAddressAdapterRefusals:
    def test_a_neutral_mac_is_carried_through_on_read(self):
        adapter = MySQLMacAddressAdapter()
        value = MacAddress.parse("08:00:2b:01:02:03")

        assert adapter.from_database(value, MacAddress) is value

    def test_an_unreadable_value_is_named(self):
        adapter = MySQLMacAddressAdapter()

        with pytest.raises(TypeConversionError, match="expected MAC address text or bytes"):
            adapter.from_database(1.5, MacAddress)
