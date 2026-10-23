# tests/rhosocial/activerecord_mysql_test/feature/backend/expression/test_mysql_show_statements.py
"""MySQL's SHOW statements, rendered from their nodes.

Two things are asserted here, and they are the two the wave asked for:

* **Each SHOW command is a node with constructor parameters.** No fluent
  setters remain, so an instance is complete the moment it is built and
  ``get_params()`` is the whole artifact. Every case therefore also rebuilds
  the node from its own parameters and requires the same SQL -- a parameter the
  class forgot to store under its own name fails there rather than surviving as
  a silently dropped filter.
* **The rendering is the dialect's.** These tests construct a dialect and
  render; they open no connection (org rules §12).

The parameter positions are part of the assertion: ``SHOW COLUMNS FROM t LIKE
%s`` binds the pattern, while ``SHOW WARNINGS LIMIT n`` inlines the count --
the command grammar takes a literal there, so a placeholder would be a syntax
error rather than a parameter.
"""

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.show import (
    ShowBinaryLogsStatement,
    ShowCharsetStatement,
    ShowCollationStatement,
    ShowColumnsStatement,
    ShowCreateTableStatement,
    ShowCreateTriggerStatement,
    ShowCreateViewStatement,
    ShowDatabasesStatement,
    ShowEnginesStatement,
    ShowErrorsStatement,
    ShowExpression,
    ShowGrantsStatement,
    ShowIndexStatement,
    ShowMasterStatusStatement,
    ShowPluginsStatement,
    ShowProcessListStatement,
    ShowSlaveStatusStatement,
    ShowStatusStatement,
    ShowTableStatusStatement,
    ShowTablesStatement,
    ShowTriggersStatement,
    ShowVariablesStatement,
    ShowWarningsStatement,
)


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


class TestConstructorOnly:
    """Every parameter is a constructor parameter; nothing is filled in later."""

    def test_no_fluent_setter_survives(self):
        setters = [
            name
            for name in dir(ShowExpression)
            if name.startswith("with_") or name in ("schema", "like", "full")
        ]
        assert setters == []

    @pytest.mark.parametrize(
        "build",
        [
            lambda d: ShowCreateTableStatement(d, "t"),
            lambda d: ShowCreateViewStatement(d, "v"),
            lambda d: ShowColumnsStatement(d, "t", full=True, like_pattern="id%"),
            lambda d: ShowIndexStatement(d, "t"),
            lambda d: ShowTablesStatement(d, full=True, like_pattern="t%"),
            lambda d: ShowDatabasesStatement(d, like_pattern="a%"),
            lambda d: ShowTableStatusStatement(d, like_pattern="t%"),
            lambda d: ShowTriggersStatement(d, table_name="t"),
            lambda d: ShowCreateTriggerStatement(d, "trg"),
            lambda d: ShowVariablesStatement(d, like_pattern="max%"),
            lambda d: ShowStatusStatement(d, like_pattern="Ssl_version", session=False),
            lambda d: ShowProcessListStatement(d, full=True),
            lambda d: ShowWarningsStatement(d, limit=3),
            lambda d: ShowErrorsStatement(d, limit=3),
            lambda d: ShowEnginesStatement(d),
            lambda d: ShowCharsetStatement(d, like_pattern="utf%"),
            lambda d: ShowCollationStatement(d, like_pattern="utf8%"),
            lambda d: ShowGrantsStatement(d, user="root", host="localhost"),
            lambda d: ShowPluginsStatement(d),
            lambda d: ShowBinaryLogsStatement(d),
            lambda d: ShowMasterStatusStatement(d),
            lambda d: ShowSlaveStatusStatement(d),
        ],
        ids=lambda build: build(MySQLDialect(version=(8, 0, 0))).__class__.__name__,
    )
    def test_params_rebuild_the_same_statement(self, dialect, build):
        expr = build(dialect)
        expected = expr.to_sql()
        rebuilt = type(expr)(dialect, **expr.get_params())
        assert rebuilt.to_sql() == expected


class TestShowCreate:
    """``SHOW CREATE ...`` names one object, database included."""

    def test_unqualified_table(self, dialect):
        sql, params = ShowCreateTableStatement(dialect, "users").to_sql()
        assert sql == "SHOW CREATE TABLE `users`"
        assert params == ()

    def test_database_qualifies_the_table(self, dialect):
        sql, _ = ShowCreateTableStatement(dialect, "users", schema="app").to_sql()
        assert sql == "SHOW CREATE TABLE `app`.`users`"

    def test_view(self, dialect):
        sql, _ = ShowCreateViewStatement(dialect, "v", schema="app").to_sql()
        assert sql == "SHOW CREATE VIEW `app`.`v`"

    def test_trigger(self, dialect):
        sql, _ = ShowCreateTriggerStatement(dialect, "trg").to_sql()
        assert sql == "SHOW CREATE TRIGGER `trg`"


class TestShowColumnsAndIndex:
    """The pattern is bound; FULL and the verb are spelled, not parameterised."""

    def test_plain(self, dialect):
        sql, params = ShowColumnsStatement(dialect, "users", schema="app").to_sql()
        assert sql == "SHOW COLUMNS FROM `app`.`users`"
        assert params == ()

    def test_full_and_like(self, dialect):
        sql, params = ShowColumnsStatement(
            dialect, "users", full=True, like_pattern="id%"
        ).to_sql()
        assert sql == "SHOW FULL COLUMNS FROM `users` LIKE %s"
        assert params == ("id%",)

    def test_index(self, dialect):
        sql, params = ShowIndexStatement(dialect, "users", schema="app").to_sql()
        assert sql == "SHOW INDEX FROM `app`.`users`"
        assert params == ()


