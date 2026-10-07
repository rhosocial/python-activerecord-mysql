# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_view.py
from typing import Tuple

from rhosocial.activerecord.backend.expression.objects import View

from .object_kind import require_kind


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
        """Format CREATE VIEW statement for MySQL.

        Raises:
            TypeError: ``expr.view`` is not a View. A Table there would render
                through its own formatter and produce ``CREATE VIEW `users```,
                which is a well-formed statement creating a view over something
                the caller never named.
        """
        require_kind(expr.view, View, "CreateViewExpression.view")
        parts = ["CREATE"]

        if expr.temporary:
            parts.append("TEMPORARY")

        if expr.replace and self.supports_create_or_replace_view():
            parts.append("OR REPLACE")

        parts.append("VIEW")
        parts.append(expr.view.to_sql()[0])

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
        """Format DROP VIEW statement for MySQL.

        The CASCADE / RESTRICT pair is consumed here: MySQL does not provide
        either behavior (``supports_cascade_view`` / ``supports_restrict_view``
        answer False), so a caller who asks for one spelling is refused by name
        rather than silently dropped.

        Raises:
            TypeError: ``expr.view`` is not a View; a Table there would render
                through its own formatter and be dropped by name.
            UnsupportedFeatureError: If the dialect does not accept the
                requested behavior keyword.
        """
        require_kind(expr.view, View, "DropViewExpression.view")
        if expr.cascade and not self.supports_cascade_view():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name, "DROP VIEW CASCADE",
                f"{self.name} does not support DROP VIEW CASCADE.",
            )
        if expr.restrict and not self.supports_restrict_view():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name, "DROP VIEW RESTRICT",
                f"{self.name} does not support DROP VIEW RESTRICT.",
            )
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.view.to_sql()[0])
        if expr.cascade:
            parts.append("CASCADE")
        elif expr.restrict:
            parts.append("RESTRICT")
        return " ".join(parts), ()
