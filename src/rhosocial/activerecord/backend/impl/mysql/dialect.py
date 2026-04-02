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
    IntrospectionSupport,
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
)
from .mixins import (
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
        ExplainExpression,
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
    # MySQL-specific mixins (before generic IntrospectionMixin to override methods)
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
    IntrospectionSupport,
    # MySQL-specific protocols
    MySQLTriggerSupport,
    MySQLTableSupport,
    MySQLSetTypeSupport,
    MySQLJSONFunctionSupport,
    MySQLSpatialSupport,
    MySQLVectorSupport,  # MySQL 9.0+ VECTOR type support
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

    def supports_json_table(self) -> bool:
        """MySQL does not have a direct JSON_TABLE equivalent, but has JSON functions."""
        return False  # MySQL doesn't have JSON_TABLE function

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
