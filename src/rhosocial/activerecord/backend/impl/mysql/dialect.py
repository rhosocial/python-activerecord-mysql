# src/rhosocial/activerecord/backend/impl/mysql/dialect.py
"""
MySQL backend SQL dialect implementation.

This dialect implements protocols for features that MySQL actually supports,
based on the MySQL version provided at initialization.
"""

from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.expression.objects import Table
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
    ViewObjectSupport,
    NamespaceSupport,
    SequenceObjectSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TruncateSupport,
    TransactionControlSupport,
    SQLFunctionSupport,
    DataTypeSupport,
    # Column Class Support Protocol
    ColumnTypeSupport,
    TypeObjectSupport,
    CreateTypeSupport,
    AlterTypeSupport,
    DropTypeSupport,
    CreateDomainSupport,
    AlterDomainSupport,
    DropDomainSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    # Named objects: each *NameMixin inherits NamespaceMixin, so they precede it.
    RelationSourceMixin,
    NamespaceMixin,
    TableNameMixin,
    ViewNameMixin,
    MaterializedViewNameMixin,
    ForeignTableNameMixin,
    IndexNameMixin,
    SequenceNameMixin,
    TriggerNameMixin,
    FunctionNameMixin,
    ProcedureNameMixin,
    TypeNameMixin,
    DomainNameMixin,
    SynonymNameMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
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
    IndexMixin,
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
    AutoIncrementMixin,
    IdentityColumnMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    TransactionControlMixin,
    SetOperationMixin,
)
from .protocols import (
    MySQLTriggerSupport,
    MySQLTableSupport,
    MySQLSetTypeSupport,
    MySQLTypeSupport,
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
    MySQLNamespaceMixin,
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
    MySQLMaintenanceMixin,
    MySQLRoutineMixin,
    MySQLTableStatementMixin,
    MySQLLoadXMLLMixin,
    MySQLAdminCommandMixin,
    MySQLDateTimeMixin,
    MySQLCharsetCollationMixin,
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
    MySQLDatabaseMixin,
    MySQLConstraintMixin,
    MySQLGeneratedColumnMixin,
    MySQLFunctionMixin,
    MySQLColumnTypeMixin,
)
from .mixins.object_kind import require_kind
from .reserved_words import MYSQL_RESERVED_WORDS
from .show.dialect import MySQLShowDialectMixin

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        InsertExpression,
    )


