# tests/rhosocial/activerecord_mysql_test/feature/backend/expression/test_mysql_literal_values.py
"""MySQL's spellings for the value literals -- construction and rendering only.

Core's one literal node owns the binding decision: ``Literal(d, value)``
binds the host value behind a placeholder, and ``Literal(d, value,
inline=True)`` -- what a DDL syntax position passes, the one that accepts
no bind parameters -- writes the value as SQL text through the dialect's
controlled literal construction. MySQL's own spellings live in the second
tier of that construction, ``MySQLLiteralValueMixin.format_literal``, and
everything else falls through to the base.

Every literal form asserted here was measured, not transcribed. Measured
on 8.0.46 (scenario ``mysql_80``, 192.168.1.3:14682) and on the server
behind scenario ``mysql_97`` (192.168.1.3:14686, which answers
``SELECT VERSION()`` with ``26.7.0``):

* ``SELECT X'0102FF'`` returns ``b'\\x01\\x02\\xff'``; a
  ``VARBINARY(16) DEFAULT X'0102FF'`` fills the column with those bytes on
  insert. Lower-case ``x'0102ff'`` is accepted too; the upper-case spelling
  is what this dialect renders.
* ``CHAR(36) DEFAULT '550e8400-e29b-41d4-a716-446655440000'`` reads the
  hyphenated canonical text back verbatim -- MySQL has no UUID type, so
  the bare quoted text is the whole spelling.
* Every INTERVAL literal attempt is refused with errno 1064 (syntax
  error): ``SELECT INTERVAL 1 DAY`` and ``DEFAULT INTERVAL 1 DAY`` in each
  column shape tried. ``INTERVAL`` exists only as the keyword parameter of
  date arithmetic, so a ``timedelta`` has no branch in this dialect's
  ``format_literal`` and the base's explicit ``TypeError`` is the answer.
* The tier-1 spellings the base renders are all accepted: ``DEFAULT TRUE``
  / ``DEFAULT FALSE`` / ``DEFAULT 42`` / ``DEFAULT 1.5`` / ``DEFAULT 1.25``
  / ``DEFAULT 'x''y'`` / ``DEFAULT '2026-10-17'`` / ``DEFAULT '10:30:00'``
  / ``DEFAULT '2026-10-17 10:00:00'`` each read back as the same value.
* Under the default ``sql_mode`` the backslash is an escape character
  (measured: the server reads ``'a\\b'`` as ``'a\\x08'``), which is why this
  dialect's ``escape_sql_string`` doubles backslashes for every inline
  string tier-1 renders, and stops doubling under ``NO_BACKSLASH_ESCAPES``.

The measurements are re-measured end to end against a running server by
``../test_mysql_literal_values_live.py``: an expression test starts no
connection and asserts what this dialect renders (§12), and the re-measurement
needs a server, so it lives with the scenario-driven tests.
"""

import datetime
import decimal
import uuid

import pytest

from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


@pytest.fixture
def dialect():
    return MySQLDialect()


class TestBinarySpelling:
    """``X'0102FF'`` -- the hex form from MySQL's literal grammar."""

    def test_data_position_binds_the_bytes(self, dialect):
        sql, params = Literal(dialect, b"\x01\x02").to_sql()
        assert sql == "%s"
        assert params == (b"\x01\x02",)

    def test_inline_position_spells_hex(self, dialect):
        sql, params = Literal(dialect, b"\x01\x02\xff", inline=True).to_sql()
        assert sql == "X'0102FF'"
        assert params == ()

    def test_the_digits_are_uppercase(self, dialect):
        sql, _ = Literal(dialect, b"\xab\xcd\xef", inline=True).to_sql()
        assert sql == "X'ABCDEF'"

    def test_an_empty_value_is_the_empty_literal(self, dialect):
        sql, _ = Literal(dialect, b"", inline=True).to_sql()
        assert sql == "X''"

    def test_bytearray_is_spelled_from_the_bytes_it_holds(self, dialect):
        sql, _ = Literal(dialect, bytearray(b"\x01"), inline=True).to_sql()
        assert sql == "X'01'"


class TestUUIDSpelling:
    """The bare quoted canonical text -- all MySQL has is a text home."""

    CANONICAL = "c73d9175-0a1d-48c6-8d30-df165461328b"

    def test_data_position_binds_the_uuid(self, dialect):
        value = uuid.UUID(self.CANONICAL)
        sql, params = Literal(dialect, value).to_sql()
        assert sql == "%s"
        assert params == (value,)

    def test_inline_position_is_the_quoted_canonical_text(self, dialect):
        sql, params = Literal(dialect, uuid.UUID(self.CANONICAL), inline=True).to_sql()
        assert sql == f"'{self.CANONICAL}'"
        assert params == ()


