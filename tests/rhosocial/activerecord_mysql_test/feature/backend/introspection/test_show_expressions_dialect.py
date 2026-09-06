# tests/rhosocial/activerecord_mysql_test/feature/backend/introspection/test_show_expressions_dialect.py
"""
Tests for the MySQL SHOW expression classes and their dialect SQL generation.

These are pure expression-level (no live server needed) tests that pin:

- ``show/expressions.py``: fluent parameter setters (schema/full/like/for_table/
  session/global_vars/global_status/limit/for_user) and to_sql() delegation to
  the dialect format_show_* methods.
- ``show/dialect.py``: every format_show_* branch (schema qualified vs bare,
  FULL, LIKE, GLOBAL, LIMIT, grants user@host).
"""

from unittest.mock import MagicMock

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.show import (
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
    ShowPluginsExpression,
    ShowProcessListExpression,
    ShowStatusExpression,
    ShowTableStatusExpression,
    ShowTablesExpression,
    ShowTriggersExpression,
    ShowVariablesExpression,
    ShowWarningsExpression,
)


@pytest.fixture
def dialect():
    """Return a MySQLDialect instance for SHOW SQL generation."""
    return MySQLDialect(version=(8, 0, 0))


def _expr(params):
    """Build a mock expression whose get_params returns the given dict."""
    expr = MagicMock()
    expr.get_params.return_value = params
    return expr


class TestShowExpressionBase:
    """Verify the ShowExpression base class behavior."""

    def test_schema_setter(self, dialect):
        """schema() should store the schema and return self for chaining."""
        expr = ShowCreateTableExpression(dialect, "users")
        result = expr.schema("app")
        assert result is expr, "schema() should return self for chaining"
        assert expr._schema == "app", "schema should be stored on the expression"

    def test_to_sql_not_implemented(self, dialect):
        """The base to_sql() should raise NotImplementedError."""
        expr = ShowExpression(dialect)
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            expr.to_sql()


class TestShowCreateExpressions:
    """Verify SHOW CREATE TABLE/VIEW/TRIGGER expression delegation."""

    def test_create_table_delegates(self, dialect):
        """ShowCreateTableExpression.to_sql() should delegate to the dialect."""
        expr = ShowCreateTableExpression(dialect, "users")
        sql, params = expr.to_sql()
        assert sql == "SHOW CREATE TABLE `users`", f"unexpected SQL: {sql}"
        assert params == (), "SHOW CREATE TABLE takes no parameters"

    def test_create_table_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored on the expression but must not alter the SHOW SQL."""
        expr = ShowCreateTableExpression(dialect, "users").schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW CREATE TABLE `users`", f"schema must not alter SQL: {sql}"

    def test_create_view_delegates(self, dialect):
        """ShowCreateViewExpression.to_sql() should delegate to the dialect."""
        expr = ShowCreateViewExpression(dialect, "user_view")
        sql, _ = expr.to_sql()
        assert sql == "SHOW CREATE VIEW `user_view`", f"unexpected SQL: {sql}"

    def test_create_view_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW CREATE VIEW SQL."""
        expr = ShowCreateViewExpression(dialect, "user_view").schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW CREATE VIEW `user_view`", f"schema must not alter SQL: {sql}"

    def test_create_trigger_delegates(self, dialect):
        """ShowCreateTriggerExpression.to_sql() should delegate to the dialect."""
        expr = ShowCreateTriggerExpression(dialect, "audit_trigger")
        sql, _ = expr.to_sql()
        assert sql == "SHOW CREATE TRIGGER `audit_trigger`", f"unexpected SQL: {sql}"

    def test_create_trigger_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW CREATE TRIGGER SQL."""
        expr = ShowCreateTriggerExpression(dialect, "audit_trigger").schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW CREATE TRIGGER `audit_trigger`", f"schema must not alter SQL: {sql}"


class TestShowColumnsExpression:
    """Verify ShowColumnsExpression fluent setters and delegation."""

    def test_full_setter(self, dialect):
        """full() should set the full flag and return self."""
        expr = ShowColumnsExpression(dialect, "users")
        result = expr.full()
        assert result is expr, "full() should return self for chaining"
        assert expr._full is True, "full flag should be stored"

    def test_full_value(self, dialect):
        """full(False) should disable the full flag."""
        expr = ShowColumnsExpression(dialect, "users", full=True)
        assert expr.full(False)._full is False, "full(False) should clear the flag"

    def test_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowColumnsExpression(dialect, "users")
        result = expr.like("id%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "id%", "pattern should be stored"

    def test_full_columns_sql(self, dialect):
        """A full columns expression should emit SHOW FULL COLUMNS."""
        expr = ShowColumnsExpression(dialect, "users", full=True)
        sql, _ = expr.to_sql()
        assert sql == "SHOW FULL COLUMNS FROM `users`", f"unexpected SQL: {sql}"

    def test_columns_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowColumnsExpression(dialect, "users").like("id%")
        sql, params = expr.to_sql()
        assert sql == "SHOW COLUMNS FROM `users` LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("id%",), "LIKE pattern should be bound"

    def test_columns_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW COLUMNS SQL."""
        expr = ShowColumnsExpression(dialect, "users").schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW COLUMNS FROM `users`", f"schema must not alter SQL: {sql}"


