# src/rhosocial/activerecord/backend/impl/mysql/mixins.py
"""MySQL dialect-specific Mixin implementations."""
from typing import Any, Dict, List, Tuple


class MySQLTriggerMixin:
    """MySQL trigger DDL implementation.

    MySQL trigger restrictions:
    - FOR EACH ROW only (no FOR EACH STATEMENT)
    - No INSTEAD OF triggers
    - No WHEN condition
    - No REFERENCING clause
    - Single event per trigger
    """

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
        """Format CREATE TRIGGER statement (MySQL syntax).

        MySQL differences from SQL:1999:
        - Does not support INSTEAD OF triggers
        - Does not support FOR EACH STATEMENT
        - Does not support WHEN condition
        - Does not support REFERENCING clause
        - Uses trigger body directly instead of function call
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if expr.timing.value == "INSTEAD OF":
            raise UnsupportedFeatureError(
                self.name,
                "INSTEAD OF triggers (MySQL does not support this feature)"
            )

        if expr.level and expr.level.value == "FOR EACH STATEMENT":
            raise UnsupportedFeatureError(
                self.name,
                "FOR EACH STATEMENT triggers (MySQL only supports FOR EACH ROW)"
            )

        if expr.condition:
            raise UnsupportedFeatureError(
                self.name,
                "WHEN condition in triggers (MySQL does not support this feature)"
            )

        if expr.referencing:
            raise UnsupportedFeatureError(
                self.name,
                "REFERENCING clause in triggers (MySQL does not support this feature)"
            )

        if len(expr.events) > 1:
            raise UnsupportedFeatureError(
                self.name,
                "multiple trigger events (MySQL only supports single event)"
            )

        if expr.update_columns:
            raise UnsupportedFeatureError(
                self.name,
                "UPDATE OF column_list (MySQL does not support this syntax)"
            )

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


class MySQLTableMixin:
    """MySQL table DDL implementation.

    MySQL-specific features:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    """

    def supports_table_like_syntax(self) -> bool:
        """MySQL supports CREATE TABLE ... LIKE syntax."""
        return True

    def supports_inline_index(self) -> bool:
        """MySQL allows inline INDEX/KEY definitions."""
        return True

    def supports_storage_engine_option(self) -> bool:
        """MySQL supports multiple storage engines."""
        return True

    def supports_charset_option(self) -> bool:
        """MySQL supports CHARSET/COLLATE at table level."""
        return True

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MySQL.

        Handles MySQL-specific syntax including:
        - LIKE syntax (copying table structure)
        - Inline index definitions
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments
        - AUTO_INCREMENT in column definitions
        """
        if 'like_table' in expr.dialect_options:
            return self._format_create_table_like(expr)

        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraintType, TableConstraintType
        )

        all_params: List[Any] = []

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self._format_column_definition_mysql(col_def, ColumnConstraintType)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        for t_const in expr.table_constraints:
            const_sql, const_params = self._format_table_constraint_mysql(t_const, TableConstraintType)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        for idx_def in expr.indexes:
            idx_sql = self._format_inline_index_mysql(idx_def)
            column_parts.append(idx_sql)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            storage_sql = self._format_storage_options_mysql(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        if 'comment' in expr.dialect_options:
            parts.append(f"COMMENT '{expr.dialect_options['comment']}'")

        return ' '.join(parts), tuple(all_params)

    def _format_create_table_like(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement."""
        like_table = expr.dialect_options['like_table']

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        if isinstance(like_table, tuple):
            schema, table = like_table
            like_table_str = f"{self.format_identifier(schema)}.{self.format_identifier(table)}"
        else:
            like_table_str = self.format_identifier(like_table)

        parts.append(f"LIKE {like_table_str}")
        return ' '.join(parts), ()

    def _format_column_definition_mysql(
        self,
        col_def,
        ColumnConstraintType
    ) -> Tuple[str, List[Any]]:
        """Format a single column definition with MySQL-specific syntax."""
        parts = [self.format_identifier(col_def.name), col_def.data_type]
        params: List[Any] = []

        constraint_parts = []
        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                constraint_parts.append("PRIMARY KEY")
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                constraint_parts.append("NOT NULL")
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                constraint_parts.append("UNIQUE")
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is not None:
                    constraint_parts.append(f"DEFAULT {constraint.default_value}")
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                constraint_parts.append("NULL")

            if constraint.is_auto_increment:
                constraint_parts.append("AUTO_INCREMENT")

        if constraint_parts:
            parts.append(' '.join(constraint_parts))

        if col_def.comment:
            parts.append(f"COMMENT '{col_def.comment}'")

        return ' '.join(parts), params

    def _format_table_constraint_mysql(
        self,
        t_const,
        TableConstraintType
    ) -> Tuple[str, List[Any]]:
        """Format a table-level constraint."""
        parts = []
        params: List[Any] = []

        if t_const.name:
            parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")

        if t_const.constraint_type == TableConstraintType.PRIMARY_KEY:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.UNIQUE:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"UNIQUE ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY:
            if t_const.columns and t_const.foreign_key_table and t_const.foreign_key_columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                ref_cols_str = ', '.join(self.format_identifier(c) for c in t_const.foreign_key_columns)
                parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {self.format_identifier(t_const.foreign_key_table)} ({ref_cols_str})")

        return ' '.join(parts), params

    def _format_inline_index_mysql(self, idx_def) -> str:
        """Format an inline index definition (MySQL-specific)."""
        parts = []

        if idx_def.unique:
            parts.append("UNIQUE")

        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))

        cols_str = ', '.join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")

        if idx_def.type:
            parts.append(f"USING {idx_def.type}")

        return ' '.join(parts)

    def _format_storage_options_mysql(self, storage_options: Dict[str, Any]) -> str:
        """Format storage options for MySQL.

        Args:
            storage_options: Dict with keys like 'ENGINE', 'DEFAULT CHARSET', 'COLLATE'

        Returns:
            Formatted storage options string (e.g., "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
        """
        parts = []
        for key, value in storage_options.items():
            parts.append(f"{key}={value}")
        return ' '.join(parts)
