# src/rhosocial/activerecord/backend/impl/mysql/mixins/maintenance.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.expression.maintenance import (
        MySQLAnalyzeTableStatement,
        MySQLChecksumTableStatement,
        MySQLCheckTableStatement,
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

    def format_mysql_analyze_table_statement(
        self,
        expr: "MySQLAnalyzeTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``ANALYZE TABLE``.

        The support gate is keyed on the node's own ``operation`` so an
        unknown keyword dispatched here still fails as an unsupported feature
        rather than rendering an unrelated statement.
        """
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            raise UnsupportedFeatureError(self.name, f"{operation} TABLE")

        parts = ["ANALYZE TABLE"]
        if expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)
        table_parts = [table.to_sql()[0] for table in expr.tables]
        parts.append(", ".join(table_parts))
        return " ".join(parts), ()

    def format_mysql_optimize_table_statement(
        self,
        expr: "MySQLOptimizeTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``OPTIMIZE TABLE``.

        The support gate is keyed on the node's own ``operation`` so an
        unknown keyword dispatched here still fails as an unsupported feature
        rather than rendering an unrelated statement.
        """
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            raise UnsupportedFeatureError(self.name, f"{operation} TABLE")

        parts = ["OPTIMIZE TABLE"]
        if expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)
        table_parts = [table.to_sql()[0] for table in expr.tables]
        parts.append(", ".join(table_parts))
        return " ".join(parts), ()

    def format_mysql_check_table_statement(
        self,
        expr: "MySQLCheckTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``CHECK TABLE`` with its optional modes.

        The support gate is keyed on the node's own ``operation`` so an
        unknown keyword dispatched here still fails as an unsupported feature
        rather than rendering an unrelated statement.
        """
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            raise UnsupportedFeatureError(self.name, f"{operation} TABLE")

        parts = ["CHECK TABLE"]
        if expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)
        table_parts = [table.to_sql()[0] for table in expr.tables]
        parts.append(", ".join(table_parts))
        if expr.options:
            parts.append(" ".join(option.value for option in expr.options))
        return " ".join(parts), ()

    def format_mysql_checksum_table_statement(
        self,
        expr: "MySQLChecksumTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``CHECKSUM TABLE`` with its optional mode.

        The support gate is keyed on the node's own ``operation`` so an
        unknown keyword dispatched here still fails as an unsupported feature
        rather than rendering an unrelated statement.
        """
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            raise UnsupportedFeatureError(self.name, f"{operation} TABLE")

        parts = ["CHECKSUM TABLE"]
        if expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)
        table_parts = [table.to_sql()[0] for table in expr.tables]
        parts.append(", ".join(table_parts))
        if expr.option:
            parts.append(expr.option.value)
        return " ".join(parts), ()

    def format_mysql_repair_table_statement(
        self,
        expr: "MySQLRepairTableStatement",
    ) -> Tuple[str, tuple]:
        """Format ``REPAIR TABLE`` with its optional modes.

        The support gate is keyed on the node's own ``operation`` so an
        unknown keyword dispatched here still fails as an unsupported feature
        rather than rendering an unrelated statement.
        """
        expr.validate(strict=self.strict_validation)
        operation = expr.operation
        support_method = f"supports_{operation.lower()}_table"
        if not hasattr(self, support_method) or not getattr(self, support_method)():
            raise UnsupportedFeatureError(self.name, f"{operation} TABLE")

        parts = ["REPAIR TABLE"]
        if expr.no_write_to_binlog.value:
            parts.append(expr.no_write_to_binlog.value)
        table_parts = [table.to_sql()[0] for table in expr.tables]
        parts.append(", ".join(table_parts))
        if expr.options:
            parts.append(" ".join(option.value for option in expr.options))
        return " ".join(parts), ()