class TestShowIndexExpression:
    """Verify ShowIndexExpression delegation."""

    def test_index_delegates(self, dialect):
        """ShowIndexExpression.to_sql() should emit SHOW INDEX."""
        expr = ShowIndexExpression(dialect, "users")
        sql, _ = expr.to_sql()
        assert sql == "SHOW INDEX FROM `users`", f"unexpected SQL: {sql}"

    def test_index_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW INDEX SQL."""
        expr = ShowIndexExpression(dialect, "users").schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW INDEX FROM `users`", f"schema must not alter SQL: {sql}"


class TestShowTablesExpression:
    """Verify ShowTablesExpression fluent setters and delegation."""

    def test_full_setter(self, dialect):
        """full() should set the full flag and return self."""
        expr = ShowTablesExpression(dialect)
        result = expr.full()
        assert result is expr, "full() should return self for chaining"
        assert expr._full is True, "full flag should be stored"

    def test_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowTablesExpression(dialect)
        result = expr.like("user%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "user%", "pattern should be stored"

    def test_tables_sql(self, dialect):
        """A plain tables expression should emit SHOW TABLES."""
        expr = ShowTablesExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW TABLES", f"unexpected SQL: {sql}"

    def test_full_tables_sql(self, dialect):
        """A full tables expression should emit SHOW FULL TABLES."""
        expr = ShowTablesExpression(dialect).full()
        sql, _ = expr.to_sql()
        assert sql == "SHOW FULL TABLES", f"unexpected SQL: {sql}"

    def test_tables_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW TABLES SQL."""
        expr = ShowTablesExpression(dialect).schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW TABLES", f"schema must not alter SQL: {sql}"

    def test_tables_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowTablesExpression(dialect).like("user%")
        sql, params = expr.to_sql()
        assert sql == "SHOW TABLES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("user%",), "LIKE pattern should be bound"


