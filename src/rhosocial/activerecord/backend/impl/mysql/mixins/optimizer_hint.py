# src/rhosocial/activerecord/backend/impl/mysql/mixins/optimizer_hint.py
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.impl.mysql.expression.optimizer_hint import (
        MySQLOptimizerHintExpression,
    )


class MySQLOptimizerHintMixin:
    """MySQL optimizer hint implementation."""

    def supports_optimizer_hint(self) -> bool:
        return self.version >= (5, 7, 0)

    def supports_hypergraph_optimizer(self) -> bool:
        return self.version >= (9, 7, 0)

    def format_optimizer_hint(self, expr: "MySQLOptimizerHintExpression") -> "Tuple[str, tuple]":
        """Format /*+ SET_VAR(...) */ hint clause."""
        parts = []
        for hint in expr.hints:
            parts.append(f"SET_VAR({hint.variable}='{hint.value}')")
        return "/*+ " + " ".join(parts) + " */", ()
