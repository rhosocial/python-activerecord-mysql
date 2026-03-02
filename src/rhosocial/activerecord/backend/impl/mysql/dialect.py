# src/rhosocial/activerecord/backend/impl/mysql/dialect.py
"""
MySQL backend SQL dialect implementation.

This dialect implements protocols for features that MySQL actually supports,
based on the MySQL version provided at initialization.
"""
from typing import Any, Dict, List, Optional, Tuple, Union

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
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class MySQLDialect(
    SQLDialectBase,
    # Include mixins for features that MySQL supports (with version-dependent implementations)
    CTEMixin,
    FilterClauseMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin,  # MySQL doesn't support RETURNING, but we'll override to indicate this
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
    LateralJoinMixin,  # MySQL 8.0.14+ supports LATERAL
    JoinMixin,
    ViewMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TableMixin,
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
        return False  # MySQL does not support sequences (uses AUTO_INCREMENT)

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
    # endregion
    # endregion