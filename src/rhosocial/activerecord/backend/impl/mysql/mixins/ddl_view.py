# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_view.py
from typing import Tuple


class MySQLViewMixin:
    """MySQL view support."""

    def supports_or_replace_view(self) -> bool:
        """Whether CREATE OR REPLACE VIEW is supported."""
        return True

    def supports_create_or_replace_view(self) -> bool:
        """Whether CREATE OR REPLACE VIEW is supported."""
        return True

    def supports_if_not_exists_view(self) -> bool:
        """MySQL does not support IF NOT EXISTS for views."""
        return False

    def supports_temporary_view(self) -> bool:
        """Whether TEMPORARY views are supported."""
        return True

    def supports_if_exists_view(self) -> bool:
        """Whether DROP VIEW IF EXISTS is supported."""
        return True

    def supports_view_check_option(self) -> bool:
        """Whether WITH CHECK OPTION is supported."""
        return True

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement for MySQL."""
        parts = ["CREATE"]

        if expr.temporary:
            parts.append("TEMPORARY")

        if expr.replace and self.supports_create_or_replace_view():
            parts.append("OR REPLACE")

        parts.append("VIEW")
        parts.append(self.format_identifier(expr.view_name))

        if expr.column_aliases:
            cols = ", ".join(self.format_identifier(c) for c in expr.column_aliases)
            parts.append(f"({cols})")

        query_sql, query_params = expr.query.to_sql()
        parts.append(f"AS {query_sql}")

        if expr.options and expr.options.check_option:
            if not self.supports_view_check_option():
                from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name, "WITH CHECK OPTION",
                    f"{self.name} does not support WITH CHECK OPTION.",
                )
            check_option = expr.options.check_option.value
            parts.append(f"WITH {check_option} CHECK OPTION")

        return " ".join(parts), query_params

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement for MySQL."""
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.view_name))
        return " ".join(parts), ()