class TestShowTablesAndDatabases:
    def test_tables_full_like_and_schema(self, dialect):
        sql, params = ShowTablesStatement(
            dialect, schema="app", full=True, like_pattern="u%"
        ).to_sql()
        assert sql == "SHOW FULL TABLES FROM `app` LIKE %s"
        assert params == ("u%",)

    def test_tables_without_filters(self, dialect):
        assert ShowTablesStatement(dialect).to_sql() == ("SHOW TABLES", ())

    def test_databases_like(self, dialect):
        assert ShowDatabasesStatement(dialect, like_pattern="a%").to_sql() == (
            "SHOW DATABASES LIKE %s",
            ("a%",),
        )

    def test_databases_without_pattern(self, dialect):
        assert ShowDatabasesStatement(dialect).to_sql() == ("SHOW DATABASES", ())

    def test_table_status(self, dialect):
        assert ShowTableStatusStatement(dialect, schema="app", like_pattern="u%").to_sql() == (
            "SHOW TABLE STATUS FROM `app` LIKE %s",
            ("u%",),
        )


class TestShowVariablesAndStatus:
    """Session is the default; the GLOBAL word is the difference."""

    def test_variables_session(self, dialect):
        assert ShowVariablesStatement(dialect, like_pattern="max%").to_sql() == (
            "SHOW VARIABLES LIKE %s",
            ("max%",),
        )

    def test_variables_global(self, dialect):
        assert ShowVariablesStatement(
            dialect, like_pattern="gtid_executed", session=False
        ).to_sql() == ("SHOW GLOBAL VARIABLES LIKE %s", ("gtid_executed",))

    def test_status_session(self, dialect):
        assert ShowStatusStatement(dialect, like_pattern="Ssl_version").to_sql() == (
            "SHOW STATUS LIKE %s",
            ("Ssl_version",),
        )

    def test_status_global(self, dialect):
        assert ShowStatusStatement(dialect, like_pattern="Ssl_version", session=False).to_sql() == (
            "SHOW GLOBAL STATUS LIKE %s",
            ("Ssl_version",),
        )


class TestShowTriggers:
    """``SHOW TRIGGERS`` filters by table through LIKE, not through a clause."""

    def test_all(self, dialect):
        assert ShowTriggersStatement(dialect, schema="app").to_sql() == (
            "SHOW TRIGGERS FROM `app`",
            (),
        )

    def test_one_table(self, dialect):
        assert ShowTriggersStatement(dialect, schema="app", table_name="users").to_sql() == (
            "SHOW TRIGGERS FROM `app` LIKE %s",
            ("users",),
        )


class TestLimitAndFull:
    """The count is a literal: the grammar takes a number, not a bind slot."""

    def test_processlist(self, dialect):
        assert ShowProcessListStatement(dialect).to_sql() == ("SHOW PROCESSLIST", ())

    def test_full_processlist(self, dialect):
        assert ShowProcessListStatement(dialect, full=True).to_sql() == (
            "SHOW FULL PROCESSLIST",
            (),
        )

    def test_warnings_limit_is_inline(self, dialect):
        assert ShowWarningsStatement(dialect, limit=10).to_sql() == (
            "SHOW WARNINGS LIMIT 10",
            (),
        )

    def test_errors_limit_is_inline(self, dialect):
        assert ShowErrorsStatement(dialect, limit=5).to_sql() == (
            "SHOW ERRORS LIMIT 5",
            (),
        )


class TestParameterless:
    """Commands with no parameters at all -- each its own node."""

    @pytest.mark.parametrize(
        "node, expected",
        [
            (ShowEnginesStatement, "SHOW ENGINES"),
            (ShowPluginsStatement, "SHOW PLUGINS"),
            (ShowBinaryLogsStatement, "SHOW BINARY LOGS"),
            (ShowMasterStatusStatement, "SHOW MASTER STATUS"),
            (ShowSlaveStatusStatement, "SHOW SLAVE STATUS"),
        ],
        ids=lambda value: getattr(value, "__name__", ""),
    )
    def test_renders(self, dialect, node, expected):
        assert node(dialect).to_sql() == (expected, ())


class TestGrants:
    def test_current_account(self, dialect):
        assert ShowGrantsStatement(dialect).to_sql() == ("SHOW GRANTS", ())

    def test_named_account(self, dialect):
        assert ShowGrantsStatement(dialect, user="root", host="localhost").to_sql() == (
            "SHOW GRANTS FOR %s@%s",
            ("root", "localhost"),
        )

    def test_user_without_host(self, dialect):
        assert ShowGrantsStatement(dialect, user="root").to_sql() == (
            "SHOW GRANTS FOR %s",
            ("root",),
        )


class TestCharsetAndCollation:
    def test_charset(self, dialect):
        assert ShowCharsetStatement(dialect, like_pattern="utf%").to_sql() == (
            "SHOW CHARACTER SET LIKE %s",
            ("utf%",),
        )

    def test_collation(self, dialect):
        assert ShowCollationStatement(dialect, like_pattern="utf8%").to_sql() == (
            "SHOW COLLATION LIKE %s",
            ("utf8%",),
        )
