# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/test_native_set_enum.py
"""MySQL ``SET``, ``ENUM`` and ``YEAR``: label semantics and server-side rejection.

Each column has one assertion axis that no other backend can express:

* ``SET('a','b','c')`` is a *member combination*, stored as a bit mask, and the
  driver hands back a Python ``set``.  The adapter's text form is the
  comma-separated member list.
* ``ENUM('red','green','blue')`` stores the label (the ``.value`` of the
  declaration), never the Python member's name, plus a 1-based index.
* ``YEAR`` is a one-byte year, not a ``DATE``: it stays an ``int`` in both
  directions and has its own 1901..2155 range.

Illegal members are rejected by the *server* in strict mode (error 1265), which
is the assertion the plan asks for rather than client-side validation.
"""

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError

from native_helpers import mark_for_write

from native_models import Shade

SET_FLAGS = {"a", "c"}
ENUM_LABEL = Shade.GREEN
YEAR_VALUE = 2024


def _raw_row(model, row_id: int) -> dict:
    """Read every native column of this family without any adapter."""
    return model.backend().fetch_one(
        "SELECT flags AS flags, flags + 0 AS mask, "
        "label AS label, label + 0 AS label_index, year AS year "
        f"FROM {model.table_name()} WHERE id = %s",
        (row_id,),
    )


def test_set_round_trips_as_a_member_set(native_set_enum):
    """S1: a set of members comes back as the same set, with the bit mask stored."""
    instance = native_set_enum(flags=SET_FLAGS)
    instance.save()

    raw = _raw_row(native_set_enum, instance.id)
    assert raw["flags"] == SET_FLAGS, "the server stored the same member combination"
    assert raw["mask"] == 5.0, "a + c are bit 0 and bit 2"

    found = native_set_enum.find_one(instance.id)
    assert found.flags == SET_FLAGS


def test_empty_set_round_trips(native_set_enum):
    """The empty member combination is ``''`` on the wire and ``set()`` in Python."""
    instance = native_set_enum(flags=set())
    instance.save()

    raw = _raw_row(native_set_enum, instance.id)
    assert raw["flags"] == set()
    assert raw["mask"] == 0.0
    assert native_set_enum.find_one(instance.id).flags == set()


def test_set_member_order_is_normalised_by_the_server(native_set_enum):
    """The adapter sorts members; the server stores them in declaration order."""
    instance = native_set_enum(flags={"c", "a"})
    instance.save()

    raw = _raw_row(native_set_enum, instance.id)
    assert raw["flags"] == {"a", "c"}
    assert raw["mask"] == 5.0


def test_invalid_set_member_is_rejected_by_the_server(native_set_enum):
    """A member outside the declared list is an error, not a silently dropped value."""
    with pytest.raises(DatabaseError) as info:
        native_set_enum(flags={"a", "z"}).save()
    assert "1265" in str(info.value), "strict mode must reject, not truncate"


def test_enum_stores_the_label_and_reads_it_back(native_set_enum):
    """The stored label is the member's ``.value``; the index is 1-based."""
    instance = native_set_enum(label=ENUM_LABEL)
    instance.save()

    raw = _raw_row(native_set_enum, instance.id)
    assert raw["label"] == "green", "ENUM stores the label, not the Python name"
    assert raw["label"] != ENUM_LABEL.name, "the Python member name is not the label"
    assert raw["label_index"] == 2, "green is the second declared label"

    found = native_set_enum.find_one(instance.id)
    assert found.label == ENUM_LABEL


def test_invalid_enum_label_is_rejected_by_the_server(native_set_enum):
    """An undeclared label is rejected by the server (strict mode, 1265)."""
    with pytest.raises(DatabaseError) as info:
        native_set_enum.backend().execute(
            f"INSERT INTO {native_set_enum.table_name()} (label) VALUES (%s)",
            ("purple",),
        )
    assert "1265" in str(info.value)


def test_year_stays_an_integer(native_set_enum):
    """``YEAR`` is not a date: it round-trips as an ``int``."""
    instance = native_set_enum(year=YEAR_VALUE)
    instance.save()

    assert _raw_row(native_set_enum, instance.id)["year"] == YEAR_VALUE
    found = native_set_enum.find_one(instance.id)
    assert found.year == YEAR_VALUE
    assert isinstance(found.year, int)
    assert not hasattr(found.year, "month"), "YEAR must not be decoded as a date"


def test_year_boundaries(native_set_enum):
    """The declared range is 1901..2155 plus the ``0000`` sentinel."""
    sentinel = native_set_enum(year=0)
    sentinel.save()
    assert _raw_row(native_set_enum, sentinel.id)["year"] == 0

    with pytest.raises(DatabaseError) as info:
        native_set_enum.backend().execute(
            f"INSERT INTO {native_set_enum.table_name()} (year) VALUES (%s)",
            (2156,),
        )
    assert "1264" in str(info.value)


def test_rewriting_is_stable(native_set_enum):
    """S2: rewriting the decoded values stores the same members and labels."""
    instance = native_set_enum(flags=SET_FLAGS, label=ENUM_LABEL, year=YEAR_VALUE)
    instance.save()

    before = _raw_row(native_set_enum, instance.id)

    found = native_set_enum.find_one(instance.id)
    mark_for_write(found, "flags", "label", "year")
    found.save()

    assert _raw_row(native_set_enum, instance.id) == before


def test_native_text_is_decoded_and_canonicalised(native_set_enum):
    """S3: member/label text written by native SQL reads back through the adapters."""
    row_id = 9001
    native_set_enum.backend().execute(
        f"INSERT INTO {native_set_enum.table_name()} (id, flags, label, year) "
        "VALUES (%s, %s, %s, %s)",
        (row_id, "b,c", "blue", 1999),
    )

    found = native_set_enum.find_one(row_id)
    assert found.flags == {"b", "c"}
    assert found.label == Shade.BLUE
    assert found.year == 1999

    mark_for_write(found, "flags", "label", "year")
    found.save()
    rewritten = _raw_row(native_set_enum, row_id)
    assert rewritten["flags"] == {"b", "c"}
    assert rewritten["label"] == "blue"
    assert rewritten["year"] == 1999
