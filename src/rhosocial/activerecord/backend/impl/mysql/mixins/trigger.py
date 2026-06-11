# src/rhosocial/activerecord/backend/impl/mysql/mixins/trigger.py
from typing import Tuple


class MySQLTriggerMixin:
    """MySQL trigger DDL implementation."""

    def supports_trigger(self) -> bool:
        """MySQL supports triggers since 5.0.2."""
        return self.version >= (5, 0, 2)

    def supports_instead_of_trigger(self) -> bool:
        """MySQL does NOT support INSTEAD OF triggers."""
        return False

    def supports_statement_trigger(self) -> bool:
        """MySQL does NOT support FOR EACH STATEMENT triggers."""
        return False

    def supports_trigger_referencing(self) -> bool:
        """MySQL does NOT support REFERENCING clause."""
        return False

    def supports_trigger_when(self) -> bool:
        """MySQL does NOT support WHEN condition."""
        return False

    def supports_trigger_if_not_exists(self) -> bool:
        """MySQL 5.7+ supports IF NOT EXISTS."""
        return self.version >= (5, 7, 0)

    def format_create_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement (MySQL syntax)."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if expr.timing.value == "INSTEAD OF":
            raise UnsupportedFeatureError(self.name, "INSTEAD OF triggers (MySQL does not support this feature)")

        if expr.level and expr.level.value == "FOR EACH STATEMENT":
            raise UnsupportedFeatureError(self.name, "FOR EACH STATEMENT triggers (MySQL only supports FOR EACH ROW)")

        if expr.condition:
            raise UnsupportedFeatureError(self.name, "WHEN condition in triggers (MySQL does not support this feature)")

        if expr.referencing:
            raise UnsupportedFeatureError(
                self.name, "REFERENCING clause in triggers (MySQL does not support this feature)"
            )

        if len(expr.events) > 1:
            raise UnsupportedFeatureError(self.name, "multiple trigger events (MySQL only supports single event)")

        if expr.update_columns:
            raise UnsupportedFeatureError(self.name, "UPDATE OF column_list (MySQL does not support this syntax)")

        parts = ["CREATE TRIGGER"]

        if expr.if_not_exists and self.supports_trigger_if_not_exists():
            parts.append("IF NOT EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))
        parts.append(expr.timing.value)

        if expr.events:
            parts.append(expr.events[0].value)

        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))
        parts.append("FOR EACH ROW")

        if expr.function_name:
            parts.append("CALL")
            parts.append(self.format_identifier(expr.function_name))

        return " ".join(parts), ()

    def format_drop_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement (MySQL syntax)."""
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()
