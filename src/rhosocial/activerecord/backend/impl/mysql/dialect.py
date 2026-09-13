# src/rhosocial/activerecord/backend/impl/mysql/dialect.py
"""
MySQL backend SQL dialect implementation.

This dialect implements protocols for features that MySQL actually supports,
based on the MySQL version provided at initialization.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol
from rhosocial.activerecord.backend.dialect.protocols import (
    CollationSupport,
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
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
    SequenceSupport,
    ConstraintSupport,
    IntrospectionSupport,
    # TRUNCATE TABLE support protocol
    TruncateSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
    # DataType Support Protocol
    DDLTypeSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CollationMixin,
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
    TruncateMixin,
    IntrospectionMixin,
    PartitionMixin,
    # New Mixins
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    TransactionControlMixin,
    SetOperationMixin,
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
    MySQLFullTextSearchSupport,
    MySQLLockingSupport,
    MySQLModifyColumnSupport,
    MySQLJsonDualityViewSupport,
    MySQLOptimizerHintSupport,
    MySQLPartitionSupport,
    MySQLRenameTableSupport,
    MySQLTableStatementSupport,
    MySQLMaintenanceSupport,
    MySQLRoutineSupport,
    MySQLLoadXMLSupport,
    MySQLAdminCommandSupport,
)
from .mixins import (
    MySQLTransactionMixin,
    MySQLDMLOperationMixin,
    MySQLFullTextSearchMixin,
    MySQLTriggerMixin,
    MySQLTableMixin,
    MySQLSetTypeMixin,
    MySQLJSONFunctionMixin,
    MySQLSpatialMixin,
    MySQLVectorMixin,
    MySQLIntrospectionMixin,
    MySQLLockingMixin,
    MySQLModifyColumnMixin,
    MySQLJsonDualityViewMixin,
    MySQLOptimizerHintMixin,
    MySQLPartitionMixin,
    MySQLTypeSupportMixin,
    MySQLRenameTableMixin,
    MySQLTruncateMixin,
    MySQLTableStatementMixin,
    MySQLMaintenanceMixin,
    MySQLRoutineMixin,
    MySQLLoadXMLLMixin,
    MySQLAdminCommandMixin,
)
from .collation import validate_mysql_collation_name
from .reserved_words import MYSQL_RESERVED_WORDS
from .show.dialect import MySQLShowDialectMixin

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.collation import CollateExpression
    from rhosocial.activerecord.backend.expression.statements import (
        CreateTableExpression,
        CreateViewExpression,
        DropViewExpression,
        ExplainExpression,
        InsertExpression,
    )
    from rhosocial.activerecord.backend.expression.statements.fulltext_match import (
        FulltextMatchExpression,
    )
    from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
        CreateTriggerExpression,
        DropTriggerExpression,
    )
    from rhosocial.activerecord.backend.expression.transaction import (
        SetTransactionExpression,
        BeginTransactionExpression,
    )


class MySQLDialect(
    SQLDialectBase,
    # Include mixins for features that MySQL supports (with version-dependent implementations)
    CollationMixin,
    CTEMixin,
    FilterClauseMixin,
    WindowFunctionMixin,
    MySQLJSONFunctionMixin,  # MySQL JSON functions (before JSONMixin to override format_json_arrow/function_expression)
    JSONMixin,
    ReturningMixin,  # MySQL doesn't support RETURNING, but we'll override to indicate this
    AdvancedGroupingMixin,
    ArrayMixin,
    ExplainMixin,
    GraphMixin,
    MySQLLockingMixin,  # MySQL FOR SHARE/NOWAIT/SKIP LOCKED (before LockingMixin for method override)
    LockingMixin,
    MergeMixin,
    OrderedSetAggregationMixin,
    QualifyClauseMixin,
    TemporalTableMixin,
    MySQLFullTextSearchMixin,  # MySQL full-text search (before IndexMixin to override supports_fulltext_index)
    MySQLTriggerMixin,  # MySQL trigger support (before IndexMixin to override trigger methods)
    MySQLDMLOperationMixin,  # MySQL DML operations (before UpsertMixin to override format_on_conflict_clause)
    UpsertMixin,
    LateralJoinMixin,  # MySQL 8.0.14+ supports LATERAL
    JoinMixin,
    ViewMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    MySQLPartitionMixin,
    PartitionMixin,
    # MySQL-specific mixins (before generic IntrospectionMixin to override methods)
    MySQLTransactionMixin,  # MySQL transaction support
    MySQLTableMixin,  # Must be before TableMixin/ConstraintMixin to override format methods
    MySQLRenameTableMixin,  # MySQL RENAME TABLE (before TableMixin to override supports_rename_table)
    TableMixin,
    MySQLTruncateMixin,  # MySQL TRUNCATE support (before TruncateMixin to override)
    TruncateMixin,
    ConstraintMixin,
    MySQLSetTypeMixin,
    MySQLSpatialMixin,
    MySQLVectorMixin,  # MySQL 9.0+ VECTOR type support
    MySQLIntrospectionMixin,  # Must be before IntrospectionMixin
    MySQLShowDialectMixin,  # MySQL SHOW commands
    MySQLModifyColumnMixin,  # MySQL MODIFY/CHANGE COLUMN support
    MySQLJsonDualityViewMixin,  # MySQL 9.7+ JSON Duality Views
    MySQLTypeSupportMixin,  # DataType formatting and parsing
    MySQLOptimizerHintMixin,  # MySQL optimizer hints (SET_VAR)
    MySQLTableStatementMixin,  # MySQL TABLE / VALUES statements (8.0.19+)
    MySQLMaintenanceMixin,  # MySQL ANALYZE/CHECK/CHECKSUM/OPTIMIZE/REPAIR TABLE
    MySQLRoutineMixin,  # MySQL stored procedures/functions/CALL
    MySQLLoadXMLLMixin,  # MySQL LOAD XML
    MySQLAdminCommandMixin,  # MySQL admin/utility commands
    IntrospectionMixin,
    # New Mixins
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    TransactionControlMixin,
    SetOperationMixin,
    # Protocols for type checking
    # Note: MySQL-specific protocols extend generic protocols,
    # so only MySQL-specific protocols are needed for isinstance checks
    CollationSupport,
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    MySQLJSONFunctionSupport,  # extends JSONSupport
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
    MySQLLockingSupport,  # extends LockingSupport
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
    SequenceSupport,
    MySQLTableSupport,  # extends TableSupport
    ConstraintSupport,
    IntrospectionSupport,
    # TRUNCATE TABLE support protocol
    TruncateSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # MySQL-specific protocols
    MySQLTriggerSupport,
    MySQLSetTypeSupport,
    MySQLSpatialSupport,
    MySQLVectorSupport,  # MySQL 9.0+ VECTOR type support
    MySQLFullTextSearchSupport,  # MySQL full-text search
    MySQLModifyColumnSupport,  # MySQL MODIFY/CHANGE COLUMN support
    MySQLJsonDualityViewSupport,  # MySQL 9.7+ JSON Duality Views
    MySQLOptimizerHintSupport,  # MySQL optimizer hints
    MySQLPartitionSupport,  # MySQL table partitioning
    MySQLDMLOperationSupport,  # MySQL DML operations (INSERT IGNORE, REPLACE INTO, LOAD DATA)
    MySQLRenameTableSupport,  # MySQL RENAME TABLE
    MySQLTableStatementSupport,  # MySQL TABLE / VALUES statements
    MySQLMaintenanceSupport,  # MySQL table maintenance
    MySQLRoutineSupport,  # MySQL stored routines / CALL
    MySQLLoadXMLSupport,  # MySQL LOAD XML
    MySQLAdminCommandSupport,  # MySQL admin/utility commands
    # Function Support Protocol
    SQLFunctionSupport,
    # DataType Support Protocol
    DDLTypeSupport,
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

    def __init__(self, version: Optional[Tuple[int, int, int]] = None,
                 sql_mode: Optional[str] = None):
        """
        Initialize MySQL dialect with specific version.

        Args:
            version: MySQL version tuple (major, minor, patch).
                If None, the dialect must be adapted via
                backend.introspect_and_adapt() before version-dependent
                features can be used.
            sql_mode: MySQL SQL mode string (e.g. "STRICT_TRANS_TABLES" or
                "...NO_BACKSLASH_ESCAPES"). Controls whether string literal
                escaping must double backslashes.
        """
        super().__init__()
        self._reserved_words = MYSQL_RESERVED_WORDS
        if version is not None:
            self.version = version
        self.sql_mode = sql_mode or "STRICT_TRANS_TABLES"

    @property
    def no_backslash_escapes(self) -> bool:
        """Whether ``NO_BACKSLASH_ESCAPES`` is in the active SQL mode.

        When active, backslash is a literal character (not an escape), so
        string literals must NOT double backslashes; only single quotes need
        doubling.
        """
        return "NO_BACKSLASH_ESCAPES" in self.sql_mode.upper()

    def get_parameter_placeholder(self, position: int = 0) -> str:
        """MySQL uses '%s' for placeholders."""
        return "%s"

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the MySQL version this dialect is configured for."""
        return self.version

    def create_schema_differ(self):
        """Return the MySQL schema differ (ordinal-position aware)."""
        from rhosocial.activerecord.backend.impl.mysql.schema.differ import (
            MySQLSchemaDiffer,
        )

        return MySQLSchemaDiffer()

    def suggested_data_types(self) -> Dict[str, type]:
        """Cross-backend type-consistency suggestions for MySQL.

        Values are the suggested replacement DataType **classes** (same
        value type as :meth:`supports_data_types`). Suggestions reflect
        MySQL's real storage model:

        - ``uuid``: no native UUID type — the MySQL convention is a
          fixed-length byte string (``BINARY(16)``), so the suggested
          replacement is ``MySQLBinaryType``.
        - ``enum``: MySQL has a native ENUM, exposed through its
          namespaced type ``MySQLEnumType`` (the generic ``enum`` name
          itself has no formatter here).
        - ``binary`` / ``varbinary``: MySQL natively renders
          ``BINARY(n)`` / ``VARBINARY(n)`` through the namespaced
          ``mysql_binary`` / ``mysql_varbinary`` types.

        Types the type mixin does render (``integer``, ``varchar``,
        ``json``, ``date``, …) are deliberately absent: they already have
        a rendering path here, so there is nothing to suggest (suggested
        keys and supported keys are disjoint by contract).
        """
        from .expression.types import (
            MySQLBinaryType,
            MySQLEnumType,
            MySQLVarBinaryType,
        )

        return {
            "uuid": MySQLBinaryType,
            "enum": MySQLEnumType,
            "binary": MySQLBinaryType,
            "varbinary": MySQLVarBinaryType,
        }

    def format_date_trunc_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        field = expr.field.value.upper()
        sql = f"CAST(DATE_FORMAT({source_sql}, %s) AS DATETIME)"
        formats = {
            "YEAR": "%Y-01-01 00:00:00",
            "MONTH": "%Y-%m-01 00:00:00",
            "DAY": "%Y-%m-%d 00:00:00",
            "HOUR": "%Y-%m-%d %H:00:00",
            "MINUTE": "%Y-%m-%d %H:%i:00",
            "SECOND": "%Y-%m-%d %H:%i:%s",
        }
        if field not in formats:
            raise UnsupportedFeatureError(self.name, f"date_trunc({expr.field.value})")
        return self.apply_alias(sql, source_params + (formats[field],), expr)

    def format_interval_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        sql = f"INTERVAL %s {expr.unit.value.upper()}"
        return self.apply_alias(sql, (expr.value,), expr)

    def format_datetime_add_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"DATE_ADD({source_sql}, {interval_sql})"
        return self.apply_alias(sql, source_params + interval_params, expr)

    def format_datetime_subtract_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"DATE_SUB({source_sql}, {interval_sql})"
        return self.apply_alias(sql, source_params + interval_params, expr)

    def format_datetime_diff_expression(self, expr: "Any") -> Tuple[str, Tuple]:
        start_sql, start_params = expr.start.to_sql()
        end_sql, end_params = expr.end.to_sql()
        sql = f"TIMESTAMPDIFF({expr.unit.value.upper()}, {start_sql}, {end_sql})"
        return self.apply_alias(sql, start_params + end_params, expr)

    def supports_collate_expression(self) -> bool:
        """MySQL supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate MySQL collation names and return their SQL representation."""
        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        return validate_mysql_collation_name(expr.collation_name, getattr(self, "version", None))

    def _escape_sql_string(self, value: str) -> str:
        """Escape string for MySQL with backslash support.

        MySQL default SQL mode (STRICT_TRANS_TABLES) treats backslash as an
        escape character, so backslashes are doubled. Under
        ``NO_BACKSLASH_ESCAPES`` backslash is a literal character and must
        NOT be doubled (only single quotes are doubled). Single quotes are
        always escaped by doubling regardless of SQL mode.

        Args:
            value: The string value to escape

        Returns:
            Escaped string safe for use in MySQL SQL statements
        """
        if not self.no_backslash_escapes:
            value = value.replace("\\", "\\\\")
        value = value.replace("'", "''")
        return value

    # region Protocol Support Checks based on version
    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_unconditional_cte_order_by(self) -> bool:
        """ORDER BY inside a CTE definition requires CTE support (8.0.0+)."""
        return self.version >= (8, 0, 0)


    def supports_window_functions(self) -> bool:
        """Window functions are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported, since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)




    def supports_rollup(self) -> bool:
        """ROLLUP is supported using WITH ROLLUP syntax since early MySQL versions."""
        return True  # Supported since MySQL 4.0.0






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


    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported in SELECT statements.

        MySQL supports FOR UPDATE since early versions. The clause locks
        selected rows preventing other transactions from modifying them.
        """
        return True




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




    def supports_right_join(self) -> bool:
        """RIGHT JOIN is supported."""
        return True




    def supports_straight_join(self) -> bool:
        """MySQL-specific STRAIGHT_JOIN is supported."""
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

    def format_identifier(self, identifier: str, need_quote: bool = True) -> str:
        """
        Format identifier using MySQL's backtick quoting mechanism.

        Args:
            identifier: Raw identifier string
            need_quote: Whether to quote the identifier. Default True.
                When False, the identifier is returned as-is without escaping.

        Returns:
            Quoted identifier with escaped internal backticks
        """
        if not need_quote:
            if self.is_reserved_word(identifier):
                import warnings
                from rhosocial.activerecord.backend.warnings import IdentifierQuotingWarning
                warnings.warn(
                    f"Identifier '{identifier}' is a reserved word in {self.name} "
                    f"and may cause SQL errors without quoting.",
                    IdentifierQuotingWarning,
                    stacklevel=2,
                )
            return identifier
        # Escape any internal backticks by doubling them
        escaped = identifier.replace("`", "``")
        return f"`{escaped}`"

    def format_column(self, expr) -> Tuple[str, Tuple]:
        """Format column reference for MySQL.

        MySQL uses database-qualified references (db.table.column) rather
        than schema-qualified ones, so schema_name is silently ignored
        here. Database qualification is handled separately through
        cross-database query support.
        """
        if expr.table:
            col_sql = f"{self.format_identifier(expr.table, expr.table_need_quote)}.{self.format_identifier(expr.name, expr.name_need_quote)}"
        else:
            col_sql = self.format_identifier(expr.name, expr.name_need_quote)

        if expr.alias:
            col_sql = f"{col_sql} AS {self.format_identifier(expr.alias, expr.alias_need_quote)}"

        return col_sql, ()

    def format_limit_offset(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Tuple[Optional[str], List[Any]]:
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


    def supports_if_exists_view(self) -> bool:
        """Whether DROP VIEW IF EXISTS is supported."""
        return True  # MySQL supports IF EXISTS

    def supports_view_check_option(self) -> bool:
        """Whether WITH CHECK OPTION is supported."""
        return True  # MySQL supports WITH CHECK OPTION


    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement for MySQL."""
        parts = ["CREATE"]

        if expr.temporary:
            parts.append("TEMPORARY")

        if expr.replace:
            parts.append("OR REPLACE")

        parts.append("VIEW")
        parts.append(self.format_identifier(expr.view_name))

        if expr.column_aliases:
            cols = ", ".join(self.format_identifier(c) for c in expr.column_aliases)
            parts.append(f"({cols})")

        query_sql, query_params = expr.query.to_sql()
        parts.append(f"AS {query_sql}")

        if expr.options and expr.options.check_option:
            check_option = expr.options.check_option.value
            parts.append(f"WITH {check_option} CHECK OPTION")

        return " ".join(parts), query_params

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement for MySQL."""
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.view_name))
        return " ".join(parts), ()

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





    # endregion

    # region Sequence Support


    # endregion

    # region Table Support
    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        return True

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        return True


    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
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
        if "like_table" in expr.dialect_options:
            return self.format_create_table_like(expr)

        # Build standard CREATE TABLE statement
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
            col_sql, col_params = self.format_column_definition(col_def)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        # Build table constraints
        for t_const in expr.table_constraints:
            const_sql, const_params = self.format_table_constraint(t_const)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        # Build inline indexes (MySQL-specific)
        for idx_def in expr.indexes:
            idx_sql = self.format_inline_index(idx_def)
            column_parts.append(idx_sql)

        # Combine all parts
        parts.append(f"({', '.join(column_parts)})")

        # Add storage options (MySQL-specific format)
        if expr.storage_options:
            storage_sql = self.format_storage_options(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        # Add table-level comment (from dialect_options)
        if "comment" in expr.dialect_options:
            escaped_comment = self._escape_sql_string(expr.dialect_options["comment"])
            parts.append(f"COMMENT '{escaped_comment}'")

        # Add partition clause generated through PartitionClause expression.
        if expr.partition is not None:
            partition_sql, partition_params = expr.partition.to_sql()
            if partition_sql:
                parts.append(partition_sql.strip())
                all_params.extend(partition_params)

        return " ".join(parts), tuple(all_params)




    def format_add_column_action(self, action) -> Tuple[str, tuple]:
        if getattr(action, "if_not_exists", None) is True:
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE ADD COLUMN IF NOT EXISTS",
                suggestion="MySQL does not support IF NOT EXISTS on ADD COLUMN. "
                     "Pre-check information_schema.COLUMNS before ALTER."
            )
        column_sql, column_params = self.format_column_definition(action.column)
        after = action.dialect_options.get("after")
        if after:
            return f"ADD COLUMN {column_sql} AFTER {self.format_identifier(after)}", column_params
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action) -> Tuple[str, tuple]:
        if getattr(action, "if_exists", None) is True:
            raise UnsupportedFeatureError(
                self.name, "DROP COLUMN IF EXISTS",
                suggestion="MySQL does not support IF EXISTS on DROP COLUMN. "
                     "Pre-check information_schema.COLUMNS before ALTER."
            )
        return super().format_drop_column_action(action)

    def format_drop_table_constraint_action(self, action) -> Tuple[str, tuple]:
        if getattr(action, "if_exists", None) is True:
            raise UnsupportedFeatureError(
                self.name, "DROP CONSTRAINT IF EXISTS",
                suggestion="MySQL does not support IF EXISTS on DROP CONSTRAINT. "
                     "Pre-check information_schema.TABLE_CONSTRAINTS before ALTER."
            )
        return super().format_drop_table_constraint_action(action)

    def format_alter_column_action(self, action) -> Tuple[str, tuple]:
        """Format ALTER TABLE ... ALTER COLUMN {SET DEFAULT | DROP DEFAULT}.

        MySQL 8.0 syntax is ``ALTER TABLE t ALTER [COLUMN] col {SET DEFAULT
        literal | DROP DEFAULT}``. Unlike the generic SQL-standard renderer,
        MySQL requires a literal for SET DEFAULT (no parenthesised
        expressions / parameters), so we inline the value.
        """
        operation = getattr(action.operation, "value", None) or str(action.operation)
        col_name = self.format_identifier(action.column_name)

        if operation == "DROP DEFAULT":
            return f"ALTER COLUMN {col_name} DROP DEFAULT", ()

        if operation == "SET DEFAULT":
            new_value = getattr(action, "new_value", None)
            if isinstance(new_value, str):
                escaped = self._escape_sql_string(new_value)
                return f"ALTER COLUMN {col_name} SET DEFAULT '{escaped}'", ()
            if new_value is None:
                raise ValueError("SET DEFAULT requires a default value")
            if hasattr(new_value, "to_sql"):
                value_sql, value_params = new_value.to_sql()
                if value_params:
                    # DDL accepts no bind parameters: re-render inline.
                    from rhosocial.activerecord.backend.expression.core import Literal
                    if isinstance(new_value, Literal):
                        return f"ALTER COLUMN {col_name} SET DEFAULT {self.inline_sql_literal(new_value.value)}", ()
                return f"ALTER COLUMN {col_name} SET DEFAULT {value_sql}", tuple(value_params)
            return f"ALTER COLUMN {col_name} SET DEFAULT {self.inline_sql_literal(new_value)}", ()

        # Fall through to the SQL-standard rendering for other operations.
        return super().format_alter_column_action(action)




    # endregion

    # region Trigger Support (MySQL-specific)









    # endregion
    
    # region FULLTEXT Index & Search Support







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

    def supports_auto_increment(self) -> bool:
        """Whether AUTO_INCREMENT column attributes are supported.

        MySQL supports AUTO_INCREMENT on integer key columns.
        """
        return True

    def supports_generated_columns(self) -> bool:
        """Whether generated (computed) columns are supported."""
        return self.supports_generated_column()

    def supports_stored_generated_columns(self) -> bool:
        """Whether STORED generated columns are supported."""
        return self.supports_generated_column()

    def supports_virtual_generated_columns(self) -> bool:
        """Whether VIRTUAL generated columns are supported."""
        return self.supports_generated_column()

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
        # JSON functions are available since MySQL 5.7.8.
        "json_extract": ((5, 7, 8), None),
        "json_extract_text": ((5, 7, 13), None),
        "json_build_object": (None, (0, 0, 0)),
        "json_array_elements": (None, (0, 0, 0)),
        "json_objectagg": ((5, 7, 22), None),
        "json_arrayagg": ((5, 7, 22), None),
        # MySQL-specific JSON function wrappers use JSON_* functions from MySQL 5.7.8.
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

        expression_constructors = {
            "xmlagg",
            "xmlattributes",
            "xmlcomment",
            "xmlconcat",
            "xmlelement",
            "xmlexists",
            "xmlforest",
            "xmlparse",
            "xmlpi",
            "xmlquery",
            "xmlroot",
            "xmlserialize",
            "xmltable",
        }
        result = {}
        for func_name in core_functions:
            if func_name not in expression_constructors:
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

    def format_set_transaction(self, expr: "SetTransactionExpression") -> Tuple[str, tuple]:
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

    def format_begin_transaction(self, expr: "BeginTransactionExpression") -> Tuple[str, tuple]:
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
                    message="READ ONLY transactions require MySQL 5.6.5 or later.",
                )
        else:
            return "START TRANSACTION", ()

    # endregion

    # region MySQL-specific DML Operations



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
        is_replace = expr.dialect_options.get("replace", False)
        is_ignore = expr.dialect_options.get("ignore", False)

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
        from rhosocial.activerecord.backend.expression.statements import DefaultValuesSource, ValuesSource, SelectSource

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

        sql = " ".join(parts)

        # Handle ON CONFLICT (ON DUPLICATE KEY UPDATE for MySQL)
        if expr.on_conflict:
            conflict_sql, conflict_params = self.format_on_conflict_clauses(expr)
            sql += f" {conflict_sql}"
            all_params.extend(conflict_params)

        # Note: MySQL does not support RETURNING clause
        if expr.returning:
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "RETURNING clause (MySQL does not support RETURNING)")

        return sql, tuple(all_params)



    # endregion
