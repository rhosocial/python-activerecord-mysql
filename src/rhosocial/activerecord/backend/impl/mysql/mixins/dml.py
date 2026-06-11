# src/rhosocial/activerecord/backend/impl/mysql/mixins/dml.py
from typing import Tuple


class MySQLDMLOperationMixin:
    """MySQL DML operations mixin."""

    def supports_insert_ignore(self) -> bool:
        return True

    def supports_replace_into(self) -> bool:
        return True

    def supports_load_data(self) -> bool:
        return True

    def format_load_data_statement(self, expr) -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement."""
        expr.validate(strict=self.strict_validation)

        parts = ["LOAD DATA"]

        if expr.options.local:
            parts.append("LOCAL")

        parts.append("INFILE")

        file_path_escaped = expr.file_path.replace("\\", "\\\\").replace("'", "\\'")
        parts.append(f"'{file_path_escaped}'")

        if expr.options.replace:
            parts.append("REPLACE")
        elif expr.options.ignore:
            parts.append("IGNORE")

        parts.append("INTO TABLE")
        parts.append(self.format_identifier(expr.table))

        if expr.options.character_set:
            parts.append(f"CHARACTER SET {expr.options.character_set}")

        field_parts = []
        if expr.options.fields_terminated_by is not None:
            field_parts.append(f"TERMINATED BY '{expr.options.fields_terminated_by}'")
        if expr.options.fields_enclosed_by is not None:
            field_parts.append(f"ENCLOSED BY '{expr.options.fields_enclosed_by}'")
        if expr.options.fields_escaped_by is not None:
            field_parts.append(f"ESCAPED BY '{expr.options.fields_escaped_by}'")
        if field_parts:
            parts.append("FIELDS " + " ".join(field_parts))

        line_parts = []
        if expr.options_lines_terminated_by is not None:
            line_parts.append(f"TERMINATED BY '{expr.options_lines_terminated_by}'")
        if expr.options_lines_starting_by is not None:
            line_parts.append(f"STARTING BY '{expr.options_lines_starting_by}'")
        if line_parts:
            parts.append("LINES " + " ".join(line_parts))

        if expr.options.skip:
            parts.append(f"IGNORE {expr.options.skip} LINES")

        if expr.options.set_assignments:
            set_parts = []
            for col, val in expr.options.set_assignments.items():
                set_parts.append(f"{self.format_identifier(col)} = {val}")
            parts.append("SET " + ", ".join(set_parts))

        return " ".join(parts), ()

    def format_on_conflict_clause(self, expr) -> Tuple[str, tuple]:
        """Format ON DUPLICATE KEY UPDATE for MySQL."""
        all_params = []
        parts = ["ON DUPLICATE KEY UPDATE"]

        update_parts = []
        if expr.update_assignments:
            for col_name, value_expr in expr.update_assignments.items():
                col_sql = self.format_identifier(col_name)
                if hasattr(value_expr, "to_sql"):
                    val_sql, val_params = value_expr.to_sql()
                    all_params.extend(val_params)
                else:
                    val_sql = str(value_expr)
                update_parts.append(f"{col_sql} = {val_sql}")

        if update_parts:
            parts.append(" ".join(update_parts))
        else:
            parts.append(f"{self.format_identifier('id')} = {self.format_identifier('id')}")

        return " ".join(parts), tuple(all_params)