class MySQLDialect(
    SQLDialectBase,
    # MySQL's own namespace rules first, and before NamespaceMixin for the C3
    # reason: MySQLNamespaceMixin overrides supports_catalog,
    # supports_catalog_qualification, validate_namespace and
    # format_qualified_name, so it has to precede the mixin that supplies the
    # defaults it replaces. It comes before the *NameMixin classes too, because
    # those inherit NamespaceMixin and would otherwise win.
    MySQLNamespaceMixin,
    # MySQLTableStatementMixin comes before RelationSourceMixin, and not for
    # tidiness: both declare supports_values_table_constructor. Core's
    # RelationSourceMixin answers False because SQL Server has no VALUES table
    # source; this backend's answers from the MySQL version, since VALUES as a
    # table value constructor arrived in 8.0.19. Only the first in the list wins,
    # so with RelationSourceMixin first this backend reported False at every
    # version and `VALUES ROW(...)` was reported unsupported on a server that
    # has supported it since 8.0.19.
    MySQLTableStatementMixin,
    # Named objects: a statement now holds a schema object and asks it for its
    # own SQL, so each kind needs a formatter here. The *NameMixin classes all
    # derive from NamespaceMixin and therefore precede it (C3).
    RelationSourceMixin,
    TableNameMixin,
    ViewNameMixin,
    MaterializedViewNameMixin,
    ForeignTableNameMixin,
    IndexNameMixin,
    SequenceNameMixin,
    TriggerNameMixin,
    FunctionNameMixin,
    ProcedureNameMixin,
    TypeNameMixin,
    DomainNameMixin,
    SynonymNameMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    NamespaceMixin,
    # MySQL-specific mixins (before generic mixins to override methods)
    MySQLDateTimeMixin,
    MySQLCharsetCollationMixin,
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
    MySQLDatabaseMixin,
    MySQLConstraintMixin,
    MySQLGeneratedColumnMixin,
    # Column types. The MySQL half states its own eighteen-entry table; there
    # is no generic table in core to compose, so it stands alone in C3. Nothing
    # else in this list can answer the column-type protocol, so it may move as
    # a unit without disturbing the order around it -- which is the reason for
    # not standing it next to MySQLTypeSupportMixin further down, where a
    # mistake would reorder the DDL formatters too. (The class attribute is
    # the version-independent answer; the one version-gated refusal lives in
    # MySQLColumnTypeMixin.suggested_column_types, so a dialect built at one
    # version cannot leak its answer into one built at another.)
    MySQLColumnTypeMixin,
    # The two auto-increment mechanisms are separate mixins, and their order
    # here is load-bearing. MySQLGeneratedColumnMixin declares the
    # parameterless AUTO_INCREMENT marker True; AutoIncrementMixin supplies
    # the fail-closed default and the formatter that consults the probe, so it
    # must come after the MySQL declaration for the True to win. IdentityColumnMixin
    # supplies the SQL-standard identity clause's probes and formatter; MySQL
    # has no GENERATED ... AS IDENTITY grammar (every version measured refuses
    # it), so every one of its probes inherits the False default and an
    # identity request is refused by name. Mixing the mixin in, rather than
    # keeping a local format_identity_clause override, is what stops ALWAYS and
    # start/increment from being silently dropped into a bare AUTO_INCREMENT.
    AutoIncrementMixin,
    IdentityColumnMixin,
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
    IndexMixin,
    # No SequenceMixin here, and its absence is deliberate rather than an
    # oversight: MySQL has no sequence object. It numbers rows with AUTO_INCREMENT
    # columns, so CREATE / DROP / ALTER SEQUENCE is not a statement the server
    # parses -- and the core formatters never consult supports_sequence(), so
    # inheriting them would render well-formed SQL MySQL would refuse rather
    # than refuse it here. Leaving the mixin out makes the absence structural:
    # the dispatch finds no formatter and raises UnsupportedFeatureError naming
    # the dialect and the statement. SequenceNameMixin above is kept, and is a
    # separate job: it names the object, so a Sequence is still accepted as an
    # identifier and Sequence(dialect, "s").to_sql() keeps rendering.
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
    UserDefinedTypeMixin,
    DomainMixin,
    MySQLOptimizerHintMixin,
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
    ViewObjectSupport,
    SequenceObjectSupport,
    MySQLTableSupport,
    ConstraintSupport,
    IntrospectionSupport,
    TruncateSupport,
    TransactionControlSupport,
    MySQLTriggerSupport,
    MySQLSetTypeSupport,
    MySQLTypeSupport,
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
    DataTypeSupport,
    TypeObjectSupport,
    CreateTypeSupport,
    AlterTypeSupport,
    DropTypeSupport,
    CreateDomainSupport,
    AlterDomainSupport,
    DropDomainSupport,
    # The naming protocol every object protocol above derives from, so it has
    # to come last: C3 requires a base to follow each of its subclasses.
    NamespaceSupport,
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

    def supports_on_conflict_clause(self) -> bool:
        """Whether INSERT can carry an ON CONFLICT style clause.

        MySQL expresses upsert via ON DUPLICATE KEY UPDATE.
        """
        return True

    def supports_multiple_on_conflict_clauses(self) -> bool:
        """MySQL's ON DUPLICATE KEY UPDATE allows only a single clause."""
        return False

    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Format INSERT statement with MySQL-specific options.

        Extends the base implementation to support the typed flags on
        ``MySQLInsertExpression``:
        - ``ignore=True`` → ``INSERT IGNORE``
        - ``replace=True`` → ``REPLACE INTO``

        Args:
            expr: InsertExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)

        Raises:
            TypeError: If ``expr.into`` is not a Table. Checked here rather than
                in the constructor because the dialect is known at render time
                and not necessarily at construction time, and a View or a
                Sequence in the INTO slot renders through its own formatter --
                a well-formed INSERT writing to something the caller never
                named.
            ValueError: If both 'ignore' and 'replace' are specified, or if
                       'replace' is used with 'on_conflict'
        """
        # Perform strict parameter validation
        if self.strict_validation:
            expr.validate(strict=True)

        require_kind(expr.into, Table, "InsertExpression.into")

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
