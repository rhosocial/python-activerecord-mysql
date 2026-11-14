# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/test_native_uuid.py
"""UUID storage on MySQL: canonical ``CHAR(36)`` and raw ``BINARY(16)``.

MySQL has no ``UUID`` type; the two conventional carriers are in use and both
must work, because the choice is the schema's, not the adapter's.  The two
tables (well, columns) are checked separately, and one assertion reads the
server's own ``BIN_TO_UUID()`` to prove both carriers hold the *same* value.
"""

import uuid

import pytest

from rhosocial.activerecord.backend.impl.mysql.adapters import MySQLUUIDAdapter

from native_helpers import mark_for_write

VALUE = uuid.UUID("12345678-1234-5678-1234-567812345678")
VALUE_HEX = VALUE.hex


def _raw_uuid(model, row_id: int) -> dict:
    return model.backend().fetch_one(
        "SELECT u_char AS char_value, LENGTH(u_char) AS char_length, "
        "u_bin AS bin_value, HEX(u_bin) AS bin_hex, LENGTH(u_bin) AS bin_length, "
        "BIN_TO_UUID(u_bin) AS bin_as_text "
        f"FROM {model.table_name()} WHERE id = %s",
        (row_id,),
    )


def test_char_36_carrier_round_trips_as_the_canonical_text(native_uuid):
    """S1: the text carrier stores the canonical 36-character form."""
    instance = native_uuid(u_char=VALUE)
    instance.save()

    raw = _raw_uuid(native_uuid, instance.id)
    assert raw["char_value"] == str(VALUE)
    assert raw["char_length"] == 36

    assert native_uuid.find_one(instance.id).u_char == VALUE


def test_binary_16_carrier_round_trips_as_raw_bytes(native_uuid):
    """S1: the binary carrier stores exactly 16 bytes, decoded back to a UUID."""
    instance = native_uuid(u_bin=VALUE)
    instance.save()

    raw = _raw_uuid(native_uuid, instance.id)
    assert raw["bin_length"] == 16
    assert raw["bin_hex"].upper() == VALUE_HEX.upper()
    assert raw["bin_as_text"] == str(VALUE)

    found = native_uuid.find_one(instance.id)
    assert found.u_bin == VALUE


def test_both_carriers_hold_the_same_value(native_uuid):
    """The server's ``BIN_TO_UUID`` agrees with the text carrier."""
    instance = native_uuid(u_char=VALUE, u_bin=VALUE)
    instance.save()

    raw = _raw_uuid(native_uuid, instance.id)
    assert raw["bin_as_text"] == raw["char_value"] == str(VALUE)

    found = native_uuid.find_one(instance.id)
    assert found.u_char == found.u_bin == VALUE


def test_rewriting_is_stable_for_both_carriers(native_uuid):
    """S2: rewriting the decoded UUID stores the identical text/bytes."""
    instance = native_uuid(u_char=VALUE, u_bin=VALUE)
    instance.save()
    before = _raw_uuid(native_uuid, instance.id)

    found = native_uuid.find_one(instance.id)
    mark_for_write(found, "u_char", "u_bin")
    found.save()

    after = _raw_uuid(native_uuid, instance.id)
    assert after["char_value"] == before["char_value"]
    assert after["bin_hex"].upper() == before["bin_hex"].upper()


def test_native_carrier_values_are_decoded(native_uuid):
    """S3: values written by native SQL (text and UNHEX) read back as UUIDs."""
    row_id = 9001
    native_uuid.backend().execute(
        f"INSERT INTO {native_uuid.table_name()} (id, u_char, u_bin) "
        "VALUES (%s, %s, UNHEX(%s))",
        (row_id, str(VALUE), VALUE_HEX),
    )

    found = native_uuid.find_one(row_id)
    assert found.u_char == VALUE
    assert found.u_bin == VALUE

    mark_for_write(found, "u_char", "u_bin")
    found.save()
    raw = _raw_uuid(native_uuid, row_id)
    assert raw["char_value"] == str(VALUE)
    assert raw["bin_hex"].upper() == VALUE_HEX.upper()


def test_uuid_adapter_binary_target_is_the_raw_sixteen_bytes():
    """The adapter's ``bytes`` target is the 16-byte form, not UTF-8 text."""
    adapter = MySQLUUIDAdapter()
    assert adapter.to_database(VALUE, bytes) == VALUE.bytes
    assert adapter.from_database(VALUE.bytes, uuid.UUID) == VALUE


def test_uuid_adapter_refuses_a_non_uuid_length_binary_value():
    """A 15-byte value cannot be silently read as a UUID."""
    adapter = MySQLUUIDAdapter()
    with pytest.raises(ValueError, match="16 bytes"):
        adapter.from_database(b"\x00" * 15, uuid.UUID)
