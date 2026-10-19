# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_column.py
from enum import Enum
from typing import TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mysql.expression.alter_column import MySQLAddColumn


class MySQLDDLColumnMixin:
    """MySQL DDL column definition and ALTER TABLE column actions."""

    def format_column(self, expr) -> Tuple[str, Tuple]:
        """Format column reference for MySQL.

        A column reference carries at most a table, and this renders
        ``table.column``. A column cannot be qualified any further: MySQL has
        no inner schema for ``db.schema.column`` to mean, and a caller who
        supplies one is told so rather than having it dropped -- a qualifier
        that vanishes without a word produces a statement against a different
        column than the caller named. For a column addressed through a relation
        that *does* carry a database, hand the relation object to the dialect
        and let the column follow its rendered name.
        """
        if expr.table:
            col_sql = f"{self.format_identifier(expr.table, expr.table_need_quote)}.{self.format_identifier(expr.name, expr.name_need_quote)}"
        else:
            col_sql = self.format_identifier(expr.name, expr.name_need_quote)

        if expr.alias:
            col_sql = f"{col_sql} AS {self.format_identifier(expr.alias, expr.alias_need_quote)}"

        return col_sql, ()

    def format_add_column_action(self, action) -> Tuple[str, tuple]:
        """Format core's ``ADD COLUMN`` action.

        ``AddColumnAction`` declares ``if_not_exists`` and ``column``, so both
        are read directly: the contract states which fields exist, and a
        formatter that probes for them cannot tell a missing field from a
        missing feature. The MySQL-only positional clause lives on
        :class:`MySQLAddColumn` and has its own entry.
        """
        if action.if_not_exists is True:
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE ADD COLUMN IF NOT EXISTS",
                suggestion="MySQL does not support IF NOT EXISTS on ADD COLUMN. "
                     "Pre-check information_schema.COLUMNS before ALTER."
            )
        column_sql, column_params = self.format_column_definition(action.column)
        return f"ADD COLUMN {column_sql}", column_params

    def format_mysql_add_column(self, action: "MySQLAddColumn") -> Tuple[str, tuple]:
        """Format MySQL's ``ADD COLUMN``, with its optional ``AFTER`` clause.

        Its own entry because it is its own node: ``AFTER <column>`` is a field
        core's action does not declare, and reading it off the core class meant
        probing for a field that is not in the contract.
        """
        if action.if_not_exists is True:
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE ADD COLUMN IF NOT EXISTS",
                suggestion="MySQL does not support IF NOT EXISTS on ADD COLUMN. "
                     "Pre-check information_schema.COLUMNS before ALTER."
            )
        column_sql, column_params = self.format_column_definition(action.column)
        if action.after:
            return f"ADD COLUMN {column_sql} AFTER {self.format_identifier(action.after)}", column_params
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action) -> Tuple[str, tuple]:
        """Format ``DROP COLUMN``."""
        if action.if_exists is True:
            raise UnsupportedFeatureError(
                self.name, "DROP COLUMN IF EXISTS",
                suggestion="MySQL does not support IF EXISTS on DROP COLUMN. "
                     "Pre-check information_schema.COLUMNS before ALTER."
            )
        return super().format_drop_column_action(action)

    def format_drop_table_constraint_action(self, action) -> Tuple[str, tuple]:
        """Format ``DROP CONSTRAINT``."""
        if action.if_exists is True:
            raise UnsupportedFeatureError(
                self.name, "DROP CONSTRAINT IF EXISTS",
                suggestion="MySQL does not support IF EXISTS on DROP CONSTRAINT. "
                     "Pre-check information_schema.TABLE_CONSTRAINTS before ALTER."
            )
        return super().format_drop_table_constraint_action(action)

    def format_references_clause(self, expr) -> Tuple[str, Tuple]:
        """Format a REFERENCES clause for MySQL.

        MySQL has no DEFERRABLE / INITIALLY ... constraint attributes, so those
        spellings are refused by name rather than rendered into SQL the server
        rejects (and rather than silently dropped, which would make them
        indistinguishable from "unspecified").
        """
        if expr.deferrable or expr.not_deferrable:
            feature = (
                "REFERENCES DEFERRABLE"
                if expr.deferrable
                else "REFERENCES NOT DEFERRABLE"
            )
            raise UnsupportedFeatureError(
                self.name, feature,
                f"{self.name} does not support {feature}."
            )
        if expr.initially_deferred or expr.initially_immediate:
            feature = (
                "REFERENCES INITIALLY DEFERRED"
                if expr.initially_deferred
                else "REFERENCES INITIALLY IMMEDIATE"
            )
            raise UnsupportedFeatureError(
                self.name, feature,
                f"{self.name} does not support {feature}."
            )
        return super().format_references_clause(expr)

    def format_alter_column_action(self, action) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... ALTER COLUMN {SET DEFAULT | DROP DEFAULT}."""
        # The contract types the operation as the enum member or the word it
        # spells, so the entry asks which one it is instead of asking the
        # object whether it happens to carry a ``value``.
        operation = (
            action.operation.value if isinstance(action.operation, Enum) else action.operation
        )
        col_name = self.format_identifier(action.column_name)

        if operation == "DROP DEFAULT":
            return f"ALTER COLUMN {col_name} DROP DEFAULT", ()

        if operation == "SET DEFAULT":
            new_value = action.new_value
            if isinstance(new_value, str):
                escaped = self._escape_sql_string(new_value)
                return f"ALTER COLUMN {col_name} SET DEFAULT '{escaped}'", ()
            if new_value is None:
                raise ValueError("SET DEFAULT requires a default value")
            if isinstance(new_value, BaseExpression):
                value_sql, value_params = new_value.to_sql()
                if value_params:
                    from rhosocial.activerecord.backend.expression.core import Literal
                    if isinstance(new_value, Literal):
                        return f"ALTER COLUMN {col_name} SET DEFAULT {self.inline_sql_literal(new_value.value)}", ()
                return f"ALTER COLUMN {col_name} SET DEFAULT {value_sql}", tuple(value_params)
            return f"ALTER COLUMN {col_name} SET DEFAULT {self.inline_sql_literal(new_value)}", ()

        return super().format_alter_column_action(action)
