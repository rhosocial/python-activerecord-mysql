# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_typed_values.py
"""MySQL's spellings for the typed value literals.

Core's value nodes render through ``inline_params`` -- a class-level
strategy, never a per-instance flag -- so the DDL-position assertions below
use a test-local DDL-position class per kind, the same lift core itself
performs when it renders a ``DEFAULT`` / ``CHECK`` tree (``Literal`` ->
``DdlLiteral``). The data-position assertions run the node classes as they
ship, which bind.

Every literal form asserted here was measured, not transcribed. Measured on
8.0.46 (scenario ``mysql_80``, 192.168.1.3:14682) and on the server behind
scenario ``mysql_97`` (192.168.1.3:14686, which answers ``SELECT VERSION()``
with ``26.7.0``):

* ``SELECT X'0102FF'`` returns ``b'\\x01\\x02\\xff'``; a
  ``VARBINARY(16) DEFAULT X'0102FF'`` fills the column with those bytes on
  insert. Lower-case ``x'0102ff'`` is accepted too; the upper-case spelling
  is what this dialect renders.
* ``CHAR(36) DEFAULT '550e8400-e29b-41d4-a716-446655440000'`` reads the
  hyphenated canonical text back verbatim -- MySQL has no UUID type, so the
  bare quoted text is the whole spelling.
* Every INTERVAL literal attempt is refused with errno 1064 (syntax error):
  ``SELECT INTERVAL 1 DAY`` and ``DEFAULT INTERVAL 1 DAY`` in each column
  shape tried. ``INTERVAL`` exists only as the keyword parameter of date
  arithmetic (``DATE_ADD('2026-10-17', INTERVAL 1 DAY)`` is accepted), so the
  base's explicit failure is the answer and this dialect defines no
  ``format_interval_value``.
* The tier-1 spellings the base renders are all accepted: ``DEFAULT TRUE``
  / ``DEFAULT FALSE`` / ``DEFAULT 42`` / ``DEFAULT 1.5`` / ``DEFAULT 1.25``
  / ``DEFAULT 'x''y'`` / ``DEFAULT '2026-10-17'`` / ``DEFAULT '10:30:00'``
  / ``DEFAULT '2026-10-17 10:00:00'`` each read back as the same value.
* Under the default ``sql_mode`` the backslash is an escape character
  (measured: the server reads ``'a\\b'`` as ``'a\\x08'``), which is why this
  dialect's ``_escape_sql_string`` doubles backslashes for every inline
  string tier-1 renders, and stops doubling under ``NO_BACKSLASH_ESCAPES``.

The live-server class at the bottom re-measures the tier-2 answers end to
end through a running server, on every scenario the suite reaches.
"""

import datetime
import decimal
import uuid

import pytest

