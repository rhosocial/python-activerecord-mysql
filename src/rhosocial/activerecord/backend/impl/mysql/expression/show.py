# src/rhosocial/activerecord/backend/impl/mysql/expression/show.py
"""
MySQL SHOW command expression classes.

This module defines expression classes for MySQL SHOW commands.
Each expression class collects parameters and delegates SQL generation
to the dialect's format_show_* methods.

Expression classes inherit from BaseExpression and implement to_sql(),
following the expression-dialect pattern used throughout the codebase.

Key design:
- **Every parameter is a constructor parameter.** There is no fluent builder:
  an instance is complete the moment ``get_params()`` reads it back, so the
  artifact is the constructor call and nothing else. The ``with_like`` /
  ``with_session`` / ``with_global_status`` setters that used to fill these
  same fields in afterwards are gone -- a parameter that can be changed after
  construction is a second, invisible constructor.
- Each parameter is stored under its **own name**, which is what
  ``get_params()`` reads. A parameter the class did not store under its own
  name is a defect, not a spelling.
- A subclass that supports a schema qualifier declares ``schema`` in its
  own ``__init__``: ``get_params()`` reads the class's own signature, so a
  parameter declared only on the base would be invisible to the formatter
  -- and the qualifier the caller passed was silently dropped.
- Expressions collect parameters (table_name, schema, options)
- Expressions hold a dialect reference
- to_sql() delegates to dialect.format_show_* methods
- Dialect handles actual SQL generation
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:
    from ..dialect import MySQLDialect


class ShowExpression(BaseExpression):
    """Base class for MySQL SHOW command expressions.

    All MySQL SHOW expressions inherit from this class. Parameters are
    declared by each ``__init__`` -- that signature is the wire contract, so a
    parameter is always passed where the node is built rather than filled in
    afterwards.
    """

    def __init__(self, dialect: "MySQLDialect", *, schema: Optional[str] = None):
        super().__init__(dialect)
        self.schema: Optional[str] = schema

    # Concrete subclasses declare their dialect formatting method by
    # overriding the `format_method` property (inherited from BaseExpression).


class ShowCreateTableStatement(ShowExpression):
    """Expression for SHOW CREATE TABLE command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table_name: str,
        *,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.table_name: str = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_create_table_statement"


class ShowCreateViewStatement(ShowExpression):
    """Expression for SHOW CREATE VIEW command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        view_name: str,
        *,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.view_name: str = view_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_create_view_statement"


class ShowColumnsStatement(ShowExpression):
    """Expression for SHOW [FULL] COLUMNS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table_name: str,
        *,
        schema: Optional[str] = None,
        full: bool = False,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.table_name: str = table_name
        self.full: bool = full
        self.like_pattern: Optional[str] = like_pattern

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_columns_statement"


class ShowIndexStatement(ShowExpression):
    """Expression for SHOW INDEX command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        table_name: str,
        *,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.table_name: str = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_index_statement"


class ShowTablesStatement(ShowExpression):
    """Expression for SHOW [FULL] TABLES command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        schema: Optional[str] = None,
        full: bool = False,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.full: bool = full
        self.like_pattern: Optional[str] = like_pattern

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_tables_statement"


class ShowDatabasesStatement(ShowExpression):
    """Expression for SHOW DATABASES command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_databases_statement"


class ShowTableStatusStatement(ShowExpression):
    """Expression for SHOW TABLE STATUS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        schema: Optional[str] = None,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.like_pattern: Optional[str] = like_pattern

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_table_status_statement"


class ShowTriggersStatement(ShowExpression):
    """Expression for SHOW TRIGGERS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        schema: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.table_name: Optional[str] = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_triggers_statement"


class ShowCreateTriggerStatement(ShowExpression):
    """Expression for SHOW CREATE TRIGGER command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        trigger_name: str,
        *,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema=schema)
        self.trigger_name: str = trigger_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_create_trigger_statement"


class ShowVariablesStatement(ShowExpression):
    """Expression for SHOW [GLOBAL] VARIABLES command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
        session: bool = True,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern
        self.session: bool = session

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_variables_statement"


class ShowStatusStatement(ShowExpression):
    """Expression for SHOW [GLOBAL] STATUS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
        session: bool = True,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern
        self.session: bool = session

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_status_statement"


class ShowProcessListStatement(ShowExpression):
    """Expression for SHOW [FULL] PROCESSLIST command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        full: bool = False,
    ):
        super().__init__(dialect)
        self.full: bool = full

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_process_list_statement"


class ShowWarningsStatement(ShowExpression):
    """Expression for SHOW WARNINGS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        limit: Optional[int] = None,
    ):
        super().__init__(dialect)
        self.limit: Optional[int] = limit

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_warnings_statement"


class ShowErrorsStatement(ShowExpression):
    """Expression for SHOW ERRORS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        limit: Optional[int] = None,
    ):
        super().__init__(dialect)
        self.limit: Optional[int] = limit

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_errors_statement"


class ShowEnginesStatement(ShowExpression):
    """Expression for SHOW ENGINES command."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_engines_statement"


class ShowCharsetStatement(ShowExpression):
    """Expression for SHOW CHARACTER SET command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_charset_statement"


class ShowCollationStatement(ShowExpression):
    """Expression for SHOW COLLATION command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_collation_statement"


class ShowGrantsStatement(ShowExpression):
    """Expression for SHOW GRANTS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        user: Optional[str] = None,
        host: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.user: Optional[str] = user
        self.host: Optional[str] = host

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_grants_statement"


class ShowPluginsStatement(ShowExpression):
    """Expression for SHOW PLUGINS command."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_plugins_statement"


class ShowBinaryLogsStatement(ShowExpression):
    """Expression for SHOW BINARY LOGS command.

    Its own node rather than a flag on another one: the command takes no
    parameters at all, so what distinguishes it from its neighbours is the
    command itself, which is exactly what a class names.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_binary_logs_statement"


class ShowMasterStatusStatement(ShowExpression):
    """Expression for SHOW MASTER STATUS command.

    MySQL 8.4 removed this command in favour of
    ``performance_schema.log_status``; the node still renders the command,
    and the caller chooses by server version which of the two to execute.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_master_status_statement"


class ShowSlaveStatusStatement(ShowExpression):
    """Expression for SHOW SLAVE STATUS command.

    MySQL 8.0.22 added ``SHOW REPLICA STATUS`` as the preferred spelling and
    9.0 removed ``SHOW SLAVE STATUS``; this node renders the older command,
    because it is the one every server in this backend's supported range
    accepts. A server that has dropped it is asked through
    ``performance_schema`` instead.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_slave_status_statement"
