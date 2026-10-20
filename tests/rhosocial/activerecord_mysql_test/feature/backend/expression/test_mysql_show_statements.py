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
    ShowBinaryLogsExpression,
    ShowCharsetExpression,
    ShowCollationExpression,
    ShowColumnsExpression,
    ShowCreateTableExpression,
    ShowCreateTriggerExpression,
    ShowCreateViewExpression,
    ShowDatabasesExpression,
    ShowEnginesExpression,
    ShowErrorsExpression,
    ShowExpression,
    ShowGrantsExpression,
    ShowIndexExpression,
    ShowMasterStatusExpression,
    ShowPluginsExpression,
    ShowProcessListExpression,
    ShowSlaveStatusExpression,
    ShowStatusExpression,
    ShowTableStatusExpression,
    ShowTablesExpression,
    ShowTriggersExpression,
    ShowVariablesExpression,
    ShowWarningsExpression,
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
            lambda d: ShowCreateTableExpression(d, "t"),
            lambda d: ShowCreateViewExpression(d, "v"),
            lambda d: ShowColumnsExpression(d, "t", full=True, like_pattern="id%"),
            lambda d: ShowIndexExpression(d, "t"),
            lambda d: ShowTablesExpression(d, full=True, like_pattern="t%"),
            lambda d: ShowDatabasesExpression(d, like_pattern="a%"),
            lambda d: ShowTableStatusExpression(d, like_pattern="t%"),
            lambda d: ShowTriggersExpression(d, table_name="t"),
            lambda d: ShowCreateTriggerExpression(d, "trg"),
            lambda d: ShowVariablesExpression(d, like_pattern="max%"),
            lambda d: ShowStatusExpression(d, like_pattern="Ssl_version", session=False),
            lambda d: ShowProcessListExpression(d, full=True),
            lambda d: ShowWarningsExpression(d, limit=3),
            lambda d: ShowErrorsExpression(d, limit=3),
            lambda d: ShowEnginesExpression(d),
            lambda d: ShowCharsetExpression(d, like_pattern="utf%"),
            lambda d: ShowCollationExpression(d, like_pattern="utf8%"),
            lambda d: ShowGrantsExpression(d, user="root", host="localhost"),
            lambda d: ShowPluginsExpression(d),
            lambda d: ShowBinaryLogsExpression(d),
            lambda d: ShowMasterStatusExpression(d),
            lambda d: ShowSlaveStatusExpression(d),
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
        sql, params = ShowCreateTableExpression(dialect, "users").to_sql()
        assert sql == "SHOW CREATE TABLE `users`"
        assert params == ()

    def test_database_qualifies_the_table(self, dialect):
        sql, _ = ShowCreateTableExpression(dialect, "users", schema="app").to_sql()
        assert sql == "SHOW CREATE TABLE `app`.`users`"

    def test_view(self, dialect):
        sql, _ = ShowCreateViewExpression(dialect, "v", schema="app").to_sql()
        assert sql == "SHOW CREATE VIEW `app`.`v`"

    def test_trigger(self, dialect):
        sql, _ = ShowCreateTriggerExpression(dialect, "trg").to_sql()
        assert sql == "SHOW CREATE TRIGGER `trg`"


class TestShowColumnsAndIndex:
    """The pattern is bound; FULL and the verb are spelled, not parameterised."""

    def test_plain(self, dialect):
        sql, params = ShowColumnsExpression(dialect, "users", schema="app").to_sql()
        assert sql == "SHOW COLUMNS FROM `app`.`users`"
        assert params == ()

    def test_full_and_like(self, dialect):
        sql, params = ShowColumnsExpression(
            dialect, "users", full=True, like_pattern="id%"
        ).to_sql()
        assert sql == "SHOW FULL COLUMNS FROM `users` LIKE %s"
        assert params == ("id%",)

    def test_index(self, dialect):
        sql, params = ShowIndexExpression(dialect, "users", schema="app").to_sql()
        assert sql == "SHOW INDEX FROM `app`.`users`"
        assert params == ()


class TestShowTablesAndDatabases:
    def test_tables_full_like_and_schema(self, dialect):
        sql, params = ShowTablesExpression(
            dialect, schema="app", full=True, like_pattern="u%"
        ).to_sql()
        assert sql == "SHOW FULL TABLES FROM `app` LIKE %s"
        assert params == ("u%",)

    def test_tables_without_filters(self, dialect):
        assert ShowTablesExpression(dialect).to_sql() == ("SHOW TABLES", ())

    def test_databases_like(self, dialect):
        assert ShowDatabasesExpression(dialect, like_pattern="a%").to_sql() == (
            "SHOW DATABASES LIKE %s",
            ("a%",),
        )

    def test_databases_without_pattern(self, dialect):
        assert ShowDatabasesExpression(dialect).to_sql() == ("SHOW DATABASES", ())

    def test_table_status(self, dialect):
        assert ShowTableStatusExpression(dialect, schema="app", like_pattern="u%").to_sql() == (
            "SHOW TABLE STATUS FROM `app` LIKE %s",
            ("u%",),
        )


