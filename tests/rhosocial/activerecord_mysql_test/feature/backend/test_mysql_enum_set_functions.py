# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_enum_set_functions.py
"""
Tests for MySQL-specific SET and Enum function factories.

Functions: find_in_set, elt, field

`find_in_set`'s searched value and `elt`'s index and values are plain Python
values and are always sent as bound parameters. Everything `field` takes is an
expression: a `Column` to read a column, a `Literal` to write a value.

The two tests that end in `_on_server` exist because the old factory decided at
run time whether a bare string was a column name or data, and both answers were
wrong without raising: `FIELD("b", "a", "b")` read columns `a` and `b` and
reported where their *contents* sat, and `FIND_IN_SET("mysql", "a,b,c")` looked
for a column called `a,b,c`.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal, core
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.functions.enum_set import (
    find_in_set,
    elt,
    field,
)


class TestMySQLEnumSetFunctions:
    """Render tests for the SET and Enum factories."""

    def test_find_in_set_column(self, mysql_dialect: MySQLDialect):
        """find_in_set() reads a SET column and sends the value as a parameter."""
        sql, params = find_in_set(mysql_dialect, "mysql", Column(mysql_dialect, "tags")).to_sql()
        assert "FIND_IN_SET(" in sql
        assert "`tags`" in sql
        assert params == ("mysql",)

    def test_find_in_set_set_as_data(self, mysql_dialect: MySQLDialect):
        """A SET written as data is a Literal, not a column named after it."""
        sql, params = find_in_set(
            mysql_dialect, "mysql", Literal(mysql_dialect, "a,b,c")
        ).to_sql()
        assert "FIND_IN_SET(" in sql
        assert "`a,b,c`" not in sql
        assert params == ("mysql", "a,b,c")

    def test_find_in_set_expression_column(self, mysql_dialect: MySQLDialect):
        """The SET side may be any expression, not only a column."""
        greatest = core.FunctionCall(
            mysql_dialect,
            "GREATEST",
            Column(mysql_dialect, "x"),
            Column(mysql_dialect, "y"),
        )
        sql, params = find_in_set(mysql_dialect, "a", greatest).to_sql()
        assert "FIND_IN_SET(" in sql
        assert "GREATEST(`x`, `y`)" in sql

    def test_elt_single_value(self, mysql_dialect: MySQLDialect):
        """elt() sends the index and the values as parameters."""
        sql, params = elt(mysql_dialect, 1, "a").to_sql()
        assert "ELT(" in sql
        assert params == (1, "a")

    def test_elt_many_values(self, mysql_dialect: MySQLDialect):
        """elt() with several values."""
        sql, params = elt(mysql_dialect, 2, "a", "b", "c").to_sql()
        assert "ELT(" in sql
        assert params == (2, "a", "b", "c")

    def test_field_data(self, mysql_dialect: MySQLDialect):
        """field() over data is all bound parameters."""
        sql, params = field(
            mysql_dialect,
            Literal(mysql_dialect, "b"),
            Literal(mysql_dialect, "a"),
            Literal(mysql_dialect, "b"),
        ).to_sql()
        assert sql.startswith("FIELD(")
        assert "`" not in sql
        assert params == ("b", "a", "b")

    def test_field_column_needle(self, mysql_dialect: MySQLDialect):
        """The needle may be a column while the list stays data."""
        sql, params = field(
            mysql_dialect,
            Column(mysql_dialect, "status"),
            Literal(mysql_dialect, "new"),
            Literal(mysql_dialect, "old"),
        ).to_sql()
        assert "FIELD(" in sql
        assert "`status`" in sql
        assert params == ("new", "old")

    def test_field_all_columns(self, mysql_dialect: MySQLDialect):
        """Every argument may be a column."""
        sql, params = field(
            mysql_dialect,
            Column(mysql_dialect, "a"),
            Column(mysql_dialect, "b"),
        ).to_sql()
        assert "FIELD(`a`, `b`)" in sql
        assert params == ()

    def test_field_single_argument(self, mysql_dialect: MySQLDialect):
        """field() passes whatever it is given straight to the function."""
        sql, params = field(mysql_dialect, Literal(mysql_dialect, "b")).to_sql()
        assert sql == "FIELD(%s)"
        assert params == ("b",)

    def test_bare_string_is_rejected_not_guessed(self, mysql_dialect: MySQLDialect):
        """A bare string used to become a column reference, silently.

        `field(dialect, "b", "a", "b")` used to render ``FIELD(`b`, `a`, `b`)`` and
        so compared the contents of columns `b` against the contents of columns
        `a` and `b`. The factory no longer decides what an argument meant, so a
        value that is not an expression fails to render instead.
        """
        with pytest.raises(AttributeError):
            field(mysql_dialect, "b", "a", "b").to_sql()


class TestMySQLEnumSetFunctionsOnServer:
    """Execution tests: rendering is not validation."""

    def test_field_over_data_on_server(self, mysql_backend):
        """FIELD over data reports the position in the list, not in a table.

        `a` and `b` below deliberately hold the same value, which is where the
        old column reading returned 1 where the answer is 2.
        """
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_field_expr (
                id INT PRIMARY KEY,
                a VARCHAR(16) NOT NULL,
                b VARCHAR(16) NOT NULL
            )
        """)
        mysql_backend.execute(
            "INSERT INTO test_field_expr (id, a, b) VALUES (1, 'mysql', 'mysql')"
        )
        try:
            sql, params = field(
                mysql_backend.dialect,
                Literal(mysql_backend.dialect, "b"),
                Literal(mysql_backend.dialect, "a"),
                Literal(mysql_backend.dialect, "b"),
            ).to_sql()
            result = mysql_backend.execute(f"SELECT {sql} AS pos FROM test_field_expr", params)
            assert result.data[0]["pos"] == 2
        finally:
            mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_field_expr")

    def test_find_in_set_data_on_server(self, mysql_backend):
        """FIND_IN_SET over a set written as data."""
        mysql_backend.execute("""
            CREATE TEMPORARY TABLE test_fis_expr (
                id INT PRIMARY KEY,
                tags SET('a', 'b', 'c') NOT NULL
            )
        """)
        mysql_backend.execute(
            "INSERT INTO test_fis_expr (id, tags) VALUES (1, 'b,c')"
        )
        try:
            sql, params = find_in_set(
                mysql_backend.dialect,
                "c",
                Literal(mysql_backend.dialect, "a,b,c"),
            ).to_sql()
            result = mysql_backend.execute(
                f"SELECT {sql} AS pos FROM test_fis_expr", params
            )
            assert result.data[0]["pos"] == 3
        finally:
            mysql_backend.execute("DROP TEMPORARY TABLE IF EXISTS test_fis_expr")
