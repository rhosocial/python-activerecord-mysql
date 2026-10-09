# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_uuid_substitute.py
"""The UUID substitute on a live server: what MySQL actually builds from it.

MySQL has no ``UUID`` data type, so ``suggested_data_types()["uuid"]`` names a
substitute and that substitute has to be the right *size*. This file checks the
size against a real server rather than against the manual alone, on every
scenario the suite is pointed at — the reasoning is in
:class:`~rhosocial.activerecord.backend.impl.mysql.expression.types.MySQLUUIDType`
and the unit-level render/parse assertions are in ``test_mysql_type_protocol``.

The two facts being pinned here:

* ``BINARY[(M)]`` — "An optional length *M* represents the column length in
  bytes. **If omitted, *M* defaults to 1.**" (manual §13.3.1,
  https://dev.mysql.com/doc/refman/8.4/en/string-type-syntax.html). So a bare
  ``BINARY`` is a **one-byte** column, and ``information_schema`` says so.
* ``UUID_TO_BIN()`` — "The return binary UUID is a ``VARBINARY(16)`` value"
  (manual §14.23,
  https://dev.mysql.com/doc/refman/8.4/en/miscellaneous-functions.html). A UUID
  is 128 bits, so the storage is 16 bytes.

Together they are what a one-byte substitution would violate: a UUID column
that cannot hold a UUID.

Verified against MySQL 5.6.51, 5.7.44, 8.0.46, 8.4.11, 9.2.0, 9.4.0 and 26.7.0
before these assertions were written.
"""

import uuid

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLBinaryType,
    MySQLUUIDType,
    MySQLVarBinaryType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

TABLE = "uuidsub_test"

#: A fixed UUID so the assertions read the same on every run.
UUID_TEXT = "6ccd780c-baba-1026-9564-5b8c656024db"
#: The same UUID with the dashes removed, hex — how it is stored in 16 bytes.
UUID_HEX = UUID_TEXT.replace("-", "")


@pytest.fixture
def ddl():
    return ExecutionOptions(stmt_type=StatementType.DDL)


def _column_type(backend, column):
    result = backend.execute(
        "SELECT COLUMN_TYPE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH"
        " FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
        " AND COLUMN_NAME = %s",
        (TABLE, column),
    )
    assert len(result.data) == 1, (column, result.data)
    return result.data[0]


def _drop(backend, ddl):
    backend.execute(f"DROP TABLE IF EXISTS {TABLE}", (), options=ddl)


def _create(backend, ddl, column_ddl):
    _drop(backend, ddl)
    backend.execute(
        f"CREATE TABLE {TABLE} (id INT PRIMARY KEY, {column_ddl})",
        (),
        options=ddl,
    )


class TestTheServerBuildsTheDocumentedColumn:
    """The DDL this dialect emits must produce the column the manual describes."""

    def test_binary_sixteen_is_sixteen_bytes(self, mysql_backend, ddl):
        """``BINARY(16)`` is a 16-byte column, as reported by the server.

        Read back from ``information_schema.COLUMNS.COLUMN_TYPE``, which is the
        same string introspection hands to ``parse_type`` — so this is what the
        round-trip assertion is reasoning about, not a restatement of it.
        """
        rendered = MySQLUUIDType(mysql_backend.dialect).to_sql()[0]
        assert rendered == "BINARY(16)"
        _create(mysql_backend, ddl, f"u {rendered}")
        row = _column_type(mysql_backend, "u")
        assert row["COLUMN_TYPE"] == "binary(16)"
        assert row["CHARACTER_MAXIMUM_LENGTH"] == 16
        _drop(mysql_backend, ddl)

    def test_bare_binary_is_one_byte(self, mysql_backend, ddl):
        """``BINARY`` is ``BINARY(1)`` — the manual's default, confirmed live.

        This is what the UUID substitution used to render, so it is the fact
        that makes the defect concrete: a caller who asked for a UUID column
        got a column this wide.
        """
        rendered = MySQLBinaryType(mysql_backend.dialect).to_sql()[0]
        assert rendered == "BINARY"
        _create(mysql_backend, ddl, f"u {rendered}")
        row = _column_type(mysql_backend, "u")
        assert row["COLUMN_TYPE"] == "binary(1)"
        assert row["CHARACTER_MAXIMUM_LENGTH"] == 1
        _drop(mysql_backend, ddl)

    def test_varbinary_has_no_lengthless_form(self, mysql_backend, ddl):
        """``VARBINARY`` without a length is a syntax error, on every server.

        This is why :class:`MySQLVarBinaryType` requires its length instead of
        rendering a bare ``VARBINARY``: the lengthless form is not a one-byte
        column, it is not SQL at all.
        """
        _drop(mysql_backend, ddl)
        with pytest.raises(DatabaseError) as excinfo:
            mysql_backend.execute(
                f"CREATE TABLE {TABLE} (c VARBINARY)", (), options=ddl)
        assert "1064" in str(excinfo.value)


