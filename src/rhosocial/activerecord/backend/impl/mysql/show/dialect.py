# src/rhosocial/activerecord/backend/impl/mysql/show/dialect.py
"""
MySQL SHOW command dialect mixin.

This module provides the MySQL-specific SQL generation for SHOW commands.
It implements the format_show_* methods that are called by the expression classes.

The mixin is added to MySQLDialect to provide SHOW command support.
All methods follow the pattern:
- Accept an expression parameter
- Extract parameters from expression.get_params()
- Generate SQL string and parameter tuple
- Return (sql, params) tuple
"""

from typing import Any, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.objects import (
    SchemaObject,
    Trigger,
    View,
    Table,
)

if TYPE_CHECKING:
    from ..expression.show import (
        ShowCreateTableExpression,
        ShowCreateViewExpression,
        ShowColumnsExpression,
        ShowIndexExpression,
        ShowTablesExpression,
        ShowDatabasesExpression,
        ShowTableStatusExpression,
        ShowTriggersExpression,
        ShowCreateTriggerExpression,
        ShowVariablesExpression,
        ShowStatusExpression,
        ShowProcessListExpression,
        ShowWarningsExpression,
        ShowErrorsExpression,
        ShowEnginesExpression,
        ShowCharsetExpression,
        ShowCollationExpression,
        ShowGrantsExpression,
        ShowPluginsExpression,
    )