from rhosocial.activerecord.backend.expression.values import (
    BinaryValue,
    BooleanValue,
    DateValue,
    DecimalValue,
    FloatValue,
    IntegerValue,
    IntervalValue,
    NullValue,
    StringValue,
    TimeValue,
    TimestampValue,
    UUIDValue,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


@pytest.fixture
def dialect():
    return MySQLDialect()


# -- the DDL-position lift ------------------------------------------------
#
# One class per kind, each declaring the strategy its position requires,
# exactly as core's own DdlLiteral does for Literal. The subclass adds no
# field and no kind: it only owns the position, which is the whole of the
# class-level inline strategy.

class DdlBinaryValue(BinaryValue):
    inline_params = True


class DdlUUIDValue(UUIDValue):
    inline_params = True


class DdlIntervalValue(IntervalValue):
    inline_params = True


class DdlNullValue(NullValue):
    inline_params = True


class DdlBooleanValue(BooleanValue):
    inline_params = True


class DdlIntegerValue(IntegerValue):
    inline_params = True


class DdlFloatValue(FloatValue):
    inline_params = True


class DdlDecimalValue(DecimalValue):
    inline_params = True


class DdlStringValue(StringValue):
    inline_params = True


class DdlDateValue(DateValue):
    inline_params = True


class DdlTimeValue(TimeValue):
    inline_params = True


class DdlTimestampValue(TimestampValue):
    inline_params = True


class TestBinaryValue:
    """``X'0102FF'`` -- the hex form from MySQL's literal grammar."""

    def test_data_position_binds_the_bytes(self, dialect):
        sql, params = BinaryValue(dialect, b"\x01\x02").to_sql()
        assert sql == "%s"
        assert params == (b"\x01\x02",)

    def test_ddl_position_spells_hex(self, dialect):
        sql, params = DdlBinaryValue(dialect, b"\x01\x02\xff").to_sql()
        assert sql == "X'0102FF'"
        assert params == ()

    def test_the_digits_are_uppercase(self, dialect):
        sql, _ = DdlBinaryValue(dialect, b"\xab\xcd\xef").to_sql()
        assert sql == "X'ABCDEF'"

    def test_an_empty_value_is_the_empty_literal(self, dialect):
        sql, _ = DdlBinaryValue(dialect, b"").to_sql()
        assert sql == "X''"

    def test_bytearray_is_normalised_before_rendering(self, dialect):
        sql, _ = DdlBinaryValue(dialect, bytearray(b"\x01")).to_sql()
        assert sql == "X'01'"


class TestUUIDValue:
    """The bare quoted canonical text -- all MySQL has is a text home."""

    CANONICAL = "c73d9175-0a1d-48c6-8d30-df165461328b"

    def test_data_position_binds_the_uuid(self, dialect):
        value = uuid.UUID(self.CANONICAL)
        sql, params = UUIDValue(dialect, value).to_sql()
        assert sql == "%s"
        assert params == (value,)

    def test_ddl_position_is_the_quoted_canonical_text(self, dialect):
        sql, params = DdlUUIDValue(dialect, uuid.UUID(self.CANONICAL)).to_sql()
        assert sql == f"'{self.CANONICAL}'"
        assert params == ()


class TestIntervalValueStaysRefused:
    """No ``format_interval_value`` on this dialect, on purpose.

    MySQL refuses every interval literal shape with errno 1064 (measured,
    see the module docstring): ``INTERVAL`` is the keyword parameter of date
    arithmetic, never a value with a literal form. The base's explicit
    failure is the answer, and the structural absence is asserted rather
    than papered over.
    """

    def test_data_position_still_binds(self, dialect):
        span = datetime.timedelta(days=2, hours=3)
        sql, params = IntervalValue(dialect, span).to_sql()
        assert sql == "%s"
        assert params == (span,)

    def test_ddl_position_keeps_the_base_refusal(self, dialect):
        with pytest.raises(NotImplementedError, match="INTERVAL literals"):
            DdlIntervalValue(dialect, datetime.timedelta(days=1)).to_sql()


class TestTierOneAgreesWithTheBase:
    """The audit: nothing overridden for the kinds MySQL spells like core.

    Each assertion is the base's spelling reached through this dialect's
    ``format_literal`` (so MySQL's escaping applies), pinned here so a base
    change that breaks MySQL's grammar is caught by this file rather than in
    the matrix, where the row would only say "renders".
    """

    def test_null_binds_then_renders_as_the_keyword(self, dialect):
        assert NullValue(dialect).to_sql() == ("%s", (None,))
        assert DdlNullValue(dialect).to_sql() == ("NULL", ())

    def test_booleans_render_as_keywords(self, dialect):
        assert DdlBooleanValue(dialect, True).to_sql() == ("TRUE", ())
        assert DdlBooleanValue(dialect, False).to_sql() == ("FALSE", ())

    def test_integers_render_as_numeric_text(self, dialect):
        assert DdlIntegerValue(dialect, 18).to_sql() == ("18", ())
        assert DdlIntegerValue(dialect, -7).to_sql() == ("-7", ())

    def test_floats_render_as_their_repr(self, dialect):
        assert DdlFloatValue(dialect, 0.5).to_sql() == ("0.5", ())
        assert DdlFloatValue(dialect, 15e-03).to_sql() == ("0.015", ())

    def test_decimals_render_exact(self, dialect):
        value = decimal.Decimal("12.34")
        assert DdlDecimalValue(dialect, value).to_sql() == ("12.34", ())

    def test_strings_double_the_quotes(self, dialect):
        sql, _ = DdlStringValue(dialect, "today's").to_sql()
        assert sql == "'today''s'"

    def test_strings_double_the_backslash_under_the_default_sql_mode(self, dialect):
        # The server reads a single backslash as an escape (measured:
        # 'a\b' comes back as 'a\x08'), so the dialect doubles backslashes
        # under the default mode for the literal to mean what the host holds.
        sql, _ = DdlStringValue(dialect, "a\\b").to_sql()
        assert sql == "'a\\\\b'"

    def test_strings_keep_the_backslash_under_no_backslash_escapes(self):
        dialect = MySQLDialect(sql_mode="NO_BACKSLASH_ESCAPES,STRICT_TRANS_TABLES")
        sql, _ = DdlStringValue(dialect, "a\\b").to_sql()
        assert sql == "'a\\b'"

    def test_dates_render_as_quoted_iso(self, dialect):
        sql, _ = DdlDateValue(dialect, datetime.date(2026, 10, 17)).to_sql()
        assert sql == "'2026-10-17'"

    def test_times_render_as_quoted_iso(self, dialect):
        sql, _ = DdlTimeValue(dialect, datetime.time(10, 3, 56)).to_sql()
        assert sql == "'10:03:56'"

    def test_timestamps_render_as_quoted_iso_with_a_space_separator(self, dialect):
        sql, _ = DdlTimestampValue(
            dialect, datetime.datetime(2024, 8, 15, 10, 59, 43)
        ).to_sql()
        assert sql == "'2024-08-15 10:59:43'"


class TestMROOrder:
    """The composed order is what resolves the two overrides."""

    def test_the_local_mixin_wins_over_the_base(self, dialect):
        assert dialect.format_binary_value.__func__.__qualname__.startswith(
            "MySQLTypedValueMixin"
        )
        assert dialect.format_uuid_value.__func__.__qualname__.startswith(
            "MySQLTypedValueMixin"
        )

    def test_the_base_answers_the_kinds_the_local_mixin_leaves_alone(self, dialect):
        assert dialect.format_null_value.__func__.__qualname__.startswith(
            "TypedValueMixin"
        )
        assert dialect.format_interval_value.__func__.__qualname__.startswith(
            "TypedValueMixin"
        )


class TestLiveServerReadsTheLiteralsBack:
    """The tier-2 answers re-measured end to end against the running server.

    The DDL read-back goes over raw SQL on purpose: the literal forms are
    this dialect's own product, and the expression layer has no
    DDL-strategy binary/UUID value class to build a ``DEFAULT`` tree from
    yet (core's own lift, ``DdlLiteral``, covers ``Literal`` only). What is
    verified here is what the wave's answers claim: the server accepts the
    spelling and hands the same value back.
    """

    def test_binary_default_roundtrips(self, mysql_backend):
        mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_bin")
        try:
            mysql_backend.execute(
                "CREATE TABLE ar_mysql_typed_bin (v VARBINARY(16) DEFAULT X'0102FF')"
            )
            mysql_backend.execute("INSERT INTO ar_mysql_typed_bin () VALUES ()")
            rows = mysql_backend.fetch_all("SELECT v FROM ar_mysql_typed_bin")
            assert [row["v"] for row in rows] == [b"\x01\x02\xff"]
        finally:
            mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_bin")

    def test_uuid_default_roundtrips(self, mysql_backend):
        canonical = "550e8400-e29b-41d4-a716-446655440000"
        mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_uuid")
        try:
            mysql_backend.execute(
                f"CREATE TABLE ar_mysql_typed_uuid (v CHAR(36) DEFAULT '{canonical}')"
            )
            mysql_backend.execute("INSERT INTO ar_mysql_typed_uuid () VALUES ()")
            rows = mysql_backend.fetch_all("SELECT v FROM ar_mysql_typed_uuid")
            assert [row["v"] for row in rows] == [canonical]
        finally:
            mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_uuid")

    def test_interval_default_is_refused(self, mysql_backend):
        mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_iv")
        try:
            with pytest.raises(Exception):  # noqa: B017 - the refusal is the point
                mysql_backend.execute(
                    "CREATE TABLE ar_mysql_typed_iv (v VARCHAR(10) DEFAULT INTERVAL 1 DAY)"
                )
        finally:
            mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_iv")

    def test_tier_one_defaults_are_accepted(self, mysql_backend):
        mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_t1")
        try:
            mysql_backend.execute(
                "CREATE TABLE ar_mysql_typed_t1 ("
                " b TINYINT DEFAULT TRUE,"
                " n TINYINT DEFAULT 42,"
                " f DOUBLE DEFAULT 1.5,"
                " s VARCHAR(16) DEFAULT 'x''y',"
                " d DATE DEFAULT '2026-10-17',"
                " ts DATETIME DEFAULT '2026-10-17 10:00:00'"
                ")"
            )
            mysql_backend.execute("INSERT INTO ar_mysql_typed_t1 () VALUES ()")
            rows = mysql_backend.fetch_all("SELECT * FROM ar_mysql_typed_t1")
            assert len(rows) == 1
        finally:
            mysql_backend.execute("DROP TABLE IF EXISTS ar_mysql_typed_t1")
