# src/rhosocial/activerecord/backend/impl/mysql/mixins/dml.py
from typing import TYPE_CHECKING, Any, List, Tuple

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import Parameter
from rhosocial.activerecord.backend.expression.objects import Table

from .object_kind import require_kind

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import OnConflictClause
    from rhosocial.activerecord.backend.impl.mysql.expression.load_data import (
        MySQLLoadDataOptions,
        MySQLLoadDataStatement,
    )


class MySQLDMLOperationMixin:
    """MySQL DML operations mixin."""

    def supports_insert_ignore(self) -> bool:
        return True

    def supports_replace_into(self) -> bool:
        return True

    def supports_load_data(self) -> bool:
        return True

    def _escape_file_path_atom(self, file_path: str) -> str:
        """Escape a declared file-path atom; MySQL treats backslash as escape."""
        return file_path.replace("\\", "\\\\").replace("'", "\\'")

    def format_mysql_load_data_statement(self, expr: "MySQLLoadDataStatement") -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement.

        Raises:
            TypeError: ``expr.table`` is not a Table. LOAD DATA writes rows, so a
                wrong kind there would render a statement loading into whatever
                object's name was supplied.
        """
        require_kind(expr.table, Table, "MySQLLoadDataStatement.table")
        expr.validate(strict=self.strict_validation)

        all_params: List[Any] = []

        parts = ["LOAD DATA"]

        if expr.options.local:
            parts.append("LOCAL")

        parts.append("INFILE")

        file_path_escaped = self._escape_file_path_atom(expr.file_path)
        parts.append(f"'{file_path_escaped}'")

        if expr.options.replace:
            parts.append("REPLACE")
        elif expr.options.ignore:
            parts.append("IGNORE")

        parts.append("INTO TABLE")
        parts.append(expr.table.to_sql()[0])

        options_sql, options_params = self.format_load_data_options(expr.options)
        if options_sql:
            parts.append(options_sql)
        all_params.extend(options_params)

        return " ".join(parts), tuple(all_params)

    def format_load_data_options(self, expr: "MySQLLoadDataOptions") -> Tuple[str, tuple]:
        """Render the LOAD DATA clauses that follow ``INTO TABLE``.

        The options node is a kind in its own right, so it carries its own
        dispatch entry; the statement formatter composes its result with the
        leading ``LOAD DATA [LOCAL] INFILE '<path>' [REPLACE|IGNORE]`` parts.
        """
        parts: List[str] = []
        all_params: List[Any] = []

        if expr.character_set:
            parts.append(f"CHARACTER SET {expr.character_set}")

        field_parts = []
        if expr.fields_terminated_by is not None:
            field_parts.append(f"TERMINATED BY '{self.escape_sql_string(expr.fields_terminated_by)}'")
        if expr.fields_enclosed_by is not None:
            field_parts.append(f"ENCLOSED BY '{self.escape_sql_string(expr.fields_enclosed_by)}'")
        if expr.fields_escaped_by is not None:
            field_parts.append(f"ESCAPED BY '{self.escape_sql_string(expr.fields_escaped_by)}'")
        if field_parts:
            parts.append("FIELDS")
            parts.append(" ".join(field_parts))

        line_parts = []
        if expr.lines_starting_by is not None:
            line_parts.append(f"STARTING BY '{self.escape_sql_string(expr.lines_starting_by)}'")
        if expr.lines_terminated_by is not None:
            line_parts.append(f"TERMINATED BY '{self.escape_sql_string(expr.lines_terminated_by)}'")
        if line_parts:
            parts.append("LINES")
            parts.append(" ".join(line_parts))

        if expr.ignore_lines is not None:
            parts.append(f"IGNORE {expr.ignore_lines} LINES")

        if expr.column_list:
            columns = ", ".join(self.format_identifier(c) for c in expr.column_list)
            parts.append(f"({columns})")

        if expr.set_assignments:
            set_parts = []
            for col, val in expr.set_assignments.items():
                col_sql = self.format_identifier(col)
                if isinstance(val, BaseExpression):
                    val_sql, val_params = val.to_sql()
                    all_params.extend(val_params)
                else:
                    val_sql, val_params = Parameter(self, val).to_sql()
                    all_params.extend(val_params)
                set_parts.append(f"{col_sql} = {val_sql}")
            parts.append("SET " + ", ".join(set_parts))

        return " ".join(parts), tuple(all_params)

    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
        """Format ON DUPLICATE KEY UPDATE for MySQL."""
        all_params = []
        parts = ["ON DUPLICATE KEY UPDATE"]

        update_parts = []
        if expr.update_assignments:
            for col_name, value_expr in expr.update_assignments.items():
                col_sql = self.format_identifier(col_name)
                if isinstance(value_expr, BaseExpression):
                    val_sql, val_params = value_expr.to_sql()
                else:
                    val_sql, val_params = Parameter(self, value_expr).to_sql()
                all_params.extend(val_params)
                update_parts.append(f"{col_sql} = {val_sql}")

        if update_parts:
            parts.append(" ".join(update_parts))
        else:
            parts.append(f"{self.format_identifier('id')} = {self.format_identifier('id')}")

        return " ".join(parts), tuple(all_params)
