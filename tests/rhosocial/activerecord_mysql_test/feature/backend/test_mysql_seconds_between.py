# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_seconds_between.py
"""The MySQL spelling of signed, fractional seconds between two instants.

``seconds_between`` asks one question -- ``end - start`` in seconds -- and the
MySQL dialect answers it with ``TIMESTAMPDIFF(MICROSECOND, ...) / 1000000``.
These tests pin the rendered SQL, the bind order and the alias; the values a
server hands back are measured in the live half beside this file.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    QueryStatement,
    seconds_between,
)
from rhosocial.activerecord.backend.expression.functions import date_diff
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


class TestMySQLSecondsBetweenRendering:
    """What the MySQL dialect writes, and in which order it binds."""

    def test_columns_render_timestampdiff_microsecond(self, mysql_dialect: MySQLDialect):
        expr = seconds_between(
            mysql_dialect,
            Column(mysql_dialect, "queued_at"),
            Column(mysql_dialect, "started_at"),
        )

        sql, params = expr.to_sql()

        assert sql == "(TIMESTAMPDIFF(MICROSECOND, `queued_at`, `started_at`) / 1000000)"
        assert params == ()

    def test_literal_bind_order_follows_sql(self, mysql_dialect: MySQLDialect):
        """``start`` is written first, so its parameter binds first."""
        expr = seconds_between(
            mysql_dialect,
            Literal(mysql_dialect, "2026-06-04 10:00:00"),
            Literal(mysql_dialect, "2026-06-04 11:00:00"),
        )

        sql, params = expr.to_sql()

        assert sql == "(TIMESTAMPDIFF(MICROSECOND, %s, %s) / 1000000)"
        assert params == ("2026-06-04 10:00:00", "2026-06-04 11:00:00")

    def test_alias_is_applied_after_the_parenthesised_expression(
        self, mysql_dialect: MySQLDialect
    ):
        expr = seconds_between(
            mysql_dialect,
            Column(mysql_dialect, "queued_at"),
            Column(mysql_dialect, "started_at"),
        ).as_("queue_seconds")

        sql, params = expr.to_sql()

        assert sql == (
            "(TIMESTAMPDIFF(MICROSECOND, `queued_at`, `started_at`) / 1000000) "
            "AS `queue_seconds`"
        )
        assert params == ()

    def test_end_before_start_keeps_its_own_operand_position(
        self, mysql_dialect: MySQLDialect
    ):
        """The sign is the operand difference; swapping the arguments swaps it.

        The dialect does not reorder the operands or negate the result, so a
        negative answer comes from MySQL's own ``end - start`` arithmetic.
        """
        forward = seconds_between(
            mysql_dialect,
            Literal(mysql_dialect, "2026-06-04 10:00:00"),
            Literal(mysql_dialect, "2026-06-04 11:00:00"),
        )
        backward = seconds_between(
            mysql_dialect,
            Literal(mysql_dialect, "2026-06-04 11:00:00"),
            Literal(mysql_dialect, "2026-06-04 10:00:00"),
        )

        assert forward.to_sql()[1] == ("2026-06-04 10:00:00", "2026-06-04 11:00:00")
        assert backward.to_sql()[1] == ("2026-06-04 11:00:00", "2026-06-04 10:00:00")

    def test_microsecond_count_is_divided_not_integer_division(
        self, mysql_dialect: MySQLDialect
    ):
        """A sub-second interval must not be rounded away.

        The divisor is the literal ``1000000`` and the operator is ``/``: on
        MySQL that yields a decimal, so a microsecond count keeps its fraction
        instead of being truncated to whole seconds.
        """
        expr = seconds_between(
            mysql_dialect,
            Column(mysql_dialect, "queued_at"),
            Column(mysql_dialect, "started_at"),
        )

        sql, _ = expr.to_sql()

        assert "MICROSECOND" in sql
        assert "/ 1000000" in sql
        assert "DIV" not in sql
        assert "CAST" not in sql

    def test_query_integration_keeps_the_alias(self, mysql_dialect: MySQLDialect):
        expr = seconds_between(
            mysql_dialect,
            Column(mysql_dialect, "queued_at"),
            Column(mysql_dialect, "started_at"),
        ).as_("queue_seconds")
        query = QueryStatement(
            mysql_dialect,
            select=[expr, Column(mysql_dialect, "id")],
            from_="attempts",
        )

        sql, params = query.to_sql()

        assert sql == (
            "SELECT (TIMESTAMPDIFF(MICROSECOND, `queued_at`, `started_at`) / 1000000) "
            "AS `queue_seconds`, `id` FROM `attempts`"
        )
        assert params == ()


class TestMySQLSecondsBetweenRefusesOtherUnits:
    """``seconds_between`` is not ``date_diff``; whole-unit spellings stay there."""

    @pytest.mark.parametrize("unit", ["year", "month", "week", "day", "hour", "minute"])
    def test_date_diff_still_counts_whole_units(self, mysql_dialect: MySQLDialect, unit: str):
        expr = date_diff(
            mysql_dialect,
            unit,
            Column(mysql_dialect, "queued_at"),
            Column(mysql_dialect, "started_at"),
        )

        sql, _ = expr.to_sql()

        assert sql == f"TIMESTAMPDIFF({unit.upper()}, `queued_at`, `started_at`)"
