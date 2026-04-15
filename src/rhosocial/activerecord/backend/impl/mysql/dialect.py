# src/rhosocial/activerecord/backend/impl/mysql/dialect.py
"""
MySQL backend SQL dialect implementation.

This dialect implements protocols for features that MySQL actually supports,
based on the MySQL version provided at initialization.
"""
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    JSONSupport,
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
    LockingSupport,
    MergeSupport,
    OrderedSetAggregationSupport,
    QualifyClauseSupport,
    TemporalTableSupport,
    UpsertSupport,
    LateralJoinSupport,
    WildcardSupport,
    JoinSupport,
    ViewSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TableSupport,
    ConstraintSupport,
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CTEMixin,
    FilterClauseMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin,
    AdvancedGroupingMixin,
    ArrayMixin,
    ExplainMixin,
    GraphMixin,
    LockingMixin,
    MergeMixin,
    OrderedSetAggregationMixin,
    QualifyClauseMixin,
    TemporalTableMixin,
    UpsertMixin,
    LateralJoinMixin,
    JoinMixin,
    ViewMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TableMixin,
    ConstraintMixin,
    IntrospectionMixin,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from .protocols import (
    MySQLTriggerSupport,
    MySQLTableSupport,
    MySQLSetTypeSupport,
    MySQLJSONFunctionSupport,
    MySQLSpatialSupport,
    MySQLVectorSupport,
    MySQLDMLOperationSupport,
)
from .mixins import (
    MySQLTransactionMixin,
    MySQLTriggerMixin,
    MySQLTableMixin,
    MySQLSetTypeMixin,
    MySQLJSONFunctionMixin,
    MySQLSpatialMixin,
    MySQLVectorMixin,
    MySQLIntrospectionMixin,
)
from .show.dialect import MySQLShowDialectMixin

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        CreateTableExpression, CreateViewExpression, DropViewExpression,
        ColumnDefinition, TableConstraint, IndexDefinition,
        ExplainExpression, InsertExpression,
    )
    from rhosocial.activerecord.backend.expression.transaction import (
        SetTransactionExpression,
        BeginTransactionExpression,
    )


