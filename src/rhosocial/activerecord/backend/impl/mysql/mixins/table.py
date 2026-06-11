# src/rhosocial/activerecord/backend/impl/mysql/mixins/table.py
from typing import Any, Dict, List, Tuple


class MySQLTableMixin:
    """MySQL table DDL implementation."""

    def supports_table_like_syntax(self) -> bool:
        return True

    def supports_inline_index(self) -> bool:
        return True

    def supports_storage_engine_option(self) -> bool:
        return True

    def supports_charset_option(self) -> bool:
        return True

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MySQL."""
        if "like_table" in expr.dialect_options:
            return self.format_create_table_like(expr)

        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType, TableConstraintType

        all_params: List[Any] = []

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self.format_column_definition(col_def)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        for t_const in expr.table_constraints:
            const_sql, const_params = self.format_table_constraint(t_const)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        for idx_def in expr.indexes:
            idx_sql = self.format_inline_index(idx_def)
            column_parts.append(idx_sql)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            storage_sql = self.format_storage_options(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        if "comment" in expr.dialect_options:
            escaped_comment = self._escape_sql_string(expr.dialect_options["comment"])
            parts.append(f"COMMENT '{escaped_comment}'")

        return " ".join(parts), tuple(all_params)

    def format_create_table_like(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement."""
        like_table = expr.dialect_options["like_table"]

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
        return " ".join(parts), ()

    def format_column_definition(self, col_def, ColumnConstraintType=None) -> Tuple[str, List[Any]]:
        """Format a single column definition with MySQL-specific syntax."""
        from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
        if not SQLDialectBase._validate_data_type(col_def.data_type):
            raise ValueError(f"Invalid data type: {col_def.data_type}")
        if ColumnConstraintType is None:
            from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType
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
                    from rhosocial.activerecord.backend.expression import bases
                    if isinstance(constraint.default_value, bases.BaseExpression):
                        default_sql, default_params = constraint.default_value.to_sql()
                        constraint_parts.append(f"DEFAULT {default_sql}")
                        params.extend(default_params)
                    elif isinstance(constraint.default_value, str):
                        escaped = self._escape_sql_string(constraint.default_value)
                        constraint_parts.append(f"DEFAULT '{escaped}'")
                    else:
                        constraint_parts.append(f"DEFAULT {constraint.default_value}")
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                constraint_parts.append("NULL")

            if constraint.is_auto_increment:
                constraint_parts.append("AUTO_INCREMENT")

        if constraint_parts:
            parts.append(" ".join(constraint_parts))

        if col_def.comment:
            escaped_comment = self._escape_sql_string(col_def.comment)
            parts.append(f"COMMENT '{escaped_comment}'")

        return " ".join(parts), params

    def format_table_constraint(self, t_const, TableConstraintType=None) -> Tuple[str, List[Any]]:
        """Format a table-level constraint."""
        if TableConstraintType is None:
            from rhosocial.activerecord.backend.expression.statements import TableConstraintType
        parts = []
        params: List[Any] = []

        if t_const.name:
            parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")

        if t_const.constraint_type == TableConstraintType.PRIMARY_KEY:
            if t_const.columns:
                cols_str = ", ".join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.UNIQUE:
            if t_const.columns:
                cols_str = ", ".join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"UNIQUE ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY:
            if t_const.columns and t_const.foreign_key_table and t_const.foreign_key_columns:
                cols_str = ", ".join(self.format_identifier(c) for c in t_const.columns)
                ref_cols_str = ", ".join(self.format_identifier(c) for c in t_const.foreign_key_columns)
                ref_table = self.format_identifier(t_const.foreign_key_table)
                parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table} ({ref_cols_str})")

        return " ".join(parts), params

    def format_inline_index(self, idx_def) -> str:
        """Format an inline INDEX definition within CREATE TABLE (MySQL-specific)."""
        parts = []
        if idx_def.unique:
            parts.append("UNIQUE")
        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))
        cols_str = ", ".join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")
        if idx_def.type:
            parts.append(f"USING {idx_def.type}")
        return " ".join(parts)

    def format_storage_options(self, storage_options: Dict[str, Any]) -> str:
        """Format MySQL table storage options (ENGINE, CHARSET, etc.)."""
        parts = []
        for key, value in storage_options.items():
            if isinstance(value, str):
                parts.append(f"{key}='{self._escape_sql_string(value)}'")
            else:
                parts.append(f"{key}={value}")
        return " ".join(parts)