class MySQLShowDialectMixin:
    """MySQL SHOW command SQL generation mixin.

    Provides format_show_* methods for generating MySQL SHOW command SQL.
    All methods take an expression parameter and return (sql, params) tuple.

    This mixin is added to MySQLDialect to provide SHOW functionality.
    """

    def _format_show_target(self, target: Any, schema: Any, kind: type) -> str:
        """Render the object a SHOW variant is about.

        ``SHOW CREATE TABLE``, ``SHOW COLUMNS FROM`` and ``SHOW INDEX FROM``
        all take a qualified object name. Building ``schema``.``name`` here by
        hand would be a second copy of the qualification rule, so the target is
        normalised to a schema object of the right *kind*, which renders itself
        through its own ``format_<kind>_object``.

        Args:
            target: The object being shown, either already a schema object or
                a bare name string.
            schema: The database name carried separately by the expression, or
                ``None``. Ignored when *target* is already an object, because
                an object knows its own database and two disagreeing sources
                for one namespace is the bug this indirection exists to remove.
            kind: The schema-object class to build when *target* is a string.
        """
        if isinstance(target, SchemaObject):
            return target.to_sql()[0]
        return kind(self, target, catalog_name=schema or None).to_sql()[0]

    # ========== SHOW CREATE Statements ==========

    def format_show_create_table(self, expr: "ShowCreateTableExpression") -> Tuple[str, tuple]:
        """Format SHOW CREATE TABLE statement."""
        params = expr.get_params()
        table_name = params["table_name"]
        schema = params.get("schema")

        return f"SHOW CREATE TABLE {self._format_show_target(table_name, schema, Table)}", ()

    def format_show_create_view(self, expr: "ShowCreateViewExpression") -> Tuple[str, tuple]:
        """Format SHOW CREATE VIEW statement."""
        params = expr.get_params()
        view_name = params["view_name"]
        schema = params.get("schema")

        return f"SHOW CREATE VIEW {self._format_show_target(view_name, schema, View)}", ()

    def format_show_create_trigger(self, expr: "ShowCreateTriggerExpression") -> Tuple[str, tuple]:
        """Format SHOW CREATE TRIGGER statement."""
        params = expr.get_params()
        trigger_name = params["trigger_name"]
        schema = params.get("schema")

        return f"SHOW CREATE TRIGGER {self._format_show_target(trigger_name, schema, Trigger)}", ()

    # ========== SHOW COLUMNS/INDEX ==========

    def format_show_columns(self, expr: "ShowColumnsExpression") -> Tuple[str, tuple]:
        """Format SHOW [FULL] COLUMNS statement."""
        params = expr.get_params()
        table_name = params["table_name"]
        schema = params.get("schema")
        full = params.get("full", False)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if full:
            parts.append("FULL")
        parts.append("COLUMNS FROM")
        parts.append(self._format_show_target(table_name, schema, Table))

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_index(self, expr: "ShowIndexExpression") -> Tuple[str, tuple]:
        """Format SHOW INDEX statement."""
        params = expr.get_params()
        table_name = params["table_name"]
        schema = params.get("schema")

        return f"SHOW INDEX FROM {self._format_show_target(table_name, schema, Table)}", ()

    # ========== SHOW TABLES/DATABASES ==========

    def format_show_tables(self, expr: "ShowTablesExpression") -> Tuple[str, tuple]:
        """Format SHOW [FULL] TABLES statement."""
        params = expr.get_params()
        schema = params.get("schema")
        full = params.get("full", False)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if full:
            parts.append("FULL")
        parts.append("TABLES")
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_databases(self, expr: "ShowDatabasesExpression") -> Tuple[str, tuple]:
        """Format SHOW DATABASES statement."""
        params = expr.get_params()
        like_pattern = params.get("like_pattern")

        if like_pattern:
            return f"SHOW DATABASES LIKE {self.p()}", (like_pattern,)
        return "SHOW DATABASES", ()

    def format_show_table_status(self, expr: "ShowTableStatusExpression") -> Tuple[str, tuple]:
        """Format SHOW TABLE STATUS statement."""
        params = expr.get_params()
        schema = params.get("schema")
        like_pattern = params.get("like_pattern")

        parts = ["SHOW TABLE STATUS"]
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    # ========== SHOW TRIGGERS ==========

    def format_show_triggers(self, expr: "ShowTriggersExpression") -> Tuple[str, tuple]:
        """Format SHOW TRIGGERS statement."""
        params = expr.get_params()
        schema = params.get("schema")
        table_name = params.get("table_name")

        parts = ["SHOW TRIGGERS"]
        if schema:
            parts.append(f"FROM {self.format_identifier(schema)}")

        sql_params = ()
        if table_name:
            parts.append(f"LIKE {self.p()}")
            sql_params = (table_name,)

        return " ".join(parts), sql_params

    # ========== SHOW VARIABLES/STATUS ==========

    def format_show_variables(self, expr: "ShowVariablesExpression") -> Tuple[str, tuple]:
        """Format SHOW VARIABLES statement."""
        params = expr.get_params()
        session = params.get("session", True)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if not session:
            parts.append("GLOBAL")
        parts.append("VARIABLES")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    def format_show_status(self, expr: "ShowStatusExpression") -> Tuple[str, tuple]:
        """Format SHOW STATUS statement."""
        params = expr.get_params()
        session = params.get("session", True)
        like_pattern = params.get("like_pattern")

        parts = ["SHOW"]
        if not session:
            parts.append("GLOBAL")
        parts.append("STATUS")

        sql_params = ()
        if like_pattern:
            parts.append(f"LIKE {self.p()}")
            sql_params = (like_pattern,)

        return " ".join(parts), sql_params

    # ========== SHOW PROCESSLIST/WARNINGS/ERRORS ==========

    def format_show_processlist(self, expr: "ShowProcessListExpression") -> Tuple[str, tuple]:
        """Format SHOW PROCESSLIST statement."""
        params = expr.get_params()
        full = params.get("full", False)

        if full:
            return "SHOW FULL PROCESSLIST", ()
        return "SHOW PROCESSLIST", ()

    def format_show_warnings(self, expr: "ShowWarningsExpression") -> Tuple[str, tuple]:
        """Format SHOW WARNINGS statement."""
        params = expr.get_params()
        limit = params.get("limit")

        if limit is not None:
            return f"SHOW WARNINGS LIMIT {limit}", ()
        return "SHOW WARNINGS", ()

    def format_show_errors(self, expr: "ShowErrorsExpression") -> Tuple[str, tuple]:
        """Format SHOW ERRORS statement."""
        params = expr.get_params()
        limit = params.get("limit")

        if limit is not None:
            return f"SHOW ERRORS LIMIT {limit}", ()
        return "SHOW ERRORS", ()

    # ========== SHOW ENGINES/CHARSET/COLLATION ==========

    def format_show_engines(self, expr: "ShowEnginesExpression") -> Tuple[str, tuple]:
        """Format SHOW ENGINES statement."""
        return "SHOW ENGINES", ()

    def format_show_charset(self, expr: "ShowCharsetExpression") -> Tuple[str, tuple]:
        """Format SHOW CHARACTER SET statement."""
        params = expr.get_params()
        like_pattern = params.get("like_pattern")

        if like_pattern:
            return f"SHOW CHARACTER SET LIKE {self.p()}", (like_pattern,)
        return "SHOW CHARACTER SET", ()

    def format_show_collation(self, expr: "ShowCollationExpression") -> Tuple[str, tuple]:
        """Format SHOW COLLATION statement."""
        params = expr.get_params()
        like_pattern = params.get("like_pattern")

        if like_pattern:
            return f"SHOW COLLATION LIKE {self.p()}", (like_pattern,)
        return "SHOW COLLATION", ()

    # ========== SHOW GRANTS/PLUGINS ==========

    def format_show_grants(self, expr: "ShowGrantsExpression") -> Tuple[str, tuple]:
        """Format SHOW GRANTS statement."""
        params = expr.get_params()
        user = params.get("user")
        host = params.get("host")

        if user:
            if host:
                return f"SHOW GRANTS FOR {self.p()}@{self.p()}", (user, host)
            return f"SHOW GRANTS FOR {self.p()}", (user,)
        return "SHOW GRANTS", ()

    def format_show_plugins(self, expr: "ShowPluginsExpression") -> Tuple[str, tuple]:
        """Format SHOW PLUGINS statement."""
        return "SHOW PLUGINS", ()