class MySQLDialect(
    SQLDialectBase,
    # Include mixins for features that MySQL supports (with version-dependent implementations)
    CTEMixin,
    FilterClauseMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin, # MySQL doesn't support RETURNING, but we'll override to indicate this
    AdvancedGroupingMixin,
    ArrayMixin,
    ExplainMixin,
    GraphMixin,
    LockingMixin,
    MergeMixin,
    OrderedSetAggregationMixin,
    QualifyClauseMixin,
    TemporalTableMixin,
    UpsertMixin,
    LateralJoinMixin, # MySQL 8.0.14+ supports LATERAL
    JoinMixin,
    ViewMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TableMixin,
    ConstraintMixin,
    # MySQL-specific mixins (before generic IntrospectionMixin to override methods)
    MySQLTransactionMixin,  # MySQL transaction support
    MySQLTriggerMixin,
    MySQLTableMixin,
    MySQLSetTypeMixin,
    MySQLJSONFunctionMixin,
    MySQLSpatialMixin,
    MySQLVectorMixin,  # MySQL 9.0+ VECTOR type support
    MySQLIntrospectionMixin,  # Must be before IntrospectionMixin
    MySQLShowDialectMixin,  # MySQL SHOW commands
    IntrospectionMixin,
    # Protocols for type checking
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    JSONSupport,
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
    LockingSupport,
    MergeSupport,
    OrderedSetAggregationSupport,
    QualifyClauseSupport,
    TemporalTableSupport,
    UpsertSupport,
    LateralJoinSupport,
    WildcardSupport,
    JoinSupport,
    ViewSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TableSupport,
    ConstraintSupport,
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # MySQL-specific protocols
    MySQLTriggerSupport,
    MySQLTableSupport,
    MySQLSetTypeSupport,
    MySQLJSONFunctionSupport,
    MySQLSpatialSupport,
    MySQLVectorSupport,  # MySQL 9.0+ VECTOR type support
    MySQLDMLOperationSupport,  # MySQL-specific DML operations (INSERT IGNORE, REPLACE INTO)
    # Function Support Protocol
    SQLFunctionSupport,
):
    """
    MySQL dialect implementation that adapts to the MySQL version.

    MySQL features and support based on version:
    - JSON operations (since 5.7.8)
    - Window functions (since 8.0.0)
    - CTEs (Common Table Expressions) (since 8.0.0)
    - LATERAL JOIN (since 8.0.14)
    - Array types (no native support, handled via JSON)
    - UPSERT (ON DUPLICATE KEY UPDATE) (since 4.1)
    - Advanced grouping (WITH ROLLUP) (since 4.0.0)
    - FILTER clause (not supported)
    - MERGE statement (not supported, use ON DUPLICATE KEY UPDATE or REPLACE)
    """

    def __init__(self, version: Tuple[int, int, int] = (8, 0, 0)):
        """
        Initialize MySQL dialect with specific version.

        Args:
            version: MySQL version tuple (major, minor, patch)
        """
        self.version = version
        super().__init__()

    def get_parameter_placeholder(self, position: int = 0) -> str:
        """MySQL uses '%s' for placeholders."""
        return "%s"

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the MySQL version this dialect is configured for."""
        return self.version

    # region Protocol Support Checks based on version
    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_materialized_cte(self) -> bool:
        """MySQL does not support MATERIALIZED hint for CTEs."""
        return False

    def supports_returning_clause(self) -> bool:
        """MySQL does not support RETURNING clause."""
        return False

    def supports_window_functions(self) -> bool:
        """Window functions are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported, since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_filter_clause(self) -> bool:
        """FILTER clause for aggregate functions is not supported in MySQL."""
        return False  # MySQL does not support FILTER clause

    def supports_json_type(self) -> bool:
        """JSON is supported since MySQL 5.7.8."""
        return self.version >= (5, 7, 8)

    def get_json_access_operator(self) -> str:
        """MySQL uses '->' for JSON access (shorthand for JSON_EXTRACT)."""
        return "->"

    def supports_rollup(self) -> bool:
        """ROLLUP is supported using WITH ROLLUP syntax since early MySQL versions."""
        return True  # Supported since MySQL 4.0.0

    def supports_cube(self) -> bool:
        """CUBE is not supported in MySQL."""
        return False  # MySQL does not support CUBE

    def supports_grouping_sets(self) -> bool:
        """GROUPING SETS is not supported in MySQL."""
        return False  # MySQL does not support GROUPING SETS

    def supports_array_type(self) -> bool:
        """MySQL does not have native array types."""
        return False  # MySQL does not have native arrays

    def supports_array_constructor(self) -> bool:
        """MySQL does not support ARRAY constructor."""
        return False  # MySQL does not have ARRAY constructor

    def supports_array_access(self) -> bool:
        """MySQL does not support native array subscript access."""
        return False  # MySQL does not have native arrays

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        # MySQL 8.0.18+ supports ANALYZE
        return self.version >= (8, 0, 18)

    def supports_explain_format(self, format_type: str) -> bool:
        """Check if specific EXPLAIN format is supported."""
        format_type_upper = format_type.upper()
        # MySQL supports TEXT, JSON formats; TREE format added in 8.0.16
        if format_type_upper == "TEXT":
            return True
        elif format_type_upper == "JSON":
            return self.version >= (5, 6, 5)  # JSON format since 5.6.5
        elif format_type_upper == "TREE":
            return self.version >= (8, 0, 16)  # TREE format since 8.0.16
        else:
            return False

    def format_explain_statement(self, explain_expr: "ExplainExpression") -> tuple:
        """Build the MySQL EXPLAIN SQL string and return (sql, params).

        MySQL syntax variants:
        - ``EXPLAIN <stmt>``
        - ``EXPLAIN FORMAT=TEXT|JSON|TREE|TRADITIONAL <stmt>``
        - ``EXPLAIN ANALYZE <stmt>``          (8.0.18+)
        - ``EXPLAIN ANALYZE FORMAT=JSON <stmt>``  (8.0.21+)

        Note: MySQL 9.x defaults to TREE format which returns a single 'EXPLAIN' column
        with text output. For consistent parsing, we force TRADITIONAL format for
        MySQL 9.0+ when no explicit format is specified.
        """
        from rhosocial.activerecord.backend.expression.statements import ExplainType

        statement_sql, statement_params = explain_expr.statement.to_sql()
        options = explain_expr.options
        parts = ["EXPLAIN"]

        # Determine if we need to add FORMAT=TRADITIONAL
        needs_traditional_format = False
        if options is None:
            # No options specified - check if MySQL 9.0+ needs TRADITIONAL format
            needs_traditional_format = self.version >= (9, 0, 0)
        else:
            # ANALYZE goes before FORMAT (MySQL ordering)
            if options.analyze:
                parts.append("ANALYZE")

            if options.format is not None:
                fmt_name = options.format.name if hasattr(options.format, "name") else str(options.format)
                parts.append(f"FORMAT={fmt_name.upper()}")
            elif options.type is not None and options.type == ExplainType.QUERY_PLAN:
                # MySQL has no QUERY PLAN keyword; fall through to plain EXPLAIN
                pass
            else:
                # No format specified - check if MySQL 9.0+ needs TRADITIONAL format
                needs_traditional_format = self.version >= (9, 0, 0)

        # MySQL 9.0+ defaults to TREE format; force TRADITIONAL for consistent parsing
        if needs_traditional_format:
            parts.append("FORMAT=TRADITIONAL")

        return f"{' '.join(parts)} {statement_sql}", statement_params

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        # MySQL doesn't have native MATCH clause like some other systems
        return False

    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported in SELECT statements.

        MySQL supports FOR UPDATE since early versions. The clause locks
        selected rows preventing other transactions from modifying them.
        """
        return True

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        return self.version >= (8, 0, 1)  # Supported since 8.0.1

    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        return False  # MySQL does not support MERGE, use ON DUPLICATE KEY UPDATE

    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported."""
        # MySQL doesn't have built-in temporal tables
        return False

    def supports_qualify_clause(self) -> bool:
        """Whether QUALIFY clause is supported."""
        # MySQL doesn't have QUALIFY clause (though can be simulated with subqueries)
        return False

    def supports_upsert(self) -> bool:
        """Whether UPSERT (ON DUPLICATE KEY UPDATE) is supported."""
        return True  # Supported since MySQL 4.1

    def get_upsert_syntax_type(self) -> str:
        """
        Get UPSERT syntax type.

        Returns:
            'ON CONFLICT' (PostgreSQL) or 'ON DUPLICATE KEY' (MySQL)
        """
        return "ON DUPLICATE KEY"

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        return self.version >= (8, 0, 14)  # LATERAL joins added in 8.0.14

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        return False  # MySQL does not support WITHIN GROUP (ORDER BY ...) syntax

    def supports_inner_join(self) -> bool:
        """INNER JOIN is supported."""
        return True

    def supports_left_join(self) -> bool:
        """LEFT JOIN is supported."""
        return True

    def supports_right_join(self) -> bool:
        """RIGHT JOIN is supported."""
        return True

    def supports_full_join(self) -> bool:
        """FULL JOIN is not directly supported (can be simulated with UNION)."""
        return False

    def supports_cross_join(self) -> bool:
        """CROSS JOIN is supported."""
        return True

    def supports_natural_join(self) -> bool:
        """NATURAL JOIN is supported."""
        return True

    def supports_wildcard(self) -> bool:
        """Wildcard (*) is supported."""
        return True
    # endregion

    # region Set Operation Support
    def supports_union(self) -> bool:
        """UNION is supported."""
        return True

    def supports_union_all(self) -> bool:
        """UNION ALL is supported."""
        return True

    def supports_intersect(self) -> bool:
        """INTERSECT is supported since MySQL 8.0.31."""
        return self.version >= (8, 0, 31)

    def supports_except(self) -> bool:
        """EXCEPT is supported since MySQL 8.0.31."""
        return self.version >= (8, 0, 31)

    def supports_set_operation_order_by(self) -> bool:
        """Set operations support ORDER BY."""
        return True

    def supports_set_operation_limit_offset(self) -> bool:
        """Set operations support LIMIT and OFFSET."""
        return True

    def supports_set_operation_for_update(self) -> bool:
        """Set operations support FOR UPDATE."""
        return True
    # endregion

    def format_identifier(self, identifier: str) -> str:
        """
        Format identifier using MySQL's backtick quoting mechanism.

        Args:
            identifier: Raw identifier string

        Returns:
            Quoted identifier with escaped internal backticks
        """
        # Escape any internal backticks by doubling them
        escaped = identifier.replace('`', '``')
        return f"`{escaped}`"

    def format_limit_offset(self, limit: Optional[int] = None,
                            offset: Optional[int] = None) -> Tuple[Optional[str], List[Any]]:
        """
        Format LIMIT and OFFSET clause for MySQL.
        
        MySQL requires LIMIT when using OFFSET.
        """
        params = []
        sql_parts = []

        if limit is not None:
            sql_parts.append("LIMIT %s")
            params.append(limit)
        
        if offset is not None:
            if limit is None:
                # MySQL requires LIMIT when using OFFSET, use a very large number
                sql_parts.append("LIMIT %s")
                params.append(18446744073709551615)  # MySQL maximum value for BIGINT UNSIGNED
            sql_parts.append("OFFSET %s")
            params.append(offset)

        if not sql_parts:
            return None, []

        return " ".join(sql_parts), params

    def supports_json_arrow_operators(self) -> bool:
        """Check if MySQL version supports -> and ->> operators."""
        # -> and ->> operators were added in MySQL 5.7.9
        return self.version >= (5, 7, 9)

    # region View Support
    def supports_or_replace_view(self) -> bool:
        """Whether CREATE OR REPLACE VIEW is supported."""
        return True  # MySQL supports OR REPLACE

    def supports_temporary_view(self) -> bool:
        """Whether TEMPORARY views are supported."""
        return True  # MySQL supports TEMPORARY views

    def supports_materialized_view(self) -> bool:
        """Whether materialized views are supported."""
        return False  # MySQL does not support materialized views

    def supports_if_exists_view(self) -> bool:
        """Whether DROP VIEW IF EXISTS is supported."""
        return True  # MySQL supports IF EXISTS

    def supports_view_check_option(self) -> bool:
        """Whether WITH CHECK OPTION is supported."""
        return True  # MySQL supports WITH CHECK OPTION

    def supports_cascade_view(self) -> bool:
        """Whether DROP VIEW CASCADE is supported."""
        return False  # MySQL does not support CASCADE for views

    def format_create_view_statement(
        self, expr: "CreateViewExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE VIEW statement for MySQL."""
        parts = ["CREATE"]

        if expr.temporary:
            parts.append("TEMPORARY")

        if expr.replace:
            parts.append("OR REPLACE")

        parts.append("VIEW")
        parts.append(self.format_identifier(expr.view_name))

        if expr.column_aliases:
            cols = ', '.join(self.format_identifier(c) for c in expr.column_aliases)
            parts.append(f"({cols})")

        query_sql, query_params = expr.query.to_sql()
        parts.append(f"AS {query_sql}")

        if expr.options and expr.options.check_option:
            check_option = expr.options.check_option.value
            parts.append(f"WITH {check_option} CHECK OPTION")

        return ' '.join(parts), query_params

    def format_drop_view_statement(
        self, expr: "DropViewExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP VIEW statement for MySQL."""
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.view_name))
        return ' '.join(parts), ()
    # endregion

    # region Schema Support
    def supports_create_schema(self) -> bool:
        """Whether CREATE SCHEMA is supported."""
        return True  # MySQL supports CREATE SCHEMA (alias for CREATE DATABASE)

    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is supported."""
        return True  # MySQL supports DROP SCHEMA (alias for DROP DATABASE)

    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is supported."""
        return True

    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is supported."""
        return True
    # endregion

    # region Index Support
    def supports_create_index(self) -> bool:
        """Whether CREATE INDEX is supported."""
        return True

    def supports_drop_index(self) -> bool:
        """Whether DROP INDEX is supported."""
        return True

    def supports_unique_index(self) -> bool:
        """Whether UNIQUE indexes are supported."""
        return True

    def supports_index_if_not_exists(self) -> bool:
        """Whether CREATE INDEX IF NOT EXISTS is supported."""
        return False  # MySQL does not support IF NOT EXISTS for indexes

    def supports_index_if_exists(self) -> bool:
        """Whether DROP INDEX IF EXISTS is supported."""
        return False  # MySQL does not support IF EXISTS for indexes
    # endregion

    # region Sequence Support
    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported."""
        return False # MySQL does not support sequences (uses AUTO_INCREMENT)

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported."""
        return False
    # endregion

    # region Table Support
    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        return True

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        return True

    def supports_temporary_table(self) -> bool:
        """Whether TEMPORARY tables are supported."""
        return True

    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported."""
        return True  # MySQL supports partitioning

    def format_create_table_statement(
        self, expr: "CreateTableExpression"
    ) -> Tuple[str, tuple]:
        """
        Format CREATE TABLE statement for MySQL.

        This method handles MySQL-specific syntax including:
        - LIKE syntax (copying table structure)
        - Inline index definitions
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments
        - AUTO_INCREMENT in column definitions

        Args:
            expr: CreateTableExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Check for LIKE syntax in dialect_options (highest priority)
        if 'like_table' in expr.dialect_options:
            return self._format_create_table_like(expr)

        # Build standard CREATE TABLE statement
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraintType, TableConstraintType
        )

        all_params: List[Any] = []

        # Build CREATE TABLE header
        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        # Build column definitions
        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self._format_column_definition_mysql(col_def, ColumnConstraintType)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        # Build table constraints
        for t_const in expr.table_constraints:
            const_sql, const_params = self._format_table_constraint_mysql(t_const, TableConstraintType)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        # Build inline indexes (MySQL-specific)
        for idx_def in expr.indexes:
            idx_sql = self._format_inline_index_mysql(idx_def)
            column_parts.append(idx_sql)

        # Combine all parts
        parts.append(f"({', '.join(column_parts)})")

        # Add storage options (MySQL-specific format)
        if expr.storage_options:
            storage_sql = self._format_storage_options_mysql(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        # Add table-level comment (from dialect_options)
        if 'comment' in expr.dialect_options:
            parts.append(f"COMMENT '{expr.dialect_options['comment']}'")

        return ' '.join(parts), tuple(all_params)

    def _format_create_table_like(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement."""
        like_table = expr.dialect_options['like_table']

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        # Handle schema-qualified table name
        if isinstance(like_table, tuple):
            schema, table = like_table
            like_table_str = f"{self.format_identifier(schema)}.{self.format_identifier(table)}"
        else:
            like_table_str = self.format_identifier(like_table)

        parts.append(f"LIKE {like_table_str}")
        return ' '.join(parts), ()

    def _format_column_definition_mysql(
        self,
        col_def: "ColumnDefinition",
        ColumnConstraintType
    ) -> Tuple[str, List[Any]]:
        """Format a single column definition with MySQL-specific syntax."""
        parts = [self.format_identifier(col_def.name), col_def.data_type]
        params: List[Any] = []

        # Build constraint parts
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

            # Handle AUTO_INCREMENT (MySQL-specific)
            if constraint.is_auto_increment:
                constraint_parts.append("AUTO_INCREMENT")

        if constraint_parts:
            parts.append(' '.join(constraint_parts))

        # Add column comment (MySQL-specific)
        if col_def.comment:
            parts.append(f"COMMENT '{col_def.comment}'")

        return ' '.join(parts), params

    def _format_table_constraint_mysql(
        self,
        t_const: "TableConstraint",
        TableConstraintType
    ) -> Tuple[str, List[Any]]:
        """Format a table-level constraint."""
        from rhosocial.activerecord.backend.expression.statements import (
            ForeignKeyConstraint, ReferentialAction,
        )

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
                ref_cols_str = ', '.join(
                    self.format_identifier(c) for c in t_const.foreign_key_columns
                )
                ref_table = self.format_identifier(t_const.foreign_key_table)
                parts.append(
                    f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table} ({ref_cols_str})"
                )

            # ON DELETE / ON UPDATE
            if isinstance(t_const, ForeignKeyConstraint):
                if t_const.on_delete != ReferentialAction.NO_ACTION:
                    parts.append(f"ON DELETE {t_const.on_delete.value}")
                if t_const.on_update != ReferentialAction.NO_ACTION:
                    parts.append(f"ON UPDATE {t_const.on_update.value}")

        elif t_const.constraint_type == TableConstraintType.CHECK and t_const.check_condition:
            check_sql, check_params = t_const.check_condition.to_sql()
            parts.append(f"CHECK ({check_sql})")
            params.extend(check_params)

            # ENFORCED / NOT ENFORCED (MySQL 8.0.16+)
            if t_const.dialect_options and t_const.dialect_options.get('enforced') is False:
                parts.append("NOT ENFORCED")

        return ' '.join(parts), params

    def _format_inline_index_mysql(self, idx_def: "IndexDefinition") -> str:
        """Format an inline index definition (MySQL-specific)."""
        parts = []

        if idx_def.unique:
            parts.append("UNIQUE")

        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))

        cols_str = ', '.join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")

        # MySQL USING syntax for index type
        if idx_def.type:
            parts.append(f"USING {idx_def.type}")

        return ' '.join(parts)

    def _format_storage_options_mysql(self, storage_options: Dict[str, Any]) -> str:
        """
        Format storage options for MySQL.

        Args:
            storage_options: Dict with keys like 'ENGINE', 'DEFAULT CHARSET', 'COLLATE'

        Returns:
            Formatted storage options string (e.g., "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
        """
        parts = []
        for key, value in storage_options.items():
            if isinstance(value, str):
                parts.append(f"{key}={value}")
            else:
                parts.append(f"{key}={value}")
        return ' '.join(parts)
    # endregion

    # region Trigger Support (MySQL-specific)
    def supports_trigger(self) -> bool:
        return True

    def supports_create_trigger(self) -> bool:
        return True

    def supports_drop_trigger(self) -> bool:
        return True

    def supports_instead_of_trigger(self) -> bool:
        return False

    def supports_statement_trigger(self) -> bool:
        return False

    def supports_trigger_referencing(self) -> bool:
        return False

    def supports_trigger_when(self) -> bool:
        return False

    def supports_trigger_if_not_exists(self) -> bool:
        return True

    def format_create_trigger_statement(
        self,
        expr
    ):
        """Format CREATE TRIGGER statement (MySQL syntax).

        MySQL differences from SQL:1999:
        - Does not support INSTEAD OF triggers
        - Does not support FOR EACH STATEMENT
        - Does not support WHEN condition
        - Does not support REFERENCING clause
        - Uses trigger body directly instead of function call
        """
        if not self.supports_trigger():
            raise UnsupportedFeatureError(self.name, "triggers")

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

    def format_drop_trigger_statement(
        self,
        expr
    ):
        """Format DROP TRIGGER statement (MySQL syntax)."""
        if not self.supports_trigger():
            raise UnsupportedFeatureError(self.name, "triggers")

        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()
    # endregion
    
    # region FULLTEXT Index Support
    def supports_fulltext_index(self) -> bool:
        """MySQL 5.6+ supports FULLTEXT for InnoDB."""
        return self.version >= (5, 6, 0)
    
    def supports_fulltext_parser(self) -> bool:
        """MySQL supports FULLTEXT parser plugins."""
        return self.version >= (5, 1, 0)
    
    def supports_fulltext_query_expansion(self) -> bool:
        """MySQL supports QUERY EXPANSION."""
        return True  # All versions with FULLTEXT support this

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format MATCH ... AGAINST expression.

        Args:
            columns: Column names to search
            search_string: Search term
            mode: Search mode - NATURAL_LANGUAGE, BOOLEAN, or QUERY_EXPANSION

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        cols_sql = ", ".join(self.format_identifier(c) for c in columns)

        placeholder = self.get_parameter_placeholder()
        search_sql = placeholder
        search_params = (search_string,)

        if mode:
            mode_upper = mode.upper()
            if mode_upper == "NATURAL_LANGUAGE":
                mode_str = "IN NATURAL LANGUAGE MODE"
            elif mode_upper == "BOOLEAN":
                mode_str = "IN BOOLEAN MODE"
            elif mode_upper == "QUERY_EXPANSION":
                mode_str = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
            else:
                mode_str = ""
        else:
            mode_str = "IN NATURAL LANGUAGE MODE"

        sql = f"MATCH({cols_sql}) AGAINST({search_sql} {mode_str})"
        return sql, search_params

    # endregion

    # region MySQL 8.0 Index Features
    def supports_invisible_index(self) -> bool:
        """Whether INVISIBLE indexes are supported.

        MySQL 8.0+ supports invisible indexes that are not used by the optimizer.
        """
        return self.version >= (8, 0, 0)

    def supports_descending_index(self) -> bool:
        """Whether descending indexes are supported.

        MySQL 8.0+ supports true descending indexes (not just reverse scans).
        """
        return self.version >= (8, 0, 0)

    def supports_functional_index(self) -> bool:
        """Whether functional (expression) indexes are supported.

        MySQL 8.0+ supports indexes on expressions (functional indexes).
        """
        return self.version >= (8, 0, 0)

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are enforced.

        MySQL 8.0.16+ enforces CHECK constraints (before that, they were parsed but ignored).
        """
        return self.version >= (8, 0, 16)

    # ConstraintSupport protocol implementation
    def supports_constraint_enforced(self) -> bool:
        """Whether ENFORCED/NOT ENFORCED constraint control is supported.

        MySQL 8.0.16+ supports ENFORCED/NOT ENFORCED (SQL:2016).
        """
        return self.version >= (8, 0, 16)

    def supports_fk_match(self) -> bool:
        """Whether MATCH {SIMPLE|PARTIAL|FULL} is supported.

        MySQL does not support MATCH clause in FOREIGN KEY.
        """
        return False

    def supports_deferrable_constraint(self) -> bool:
        """Whether DEFERRABLE constraints are supported.

        MySQL does not support DEFERRABLE (SQL:1999).
        """
        return False

    def supports_generated_column(self) -> bool:
        """Whether generated (computed) columns are supported.

        MySQL 5.7+ supports generated columns (STORED and VIRTUAL).
        """
        return self.version >= (5, 7, 0)

    def supports_default_column_value_expression(self) -> bool:
        """Whether DEFAULT column values can use expressions.

        MySQL 8.0+ supports expressions in DEFAULT column values.
        """
        return self.version >= (8, 0, 0)
    # endregion

    # region Transaction Control

    # MySQL function version support: function_name -> (min_version, max_version)
    # min_version: minimum supported version (inclusive), None = all versions
    # max_version: maximum supported version (inclusive), None = no upper limit
    # Reference: https://dev.mysql.com/doc/refman/en/inline-functions.html
    _MYSQL_FUNCTION_VERSIONS = {
        # JSON functions: MySQL 5.7.8+
        "json_extract": ((5, 7, 8), None),
        "json_unquote": ((5, 7, 8), None),
        "json_object": ((5, 7, 8), None),
        "json_array": ((5, 7, 8), None),
        "json_contains": ((5, 7, 8), None),
        "json_set": ((5, 7, 8), None),
        "json_remove": ((5, 7, 8), None),
        "json_type": ((5, 7, 8), None),
        "json_valid": ((5, 7, 8), None),
        "json_search": ((5, 7, 8), None),
        # Spatial functions: MySQL 5.7+ (renamed from ST_* to lowercase)
        "st_geom_from_text": ((5, 7, 0), None),
        "st_geom_from_wkb": ((5, 7, 0), None),
        "st_as_text": ((5, 7, 0), None),
        "st_as_geojson": ((5, 7, 5), None),
        "st_distance": ((5, 7, 0), None),
        "st_within": ((5, 7, 0), None),
        "st_contains": ((5, 7, 0), None),
        "st_intersects": ((5, 7, 0), None),
        # Full-text search: MySQL 5.6+ (with some features requiring 5.7+)
        "match_against": (None, None),  # Available since early versions
        # SET type functions: All MySQL versions
        "find_in_set": (None, None),
        # Enum type functions: All MySQL versions
        "elt": (None, None),
        "field": (None, None),
        # Math enhanced functions: All MySQL versions
        "round_": (None, None),
        "pow": (None, None),
        "power": (None, None),
        "sqrt": (None, None),
        "mod": (None, None),
        "ceil": (None, None),
        "floor": (None, None),
        "trunc": (None, None),
        "max_": (None, None),
        "min_": (None, None),
        "avg": (None, None),
        # Bitwise functions: All MySQL versions
        "bit_and": (None, None),
        "bit_or": (None, None),
        "bit_xor": (None, None),
        "bit_count": (None, None),
        "bit_get_bit": ((8, 0, 0), None),  # BIT() function added in 8.0
        "bit_shift_left": ((8, 0, 0), None),  # Added in 8.0
        "bit_shift_right": ((8, 0, 0), None),  # Added in 8.0
    }

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        This method combines:
        1. Core functions from rhosocial.activerecord.backend.expression.functions
        2. MySQL-specific functions from rhosocial.activerecord.backend.impl.mysql.functions

        MySQL version-specific functions:
        - JSON functions: MySQL 5.7.8+
        - Spatial functions: MySQL 5.7+
        - GeoJSON functions: MySQL 5.7.5+

        Returns:
            Dict mapping function names to True (supported) or False.
        """
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.mysql import functions as mysql_functions

        result = {}
        for func_name in core_functions:
            result[func_name] = self._is_mysql_function_supported(func_name)

        mysql_funcs = getattr(mysql_functions, "__all__", [])
        for func_name in mysql_funcs:
            if func_name not in result:
                result[func_name] = self._is_mysql_function_supported(func_name)

        return result

    def _is_mysql_function_supported(self, func_name: str) -> bool:
        """Check if a MySQL-specific function is supported based on version.

        Args:
            func_name: Name of the MySQL function

        Returns:
            True if supported, False otherwise
        """
        version_range = self._MYSQL_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True

    def supports_transaction_mode(self) -> bool:
        """MySQL supports READ ONLY transactions (5.6.5+)."""
        return self.version >= (5, 6, 5)

    def supports_isolation_level_in_begin(self) -> bool:
        """MySQL does not support isolation level in START TRANSACTION.

        MySQL uses SET TRANSACTION ISOLATION LEVEL before START TRANSACTION.
        """
        return False

    def supports_read_only_transaction(self) -> bool:
        """MySQL supports READ ONLY transactions (5.6.5+)."""
        return self.version >= (5, 6, 5)

    def supports_deferrable_transaction(self) -> bool:
        """MySQL does not support DEFERRABLE mode."""
        return False

    def supports_savepoint(self) -> bool:
        """MySQL supports savepoints."""
        return True

    def format_set_transaction(
        self, expr: "SetTransactionExpression"
    ) -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for MySQL.

        MySQL requires SET TRANSACTION ISOLATION LEVEL to be executed before
        START TRANSACTION when a specific isolation level is needed. This method
        generates the appropriate SET TRANSACTION statement.

        Args:
            expr: SetTransactionExpression with isolation level and/or mode.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Note:
            This statement must be executed before START TRANSACTION.
            The MySQLTransactionManager._do_begin() handles this sequencing.
        """
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        params = expr.get_params()
        parts = []

        # Handle isolation level
        isolation_level = params.get("isolation_level")
        if isolation_level is not None:
            level_names = {
                IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                IsolationLevel.SERIALIZABLE: "SERIALIZABLE",
            }
            level_name = level_names.get(isolation_level)
            if level_name:
                parts.append(f"ISOLATION LEVEL {level_name}")

        # Handle transaction mode (READ ONLY/READ WRITE)
        mode = params.get("mode")
        if mode is not None:
            if mode == TransactionMode.READ_ONLY:
                parts.append("READ ONLY")
            elif mode == TransactionMode.READ_WRITE:
                parts.append("READ WRITE")

        if not parts:
            return "SET TRANSACTION", ()

        return f"SET TRANSACTION {' '.join(parts)}", ()

    def format_begin_transaction(
        self, expr: "BeginTransactionExpression"
    ) -> Tuple[str, tuple]:
        """Format START TRANSACTION statement for MySQL.

        This method returns a SINGLE SQL statement as required by the protocol.
        For MySQL, isolation level must be set separately using SET TRANSACTION
        before START TRANSACTION. The TransactionManager handles this sequencing.

        Args:
            expr: BeginTransactionExpression with isolation level and mode.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Note:
            Isolation level is NOT included in this statement. Use
            format_set_transaction() for that purpose, which should be called
            before this method by MySQLTransactionManager._do_begin().
        """
        from rhosocial.activerecord.backend.transaction import TransactionMode

        params = expr.get_params()

        # Build START TRANSACTION (without isolation level)
        mode = params.get("mode")
        if mode == TransactionMode.READ_ONLY:
            if self.supports_read_only_transaction():
                return "START TRANSACTION READ ONLY", ()
            else:
                from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError
                raise UnsupportedTransactionModeError(
                    feature="READ ONLY transactions",
                    backend="MySQL",
                    message="READ ONLY transactions require MySQL 5.6.5 or later."
                )
        else:
            return "START TRANSACTION", ()

    # endregion

    # region MySQL-specific DML Operations

    def supports_insert_ignore(self) -> bool:
        """Whether INSERT IGNORE is supported.

        MySQL supports INSERT IGNORE in all versions.
        """
        return True

    def supports_replace_into(self) -> bool:
        """Whether REPLACE INTO is supported.

        MySQL supports REPLACE INTO in all versions.
        """
        return True

    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Format INSERT statement with MySQL-specific options.

        Extends the base implementation to support:
        - INSERT IGNORE via dialect_options={'ignore': True}
        - REPLACE INTO via dialect_options={'replace': True}

        Args:
            expr: InsertExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)

        Raises:
            ValueError: If both 'ignore' and 'replace' are specified, or if
                       'replace' is used with 'on_conflict'
        """
        # Perform strict parameter validation
        if self.strict_validation:
            expr.validate(strict=True)

        # Check for conflicting options
        is_replace = expr.dialect_options.get('replace', False)
        is_ignore = expr.dialect_options.get('ignore', False)

        if is_replace and is_ignore:
            raise ValueError("Cannot use both 'replace' and 'ignore' options together")

        if is_replace and expr.on_conflict:
            raise ValueError("REPLACE INTO does not support ON CONFLICT clause")

        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)

        # Build INSERT or REPLACE clause
        if is_replace:
            parts = ["REPLACE INTO"]
        else:
            parts = ["INSERT"]
            if is_ignore:
                parts.append("IGNORE")
            parts.append("INTO")
        parts.append(table_sql)

        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"
            parts.append(columns_sql)

        # Format source (VALUES, SELECT, or DEFAULT VALUES)
        from rhosocial.activerecord.backend.expression.statements import (
            DefaultValuesSource, ValuesSource, SelectSource
        )

        if isinstance(expr.source, DefaultValuesSource):
            parts.append("DEFAULT VALUES")
        elif isinstance(expr.source, ValuesSource):
            all_rows_sql = []
            for row in expr.source.values_list:
                row_sql, row_params = [], []
                for val in row:
                    s, p = val.to_sql()
                    row_sql.append(s)
                    row_params.extend(p)
                all_rows_sql.append(f"({', '.join(row_sql)})")
                all_params.extend(row_params)
            parts.append("VALUES " + ", ".join(all_rows_sql))
        elif isinstance(expr.source, SelectSource):
            s_sql, s_params = expr.source.select_query.to_sql()
            parts.append(s_sql)
            all_params.extend(s_params)

        sql = ' '.join(parts)

        # Handle ON CONFLICT (ON DUPLICATE KEY UPDATE for MySQL)
        if expr.on_conflict:
            conflict_sql, conflict_params = expr.on_conflict.to_sql()
            sql += f" {conflict_sql}"
            all_params.extend(conflict_params)

        # Note: MySQL does not support RETURNING clause
        if expr.returning:
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause (MySQL does not support RETURNING)"
            )

        return sql, tuple(all_params)

    def supports_load_data(self) -> bool:
        """Whether LOAD DATA INFILE is supported.

        MySQL supports LOAD DATA INFILE in all versions.
        """
        return True

    def format_load_data_statement(self, expr) -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement.

        Args:
            expr: LoadDataExpression instance

        Returns:
            Tuple of (SQL string, empty tuple - no parameters for LOAD DATA)

        Raises:
            ValueError: If both replace and ignore are True
        """
        expr.validate(strict=self.strict_validation)

        parts = ["LOAD DATA"]

        if expr.options.local:
            parts.append("LOCAL")

        parts.append("INFILE")

        # File path needs to be quoted as string literal
        file_path_escaped = expr.file_path.replace("", "").replace("'", "\'")
        parts.append(f"'{file_path_escaped}'")

        if expr.options.replace:
            parts.append("REPLACE")
        elif expr.options.ignore:
            parts.append("IGNORE")

        parts.append("INTO TABLE")
        parts.append(self.format_identifier(expr.table))

        # Character set
        if expr.options.character_set:
            parts.append(f"CHARACTER SET {expr.options.character_set}")

        # Fields options
        field_parts = []
        if expr.options.fields_terminated_by is not None:
            term = expr.options.fields_terminated_by.replace("", "").replace("'", "\'")
            field_parts.append(f"TERMINATED BY '{term}'")
        if expr.options.fields_enclosed_by is not None:
            enc = expr.options.fields_enclosed_by.replace("", "").replace("'", "\'")
            field_parts.append(f"ENCLOSED BY '{enc}'")
        if expr.options.fields_escaped_by is not None:
            esc = expr.options.fields_escaped_by.replace("", "").replace("'", "\'")
            field_parts.append(f"ESCAPED BY '{esc}'")

        if field_parts:
            parts.append("FIELDS")
            parts.append(" ".join(field_parts))

        # Lines options
        line_parts = []
        if expr.options.lines_starting_by is not None:
            start = expr.options.lines_starting_by.replace("", "").replace("'", "\'")
            line_parts.append(f"STARTING BY '{start}'")
        if expr.options.lines_terminated_by is not None:
            term = expr.options.lines_terminated_by.replace("", "").replace("'", "\'")
            line_parts.append(f"TERMINATED BY '{term}'")

        if line_parts:
            parts.append("LINES")
            parts.append(" ".join(line_parts))

        # Ignore lines
        if expr.options.ignore_lines is not None:
            parts.append(f"IGNORE {expr.options.ignore_lines} LINES")

        # Column list
        if expr.options.column_list:
            columns = ", ".join(
                self.format_identifier(c) for c in expr.options.column_list
            )
            parts.append(f"({columns})")

        # SET assignments (future enhancement)
        if expr.options.set_assignments:
            set_parts = []
            for col, val in expr.options.set_assignments.items():
                set_parts.append(f"{self.format_identifier(col)} = {val}")
            parts.append("SET " + ", ".join(set_parts))

        return " ".join(parts), ()

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE is supported.

        JSON_TABLE is supported in MySQL 8.0.4+.
        """
        return self.version >= (8, 0, 4)

    def format_json_table_expression(self, expr) -> Tuple[str, tuple]:
        """Format JSON_TABLE expression.

        Args:
            expr: JSONTableExpression instance

        Returns:
            Tuple of (SQL string, empty tuple)
        """
        expr.validate(strict=self.strict_validation)

        parts = ["JSON_TABLE("]
        parts.append(expr.json_doc)
        parts.append(",")
        parts.append(expr.path)
        parts.append(" COLUMNS (")

        # Format columns
        column_parts = []
        for col in expr.columns:
            if col.ordinality:
                column_parts.append(f"{self.format_identifier(col.name)} FOR ORDINALITY")
            elif col.exists:
                column_parts.append(f"{self.format_identifier(col.name)} {col.type} EXISTS PATH '{col.path}'")
            else:
                col_def = f"{self.format_identifier(col.name)} {col.type}"
                if col.path:
                    col_def += f" PATH '{col.path}'"
                if col.error_handling:
                    if col.error_handling.upper() == 'DEFAULT':
                        col_def += f" DEFAULT {col.default_value} ON ERROR"
                    else:
                        col_def += f" {col.error_handling.upper()} ON ERROR"
                column_parts.append(col_def)

        # Format nested paths
        for nested in expr.nested_paths:
            nested_def = f"NESTED PATH '{nested.path}' COLUMNS ("
            nested_cols = []
            for col in nested.columns:
                if col.ordinality:
                    nested_cols.append(f"{self.format_identifier(col.name)} FOR ORDINALITY")
                else:
                    nested_cols.append(f"{self.format_identifier(col.name)} {col.type} PATH '{col.path}'")
            nested_def += ", ".join(nested_cols) + ")"
            if nested.alias:
                nested_def = f"{nested.alias} AS " + nested_def
            column_parts.append(nested_def)

        parts.append(", ".join(column_parts))
        parts.append("))")

        if expr.alias:
            parts.append(f" AS {expr.alias}")

        return "".join(parts), ()

    # endregion
