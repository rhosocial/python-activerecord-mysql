# src/rhosocial/activerecord/backend/impl/mysql/expression/introspection.py
"""MySQL introspection queries the core catalog does not model.

Core's catalog expressions cover the objects every engine shares: tables and
their columns, indexes, foreign keys, views, triggers. The families here are
MySQL's own and have no core object:

* **storage options** -- engine, row format, collation, auto-increment,
  comment and the size estimates, which live in ``information_schema.TABLES``
  beside the rows core already reads but are not part of core's projection;
* **partitions** -- which live in a separate ``information_schema.PARTITIONS``
  relation and belong to one table rather than to the database;
* **routines** -- procedures and functions from ``information_schema.ROUTINES``,
  with their parameters read from ``information_schema.PARAMETERS``;
* **constraints** -- ``information_schema.TABLE_CONSTRAINTS`` joined to
  ``CHECK_CONSTRAINTS`` for the CHECK expression and to ``KEY_COLUMN_USAGE``
  for the column list.

Each is expressed here and rendered by the dialect, so a MySQL query is a
statement object with a ``format_method`` and the SQL comes out of the
expression system: no caller assembles text, and the dialect owns the
placeholder syntax and the quoting of ``information_schema``.

The object reads one database at a time -- MySQL's only namespace level above
a table -- so every class takes the database and, where the question is about
one table, its name.

Example:
    >>> expr = MySQLTableOptionsListQueryStatement(dialect, schema="shop")
    >>> sql, params = expr.to_sql()
"""

from typing import Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.introspection import (
    IntrospectionExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase

__all__ = [
    "MySQLTableOptionsListQueryStatement",
    "MySQLTableOptionsInfoQueryStatement",
    "MySQLPartitionListQueryStatement",
    "MySQLRoutineListQueryStatement",
    "MySQLRoutineInfoQueryStatement",
    "MySQLConstraintListQueryStatement",
]


class MySQLTableOptionsListQueryStatement(IntrospectionExpression):
    """Storage options for every base table in one database.

    ``TABLE_TYPE = 'BASE TABLE'`` is part of the question rather than a filter
    applied afterwards: the relation also carries views, and a view has no
    engine to report.
    """

    def __init__(self, dialect: "SQLDialectBase", schema: Optional[str] = None):
        """
        Args:
            dialect: The SQL dialect to use for formatting.
            schema: The database to read, or ``None`` to leave the resolution
                to the formatter.
        """
        super().__init__(dialect, schema=schema)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_options_list_query_statement"


class MySQLTableOptionsInfoQueryStatement(IntrospectionExpression):
    """Storage options for one base table.

    Same projection as the list form, narrowed by name. An absent table then
    yields no rows rather than a second query against a different relation.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
    ):
        """
        Args:
            dialect: The SQL dialect to use for formatting.
            table_name: The table whose options are wanted.
            schema: The database to read, or ``None`` to leave the resolution
                to the formatter.
        """
        super().__init__(dialect, schema=schema)
        self.table_name: str = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_options_info_query_statement"


class MySQLPartitionListQueryStatement(IntrospectionExpression):
    """Partitions and subpartitions of one table.

    A non-partitioned table is reported by one row whose ``PARTITION_NAME`` is
    NULL, so the predicate excludes it rather than filtering afterwards: an
    empty result then means exactly "this table is not partitioned", and the
    order is the engine's own ordinal pair.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
    ):
        """
        Args:
            dialect: The SQL dialect to use for formatting.
            table_name: The table whose partitions are wanted.
            schema: The database to read, or ``None`` to leave the resolution
                to the formatter.
        """
        super().__init__(dialect, schema=schema)
        self.table_name: str = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_list_query_statement"


class MySQLRoutineListQueryStatement(IntrospectionExpression):
    """Routines in one database, with their parameters.

    ``ROUTINES`` carries the routine's own facts and ``PARAMETERS`` carries
    the arguments; the two are joined here so a listing is one question rather
    than one query per routine. A function also reports its return value in
    ``PARAMETERS`` at ordinal zero, which is why the ordering starts at that
    ordinal -- the parser reads zero as the return value, not as an argument.
    """

    def __init__(self, dialect: "SQLDialectBase", schema: Optional[str] = None):
        """
        Args:
            dialect: The SQL dialect to use for formatting.
            schema: The database to read, or ``None`` to leave the resolution
                to the formatter.
        """
        super().__init__(dialect, schema=schema)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_routine_list_query_statement"


class MySQLRoutineInfoQueryStatement(IntrospectionExpression):
    """One routine, narrowed by name and optionally by kind.

    A naming collision is possible: MySQL keeps procedures and functions in
    separate object kinds, so the same name may exist in both. ``kind``
    disambiguates; when it is omitted the parser receives every matching kind
    and reports the first in the engine's ordering rather than inventing an
    answer.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        routine_name: str,
        kind: Optional[str] = None,
        schema: Optional[str] = None,
    ):
        """
        Args:
            dialect: The SQL dialect to use for formatting.
            routine_name: The routine whose facts are wanted.
            kind: ``"PROCEDURE"`` or ``"FUNCTION"`` to narrow a name shared by
                both kinds, or ``None`` to ask for either.
            schema: The database to read, or ``None`` to leave the resolution
                to the formatter.
        """
        super().__init__(dialect, schema=schema)
        self.routine_name: str = routine_name
        self.kind: Optional[str] = kind

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_routine_info_query_statement"


class MySQLConstraintListQueryStatement(IntrospectionExpression):
    """Table constraints in one database, optionally narrowed to one table.

    ``TABLE_CONSTRAINTS`` names the constraint and its type;
    ``CHECK_CONSTRAINTS`` supplies the expression a CHECK constraint holds;
    and ``KEY_COLUMN_USAGE`` supplies the column list that primary-key,
    unique and foreign-key constraints have. Both side relations are joined
    with a LEFT JOIN because a constraint has rows in at most one of them --
    an inner join would drop the constraint kind whose side relation it is not.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ):
        """
        Args:
            dialect: The SQL dialect to use for formatting.
            table_name: A table to narrow the listing to, or ``None`` for every
                constraint in the database.
            schema: The database to read, or ``None`` to leave the resolution
                to the formatter.
        """
        super().__init__(dialect, schema=schema)
        self.table_name: Optional[str] = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_constraint_list_query_statement"
