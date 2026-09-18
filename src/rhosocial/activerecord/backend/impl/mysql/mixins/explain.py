# src/rhosocial/activerecord/backend/impl/mysql/mixins/explain.py
from typing import Tuple


class MySQLExplainMixin:
    """MySQL EXPLAIN statement support."""

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        return self.version >= (8, 0, 18)

    def supports_explain_format(self, format_type: str) -> bool:
        """Check if specific EXPLAIN format is supported."""
        format_type_upper = format_type.upper()
        if format_type_upper == "TEXT":
            return True
        elif format_type_upper == "JSON":
            return self.version >= (5, 6, 5)
        elif format_type_upper == "TREE":
            return self.version >= (8, 0, 16)
        else:
            return False

    def format_explain_statement(self, explain_expr: "ExplainExpression") -> tuple:
        """Build the MySQL EXPLAIN SQL string and return (sql, params)."""
        from rhosocial.activerecord.backend.expression.statements import ExplainType

        statement_sql, statement_params = explain_expr.statement.to_sql()
        options = explain_expr.options
        parts = ["EXPLAIN"]

        needs_traditional_format = False
        if options is None:
            needs_traditional_format = self.version >= (9, 0, 0)
        else:
            if options.analyze:
                parts.append("ANALYZE")

            if options.format is not None:
                fmt_name = options.format.name if hasattr(options.format, "name") else str(options.format)
                parts.append(f"FORMAT={fmt_name.upper()}")
            elif options.type is not None and options.type == ExplainType.QUERY_PLAN:
                pass
            else:
                needs_traditional_format = self.version >= (9, 0, 0)

        if needs_traditional_format:
            parts.append("FORMAT=TRADITIONAL")

        return f"{' '.join(parts)} {statement_sql}", statement_params
