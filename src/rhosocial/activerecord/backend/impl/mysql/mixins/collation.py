# src/rhosocial/activerecord/backend/impl/mysql/mixins/collation.py
from typing import Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from ..collation import validate_mysql_collation_name


class MySQLCollationMixin:
    """MySQL collation expression support."""

    def supports_collate_expression(self) -> bool:
        """MySQL supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate MySQL collation names and return their SQL representation."""
        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        return validate_mysql_collation_name(expr.collation_name, getattr(self, "version", None))
