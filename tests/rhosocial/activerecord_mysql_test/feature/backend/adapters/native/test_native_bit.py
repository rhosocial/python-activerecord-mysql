# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/test_native_bit.py
"""MySQL ``BIT(n)`` columns: widths, targets and the stored bit value.

``BIT`` is a bit string, not a truth value, and its width is part of the type.
The adapter offers three driver targets:

* ``int``  -- the significant bits as an integer (works for any width);
* ``bytes`` -- the whole-byte form (exact only when the bits fit the width);
* ``str``  -- the bit text, which is the form a **text** carrier takes.

A native ``BIT(n)`` column takes ``int``/``bytes``; a bound ``str`` is read as a
decimal number by the server and is rejected as too long (measured below).
Because a ``BIT`` value carries no length metadata, the width is declared on
the adapter instance (``MySQLBitStringAdapter(bit_length=n)``), not inferred.
"""

import pytest

from rhosocial.activerecord.backend.adapters import BitString
from rhosocial.activerecord.backend.errors import DatabaseError, TypeConversionError
from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLBitStringAdapter

from native_helpers import mark_for_write

BITS_8 = BitString.from_bits("10101010")
BITS_13 = BitString.from_bits("1010000001101")
BITS_13_INT = 5133
BITS_13_HEX = "140D"


def _raw_bit(model, column: str, row_id: int):
    """Read the column, its integer value and its hex bytes without adapters."""
    row = model.backend().fetch_one(
        f"SELECT {column} AS v, {column} + 0 AS n, HEX({column}) AS h "
        f"FROM {model.table_name()} WHERE id = %s",
        (row_id,),
    )
    return row["v"], row["n"], row["h"]


def test_byte_aligned_bit_column_round_trips(native_bit):
    """S1: an 8-bit value comes back as the same bit string."""
    instance = native_bit(bits8=BITS_8)
    instance.save()

    found = native_bit.find_one(instance.id)
    assert found.bits8 == BITS_8
    assert found.bits8.bit_length == 8
    assert _raw_bit(native_bit, "bits8", instance.id) == (170, 170, "AA")


def test_non_byte_aligned_bit_column_round_trips(native_bit):
    """S1: a 13-bit value keeps its width and its leading bits."""
    instance = native_bit(bits13=BITS_13)
    instance.save()

    found = native_bit.find_one(instance.id)
    assert found.bits13 == BITS_13
    assert found.bits13.bit_length == 13, "a declared width must restore 13 bits"
    assert _raw_bit(native_bit, "bits13", instance.id) == (
        BITS_13_INT,
        BITS_13_INT,
        BITS_13_HEX,
    )


def test_bytes_target_round_trips_on_a_13_bit_column(native_bit):
    """The ``bytes`` target binds the whole-byte form; the server keeps the bits."""
    instance = native_bit(bits_bytes=BITS_13)
    instance.save()

    found = native_bit.find_one(instance.id)
    assert found.bits_bytes == BITS_13
    assert _raw_bit(native_bit, "bits_bytes", instance.id) == (
        BITS_13_INT,
        BITS_13_INT,
        BITS_13_HEX,
    )


def test_rewriting_is_stable(native_bit):
    """S2: writing the decoded value back stores exactly the same bit value."""
    instance = native_bit(bits8=BITS_8, bits13=BITS_13, bits_bytes=BITS_13)
    instance.save()

    before = {
        column: _raw_bit(native_bit, column, instance.id)
        for column in ("bits8", "bits13", "bits_bytes")
    }

    found = native_bit.find_one(instance.id)
    mark_for_write(found, "bits8", "bits13", "bits_bytes")
    found.save()

    for column, raw in before.items():
        assert _raw_bit(native_bit, column, instance.id) == raw


def test_bit_literal_written_as_native_sql_is_decoded(native_bit):
    """S3: the server's own ``b'...'`` literal reads back through the adapter."""
    row_id = 9001
    native_bit.backend().execute(
        f"INSERT INTO {native_bit.table_name()} (id, bits13) " "VALUES (%s, b'1010000001101')",
        (row_id,),
    )

    found = native_bit.find_one(row_id)
    assert found.bits13 == BITS_13
    assert found.bits13.bit_length == 13
    assert _raw_bit(native_bit, "bits13", row_id) == (BITS_13_INT, BITS_13_INT, BITS_13_HEX)


def test_bit_text_target_is_the_text_carrier_form_only():
    """The adapter's ``str`` target produces bit text; that is not a BIT column form."""
    assert MySQLBitStringAdapter().to_database(BITS_13, str) == "1010000001101"


def test_bytes_target_is_right_aligned_big_endian():
    """The ``bytes`` target carries the value, not the padded byte layout.

    ``BitString.data`` pads the low end (13 bits -> b'\\xa0\\x68' = 41064), which
    a ``BIT(13)`` column reads as an over-wide number. The adapter binds the
    big-endian value instead (5133 -> b'\\x14\\x0d'); byte-aligned widths are
    identical either way.
    """
    adapter = MySQLBitStringAdapter()
    assert adapter.to_database(BITS_13, bytes) == b"\x14\x0d"
    assert adapter.to_database(BITS_8, bytes) == BITS_8.data


def test_bit_text_bound_to_a_bit_column_is_rejected_by_the_server(native_bit):
    """A native ``BIT(13)`` column does not accept the bit *text* form.

    Measured error: 1406 "Data too long for column 'bits13'" -- the server reads
    the string as a decimal number (1010000001101) which does not fit in 13
    bits.  The adapter's text form belongs to TEXT carriers.
    """
    adapter = MySQLBitStringAdapter()
    with pytest.raises(DatabaseError) as info:
        native_bit.backend().execute(
            f"INSERT INTO {native_bit.table_name()} (bits13) VALUES (%s)",
            (adapter.to_database(BITS_13, str),),
        )
    assert "1406" in str(info.value)


def test_value_wider_than_the_column_is_rejected(native_bit):
    """A 14-bit value bound as ``int`` does not fit the ``BIT(13)`` column."""
    over_wide = BitString.from_int(0x2000, 14)
    with pytest.raises(DatabaseError) as info:
        native_bit(bits13=over_wide).save()
    assert "1406" in str(info.value)


def test_declared_width_refuses_an_over_wide_value_on_read():
    """The adapter's own width check: 8192 does not fit in 13 declared bits."""
    adapter = MySQLBitStringAdapter(bit_length=13)
    with pytest.raises(TypeConversionError, match="does not fit in 13 bits"):
        adapter.from_database(8192, BitString)
