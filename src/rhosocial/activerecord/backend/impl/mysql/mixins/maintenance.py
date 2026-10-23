# src/rhosocial/activerecord/backend/impl/mysql/mixins/maintenance.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.objects import RelationObject
    from rhosocial.activerecord.backend.impl.mysql.expression.maintenance import (
        MySQLAnalyzeTableStatement,
        MySQLCheckTableStatement,
        MySQLChecksumTableStatement,
        MySQLOptimizeTableStatement,
        MySQLRepairTableStatement,
    )


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

    def _render_mysql_table_maintenance(self, expr) -> Tuple[str, tuple]:
        """Render the whole-table maintenance shape the five entries share.

        The public entries are one per kind; this is the shared assembly,
        reached only from them. The keyword comes from the node's own
        ``operation`` -- a class attribute each subclass declares -- so no
        entry has to be told which word it renders.
        """
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            feature = f"{operation} TABLE"
            raise UnsupportedFeatureError(self.name, feature)

        parts = [f"{operation} TABLE"]

        if expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)

        table_parts = [self._format_maintenance_table(t) for t in expr.tables]
        parts.append(", ".join(table_parts))

        if operation == "CHECK" and expr.options:
            parts.append(" ".join(option.value for option in expr.options))
        elif operation == "CHECKSUM" and expr.option:
            parts.append(expr.option.value)
        elif operation == "REPAIR" and expr.options:
            parts.append(" ".join(option.value for option in expr.options))

        return " ".join(parts), ()

    def format_mysql_analyze_table_statement(
        self,
        expr: "MySQLAnalyzeTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``ANALYZE TABLE``."""
        return self._render_mysql_table_maintenance(expr)

    def format_mysql_optimize_table_statement(
        self,
        expr: "MySQLOptimizeTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``OPTIMIZE TABLE``."""
        return self._render_mysql_table_maintenance(expr)

    def format_mysql_check_table_statement(
        self,
        expr: "MySQLCheckTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``CHECK TABLE`` with its optional modes."""
        return self._render_mysql_table_maintenance(expr)

    def format_mysql_checksum_table_statement(
        self,
        expr: "MySQLChecksumTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``CHECKSUM TABLE`` with its optional mode."""
        return self._render_mysql_table_maintenance(expr)

    def format_mysql_repair_table_statement(
        self,
        expr: "MySQLRepairTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``REPAIR TABLE`` with its optional modes."""
        return self._render_mysql_table_maintenance(expr)

    def _format_maintenance_table(self, table: "RelationObject") -> str:
        """Render one maintenance target through its own formatter.

        The object carries the catalog, so there is no tuple to unpack and no
        second copy of the qualification rule to drift out of step.
        """
        return table.to_sql()[0]