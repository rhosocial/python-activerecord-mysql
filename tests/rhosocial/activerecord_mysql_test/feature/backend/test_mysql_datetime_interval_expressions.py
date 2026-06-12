# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_datetime_interval_expressions.py
"""Tests for MySQL datetime interval expressions."""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal, QueryExpression
from rhosocial.activerecord.backend.expression.functions import (
    date_add,
    date_diff,
    date_part,
    date_sub,
    date_trunc,
    extract,
    interval,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


class TestMySQLDateTimeIntervalExpressions:
    @pytest.mark.parametrize(
        "field",
        ["year", "month", "day", "hour", "minute", "second"],
    )
    def test_extract_datetime_fields(self, mysql_dialect: MySQLDialect, field: str):
        expr = extract(mysql_dialect, field, Column(mysql_dialect, "created_at"))

        sql, params = expr.to_sql()

        assert sql == f"EXTRACT({field.upper()} FROM `created_at`)"
        assert params == ()

    def test_date_part_uses_extract_mapping(self, mysql_dialect: MySQLDialect):
        expr = date_part(mysql_dialect, "day", Column(mysql_dialect, "created_at"))

        sql, params = expr.to_sql()

        assert sql == "EXTRACT(DAY FROM `created_at`)"
        assert params == ()

    @pytest.mark.parametrize(
        "field,fmt",
        [
            ("year", "%Y-01-01 00:00:00"),
            ("month", "%Y-%m-01 00:00:00"),
            ("day", "%Y-%m-%d 00:00:00"),
            ("hour", "%Y-%m-%d %H:00:00"),
            ("minute", "%Y-%m-%d %H:%i:00"),
            ("second", "%Y-%m-%d %H:%i:%s"),
        ],
    )
    def test_date_trunc_datetime_fields(self, mysql_dialect: MySQLDialect, field: str, fmt: str):
        expr = date_trunc(mysql_dialect, field, Column(mysql_dialect, "created_at"))

        sql, params = expr.to_sql()

        assert sql == "CAST(DATE_FORMAT(`created_at`, %s) AS DATETIME)"
        assert params == (fmt,)

    def test_date_trunc_week_is_unsupported(self, mysql_dialect: MySQLDialect):
        expr = date_trunc(mysql_dialect, "week", Column(mysql_dialect, "created_at"))

        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_interval_expression(self, mysql_dialect: MySQLDialect):
        expr = interval(mysql_dialect, 2, "hour")

        sql, params = expr.to_sql()

        assert sql == "INTERVAL %s HOUR"
        assert params == (2,)

    def test_date_add_column_source(self, mysql_dialect: MySQLDialect):
        expr = date_add(mysql_dialect, Column(mysql_dialect, "created_at"), 1, "day")

        sql, params = expr.to_sql()

        assert sql == "DATE_ADD(`created_at`, INTERVAL %s DAY)"
        assert params == (1,)

    def test_date_sub_interval_expression(self, mysql_dialect: MySQLDialect):
        expr = date_sub(
            mysql_dialect,
            Column(mysql_dialect, "created_at"),
            interval(mysql_dialect, 2, "hour"),
        )

        sql, params = expr.to_sql()

        assert sql == "DATE_SUB(`created_at`, INTERVAL %s HOUR)"
        assert params == (2,)

    def test_date_add_literal_source_params_order(self, mysql_dialect: MySQLDialect):
        expr = date_add(
            mysql_dialect,
            Literal(mysql_dialect, "2026-06-04 10:00:00"),
            30,
            "minute",
        )

        sql, params = expr.to_sql()

        assert sql == "DATE_ADD(%s, INTERVAL %s MINUTE)"
        assert params == ("2026-06-04 10:00:00", 30)

    @pytest.mark.parametrize(
        "unit",
        ["year", "month", "week", "day", "hour", "minute", "second"],
    )
    def test_date_diff_supported_units(self, mysql_dialect: MySQLDialect, unit: str):
        expr = date_diff(
            mysql_dialect,
            unit,
            Column(mysql_dialect, "started_at"),
            Column(mysql_dialect, "ended_at"),
        )

        sql, params = expr.to_sql()

        assert sql == f"TIMESTAMPDIFF({unit.upper()}, `started_at`, `ended_at`)"
        assert params == ()

    def test_alias_and_cast(self, mysql_dialect: MySQLDialect):
        expr = (
            date_diff(
                mysql_dialect,
                "day",
                Column(mysql_dialect, "started_at"),
                Column(mysql_dialect, "ended_at"),
            )
            .cast("SIGNED")
            .as_("elapsed_days")
        )

        sql, params = expr.to_sql()

        assert sql == ("CAST(TIMESTAMPDIFF(DAY, `started_at`, `ended_at`) AS SIGNED) AS `elapsed_days`")
        assert params == ()

    def test_query_expression_integration(self, mysql_dialect: MySQLDialect):
        shifted = date_add(mysql_dialect, Column(mysql_dialect, "created_at"), 1, "day")
        query = QueryExpression(
            mysql_dialect,
            select=[extract(mysql_dialect, "year", Column(mysql_dialect, "created_at"))],
            from_="events",
            where=shifted > Literal(mysql_dialect, "2026-01-01"),
        )

        sql, params = query.to_sql()

        assert "EXTRACT(YEAR FROM `created_at`)" in sql
        assert "DATE_ADD(`created_at`, INTERVAL %s DAY) > %s" in sql
        assert params == (1, "2026-01-01")
