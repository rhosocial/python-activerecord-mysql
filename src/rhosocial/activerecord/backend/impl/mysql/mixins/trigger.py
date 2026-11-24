# src/rhosocial/activerecord/backend/impl/mysql/mixins/trigger.py
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger

from .object_kind import require_kind

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
        CreateTriggerStatement,
        DropTriggerStatement,
    )


class MySQLTriggerMixin:
    """MySQL trigger DDL implementation."""

    def supports_trigger(self) -> bool:
        """MySQL supports triggers since 5.0.2."""
        return self.version_at_least((5, 0, 2))

    def supports_create_trigger(self) -> bool:
        """MySQL supports CREATE TRIGGER since 5.0.2."""
        return self.version_at_least((5, 0, 2))

    def supports_drop_trigger(self) -> bool:
        """MySQL supports DROP TRIGGER since 5.0.2."""
        return self.version_at_least((5, 0, 2))

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
        """Whether ``CREATE TRIGGER IF NOT EXISTS`` is supported.

        The MySQL 8.0 Reference Manual documents the option as supported
        "with CREATE TRIGGER beginning with MySQL 8.0.29"; the grammar before
        that has no ``IF NOT EXISTS``, so the request is refused rather than
        rendered. See https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html
        """
        return self.version_at_least((8, 0, 29))

    def supports_trigger_if_exists(self) -> bool:
        """Whether ``DROP TRIGGER IF EXISTS`` is supported.

        MySQL 5.0 Reference Manual, "13.1.18 DROP TRIGGER Syntax": "The
        IF EXISTS clause was added in MySQL 5.0.32."
        """
        return self.version_at_least((5, 0, 32))

    def format_create_trigger_statement(self, expr: "CreateTriggerStatement") -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement (MySQL syntax).

        Raises:
            TypeError: One of the three named objects is the wrong kind --
                ``expr.trigger`` must be a Trigger, ``expr.table`` a Table, and
                ``expr.function`` a Function when it is set. Each renders itself,
                so a wrong kind produces a well-formed statement naming the wrong
                object.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        require_kind(expr.trigger, Trigger, "CreateTriggerStatement.trigger")
        require_kind(expr.table, Table, "CreateTriggerStatement.table")
        if expr.function is not None:
            require_kind(
                expr.function, Function, "CreateTriggerStatement.function"
            )
        if not self.supports_trigger():
            raise UnsupportedFeatureError(self.name, "triggers")

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

        if expr.if_not_exists:
            if not self.supports_trigger_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "CREATE TRIGGER IF NOT EXISTS",
                    f"{self.name} does not support CREATE TRIGGER IF NOT EXISTS "
                    "before MySQL 8.0.29."
                )
            parts.append("IF NOT EXISTS")

        parts.append(expr.trigger.to_sql()[0])
        parts.append(expr.timing.value)

        if expr.events:
            parts.append(expr.events[0].value)

        parts.append("ON")
        parts.append(expr.table.to_sql()[0])
        parts.append("FOR EACH ROW")

        if expr.function is not None:
            parts.append("CALL")
            parts.append(expr.function.to_sql()[0])

        return " ".join(parts), ()

    def format_drop_trigger_statement(self, expr: "DropTriggerStatement") -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement (MySQL syntax).

        Raises:
            TypeError: ``expr.trigger`` is not a Trigger.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        require_kind(expr.trigger, Trigger, "DropTriggerStatement.trigger")
        if not self.supports_trigger():
            raise UnsupportedFeatureError(self.name, "triggers")

        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            if not self.supports_trigger_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP TRIGGER IF EXISTS",
                    f"{self.name} does not support DROP TRIGGER IF EXISTS "
                    "before MySQL 5.0.32."
                )
            parts.append("IF EXISTS")

        parts.append(expr.trigger.to_sql()[0])

        return " ".join(parts), ()
