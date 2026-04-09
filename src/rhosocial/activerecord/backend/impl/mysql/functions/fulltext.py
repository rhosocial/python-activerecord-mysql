# src/rhosocial/activerecord/backend/impl/mysql/functions/fulltext.py
"""
MySQL full-text search function factories.

Functions: match_against
"""

from typing import Union, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core, operators

if TYPE_CHECKING:  # pragma: no cover
    from .dialect import MySQLDialect


def match_against(
    dialect: "MySQLDialect",
    columns: Union[str, List[str], "bases.BaseExpression"],
    search_string: str,
    mode: Optional[str] = None,
) -> "operators.RawSQLExpression":
    """
    Creates a MATCH ... AGAINST expression for full-text search.

    Usage rules:
    - Natural language mode (default): match_against(dialect, "content", "search term")
    - Boolean mode: match_against(dialect, "content", "+term -exclude", mode="BOOLEAN")
    - Query expansion: match_against(dialect, "content", "search term", mode="QUERY_EXPANSION")

    Args:
        dialect: The MySQL dialect instance
        columns: Column name(s) to search
        search_string: Search string
        mode: Search mode - "NATURAL_LANGUAGE", "BOOLEAN", or "QUERY_EXPANSION"

    Returns:
        A RawSQLExpression instance representing MATCH ... AGAINST

    Version: MySQL 5.6+ (with parser option in 5.7+)
    """
    if isinstance(columns, bases.BaseExpression):
        cols_sql, cols_params = columns.to_sql()
    elif isinstance(columns, list):
        cols_sql = ", ".join(dialect.format_identifier(c) for c in columns)
    else:
        cols_sql = dialect.format_identifier(columns)

    search_expr = core.Literal(dialect, search_string)
    search_sql, search_params = search_expr.to_sql()

    if mode is None or mode.upper() == "NATURAL_LANGUAGE":
        mode_str = "IN NATURAL LANGUAGE MODE"
    elif mode.upper() == "BOOLEAN":
        mode_str = "IN BOOLEAN MODE"
    elif mode.upper() == "QUERY_EXPANSION":
        mode_str = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
    else:
        mode_str = ""

    sql = f"MATCH({cols_sql}) AGAINST({search_sql} {mode_str})"
    return operators.RawSQLExpression(dialect, sql, search_params)


__all__ = [
    "match_against",
]