# src/rhosocial/activerecord/backend/impl/mysql/mixins/fulltext.py
from typing import Tuple


class MySQLFullTextSearchMixin:
    """MySQL full-text search mixin."""

    def supports_fulltext_index(self) -> bool:
        """Whether FULLTEXT index is supported (MySQL 5.6+ InnoDB)."""
        return self.version >= (5, 6, 0)

    def supports_fulltext_search(self) -> bool:
        """Whether full-text search (MATCH ... AGAINST) is supported.

        MySQL exposes FULLTEXT indexes and ``MATCH ... AGAINST`` together,
        so this delegates to :meth:`supports_fulltext_index`. Override in
        subclasses only if a future MySQL-flavoured backend decouples the
        two.
        """
        return self.supports_fulltext_index()

    def supports_fulltext_parser(self) -> bool:
        return self.version >= (5, 1, 0)

    def supports_fulltext_query_expansion(self) -> bool:
        return True

    def format_fulltext_index_options(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLFulltextIndexOptionsExpression` node."""
        from ..expression.fulltext import MySQLFulltextIndexOptionsExpression

        if not isinstance(expr, MySQLFulltextIndexOptionsExpression):
            raise TypeError(
                f"format_fulltext_index_options expects MySQLFulltextIndexOptionsExpression, "
                f"got {type(expr).__name__}"
            )

        col_parts = [self.format_identifier(c) for c in expr.columns]
        sql = f"FULLTEXT {self.format_identifier(expr.index_name)} ({', '.join(col_parts)})"
        if expr.parser_name:
            sql += f" WITH PARSER {self.format_identifier(expr.parser_name)}"
        return sql, ()

    def format_match_against(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLMatchAgainstExpression` node."""
        cols_sql = ", ".join(self.format_identifier(c) for c in expr.columns)

        placeholder = self.get_parameter_placeholder()
        search_sql = placeholder
        search_params = (expr.search_string,)

        mode = expr.mode
        if mode:
            mode_upper = mode.upper()
            if mode_upper == "NATURAL_LANGUAGE":
                mode_str = "IN NATURAL LANGUAGE MODE"
            elif mode_upper == "BOOLEAN":
                mode_str = "IN BOOLEAN MODE"
            elif mode_upper == "QUERY_EXPANSION":
                mode_str = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
            else:
                mode_str = ""
        else:
            mode_str = "IN NATURAL LANGUAGE MODE"

        sql = f"MATCH({cols_sql}) AGAINST({search_sql} {mode_str})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, search_params
