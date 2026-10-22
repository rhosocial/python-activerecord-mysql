# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_table.py
from typing import Any, List, TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.expression.objects import Table

from .object_kind import require_kind

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        ColumnDefinition,
        CreateTableLikeStatement,
        IndexDefinition,
        StorageOptionsExpression,
        TableCheckConstraint,
        TableForeignKeyConstraint,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.table_expr import (
        MySQLStorageOptionsExpression,
    )


class MySQLTableMixin:
    """MySQL table DDL implementation."""

    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        return True

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        return True


    def supports_create_table_as_bind_parameters(self) -> bool:
        """MySQL accepts bind parameters in a CTAS body.

        Measured on 9.7: ``CREATE TABLE t AS SELECT %s FROM s`` is accepted
        and the table is created. MySQL's "parameters" are interpolated
        client-side, so the value is baked into the statement's text.
        """
        return True
    def supports_create_table_like(self) -> bool:
        return True

    def supports_inline_index(self) -> bool:
        return True

    def supports_table_comment(self) -> bool:
        """Whether inline ``COMMENT 'text'`` on ``CREATE TABLE`` is supported.

        MySQL renders the table comment as an inline table option (and the
        column comment inside the column definition), so both capabilities
        advertise True and the inline path is the rendering path. Comment
        length limits (table 2048 / column 1024 characters) are a known
        boundary and are not enforced.
        """
        return True

    def supports_column_comment(self) -> bool:
        """Whether inline ``COMMENT 'text'`` in a column definition is
        supported. MySQL renders it natively."""
        return True

    def supports_storage_engine_option(self) -> bool:
        return True

    def supports_charset_option(self) -> bool:
        return True

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MySQL.

        This method handles MySQL-specific syntax including:
        - Inline index definitions
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments
        - AUTO_INCREMENT in column definitions
        - Partition clause

        Raises:
            TypeError: ``expr.table`` is not a Table. A View or a Sequence there
                renders through its own formatter and would produce a
                well-formed CREATE TABLE over the wrong kind of object's name.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        require_kind(expr.table, Table, "CreateTableStatement.table")
        if expr.tablespace:
            raise UnsupportedFeatureError(
                self.name, "TABLESPACE",
                "MySQL does not support table tablespaces.",
            )
        if expr.inherits:
            raise UnsupportedFeatureError(
                self.name, "table INHERITS",
                "MySQL does not support table inheritance.",
            )
        all_params: List[Any] = []

        options_part = ""
        table_options = expr.table_options
        if table_options is not None:
            options_sql, options_params = table_options.to_sql()
            if options_sql:
                options_part = options_sql
            all_params.extend(options_params)
        parts = ["CREATE"]
        if options_part:
            parts.append(options_part)
        if expr.temporary:
            parts.append("TEMPORARY")
        parts.append("TABLE")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        table_sql, table_params = expr.table.to_sql()
        parts.append(table_sql)
        all_params.extend(table_params)

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
            idx_sql, idx_params = self.format_index_definition(idx_def)
            column_parts.append(idx_sql)
            all_params.extend(idx_params)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            from rhosocial.activerecord.backend.expression.statements.ddl_table import StorageOptionsExpression
            storage_expr = (
                StorageOptionsExpression(self, expr.storage_options)
                if isinstance(expr.storage_options, dict)
                else expr.storage_options
            )
            storage_sql, storage_params = self.format_storage_options(storage_expr)
            if storage_sql:
                parts.append(storage_sql)
                all_params.extend(storage_params)

        from rhosocial.activerecord.backend.impl.mysql.expression.table_options import (
            MySQLCreateTableOptions,
        )
        if table_options is not None and table_options.comment is not None:
            comment_sql, _ = self.format_table_comment_clause(table_options.comment)
            parts.append(comment_sql.strip())

        if isinstance(table_options, MySQLCreateTableOptions):
            if table_options.engine:
                parts.append(f"ENGINE={self.inline_sql_literal(table_options.engine)}")
            if table_options.charset:
                parts.append(f"DEFAULT CHARSET={self.inline_sql_literal(table_options.charset)}")
            if table_options.collate:
                parts.append(f"COLLATE={self.inline_sql_literal(table_options.collate)}")
            if table_options.auto_increment is not None:
                parts.append(f"AUTO_INCREMENT={int(table_options.auto_increment)}")
            if table_options.row_format:
                parts.append(f"ROW_FORMAT={table_options.row_format}")

        if expr.partition is not None:
            partition_sql, partition_params = expr.partition.to_sql()
            if partition_sql:
                parts.append(partition_sql.strip())
                all_params.extend(partition_params)

        return " ".join(parts), tuple(all_params)

    def format_create_table_like_statement(self, expr: "CreateTableLikeStatement") -> Tuple[str, tuple]:
        """Render ``CREATE TABLE ... LIKE`` via the generic TableMixin formatter."""
        return super().format_create_table_like_statement(expr)

    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, tuple]:
        """Format a single column definition with MySQL-specific syntax.

        Accepts both the generic ``ColumnDefinition`` and the MySQL
        ``MySQLColumnDefinition``; the latter's MySQL-only attributes
        (``character_set`` / ``column_format`` / ``storage`` / ``invisible``)
        are rendered here.
        """
        from rhosocial.activerecord.backend.impl.mysql.expression.column import (
            MySQLColumnDefinition,
        )
        from rhosocial.activerecord.backend.expression.statements import (
            AutoIncrementClause,
        )

        type_sql, type_params = col_def.data_type.to_sql()
        parts = [self.format_identifier(col_def.name), type_sql]
        params: List[Any] = list(type_params)

        for constraint in col_def.constraints:
            suffix, cp = self.format_column_constraint(constraint)
            constraint_text = suffix.strip()
            if constraint_text:
                parts.append(constraint_text)
            params.extend(list(cp))
            from rhosocial.activerecord.backend.expression.statements import (
                ColumnPrimaryKeyConstraint,
            )

            if (
                isinstance(constraint.branch, ColumnPrimaryKeyConstraint)
                and constraint.branch.is_auto_increment
            ):
                # The marker is rendered by the dialect's
                # format_auto_increment_clause, not spelled here: the formatter
                # consults supports_auto_increment_column(), so the capability
                # probe decides, and a dialect that declines the marker refuses
                # rather than emitting a token its server rejects.
                marker_sql, marker_params = AutoIncrementClause(self).to_sql()
                parts.append(marker_sql.strip())
                params.extend(marker_params)

        attr_sql, attr_params = self.format_column_attributes(col_def)
        if attr_sql:
            parts.append(attr_sql.strip())
        params.extend(attr_params)

        if isinstance(col_def, MySQLColumnDefinition):
            if col_def.character_set:
                parts.append(f"CHARACTER SET {self.format_identifier(col_def.character_set)}")
            if col_def.column_format is not None:
                parts.append(f"COLUMN_FORMAT {col_def.column_format.value}")
            if col_def.storage is not None:
                parts.append(f"STORAGE {col_def.storage.value}")
            if col_def.invisible:
                parts.append("INVISIBLE")

        if col_def.comment is not None:
            comment_sql, _ = self.format_column_comment_clause(col_def.comment)
            parts.append(comment_sql.strip())

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            parts.append(gen_sql.lstrip())
            params.extend(gen_params)

        return " ".join(parts), params

    def format_table_check_constraint(
        self, constraint: "TableCheckConstraint"
    ) -> Tuple[str, tuple]:
        """Format a table-level ``CHECK`` body behind this server's version gate.

        The core's table-level CHECK body renders without consulting a
        probe; MySQL's server accepted and *enforced* CHECK only from
        8.0.16 on (below that the clause parses and is discarded -- see
        ``supports_check_constraint``), so the version gate stays on the
        branch this backend overrides.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )

        if not self.supports_check_constraint():
            raise UnsupportedFeatureError(
                self.name,
                "CHECK constraint",
                f"{self.name} does not support CHECK constraints.",
            )
        return super().format_table_check_constraint(constraint)

    def format_table_foreign_key_constraint(
        self, constraint: "TableForeignKeyConstraint"
    ) -> Tuple[str, tuple]:
        """Format a table-level ``FOREIGN KEY`` with MySQL's spaced column list.

        MySQL's own DDL (``SHOW CREATE TABLE``) sets the referenced column
        list off with a space -- ``FOREIGN KEY (`d`) REFERENCES `p` (`id`)``
        -- and this backend's tests and DDL fixtures pin that spelling, so
        the reference body is re-spaced here rather than through the
        core's ``REFERENCES t(c)``. The referential actions and ``MATCH``
        still ride the shared ``ReferencesClause`` machinery, so the
        capability probes stay consulted (``supports_fk_match`` refuses
        MATCH on this server).

        Raises:
            ValueError: The local columns, the referenced columns or the
                referenced table are missing.
        """
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            ReferencesClause,
        )

        if not constraint.columns:
            raise ValueError(
                "FOREIGN KEY constraint must have at least one local column specified."
            )
        referenced_table, referenced_columns = constraint.references
        if not referenced_columns:
            raise ValueError(
                "FOREIGN KEY constraint must have at least one foreign key column specified."
            )
        if not referenced_table:
            raise ValueError("FOREIGN KEY constraint must have a foreign key table specified.")
        cols_str = ", ".join(self.format_identifier(c) for c in constraint.columns)
        references = ReferencesClause(
            self,
            referenced_table,
            list(referenced_columns),
            on_delete=constraint.on_delete,
            on_update=constraint.on_update,
            match_type=constraint.match_type,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        # The shared clause renders "REFERENCES <table>(<cols>)..."; MySQL
        # spells the column list with a space: "REFERENCES <table> (<cols>)...".
        head, rest = ref_sql.split("(", 1)
        return f"FOREIGN KEY ({cols_str}) {head} ({rest}", tuple(ref_params)

    def format_index_definition(self, idx_def: "IndexDefinition") -> Tuple[str, tuple]:
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
        return " ".join(parts), ()

    def format_storage_options(self, expr: "StorageOptionsExpression") -> Tuple[str, tuple]:
        """Format core's table storage options (ENGINE, CHARSET, etc.)."""
        return self._render_storage_options(expr.options), ()

    def format_mysql_storage_options_expression(
        self,
        expr: "MySQLStorageOptionsExpression",
    ) -> Tuple[str, tuple]:
        """Format :class:`MySQLStorageOptionsExpression`.

        Its own entry because it is its own node: the constructor parameter is
        ``storage_options`` where core's node calls the same mapping
        ``options``, and one entry reading the other field raised
        ``AttributeError`` on half of the pair.
        """
        return self._render_storage_options(expr.storage_options), ()

    def _render_storage_options(self, options) -> str:
        parts = []
        for key, value in options.items():
            rendered = self.inline_sql_literal(value)
            parts.append(f"{key}={rendered}")
        return " ".join(parts)

