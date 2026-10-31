# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_literal_values_live.py
"""The live half of the literal-spelling verification.

The tier-2 answers this wave recorded -- ``X'0102FF'`` for binary, the bare
quoted canonical text for a UUID, no literal form at all for an INTERVAL --
are claims about what a server accepts and hands back. Asserting them needs a
running server, so they live here, in the scenario-driven part of the suite,
and not in the expression tests beside them: an expression test starts no
connection, builds a tree and checks what the dialect renders (§12). What is
verified here is the round trip through MySQL itself, on every scenario the
suite reaches.

The rendering assertions -- the half that needs no connection -- stay in
``expression/test_mysql_literal_values.py``.
"""

import pytest


class TestLiveServerReadsTheLiteralsBack:
    """The tier-2 answers re-measured end to end against the running server.

    The DDL read-back goes over raw SQL on purpose: the literal forms are
    this dialect's own product, and what is verified here is what the
    wave's answers claim -- the server accepts the spelling and hands the
    same value back.
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