class TestShowVariablesAndStatus:
    """Session is the default; the GLOBAL word is the difference."""

    def test_variables_session(self, dialect):
        assert ShowVariablesExpression(dialect, like_pattern="max%").to_sql() == (
            "SHOW VARIABLES LIKE %s",
            ("max%",),
        )

    def test_variables_global(self, dialect):
        assert ShowVariablesExpression(
            dialect, like_pattern="gtid_executed", session=False
        ).to_sql() == ("SHOW GLOBAL VARIABLES LIKE %s", ("gtid_executed",))

    def test_status_session(self, dialect):
        assert ShowStatusExpression(dialect, like_pattern="Ssl_version").to_sql() == (
            "SHOW STATUS LIKE %s",
            ("Ssl_version",),
        )

    def test_status_global(self, dialect):
        assert ShowStatusExpression(dialect, like_pattern="Ssl_version", session=False).to_sql() == (
            "SHOW GLOBAL STATUS LIKE %s",
            ("Ssl_version",),
        )


class TestShowTriggers:
    """``SHOW TRIGGERS`` filters by table through LIKE, not through a clause."""

    def test_all(self, dialect):
        assert ShowTriggersExpression(dialect, schema="app").to_sql() == (
            "SHOW TRIGGERS FROM `app`",
            (),
        )

    def test_one_table(self, dialect):
        assert ShowTriggersExpression(dialect, schema="app", table_name="users").to_sql() == (
            "SHOW TRIGGERS FROM `app` LIKE %s",
            ("users",),
        )


class TestLimitAndFull:
    """The count is a literal: the grammar takes a number, not a bind slot."""

    def test_processlist(self, dialect):
        assert ShowProcessListExpression(dialect).to_sql() == ("SHOW PROCESSLIST", ())

    def test_full_processlist(self, dialect):
        assert ShowProcessListExpression(dialect, full=True).to_sql() == (
            "SHOW FULL PROCESSLIST",
            (),
        )

    def test_warnings_limit_is_inline(self, dialect):
        assert ShowWarningsExpression(dialect, limit=10).to_sql() == (
            "SHOW WARNINGS LIMIT 10",
            (),
        )

    def test_errors_limit_is_inline(self, dialect):
        assert ShowErrorsExpression(dialect, limit=5).to_sql() == (
            "SHOW ERRORS LIMIT 5",
            (),
        )


class TestParameterless:
    """Commands with no parameters at all -- each its own node."""

    @pytest.mark.parametrize(
        "node, expected",
        [
            (ShowEnginesExpression, "SHOW ENGINES"),
            (ShowPluginsExpression, "SHOW PLUGINS"),
            (ShowBinaryLogsExpression, "SHOW BINARY LOGS"),
            (ShowMasterStatusExpression, "SHOW MASTER STATUS"),
            (ShowSlaveStatusExpression, "SHOW SLAVE STATUS"),
        ],
        ids=lambda value: getattr(value, "__name__", ""),
    )
    def test_renders(self, dialect, node, expected):
        assert node(dialect).to_sql() == (expected, ())


class TestGrants:
    def test_current_account(self, dialect):
        assert ShowGrantsExpression(dialect).to_sql() == ("SHOW GRANTS", ())

    def test_named_account(self, dialect):
        assert ShowGrantsExpression(dialect, user="root", host="localhost").to_sql() == (
            "SHOW GRANTS FOR %s@%s",
            ("root", "localhost"),
        )

    def test_user_without_host(self, dialect):
        assert ShowGrantsExpression(dialect, user="root").to_sql() == (
            "SHOW GRANTS FOR %s",
            ("root",),
        )


class TestCharsetAndCollation:
    def test_charset(self, dialect):
        assert ShowCharsetExpression(dialect, like_pattern="utf%").to_sql() == (
            "SHOW CHARACTER SET LIKE %s",
            ("utf%",),
        )

    def test_collation(self, dialect):
        assert ShowCollationExpression(dialect, like_pattern="utf8%").to_sql() == (
            "SHOW COLLATION LIKE %s",
            ("utf8%",),
        )