class TestIntervalStaysRefused:
    """No ``timedelta`` branch in this dialect's ``format_literal``, on purpose.

    MySQL refuses every interval literal shape with errno 1064 (measured,
    see the module docstring): ``INTERVAL`` is the keyword parameter of
    date arithmetic, never a value with a literal form. The base's explicit
    ``TypeError`` is the answer, and the structural absence is asserted
    rather than papered over.
    """

    def test_data_position_still_binds(self, dialect):
        span = datetime.timedelta(days=2, hours=3)
        sql, params = Literal(dialect, span).to_sql()
        assert sql == "%s"
        assert params == (span,)

    def test_inline_position_keeps_the_base_refusal(self, dialect):
        with pytest.raises(TypeError, match="has no inline SQL literal form"):
            Literal(dialect, datetime.timedelta(days=1), inline=True).to_sql()


class TestTierOneAgreesWithTheBase:
    """The audit: nothing overridden for the kinds MySQL spells like core.

    Each assertion is the base's spelling reached through this dialect's
    ``format_literal`` (so MySQL's escaping applies), pinned here so a base
    change that breaks MySQL's grammar is caught by this file rather than
    in the matrix, where the row would only say "renders".
    """

    def test_null_binds_then_renders_as_the_keyword(self, dialect):
        assert Literal(dialect, None).to_sql() == ("%s", (None,))
        assert Literal(dialect, None, inline=True).to_sql() == ("NULL", ())

    def test_booleans_render_as_keywords(self, dialect):
        assert Literal(dialect, True, inline=True).to_sql() == ("TRUE", ())
        assert Literal(dialect, False, inline=True).to_sql() == ("FALSE", ())

    def test_integers_render_as_numeric_text(self, dialect):
        assert Literal(dialect, 18, inline=True).to_sql() == ("18", ())
        assert Literal(dialect, -7, inline=True).to_sql() == ("-7", ())

    def test_floats_render_as_their_repr(self, dialect):
        assert Literal(dialect, 0.5, inline=True).to_sql() == ("0.5", ())
        assert Literal(dialect, 15e-03, inline=True).to_sql() == ("0.015", ())

    def test_decimals_render_exact(self, dialect):
        value = decimal.Decimal("12.34")
        assert Literal(dialect, value, inline=True).to_sql() == ("12.34", ())

    def test_strings_double_the_quotes(self, dialect):
        sql, _ = Literal(dialect, "today's", inline=True).to_sql()
        assert sql == "'today''s'"

    def test_strings_double_the_backslash_under_the_default_sql_mode(self, dialect):
        # The server reads a single backslash as an escape (measured:
        # 'a\b' comes back as 'a\x08'), so the dialect doubles backslashes
        # under the default mode for the literal to mean what the host holds.
        sql, _ = Literal(dialect, "a\\b", inline=True).to_sql()
        assert sql == "'a\\\\b'"

    def test_strings_keep_the_backslash_under_no_backslash_escapes(self):
        dialect = MySQLDialect(sql_mode="NO_BACKSLASH_ESCAPES,STRICT_TRANS_TABLES")
        sql, _ = Literal(dialect, "a\\b", inline=True).to_sql()
        assert sql == "'a\\b'"

    def test_dates_render_as_quoted_iso(self, dialect):
        sql, _ = Literal(dialect, datetime.date(2026, 10, 17), inline=True).to_sql()
        assert sql == "'2026-10-17'"

    def test_times_render_as_quoted_iso(self, dialect):
        sql, _ = Literal(dialect, datetime.time(10, 3, 56), inline=True).to_sql()
        assert sql == "'10:03:56'"

    def test_datetimes_render_as_quoted_iso_with_a_space_separator(self, dialect):
        sql, _ = Literal(
            dialect, datetime.datetime(2024, 8, 15, 10, 59, 43), inline=True
        ).to_sql()
        assert sql == "'2024-08-15 10:59:43'"


class TestMROOrder:
    """The composed order is what resolves the tier-2 spellings."""

    def test_the_local_mixin_wins_over_the_base(self, dialect):
        assert dialect.format_literal.__func__.__qualname__.startswith(
            "MySQLLiteralValueMixin"
        )

    def test_inline_literals_route_through_the_local_mixin(self, dialect):
        # format_literal_expression hands inline=True literals to
        # format_literal, so the MRO test and the rendering test agree.
        sql, _ = Literal(dialect, b"\x01", inline=True).to_sql()
        assert sql == "X'01'"
