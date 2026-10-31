# src/rhosocial/activerecord/backend/impl/mysql/expression/introspection.py
"""MySQL introspection queries the core catalog does not model.

Core's catalog expressions cover the objects every engine shares: tables and
their columns, indexes, foreign keys, views, triggers. Two families are
MySQL's own and have no core object:

* **storage options** -- engine, row format, collation, auto-increment,
  comment and the size estimates, which live in ``information_schema.TABLES``
  beside the rows core already reads but are not part of core's projection;
* **partitions** -- which live in a separate ``information_schema.PARTITIONS``
  relation and belong to one table rather than to the database.

Both are expressed here and rendered by the dialect, so a MySQL query is a
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

from typing import Optional

from rhosocial.activerecord.backend.expression.introspection import (
    IntrospectionExpression,
)

__all__ = [
    "MySQLTableOptionsListQueryStatement",
    "MySQLTableOptionsInfoQueryStatement",
    "MySQLPartitionListQueryStatement",
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
