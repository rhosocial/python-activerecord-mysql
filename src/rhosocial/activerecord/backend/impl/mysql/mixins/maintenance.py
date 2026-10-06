# src/rhosocial/activerecord/backend/impl/mysql/mixins/maintenance.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.objects import RelationObject


class MySQLMaintenanceMixin:
    """MySQL whole-table maintenance statement support.

    Implements ANALYZE / CHECK / CHECKSUM / OPTIMIZE / REPAIR TABLE,
    distinct from the partition-level variants in MySQLPartitionMixin.

    Each table is a schema object, so a qualified name is a property of the
    object the caller built rather than a string the dialect has to re-split:
    ``ANALYZE TABLE ``db`.`users` `` comes from
    ``Table(dialect, "users", catalog_name="db")``.
    """

    def supports_analyze_table(self) -> bool:
        return True

    def supports_check_table(self) -> bool:
        return True

    def supports_checksum_table(self) -> bool:
        return True

    def supports_optimize_table(self) -> bool:
        return True

    def supports_repair_table(self) -> bool:
        return True

    def format_table_maintenance_statement(self, expr) -> Tuple[str, tuple]:
        """Format a whole-table maintenance statement (analyze/check/...)."""
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            feature = f"{operation} TABLE"
            raise UnsupportedFeatureError(self.name, feature)

        parts = [f"{operation} TABLE"]

        if hasattr(expr, "no_write_to_binlog") and expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)

        table_parts = [self._format_maintenance_table(t) for t in expr.tables]
        parts.append(", ".join(table_parts))

        if operation == "CHECK" and getattr(expr, "options", None):
            parts.append(" ".join(option.value for option in expr.options))
        elif operation == "CHECKSUM" and getattr(expr, "option", None):
            parts.append(expr.option.value)
        elif operation == "REPAIR" and getattr(expr, "options", None):
            parts.append(" ".join(option.value for option in expr.options))

        return " ".join(parts), ()

    def _format_maintenance_table(self, table: "RelationObject") -> str:
        """Render one maintenance target through its own formatter.

        The object carries the catalog, so there is no tuple to unpack and no
        second copy of the qualification rule to drift out of step.
        """
        return table.to_sql()[0]