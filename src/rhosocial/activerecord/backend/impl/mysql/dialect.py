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
    TruncateSupport,
    TransactionControlSupport,
    SQLFunctionSupport,
    DDLTypeSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CollationMixin,
    CTEMixin,

    WindowFunctionMixin,
    JSONMixin,

    ArrayMixin,
    ExplainMixin,
    GraphMixin,

    MergeMixin,

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
    MySQLDateTimeMixin,
    MySQLCollationMixin,
    MySQLCTEMixin,
    MySQLWindowMixin,
    MySQLGroupingMixin,
    MySQLExplainMixin,
    MySQLDQLMixin,
    MySQLJoinMixin,
    MySQLSetOperationMixin,
    MySQLDDLColumnMixin,
    MySQLViewMixin,
    MySQLSchemaMixin,
    MySQLConstraintMixin,
    MySQLGeneratedColumnMixin,
    MySQLFunctionMixin,
)
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
    # MySQL-specific mixins (before generic mixins to override methods)
    MySQLDateTimeMixin,
    MySQLCollationMixin,
    MySQLCTEMixin,
    MySQLWindowMixin,
    MySQLGroupingMixin,
    MySQLExplainMixin,
    MySQLDQLMixin,
    MySQLJoinMixin,
    MySQLSetOperationMixin,
    MySQLDDLColumnMixin,
    MySQLViewMixin,
    MySQLSchemaMixin,
    MySQLConstraintMixin,
    MySQLGeneratedColumnMixin,
    MySQLFunctionMixin,
    # Generic mixins
    CollationMixin,
    CTEMixin,

    WindowFunctionMixin,
    MySQLJSONFunctionMixin,
    JSONMixin,

    ArrayMixin,
    ExplainMixin,
    GraphMixin,
    MySQLLockingMixin,

    MergeMixin,

    TemporalTableMixin,
    MySQLFullTextSearchMixin,
    MySQLTriggerMixin,
    MySQLDMLOperationMixin,
    UpsertMixin,
    LateralJoinMixin,
    JoinMixin,
    ViewMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    MySQLPartitionMixin,
    PartitionMixin,
    MySQLTransactionMixin,
    MySQLTableMixin,
    MySQLRenameTableMixin,
    TableMixin,
    MySQLTruncateMixin,
    TruncateMixin,
    ConstraintMixin,
    MySQLSetTypeMixin,
    MySQLSpatialMixin,
    MySQLVectorMixin,
    MySQLIntrospectionMixin,
    MySQLShowDialectMixin,
    MySQLModifyColumnMixin,
    MySQLJsonDualityViewMixin,
    MySQLTypeSupportMixin,
    MySQLOptimizerHintMixin,
    MySQLTableStatementMixin,
    MySQLMaintenanceMixin,
    MySQLRoutineMixin,
    MySQLLoadXMLLMixin,
    MySQLAdminCommandMixin,
    IntrospectionMixin,
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    TransactionControlMixin,
    SetOperationMixin,
    # Protocols for type checking
    CollationSupport,
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    MySQLJSONFunctionSupport,
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
    MySQLLockingSupport,
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
    MySQLTableSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TruncateSupport,
    TransactionControlSupport,
    MySQLTriggerSupport,
    MySQLSetTypeSupport,
    MySQLSpatialSupport,
    MySQLVectorSupport,
    MySQLFullTextSearchSupport,
    MySQLModifyColumnSupport,
    MySQLJsonDualityViewSupport,
    MySQLOptimizerHintSupport,
    MySQLPartitionSupport,
    MySQLDMLOperationSupport,
    MySQLRenameTableSupport,
    MySQLTableStatementSupport,
    MySQLMaintenanceSupport,
    MySQLRoutineSupport,
    MySQLLoadXMLSupport,
    MySQLAdminCommandSupport,
    SQLFunctionSupport,
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

    def supports_json_arrow_operators(self) -> bool:
        """Check if MySQL version supports -> and ->> operators."""
        return self.version >= (5, 7, 9)

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
        is_replace = getattr(expr, "replace", False)
        is_ignore = getattr(expr, "ignore", False)

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