class TestTheColumnHoldsAUUID:
    """The point of the substitution: a 16-byte UUID fits, and survives."""

    def test_a_uuid_round_trips_through_the_emitted_ddl(self, mysql_backend, ddl):
        rendered = MySQLUUIDType(mysql_backend.dialect).to_sql()[0]
        _create(mysql_backend, ddl, f"u {rendered}")
        mysql_backend.execute(
            f"INSERT INTO {TABLE} (id, u) VALUES (%s, UNHEX(%s))", (1, UUID_HEX)
        )
        result = mysql_backend.execute(
            f"SELECT HEX(u) AS h, LENGTH(u) AS n FROM {TABLE} WHERE id = %s", (1,)
        )
        assert len(result.data) == 1
        assert result.data[0]["h"].upper() == UUID_HEX.upper()
        assert result.data[0]["n"] == 16
        _drop(mysql_backend, ddl)

    def test_it_stays_sixteen_bytes_without_being_padded(self, mysql_backend, ddl):
        """``BINARY``'s 0x00 right-padding never fires for a UUID.

        The manual warns that stored ``BINARY`` values are right-padded to the
        column length with ``0x00`` and no trailing bytes are removed on
        retrieval (§13.3.3, https://dev.mysql.com/doc/refman/8.4/en/binary-varbinary.html),
        which is the usual reason to prefer ``VARBINARY``. A UUID is never
        shorter than 16 bytes, so the caveat is checked here rather than
        assumed: the value read back is byte-for-byte the value stored.
        """
        rendered = MySQLUUIDType(mysql_backend.dialect).to_sql()[0]
        _create(mysql_backend, ddl, f"u {rendered}")
        # A UUID whose *last* byte is 0x00 — the byte a padding scheme would be
        # most likely to swallow.
        value = uuid.UUID(int=0x0102030405060708090A0B0C0D0E0F00)
        hex_value = value.hex
        mysql_backend.execute(
            f"INSERT INTO {TABLE} (id, u) VALUES (%s, UNHEX(%s))", (1, hex_value)
        )
        result = mysql_backend.execute(
            f"SELECT HEX(u) AS h, LENGTH(u) AS n FROM {TABLE} WHERE id = %s", (1,)
        )
        assert result.data[0]["h"].upper() == hex_value.upper()
        assert result.data[0]["n"] == 16
        _drop(mysql_backend, ddl)

    def test_a_one_byte_column_cannot_hold_one(self, mysql_backend, ddl):
        """What the old substitution produced, shown against the server.

        The value does not survive: a strict-mode server rejects the insert
        with error 1406, and a non-strict one (MySQL 5.6 by default) keeps only
        the first byte. Either way the UUID is gone and nothing in the DDL said
        it would be — which is why the width had to be pinned rather than left
        to MySQL's default.
        """
        _create(mysql_backend, ddl, f"u {MySQLBinaryType(mysql_backend.dialect).to_sql()[0]}")
        try:
            mysql_backend.execute(
                f"INSERT INTO {TABLE} (id, u) VALUES (%s, UNHEX(%s))", (1, UUID_HEX)
            )
        except DatabaseError:
            pass  # strict mode: rejected with error 1406, the same outcome
        result = mysql_backend.execute(f"SELECT LENGTH(u) AS n FROM {TABLE}")
        assert result.data == [{"n": 1}] or all(
            row["n"] == 1 for row in result.data
        )
        _drop(mysql_backend, ddl)


class TestVarBinaryStillBehaves:
    """The length requirement must not have cost ``VARBINARY`` anything."""

    def test_it_renders_and_holds_the_bytes_it_is_given(self, mysql_backend, ddl):
        rendered = MySQLVarBinaryType(mysql_backend.dialect, 16).to_sql()[0]
        assert rendered == "VARBINARY(16)"
        _create(mysql_backend, ddl, f"u {rendered}")
        row = _column_type(mysql_backend, "u")
        assert row["COLUMN_TYPE"] == "varbinary(16)"
        mysql_backend.execute(
            f"INSERT INTO {TABLE} (id, u) VALUES (%s, UNHEX(%s))", (1, UUID_HEX)
        )
        result = mysql_backend.execute(
            f"SELECT HEX(u) AS h, LENGTH(u) AS n FROM {TABLE} WHERE id = %s", (1,)
        )
        assert result.data[0]["h"].upper() == UUID_HEX.upper()
        assert result.data[0]["n"] == 16
        _drop(mysql_backend, ddl)