class TestShowDatabasesExpression:
    """Verify ShowDatabasesExpression fluent setter and delegation."""

    def test_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowDatabasesExpression(dialect)
        result = expr.like("shop%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "shop%", "pattern should be stored"

    def test_databases_sql(self, dialect):
        """A plain databases expression should emit SHOW DATABASES."""
        expr = ShowDatabasesExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW DATABASES", f"unexpected SQL: {sql}"

    def test_databases_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowDatabasesExpression(dialect).like("shop%")
        sql, params = expr.to_sql()
        assert sql == "SHOW DATABASES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("shop%",), "LIKE pattern should be bound"


class TestShowTableStatusExpression:
    """Verify ShowTableStatusExpression fluent setter and delegation."""

    def test_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowTableStatusExpression(dialect)
        result = expr.like("user%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "user%", "pattern should be stored"

    def test_table_status_sql(self, dialect):
        """A plain table status expression should emit SHOW TABLE STATUS."""
        expr = ShowTableStatusExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW TABLE STATUS", f"unexpected SQL: {sql}"

    def test_table_status_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW TABLE STATUS SQL."""
        expr = ShowTableStatusExpression(dialect).schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW TABLE STATUS", f"schema must not alter SQL: {sql}"

    def test_table_status_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowTableStatusExpression(dialect).like("user%")
        sql, params = expr.to_sql()
        assert sql == "SHOW TABLE STATUS LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("user%",), "LIKE pattern should be bound"


class TestShowTriggersExpression:
    """Verify ShowTriggersExpression fluent setter and delegation."""

    def test_for_table_setter(self, dialect):
        """for_table() should store the table filter and return self."""
        expr = ShowTriggersExpression(dialect)
        result = expr.for_table("users")
        assert result is expr, "for_table() should return self for chaining"
        assert expr._table == "users", "table filter should be stored"

    def test_triggers_sql(self, dialect):
        """A plain triggers expression should emit SHOW TRIGGERS."""
        expr = ShowTriggersExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW TRIGGERS", f"unexpected SQL: {sql}"

    def test_triggers_for_table_sql(self, dialect):
        """A table filter should be emitted as a bound LIKE."""
        expr = ShowTriggersExpression(dialect).for_table("users")
        sql, params = expr.to_sql()
        assert sql == "SHOW TRIGGERS LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("users",), "table filter should be bound"

    def test_triggers_schema_stored_but_not_embedded(self, dialect):
        """schema() is stored but must not alter the SHOW TRIGGERS SQL."""
        expr = ShowTriggersExpression(dialect).schema("app")
        assert expr._schema == "app", "schema should be stored on the expression"
        sql, _ = expr.to_sql()
        assert sql == "SHOW TRIGGERS", f"schema must not alter SQL: {sql}"


class TestShowVariablesExpression:
    """Verify ShowVariablesExpression session/global and like behavior."""

    def test_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowVariablesExpression(dialect)
        result = expr.like("max%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "max%", "pattern should be stored"

    def test_session_setter(self, dialect):
        """session() should keep session scope and return self."""
        expr = ShowVariablesExpression(dialect, session=False)
        result = expr.session()
        assert result is expr, "session() should return self for chaining"
        assert expr._session is True, "session flag should be set"

    def test_global_vars(self, dialect):
        """global_vars() should switch to global scope."""
        expr = ShowVariablesExpression(dialect).global_vars()
        assert expr._session is False, "global_vars() should clear the session flag"

    def test_session_sql(self, dialect):
        """A session variables expression should emit SHOW VARIABLES."""
        expr = ShowVariablesExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW VARIABLES", f"unexpected SQL: {sql}"

    def test_global_sql(self, dialect):
        """A global variables expression should emit SHOW GLOBAL VARIABLES."""
        expr = ShowVariablesExpression(dialect).global_vars()
        sql, _ = expr.to_sql()
        assert sql == "SHOW GLOBAL VARIABLES", f"unexpected SQL: {sql}"

    def test_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowVariablesExpression(dialect).like("max%")
        sql, params = expr.to_sql()
        assert sql == "SHOW VARIABLES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("max%",), "LIKE pattern should be bound"


class TestShowStatusExpression:
    """Verify ShowStatusExpression session/global and like behavior."""

    def test_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowStatusExpression(dialect)
        result = expr.like("Uptime%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "Uptime%", "pattern should be stored"

    def test_session_setter(self, dialect):
        """session() should keep session scope and return self."""
        expr = ShowStatusExpression(dialect, session=False)
        result = expr.session()
        assert result is expr, "session() should return self for chaining"
        assert expr._session is True, "session flag should be set"

    def test_global_status(self, dialect):
        """global_status() should switch to global scope."""
        expr = ShowStatusExpression(dialect).global_status()
        assert expr._session is False, "global_status() should clear the session flag"

    def test_session_sql(self, dialect):
        """A session status expression should emit SHOW STATUS."""
        expr = ShowStatusExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW STATUS", f"unexpected SQL: {sql}"

    def test_global_sql(self, dialect):
        """A global status expression should emit SHOW GLOBAL STATUS."""
        expr = ShowStatusExpression(dialect).global_status()
        sql, _ = expr.to_sql()
        assert sql == "SHOW GLOBAL STATUS", f"unexpected SQL: {sql}"

    def test_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowStatusExpression(dialect).like("Uptime%")
        sql, params = expr.to_sql()
        assert sql == "SHOW STATUS LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("Uptime%",), "LIKE pattern should be bound"


class TestShowProcessListExpression:
    """Verify ShowProcessListExpression full flag and delegation."""

    def test_full_setter(self, dialect):
        """full() should set the full flag and return self."""
        expr = ShowProcessListExpression(dialect)
        result = expr.full()
        assert result is expr, "full() should return self for chaining"
        assert expr._full is True, "full flag should be stored"

    def test_processlist_sql(self, dialect):
        """A plain processlist expression should emit SHOW PROCESSLIST."""
        expr = ShowProcessListExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW PROCESSLIST", f"unexpected SQL: {sql}"

    def test_full_processlist_sql(self, dialect):
        """A full processlist expression should emit SHOW FULL PROCESSLIST."""
        expr = ShowProcessListExpression(dialect).full()
        sql, _ = expr.to_sql()
        assert sql == "SHOW FULL PROCESSLIST", f"unexpected SQL: {sql}"


class TestShowWarningsErrorsExpression:
    """Verify ShowWarningsExpression and ShowErrorsExpression limit behavior."""

    def test_warnings_limit_setter(self, dialect):
        """limit() should store the count and return self."""
        expr = ShowWarningsExpression(dialect)
        result = expr.limit(5)
        assert result is expr, "limit() should return self for chaining"
        assert expr._limit == 5, "limit should be stored"

    def test_warnings_sql(self, dialect):
        """A plain warnings expression should emit SHOW WARNINGS."""
        expr = ShowWarningsExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW WARNINGS", f"unexpected SQL: {sql}"

    def test_warnings_limit_sql(self, dialect):
        """A limit should be appended to SHOW WARNINGS."""
        expr = ShowWarningsExpression(dialect, limit=5)
        sql, _ = expr.to_sql()
        assert sql == "SHOW WARNINGS LIMIT 5", f"unexpected SQL: {sql}"

    def test_errors_limit_setter(self, dialect):
        """limit() should store the count and return self."""
        expr = ShowErrorsExpression(dialect)
        result = expr.limit(3)
        assert result is expr, "limit() should return self for chaining"
        assert expr._limit == 3, "limit should be stored"

    def test_errors_sql(self, dialect):
        """A plain errors expression should emit SHOW ERRORS."""
        expr = ShowErrorsExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW ERRORS", f"unexpected SQL: {sql}"

    def test_errors_limit_sql(self, dialect):
        """A limit should be appended to SHOW ERRORS."""
        expr = ShowErrorsExpression(dialect, limit=3)
        sql, _ = expr.to_sql()
        assert sql == "SHOW ERRORS LIMIT 3", f"unexpected SQL: {sql}"


class TestShowSimpleExpressions:
    """Verify the simple SHOW expressions delegate to the dialect."""

    def test_engines(self, dialect):
        """ShowEnginesExpression.to_sql() should emit SHOW ENGINES."""
        expr = ShowEnginesExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW ENGINES", f"unexpected SQL: {sql}"

    def test_plugins(self, dialect):
        """ShowPluginsExpression.to_sql() should emit SHOW PLUGINS."""
        expr = ShowPluginsExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW PLUGINS", f"unexpected SQL: {sql}"


class TestShowCharsetCollationExpression:
    """Verify ShowCharsetExpression and ShowCollationExpression like behavior."""

    def test_charset_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowCharsetExpression(dialect)
        result = expr.like("utf8%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "utf8%", "pattern should be stored"

    def test_charset_sql(self, dialect):
        """A plain charset expression should emit SHOW CHARACTER SET."""
        expr = ShowCharsetExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW CHARACTER SET", f"unexpected SQL: {sql}"

    def test_charset_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowCharsetExpression(dialect).like("utf8%")
        sql, params = expr.to_sql()
        assert sql == "SHOW CHARACTER SET LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("utf8%",), "LIKE pattern should be bound"

    def test_collation_like_setter(self, dialect):
        """like() should store the pattern and return self."""
        expr = ShowCollationExpression(dialect)
        result = expr.like("utf8mb4%")
        assert result is expr, "like() should return self for chaining"
        assert expr._like_pattern == "utf8mb4%", "pattern should be stored"

    def test_collation_sql(self, dialect):
        """A plain collation expression should emit SHOW COLLATION."""
        expr = ShowCollationExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW COLLATION", f"unexpected SQL: {sql}"

    def test_collation_like_sql(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        expr = ShowCollationExpression(dialect).like("utf8mb4%")
        sql, params = expr.to_sql()
        assert sql == "SHOW COLLATION LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("utf8mb4%",), "LIKE pattern should be bound"


class TestShowGrantsExpression:
    """Verify ShowGrantsExpression for_user and delegation."""

    def test_for_user_setter(self, dialect):
        """for_user() should store user/host and return self."""
        expr = ShowGrantsExpression(dialect)
        result = expr.for_user("app", "10.0.0.%")
        assert result is expr, "for_user() should return self for chaining"
        assert expr._user == "app", "user should be stored"
        assert expr._host == "10.0.0.%", "host should be stored"

    def test_grants_sql(self, dialect):
        """A bare grants expression should emit SHOW GRANTS."""
        expr = ShowGrantsExpression(dialect)
        sql, _ = expr.to_sql()
        assert sql == "SHOW GRANTS", f"unexpected SQL: {sql}"

    def test_grants_user_sql(self, dialect):
        """A user-only grants expression should bind the user."""
        expr = ShowGrantsExpression(dialect, user="app")
        sql, params = expr.to_sql()
        assert sql == "SHOW GRANTS FOR %s", f"unexpected SQL: {sql}"
        assert params == ("app",), "user should be bound"

    def test_grants_user_host_sql(self, dialect):
        """A user@host grants expression should bind both."""
        expr = ShowGrantsExpression(dialect).for_user("app", "10.0.0.%")
        sql, params = expr.to_sql()
        assert sql == "SHOW GRANTS FOR %s@%s", f"unexpected SQL: {sql}"
        assert params == ("app", "10.0.0.%"), "user and host should be bound"


class TestShowDialectFormatting:
    """Verify every format_show_* branch directly with mock expressions."""

    def test_create_table_bare(self, dialect):
        """SHOW CREATE TABLE should quote the bare table name."""
        sql, params = dialect.format_show_create_table(_expr({"table": "users"}))
        assert sql == "SHOW CREATE TABLE `users`", f"unexpected SQL: {sql}"
        assert params == (), "SHOW CREATE TABLE takes no parameters"

    def test_create_table_schema(self, dialect):
        """SHOW CREATE TABLE should quote schema.table when schema is set."""
        sql, _ = dialect.format_show_create_table(_expr({"table": "users", "schema": "app"}))
        assert sql == "SHOW CREATE TABLE `app`.`users`", f"unexpected SQL: {sql}"

    def test_create_view_bare(self, dialect):
        """SHOW CREATE VIEW should quote the bare view name."""
        sql, _ = dialect.format_show_create_view(_expr({"view_name": "v"}))
        assert sql == "SHOW CREATE VIEW `v`", f"unexpected SQL: {sql}"

    def test_create_view_schema(self, dialect):
        """SHOW CREATE VIEW should quote schema.view when schema is set."""
        sql, _ = dialect.format_show_create_view(_expr({"view_name": "v", "schema": "app"}))
        assert sql == "SHOW CREATE VIEW `app`.`v`", f"unexpected SQL: {sql}"

    def test_create_trigger_bare(self, dialect):
        """SHOW CREATE TRIGGER should quote the bare trigger name."""
        sql, _ = dialect.format_show_create_trigger(_expr({"trigger": "trg"}))
        assert sql == "SHOW CREATE TRIGGER `trg`", f"unexpected SQL: {sql}"

    def test_create_trigger_schema(self, dialect):
        """SHOW CREATE TRIGGER should quote schema.trigger when schema is set."""
        sql, _ = dialect.format_show_create_trigger(_expr({"trigger": "trg", "schema": "app"}))
        assert sql == "SHOW CREATE TRIGGER `app`.`trg`", f"unexpected SQL: {sql}"

    def test_columns_bare(self, dialect):
        """SHOW COLUMNS should reference the bare table."""
        sql, params = dialect.format_show_columns(_expr({"table": "users"}))
        assert sql == "SHOW COLUMNS FROM `users`", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_columns_full(self, dialect):
        """FULL should appear for full column listing."""
        sql, _ = dialect.format_show_columns(_expr({"table": "users", "full": True}))
        assert sql == "SHOW FULL COLUMNS FROM `users`", f"unexpected SQL: {sql}"

    def test_columns_schema(self, dialect):
        """SHOW COLUMNS should prefix the schema when present in params."""
        sql, _ = dialect.format_show_columns(_expr({"table": "users", "schema": "app"}))
        assert sql == "SHOW COLUMNS FROM `app`. `users`", f"unexpected SQL: {sql}"

    def test_columns_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_columns(_expr({"table": "users", "like_pattern": "id%"}))
        assert sql == "SHOW COLUMNS FROM `users` LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("id%",), "LIKE pattern should be bound"

    def test_index_bare(self, dialect):
        """SHOW INDEX should reference the bare table."""
        sql, _ = dialect.format_show_index(_expr({"table": "users"}))
        assert sql == "SHOW INDEX FROM `users`", f"unexpected SQL: {sql}"

    def test_index_schema(self, dialect):
        """SHOW INDEX should prefix the schema."""
        sql, _ = dialect.format_show_index(_expr({"table": "users", "schema": "app"}))
        assert sql == "SHOW INDEX FROM `app`.`users`", f"unexpected SQL: {sql}"

    def test_tables_bare(self, dialect):
        """SHOW TABLES should render without modifiers."""
        sql, params = dialect.format_show_tables(_expr({}))
        assert sql == "SHOW TABLES", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_tables_full(self, dialect):
        """FULL should appear for full table listing."""
        sql, _ = dialect.format_show_tables(_expr({"full": True}))
        assert sql == "SHOW FULL TABLES", f"unexpected SQL: {sql}"

    def test_tables_schema(self, dialect):
        """SHOW TABLES FROM schema should be emitted for schema-scoped queries."""
        sql, _ = dialect.format_show_tables(_expr({"schema": "app"}))
        assert sql == "SHOW TABLES FROM `app`", f"unexpected SQL: {sql}"

    def test_tables_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_tables(_expr({"like_pattern": "user%"}))
        assert sql == "SHOW TABLES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("user%",), "LIKE pattern should be bound"

    def test_databases_bare(self, dialect):
        """SHOW DATABASES should render without modifiers."""
        sql, params = dialect.format_show_databases(_expr({}))
        assert sql == "SHOW DATABASES", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_databases_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_databases(_expr({"like_pattern": "shop%"}))
        assert sql == "SHOW DATABASES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("shop%",), "LIKE pattern should be bound"

    def test_table_status_bare(self, dialect):
        """SHOW TABLE STATUS should render without modifiers."""
        sql, params = dialect.format_show_table_status(_expr({}))
        assert sql == "SHOW TABLE STATUS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_table_status_schema(self, dialect):
        """SHOW TABLE STATUS FROM schema should be emitted when schema is set."""
        sql, _ = dialect.format_show_table_status(_expr({"schema": "app"}))
        assert sql == "SHOW TABLE STATUS FROM `app`", f"unexpected SQL: {sql}"

    def test_table_status_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_table_status(_expr({"like_pattern": "user%"}))
        assert sql == "SHOW TABLE STATUS LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("user%",), "LIKE pattern should be bound"

    def test_triggers_bare(self, dialect):
        """SHOW TRIGGERS should render without modifiers."""
        sql, params = dialect.format_show_triggers(_expr({}))
        assert sql == "SHOW TRIGGERS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_triggers_schema(self, dialect):
        """SHOW TRIGGERS FROM schema should be emitted when schema is set."""
        sql, _ = dialect.format_show_triggers(_expr({"schema": "app"}))
        assert sql == "SHOW TRIGGERS FROM `app`", f"unexpected SQL: {sql}"

    def test_triggers_table(self, dialect):
        """A table filter should be emitted as a bound LIKE."""
        sql, params = dialect.format_show_triggers(_expr({"table": "users"}))
        assert sql == "SHOW TRIGGERS LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("users",), "table filter should be bound"

    def test_variables_session(self, dialect):
        """Session scope should render SHOW VARIABLES."""
        sql, params = dialect.format_show_variables(_expr({"session": True}))
        assert sql == "SHOW VARIABLES", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_variables_global(self, dialect):
        """Global scope should render SHOW GLOBAL VARIABLES."""
        sql, _ = dialect.format_show_variables(_expr({"session": False}))
        assert sql == "SHOW GLOBAL VARIABLES", f"unexpected SQL: {sql}"

    def test_variables_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_variables(_expr({"session": True, "like_pattern": "max%"}))
        assert sql == "SHOW VARIABLES LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("max%",), "LIKE pattern should be bound"

    def test_status_session(self, dialect):
        """Session scope should render SHOW STATUS."""
        sql, params = dialect.format_show_status(_expr({"session": True}))
        assert sql == "SHOW STATUS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_status_global(self, dialect):
        """Global scope should render SHOW GLOBAL STATUS."""
        sql, _ = dialect.format_show_status(_expr({"session": False}))
        assert sql == "SHOW GLOBAL STATUS", f"unexpected SQL: {sql}"

    def test_status_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_status(_expr({"session": True, "like_pattern": "Uptime%"}))
        assert sql == "SHOW STATUS LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("Uptime%",), "LIKE pattern should be bound"

    def test_processlist(self, dialect):
        """SHOW PROCESSLIST should render without modifiers."""
        sql, params = dialect.format_show_processlist(_expr({}))
        assert sql == "SHOW PROCESSLIST", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_processlist_full(self, dialect):
        """FULL should appear for full processlist."""
        sql, _ = dialect.format_show_processlist(_expr({"full": True}))
        assert sql == "SHOW FULL PROCESSLIST", f"unexpected SQL: {sql}"

    def test_warnings(self, dialect):
        """SHOW WARNINGS should render without modifiers."""
        sql, params = dialect.format_show_warnings(_expr({}))
        assert sql == "SHOW WARNINGS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_warnings_limit(self, dialect):
        """A limit should be appended to SHOW WARNINGS."""
        sql, _ = dialect.format_show_warnings(_expr({"limit": 5}))
        assert sql == "SHOW WARNINGS LIMIT 5", f"unexpected SQL: {sql}"

    def test_errors(self, dialect):
        """SHOW ERRORS should render without modifiers."""
        sql, params = dialect.format_show_errors(_expr({}))
        assert sql == "SHOW ERRORS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_errors_limit(self, dialect):
        """A limit should be appended to SHOW ERRORS."""
        sql, _ = dialect.format_show_errors(_expr({"limit": 3}))
        assert sql == "SHOW ERRORS LIMIT 3", f"unexpected SQL: {sql}"

    def test_engines(self, dialect):
        """SHOW ENGINES should render."""
        sql, params = dialect.format_show_engines(_expr({}))
        assert sql == "SHOW ENGINES", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_charset_bare(self, dialect):
        """SHOW CHARACTER SET should render without modifiers."""
        sql, params = dialect.format_show_charset(_expr({}))
        assert sql == "SHOW CHARACTER SET", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_charset_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_charset(_expr({"like_pattern": "utf8%"}))
        assert sql == "SHOW CHARACTER SET LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("utf8%",), "LIKE pattern should be bound"

    def test_collation_bare(self, dialect):
        """SHOW COLLATION should render without modifiers."""
        sql, params = dialect.format_show_collation(_expr({}))
        assert sql == "SHOW COLLATION", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_collation_like(self, dialect):
        """A LIKE filter should be bound as a parameter."""
        sql, params = dialect.format_show_collation(_expr({"like_pattern": "utf8mb4%"}))
        assert sql == "SHOW COLLATION LIKE %s", f"unexpected SQL: {sql}"
        assert params == ("utf8mb4%",), "LIKE pattern should be bound"

    def test_grants_bare(self, dialect):
        """SHOW GRANTS should render without modifiers."""
        sql, params = dialect.format_show_grants(_expr({}))
        assert sql == "SHOW GRANTS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"

    def test_grants_user(self, dialect):
        """SHOW GRANTS FOR user should bind the user."""
        sql, params = dialect.format_show_grants(_expr({"user": "app"}))
        assert sql == "SHOW GRANTS FOR %s", f"unexpected SQL: {sql}"
        assert params == ("app",), "user should be bound"

    def test_grants_user_host(self, dialect):
        """SHOW GRANTS FOR user@host should bind user and host."""
        sql, params = dialect.format_show_grants(_expr({"user": "app", "host": "10.0.0.%"}))
        assert sql == "SHOW GRANTS FOR %s@%s", f"unexpected SQL: {sql}"
        assert params == ("app", "10.0.0.%"), "user and host should be bound"

    def test_plugins(self, dialect):
        """SHOW PLUGINS should render."""
        sql, params = dialect.format_show_plugins(_expr({}))
        assert sql == "SHOW PLUGINS", f"unexpected SQL: {sql}"
        assert params == (), "no parameters expected"