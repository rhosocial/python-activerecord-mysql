# src/rhosocial/activerecord/backend/impl/mysql/expression/show.py
"""
MySQL SHOW command expression classes.

This module defines expression classes for MySQL SHOW commands.
Each expression class collects parameters and delegates SQL generation
to the dialect's format_show_* methods.

Expression classes inherit from BaseExpression and implement to_sql(),
following the expression-dialect pattern used throughout the codebase.

Key design:
- Every constructor parameter is stored under its **own name**: the
  attribute ``get_params()`` reads and the one an artifact carries. The
  fluent setters that used to share these names (``schema()``, ``full()``,
  ``like()``, ...) are ``with_*`` now, mirroring core's own introspection
  expressions -- the parameter owns the plain name, the setter keeps its
  ergonomics, and neither shadows the other. The underscore-prefixed
  storage this module used is what core's introspection-based
  ``get_params()`` refuses to paper over: a parameter the class did not
  store under its own name is a defect, not a spelling.
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

    All MySQL SHOW expressions inherit from this class and provide
    fluent ``with_*`` methods for setting parameters; each parameter is
    stored under the name it was declared with.
    """

    def __init__(self, dialect: "MySQLDialect", *, schema: Optional[str] = None):
        super().__init__(dialect)
        self.schema: Optional[str] = schema

    def with_schema(self, name: str) -> "ShowExpression":
        """Set the schema/database name.

        Args:
            name: Schema or database name.

        Returns:
            Self for method chaining.
        """
        self.schema = name
        return self

    # Concrete subclasses declare their dialect formatting method by
    # overriding the `format_method` property (inherited from BaseExpression).


class ShowCreateTableExpression(ShowExpression):
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
        return "format_show_create_table"



class ShowCreateViewExpression(ShowExpression):
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
        return "format_show_create_view"



class ShowColumnsExpression(ShowExpression):
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

    def with_full(self, value: bool = True) -> "ShowColumnsExpression":
        """Include additional column information (privileges, comments)."""
        self.full = value
        return self

    def with_like(self, pattern: str) -> "ShowColumnsExpression":
        """Filter columns by name pattern."""
        self.like_pattern = pattern
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_columns"



class ShowIndexExpression(ShowExpression):
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
        return "format_show_index"



class ShowTablesExpression(ShowExpression):
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

    def with_full(self, value: bool = True) -> "ShowTablesExpression":
        """Include table type (BASE TABLE or VIEW)."""
        self.full = value
        return self

    def with_like(self, pattern: str) -> "ShowTablesExpression":
        """Filter tables by name pattern."""
        self.like_pattern = pattern
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_tables"



class ShowDatabasesExpression(ShowExpression):
    """Expression for SHOW DATABASES command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern

    def with_like(self, pattern: str) -> "ShowDatabasesExpression":
        """Filter databases by name pattern."""
        self.like_pattern = pattern
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_databases"



class ShowTableStatusExpression(ShowExpression):
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

    def with_like(self, pattern: str) -> "ShowTableStatusExpression":
        """Filter tables by name pattern."""
        self.like_pattern = pattern
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_table_status"



class ShowTriggersExpression(ShowExpression):
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

    def with_table_name(self, table_name: str) -> "ShowTriggersExpression":
        """Filter triggers for a specific table."""
        self.table_name = table_name
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_triggers"



class ShowCreateTriggerExpression(ShowExpression):
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
        return "format_show_create_trigger"



class ShowVariablesExpression(ShowExpression):
    """Expression for SHOW VARIABLES command."""

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

    def with_like(self, pattern: str) -> "ShowVariablesExpression":
        """Filter variables by name pattern."""
        self.like_pattern = pattern
        return self

    def with_session(self, value: bool = True) -> "ShowVariablesExpression":
        """Show session variables (default)."""
        self.session = value
        return self

    def with_global_vars(self) -> "ShowVariablesExpression":
        """Show global variables."""
        self.session = False
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_variables"



class ShowStatusExpression(ShowExpression):
    """Expression for SHOW STATUS command."""

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

    def with_like(self, pattern: str) -> "ShowStatusExpression":
        """Filter status by name pattern."""
        self.like_pattern = pattern
        return self

    def with_session(self, value: bool = True) -> "ShowStatusExpression":
        """Show session status (default)."""
        self.session = value
        return self

    def with_global_status(self) -> "ShowStatusExpression":
        """Show global status."""
        self.session = False
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_status"



class ShowProcessListExpression(ShowExpression):
    """Expression for SHOW PROCESSLIST command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        full: bool = False,
    ):
        super().__init__(dialect)
        self.full: bool = full

    def with_full(self, value: bool = True) -> "ShowProcessListExpression":
        """Include full query text."""
        self.full = value
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_processlist"



class ShowWarningsExpression(ShowExpression):
    """Expression for SHOW WARNINGS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        limit: Optional[int] = None,
    ):
        super().__init__(dialect)
        self.limit: Optional[int] = limit

    def with_limit(self, count: int) -> "ShowWarningsExpression":
        """Limit number of warnings returned."""
        self.limit = count
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_warnings"



class ShowErrorsExpression(ShowExpression):
    """Expression for SHOW ERRORS command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        limit: Optional[int] = None,
    ):
        super().__init__(dialect)
        self.limit: Optional[int] = limit

    def with_limit(self, count: int) -> "ShowErrorsExpression":
        """Limit number of errors returned."""
        self.limit = count
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_errors"



class ShowEnginesExpression(ShowExpression):
    """Expression for SHOW ENGINES command."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_engines"



class ShowCharsetExpression(ShowExpression):
    """Expression for SHOW CHARACTER SET command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern

    def with_like(self, pattern: str) -> "ShowCharsetExpression":
        """Filter character sets by name pattern."""
        self.like_pattern = pattern
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_charset"



class ShowCollationExpression(ShowExpression):
    """Expression for SHOW COLLATION command."""

    def __init__(
        self,
        dialect: "MySQLDialect",
        *,
        like_pattern: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.like_pattern: Optional[str] = like_pattern

    def with_like(self, pattern: str) -> "ShowCollationExpression":
        """Filter collations by name pattern."""
        self.like_pattern = pattern
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_collation"



class ShowGrantsExpression(ShowExpression):
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

    def with_user(self, user: str, host: Optional[str] = None) -> "ShowGrantsExpression":
        """Show grants for a specific user."""
        self.user = user
        self.host = host
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_grants"



class ShowPluginsExpression(ShowExpression):
    """Expression for SHOW PLUGINS command."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_show_plugins"
