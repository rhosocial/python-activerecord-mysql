# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/functions/test_seconds_between_live.py
"""The live half of the ``seconds_between`` verification, on MySQL itself.

The rendering assertions -- the SQL text, the bind order and the alias -- stay
in ``test_mysql_seconds_between.py`` and start no connection. What is measured
here is what the server actually returns for the two cases the node exists for:
a signed interval and a fractional one.

Like the rest of the scenario-driven suite, this file needs a configured MySQL
server; with no scenario it is skipped rather than failed.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    QueryStatement,
    seconds_between,
)


def _elapsed(backend, start: str, end: str) -> float:
    """Run ``seconds_between(start, end)`` against the server."""
    dialect = backend.dialect
    expr = seconds_between(dialect, Literal(dialect, start), Literal(dialect, end))
    query = QueryStatement(dialect, select=[expr.as_("seconds")])
    sql, params = query.to_sql()
    rows = backend.fetch_all(sql, params)
    return float(rows[0]["seconds"])


class TestLiveSecondsBetween:
    """The value MySQL's ``TIMESTAMPDIFF(MICROSECOND, ...) / 1000000`` produces."""

    @pytest.mark.parametrize(
        "start,end,expected",
        [
            ("2026-06-04 10:00:00", "2026-06-04 10:00:00", 0.0),
            ("2026-06-04 10:00:00", "2026-06-04 11:00:00", 3600.0),
            ("2026-06-04 11:00:00", "2026-06-04 10:00:00", -3600.0),
            ("2026-01-31 23:59:59", "2026-02-01 00:00:00", 1.0),
            ("2025-12-31 12:00:00", "2026-01-01 12:00:00", 86400.0),
            ("2026-06-04 10:00:00.000000", "2026-06-04 10:00:00.500000", 0.5),
            ("2026-06-04 10:00:00.250000", "2026-06-04 10:00:00.000000", -0.25),
        ],
    )
    def test_interval(self, mysql_backend_single, start: str, end: str, expected: float):
        # The dialect divides by the literal 1000000, so MySQL's decimal
        # division keeps at least four fractional digits.
        assert _elapsed(mysql_backend_single, start, end) == pytest.approx(expected, abs=1e-4)

    def test_columns_in_a_row(self, mysql_backend_single):
        """The same question asked of two columns, not two literals."""
        backend = mysql_backend_single
        backend.execute("DROP TABLE IF EXISTS ar_mysql_seconds_between")
        try:
            backend.execute(
                "CREATE TABLE ar_mysql_seconds_between ("
                " id INT PRIMARY KEY,"
                " started_at DATETIME(6),"
                " ended_at DATETIME(6))"
            )
            backend.execute(
                "INSERT INTO ar_mysql_seconds_between VALUES "
                "(1, '2026-03-01 00:00:00', '2026-03-02 00:00:00'),"
                "(2, '2026-03-02 00:00:00', '2026-03-01 00:00:00'),"
                "(3, '2026-03-01 00:00:00.750000', '2026-03-01 00:00:01.000000')"
            )

            dialect = backend.dialect
            expr = seconds_between(
                dialect,
                Column(dialect, "started_at"),
                Column(dialect, "ended_at"),
            )
            query = QueryStatement(
                dialect,
                select=[expr.as_("seconds"), Column(dialect, "id")],
                from_="ar_mysql_seconds_between",
            )
            sql, params = query.to_sql()
            rows = {row["id"]: float(row["seconds"]) for row in backend.fetch_all(sql, params)}

            assert rows[1] == pytest.approx(86400.0, abs=1e-4)
            assert rows[2] == pytest.approx(-86400.0, abs=1e-4)
            assert rows[3] == pytest.approx(0.25, abs=1e-4)
        finally:
            backend.execute("DROP TABLE IF EXISTS ar_mysql_seconds_between")
