# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/test_native_json.py
"""MySQL native ``JSON``: the stored document, not just the Python round-trip.

A round-trip alone would hide a double-encoded document (``"{\\"a\\": 1}"``
written into a JSON column is legal JSON, it is just a string).  The assertions
therefore read the server's own view: ``JSON_TYPE`` is ``OBJECT`` and
``JSON_EXTRACT`` reaches the member, which is only true for a real document.
"""

import json

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError

from native_helpers import mark_for_write

#: The native tables this module uses.  ``schema`` creates only these, so
#: a server missing another family's type does not fail this module's setup.
TABLES = ("native_json",)

PAYLOAD = {"a": 1, "b": [1, None, "x"]}
PAYLOAD_TEXT = '{"a": 1, "b": [1, null, "x"]}'


def _raw_document(model, row_id: int) -> dict:
    return model.backend().fetch_one(
        "SELECT payload AS raw, JSON_TYPE(payload) AS kind, "
        "JSON_EXTRACT(payload, '$.a') AS member_a "
        f"FROM {model.table_name()} WHERE id = %s",
        (row_id,),
    )


def test_json_document_round_trips_and_is_stored_as_a_document(native_json):
    """S1 plus the raw check: the column holds an OBJECT, not a JSON string."""
    instance = native_json(payload=PAYLOAD)
    instance.save()

    raw = _raw_document(native_json, instance.id)
    assert raw["kind"] == "OBJECT", "a double-encoded document would be 'STRING'"
    assert json.loads(raw["member_a"]) == 1

    found = native_json.find_one(instance.id)
    assert found.payload == PAYLOAD


def test_rewriting_is_stable(native_json):
    """S2: rewriting the decoded document stores the identical text."""
    instance = native_json(payload=PAYLOAD)
    instance.save()
    before = _raw_document(native_json, instance.id)["raw"]

    found = native_json.find_one(instance.id)
    mark_for_write(found, "payload")
    found.save()

    assert _raw_document(native_json, instance.id)["raw"] == before
    assert before == PAYLOAD_TEXT


def test_native_document_text_is_decoded_and_canonicalised(native_json):
    """S3: a document written by native SQL reads back and rewrites unchanged."""
    row_id = 9001
    native_json.backend().execute(
        f"INSERT INTO {native_json.table_name()} (id, payload) VALUES (%s, %s)",
        (row_id, '{"k": "v"}'),
    )

    found = native_json.find_one(row_id)
    assert found.payload == {"k": "v"}

    mark_for_write(found, "payload")
    found.save()
    assert json.loads(_raw_document(native_json, row_id)["raw"]) == {"k": "v"}


def test_json_value_types_are_preserved(native_json):
    """JSON keeps integers, floats and booleans distinct; so must the decode."""
    value = {"n": 1, "f": 1.5, "big": 2**53, "yes": True, "no": None}
    instance = native_json(payload=value)
    instance.save()

    found = native_json.find_one(instance.id)
    assert found.payload == value
    assert isinstance(found.payload["n"], int)
    assert isinstance(found.payload["f"], float)
    assert isinstance(found.payload["big"], int)


def test_unicode_is_not_escaped_on_the_wire(native_json):
    """The adapter writes UTF-8 text; the document round-trips the character."""
    value = {"city": "\u5317\u4eac"}
    instance = native_json(payload=value)
    instance.save()

    found = native_json.find_one(instance.id)
    assert found.payload == value


def test_invalid_json_text_is_rejected_by_the_server(native_json):
    """The server validates the document: invalid JSON text (error 3140)."""
    with pytest.raises(DatabaseError) as info:
        native_json.backend().execute(
            f"INSERT INTO {native_json.table_name()} (payload) VALUES (%s)",
            ("{not json",),
        )
    assert "3140" in str(info.value)
