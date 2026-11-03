# src/rhosocial/activerecord/backend/impl/mysql/mixins/introspection.py
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
    from rhosocial.activerecord.backend.expression.introspection import (
        DatabaseInfoQueryStatement,
        TableListQueryStatement,
        ColumnInfoQueryStatement,
        IndexInfoQueryStatement,
        ForeignKeyQueryStatement,
        ViewListQueryStatement,
        ViewInfoQueryStatement,
        TriggerListQueryStatement,
        TableUsageStatsQueryStatement,
        UnusedIndexesQueryStatement,
        RuntimeMetricsQueryStatement,
        IndexUsageStatsQueryStatement,
        ObjectDependencyQueryStatement,
        DDLStatementQueryStatement,
        ColumnDataProfileQueryStatement,
        ColumnValueSampleQueryStatement,
        JoinCoverageQueryStatement,
    )
    from ...expression.introspection import (
        MySQLTableOptionsListQueryStatement,
        MySQLTableOptionsInfoQueryStatement,
        MySQLPartitionListQueryStatement,
    )


#: MySQL's own metadata databases. A caller asking for "user tables" does not
#: mean these four, so they are excluded unless system objects were requested.
SYSTEM_SCHEMAS = ("information_schema", "performance_schema", "mysql", "sys")

#: The storage-options projection, shared by the list and the single-table
#: form: one engine's facts about a table, in the order the catalogue reports
#: them. ``DATA_LENGTH`` and ``INDEX_LENGTH`` are byte estimates for InnoDB.
TABLE_OPTION_COLUMNS = (
    "TABLE_SCHEMA",
    "TABLE_NAME",
    "ENGINE",
    "ROW_FORMAT",
    "TABLE_COLLATION",
    "AUTO_INCREMENT",
    "TABLE_COMMENT",
    "CREATE_OPTIONS",
    "DATA_LENGTH",
    "INDEX_LENGTH",
)

#: The partition projection: one row per partition or subpartition, in the
#: engine's ordinal order.
PARTITION_COLUMNS = (
    "TABLE_SCHEMA",
    "TABLE_NAME",
    "PARTITION_NAME",
    "SUBPARTITION_NAME",
    "PARTITION_METHOD",
    "PARTITION_EXPRESSION",
    "PARTITION_DESCRIPTION",
    "PARTITION_ORDINAL_POSITION",
    "SUBPARTITION_ORDINAL_POSITION",
    "TABLE_ROWS",
    "DATA_LENGTH",
    "INDEX_LENGTH",
)


class MySQLIntrospectionMixin:
    """MySQL introspection capability declaration and query formatting.

    This mixin implements the IntrospectionSupport protocol by:
    1. Declaring which introspection features MySQL supports (supports_* methods)
    2. Formatting SQL queries for introspection (format_*_query methods)

    The format_*_query methods are called by Expression.to_sql() to generate
    database-specific SQL using information_schema.

    Architecture flow:
        Introspector._build_*_sql() [base class]
            → Expression(Dialect).to_sql()
                → Dialect.format_*_query() [this mixin]
                    → Returns SQL and parameters

    Every query here is an expression tree, not assembled text: a projection of
    :class:`~...expression.core.Column` nodes, a relation, a conjunction of
    predicates and an ordering. What a query *asks* is therefore a structure the
    rest of the framework can inspect, and this module writes no clause at all --
    the dialect renders each node.

    MySQL supports all introspection features via information_schema.
    """

    def supports_table_options_introspection(self) -> bool:
        """MySQL answers for a table's storage options from ``information_schema.TABLES``.

        The capability for the ``introspect table-options`` family: engine, row
        format, collation and the byte estimates the same view already reports."""
        return True

    def supports_table_storage_introspection(self) -> bool:
        """MySQL answers the per-table storage slots from the same TABLES view.

        ``information_schema.TABLES`` reports ``TABLE_ROWS``, ``DATA_LENGTH`` and
        ``INDEX_LENGTH`` per table, so the narrow slots of
        :class:`~rhosocial.activerecord.backend.introspection.types.IntrospectionTableInfo`
        -- ``size_bytes``, ``row_count`` and the data/index split -- are all
        answerable. The bytes are the server's own accounting, an estimate for
        InnoDB rather than an exact sum of row sizes."""
        return True

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """MySQL supports introspection via information_schema."""
        return True

    def supports_database_info(self) -> bool:
        """MySQL supports database info via information_schema.SCHEMATA."""
        return True

    def supports_table_introspection(self) -> bool:
        """MySQL supports table introspection via information_schema.TABLES."""
        return True

    def supports_column_introspection(self) -> bool:
        """MySQL supports column introspection via information_schema.COLUMNS."""
        return True

    def supports_index_introspection(self) -> bool:
        """MySQL supports index introspection via information_schema.STATISTICS."""
        return True

    def supports_foreign_key_introspection(self) -> bool:
        """MySQL supports foreign key introspection via information_schema."""
        return True

    def supports_view_introspection(self) -> bool:
        """MySQL supports view introspection via information_schema.VIEWS."""
        return True

    def supports_trigger_introspection(self) -> bool:
        """MySQL supports trigger introspection via information_schema.TRIGGERS."""
        return True

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        return [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.FOREIGN_KEY,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]

    # ========== Query Formatting ==========

    def _information_schema_query(
        self,
        relation: str,
        projections: "list",
        conditions: "list",
        order_by: "Optional[list]" = None,
        source: "Any" = None,
    ) -> Tuple[str, tuple]:
        """Build a SELECT over one catalogue relation.

        Each formatter below supplies only what varies -- the relation, the
        projection, the conjunction and the ordering -- and the shape lives
        here. The relation is a :class:`Table` carrying its database in the
        catalog slot, because MySQL's only namespace level is the database and
        putting ``information_schema`` in ``schema_name`` would be refused
        rather than silently dropped. A formatter reading the performance
        schema passes its own relation through ``source``, with that database
        in the same slot.

        A caller with nothing to filter -- the runtime listing, which describes
        a server rather than a schema -- passes an empty list, and gets no
        WHERE at all. An empty ``LogicalPredicate`` would render a ``WHERE``
        keyword with no condition after it, which the server rejects.

        Args:
            relation: The ``information_schema`` relation being read.
            projections: The select list, in order.
            conditions: Conditions to AND together; none means no WHERE.
            order_by: The ordering expressions, or ``None`` for no ORDER BY.
            source: A pre-built FROM source (a join for the foreign-key query,
                another catalogue for the performance schema), or ``None`` to
                read *relation* directly.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.objects import Table

        kwargs: "dict" = {
            "select": projections,
            "from_": (
                source
                if source is not None
                else Table(self, relation, catalog_name="information_schema")
            ),
        }
        if conditions:
            kwargs["where"] = WhereClause(
                self, LogicalPredicate(self, "AND", *conditions)
            )
        if order_by is not None:
            kwargs["order_by"] = OrderByClause(self, order_by)
        return QueryStatement(self, **kwargs).to_sql()

    def format_database_info_query_statement(self, expr: "DatabaseInfoQueryStatement") -> Tuple[str, tuple]:
        """Format database information query."""
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        params = expr.get_params()
        schema = params.get("schema", "")

        return self._information_schema_query(
            "SCHEMATA",
            [
                Column(self, "DEFAULT_CHARACTER_SET_NAME"),
                Column(self, "DEFAULT_COLLATION_NAME"),
            ],
            [ComparisonPredicate(self, "eq", Column(self, "SCHEMA_NAME"), Literal(self, schema))],
        )

    def format_table_list_query_statement(self, expr: "TableListQueryStatement") -> Tuple[str, tuple]:
        """Format table list query."""
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            InPredicate,
            Literal,
            LogicalPredicate,
        )

        params = expr.get_params()
        schema = params.get("schema", "")
        include_views = params.get("include_views", True)
        include_system = params.get("include_system", False)
        table_type = params.get("table_type")

        # The bound schema value comes first, so the parameter tuple keeps the
        # order the concatenated form produced.
        conditions = [
            ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema))
        ]
        if not include_system:
            # The exclusion list is literal-inline: it is a fact about the
            # engine, not caller data, so it never becomes a bind parameter.
            conditions.append(
                LogicalPredicate(
                    self,
                    "NOT",
                    InPredicate(
                        self,
                        Column(self, "TABLE_SCHEMA"),
                        Literal(self, SYSTEM_SCHEMAS, inline=True),
                    ),
                )
            )
        if not include_views:
            conditions.append(
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "TABLE_TYPE"),
                    Literal(self, "BASE TABLE", inline=True),
                )
            )
        if table_type:
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_TYPE"), Literal(self, table_type)
                )
            )

        return self._information_schema_query(
            "TABLES",
            [
                Column(self, "TABLE_NAME"),
                Column(self, "TABLE_TYPE"),
                Column(self, "TABLE_COMMENT"),
                Column(self, "TABLE_ROWS"),
                # The storage split rides the same query that already reported
                # the row count and the data bytes: MySQL's storage is
                # row-plus-index shaped, so one projection answers both.
                Column(self, "DATA_LENGTH"),
                Column(self, "INDEX_LENGTH"),
                Column(self, "AUTO_INCREMENT"),
                Column(self, "CREATE_TIME"),
                Column(self, "UPDATE_TIME"),
            ],
            conditions,
        )

    def format_column_info_query_statement(self, expr: "ColumnInfoQueryStatement") -> Tuple[str, tuple]:
        """Format column information query."""
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema", "")

        return self._information_schema_query(
            "COLUMNS",
            [
                Column(self, "COLUMN_NAME"),
                Column(self, "ORDINAL_POSITION"),
                Column(self, "COLUMN_DEFAULT"),
                Column(self, "IS_NULLABLE"),
                Column(self, "DATA_TYPE"),
                Column(self, "CHARACTER_MAXIMUM_LENGTH"),
                Column(self, "NUMERIC_PRECISION"),
                Column(self, "NUMERIC_SCALE"),
                Column(self, "COLUMN_TYPE"),
                Column(self, "COLUMN_KEY"),
                Column(self, "EXTRA"),
                Column(self, "COLUMN_COMMENT"),
                Column(self, "CHARACTER_SET_NAME"),
                Column(self, "COLLATION_NAME"),
            ],
            [
                ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)),
                ComparisonPredicate(self, "eq", Column(self, "TABLE_NAME"), Literal(self, table_name)),
            ],
            [Column(self, "ORDINAL_POSITION")],
        )

    def format_index_info_query_statement(self, expr: "IndexInfoQueryStatement") -> Tuple[str, tuple]:
        """Format index information query."""
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema", "")

        return self._information_schema_query(
            "STATISTICS",
            [
                Column(self, "INDEX_NAME"),
                Column(self, "NON_UNIQUE"),
                Column(self, "SEQ_IN_INDEX"),
                Column(self, "COLUMN_NAME"),
                Column(self, "INDEX_TYPE"),
                Column(self, "SUB_PART"),
                Column(self, "NULLABLE"),
            ],
            [
                ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)),
                ComparisonPredicate(self, "eq", Column(self, "TABLE_NAME"), Literal(self, table_name)),
            ],
            [Column(self, "INDEX_NAME"), Column(self, "SEQ_IN_INDEX")],
        )

    def format_foreign_key_query_statement(self, expr: "ForeignKeyQueryStatement") -> Tuple[str, tuple]:
        """Format foreign key information query."""
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            IsNullPredicate,
            JoinClause,
            Literal,
            LogicalPredicate,
        )
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources.relation import NamedRelationRef

        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema", "")

        usage = NamedRelationRef(
            self,
            Table(self, "KEY_COLUMN_USAGE", catalog_name="information_schema"),
            alias="kcu",
        )
        constraints = NamedRelationRef(
            self,
            Table(self, "REFERENTIAL_CONSTRAINTS", catalog_name="information_schema"),
            alias="rc",
        )
        join = JoinClause(
            self,
            left_table=usage,
            right_table=constraints,
            join_type="JOIN",
            condition=LogicalPredicate(
                self,
                "AND",
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "CONSTRAINT_NAME", table="kcu"),
                    Column(self, "CONSTRAINT_NAME", table="rc"),
                ),
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "CONSTRAINT_SCHEMA", table="kcu"),
                    Column(self, "CONSTRAINT_SCHEMA", table="rc"),
                ),
            ),
        )

        return self._information_schema_query(
            "KEY_COLUMN_USAGE",
            [
                Column(self, "CONSTRAINT_NAME", table="kcu"),
                Column(self, "COLUMN_NAME", table="kcu"),
                Column(self, "ORDINAL_POSITION", table="kcu"),
                Column(self, "REFERENCED_TABLE_NAME", table="kcu"),
                Column(self, "REFERENCED_COLUMN_NAME", table="kcu"),
                Column(self, "UPDATE_RULE", table="rc"),
                Column(self, "DELETE_RULE", table="rc"),
            ],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_SCHEMA", table="kcu"), Literal(self, schema)
                ),
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_NAME", table="kcu"), Literal(self, table_name)
                ),
                # A usage row without a referenced table is a plain index
                # column, not a foreign key: the predicate says so in the tree.
                IsNullPredicate(self, Column(self, "REFERENCED_TABLE_NAME", table="kcu"), is_not=True),
            ],
            [
                Column(self, "CONSTRAINT_NAME", table="kcu"),
                Column(self, "ORDINAL_POSITION", table="kcu"),
            ],
            source=join,
        )

    def format_view_list_query_statement(self, expr: "ViewListQueryStatement") -> Tuple[str, tuple]:
        """Format view list query."""
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            InPredicate,
            Literal,
            LogicalPredicate,
        )

        params = expr.get_params()
        schema = params.get("schema", "")
        include_system = params.get("include_system", False)

        conditions = [
            ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema))
        ]
        if not include_system:
            conditions.append(
                LogicalPredicate(
                    self,
                    "NOT",
                    InPredicate(
                        self,
                        Column(self, "TABLE_SCHEMA"),
                        Literal(self, SYSTEM_SCHEMAS, inline=True),
                    ),
                )
            )

        return self._information_schema_query(
            "VIEWS",
            [
                Column(self, "TABLE_NAME"),
                Column(self, "VIEW_DEFINITION"),
                Column(self, "CHECK_OPTION"),
                Column(self, "IS_UPDATABLE"),
            ],
            conditions,
            [Column(self, "TABLE_NAME")],
        )

    def format_view_info_query_statement(self, expr: "ViewInfoQueryStatement") -> Tuple[str, tuple]:
        """Format single view information query."""
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        params = expr.get_params()
        view_name = params.get("view_name", "")
        schema = params.get("schema", "")

        return self._information_schema_query(
            "VIEWS",
            [
                Column(self, "TABLE_NAME"),
                Column(self, "VIEW_DEFINITION"),
                Column(self, "CHECK_OPTION"),
                Column(self, "IS_UPDATABLE"),
            ],
            [
                ComparisonPredicate(self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)),
                ComparisonPredicate(self, "eq", Column(self, "TABLE_NAME"), Literal(self, view_name)),
            ],
        )

    def format_trigger_list_query_statement(self, expr: "TriggerListQueryStatement") -> Tuple[str, tuple]:
        """Format trigger list query."""
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        params = expr.get_params()
        table_name = params.get("table_name")
        schema = params.get("schema", "")

        conditions = [
            ComparisonPredicate(self, "eq", Column(self, "TRIGGER_SCHEMA"), Literal(self, schema))
        ]
        if table_name:
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "EVENT_OBJECT_TABLE"), Literal(self, table_name)
                )
            )

        return self._information_schema_query(
            "TRIGGERS",
            [
                Column(self, "TRIGGER_NAME"),
                Column(self, "EVENT_MANIPULATION"),
                Column(self, "EVENT_OBJECT_TABLE"),
                Column(self, "ACTION_TIMING"),
                Column(self, "ACTION_STATEMENT"),
                Column(self, "CREATED"),
            ],
            conditions,
            [Column(self, "TRIGGER_NAME")],
        )

    def format_table_options_list_query_statement(
        self, expr: "MySQLTableOptionsListQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the storage-options query for every base table.

        ``DATA_LENGTH`` and ``INDEX_LENGTH`` are bytes for InnoDB estimates of
        the clustered index, not exact sizes; the parser repeats the caveat
        next to the numbers.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        schema = expr.get_params().get("schema") or ""

        return self._information_schema_query(
            "TABLES",
            [Column(self, name) for name in TABLE_OPTION_COLUMNS],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)
                ),
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "TABLE_TYPE"),
                    Literal(self, "BASE TABLE", inline=True),
                ),
            ],
            [Column(self, "TABLE_NAME")],
        )

    def format_table_options_info_query_statement(
        self, expr: "MySQLTableOptionsInfoQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the storage-options query for one table."""
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        params = expr.get_params()
        schema = params.get("schema") or ""
        table_name = params.get("table_name", "")

        return self._information_schema_query(
            "TABLES",
            [Column(self, name) for name in TABLE_OPTION_COLUMNS],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)
                ),
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_NAME"), Literal(self, table_name)
                ),
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "TABLE_TYPE"),
                    Literal(self, "BASE TABLE", inline=True),
                ),
            ],
        )

    def format_partition_list_query_statement(
        self, expr: "MySQLPartitionListQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the partition query for one table.

        ``PARTITION_NAME IS NOT NULL`` drops the row a non-partitioned table
        always has, so an empty answer means "not partitioned" and nothing
        weaker than that.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        params = expr.get_params()
        schema = params.get("schema") or ""
        table_name = params.get("table_name", "")

        return self._information_schema_query(
            "PARTITIONS",
            [Column(self, name) for name in PARTITION_COLUMNS],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_SCHEMA"), Literal(self, schema)
                ),
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_NAME"), Literal(self, table_name)
                ),
                Column(self, "PARTITION_NAME").is_not_null(),
            ],
            [
                Column(self, "PARTITION_ORDINAL_POSITION"),
                Column(self, "SUBPARTITION_ORDINAL_POSITION"),
            ],
        )

    def supports_unused_indexes_detection(self) -> bool:
        """MySQL answers from ``sys.schema_unused_indexes``.

        That view exists in stock MySQL 5.7+ and MariaDB does not ship it --
        which is why the capability is declared here rather than inherited
        from a shared MySQL-family mixin. What the view means: an index the
        performance schema has seen no *access* for, counting from the last
        time the table's statistics were reset. It is a strong hint and not a
        proof -- a table nobody has queried since a restart reports all of its
        indexes, and the view covers only tables the performance schema
        instruments -- so the answer is read as "worth reviewing", never as
        "safe to drop".
        """
        return True

    def format_unused_indexes_query_statement(
        self, expr: "UnusedIndexesQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the unused-indexes listing from ``sys.schema_unused_indexes``.

        The view already carries the address the caller needs -- schema,
        object, index name -- so the projection is the view's own columns
        rather than a join against ``information_schema``: the join would add
        nothing and could disagree with the view about which tables it covers.

        The schema filter is applied here rather than left to the caller
        because the view is database-wide and a caller asking about one schema
        should not have to post-filter a listing that may be large.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
        from rhosocial.activerecord.backend.expression.statements import (
            QueryStatement,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.statements.dql import (
            OrderByClause,
        )

        params = expr.get_params()
        schema = params.get("schema", "")

        # ``sys`` rides the catalog slot: MySQL's only namespace level is the
        # database, and putting it in schema_name is refused rather than
        # silently dropped (the same rule ``_information_schema_query`` spells
        # out for ``information_schema``).
        view = Table(self, "schema_unused_indexes", catalog_name="sys")
        column = Column(self, "object_schema")
        statement = QueryStatement(
            self,
            select=[
                Column(self, "object_schema"),
                Column(self, "object_name"),
                Column(self, "index_name"),
            ],
            from_=NamedRelationRef(self, view),
            where=WhereClause(
                self,
                condition=ComparisonPredicate(
                    self, "eq", column, Literal(self, schema)
                ),
            ),
            order_by=OrderByClause(
                self,
                expressions=[
                    (Column(self, "object_schema"), "ASC"),
                    (Column(self, "object_name"), "ASC"),
                    (Column(self, "index_name"), "ASC"),
                ],
            ),
        )
        return statement.to_sql()


    def supports_runtime_stats(self) -> bool:
        """MySQL answers runtime measurements from ``performance_schema``.

        Its counters cover the server's *uptime* rather than a resettable
        window, which is a different tense from PostgreSQL's: a zero means
        "not since startup" and the numbers carry as far as the server has
        been up. The family is only as available as the performance schema,
        which is an install-time option -- hence the docstring here rather
        than a promise on the probe alone.
        """
        return True

    def supports_index_stats(self) -> bool:
        """MySQL answers per-index counters from the performance schema.

        ``table_io_waits_summary_by_index_usage`` keeps the per-index split of the
        table-level counters already used for ``table_stats``, so "how much
        is this index used" and "which access shape" are both answerable.
        """
        return True

    def supports_object_dependencies(self) -> bool:
        """MySQL answers dependencies from ``referential_constraints``.

        That catalogue covers **foreign keys only** -- it does not record
        which view or trigger references which table. So the answer is a real
        graph and a partial one, and the docstring says which part rather
        than letting a reader assume the catalogue is complete.
        """
        return True

    def supports_ddl_extraction(self) -> bool:
        """MySQL answers natively: ``SHOW CREATE TABLE`` (and VIEW / PROCEDURE).

        Unlike PostgreSQL, the engine itself will hand back the DDL it holds,
        so ``DDLStatement.native`` is True and the text is the engine's own
        rather than an assembly pretending to be.
        """
        return True

    def supports_ddl_extraction_native(self) -> bool:
        """True -- ``SHOW CREATE`` is MySQL's own retrieval, not an assembly."""
        return True

    def supports_table_stats(self) -> bool:
        """MySQL answers per-table usage counters from the performance schema.

        The source is ``performance_schema.table_io_waits_summary_by_table``,
        whose per-table wait counters count I/O operations since the server
        last started -- not since some resettable epoch -- and cover only
        tables the performance schema instruments. A zero is therefore "no
        I/O the collector saw", and the counters of two different servers are
        not comparable; both facts are the reader's to keep in mind, and the
        engine-specific split (fetches versus inserts versus updates) rides
        the row into ``extra`` rather than being forced into the common
        slots.
        """
        return True

    def format_table_usage_stats_query_statement(
        self, expr: "TableUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the per-table usage-counter listing from the performance schema.

        One row per instrumented table, projected from
        ``table_io_waits_summary_by_table``: ``count_read`` and
        ``count_write`` are the I/O sides the common shape names, and the
        view's finer split -- ``count_fetch``, ``count_insert``,
        ``count_update``, ``count_delete`` -- travels with the row into
        ``extra``, where ``TableUsageStats``' docstring says engine-specific
        counters belong.

        No row estimate is projected: the performance schema's summary view
        does not carry one, and MySQL's estimate lives in
        ``information_schema.tables``.TABLE_ROWS -- a different source with a
        different refresh schedule, whose number beside these counters would
        look more correlated than it is. ``estimated_row_count`` stays None
        here, and ``IntrospectionTableInfo.row_count`` is already the place
        the estimate is answered from.

        MySQL's counters are for I/O operations the performance schema timed,
        since server start -- a different tense from PostgreSQL's statement
        counters, and one more reason the two engines' numbers are not
        comparable.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
        from rhosocial.activerecord.backend.expression.statements import (
            QueryStatement,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.statements.dql import (
            OrderByClause,
        )

        params = expr.get_params()
        schema = params.get("schema", "")

        stats = Table(self, "table_io_waits_summary_by_table", catalog_name="performance_schema")

        object_schema = Column(self, "OBJECT_SCHEMA")
        object_name = Column(self, "OBJECT_NAME")

        statement = QueryStatement(
            self,
            select=[
                # The common shape's address slots, so the parser reads one
                # spelling on every engine: ``table_name`` is the name it keys
                # a row by.
                object_schema.as_("schema_name"),
                object_name.as_("table_name"),
                Column(self, "count_read"),
                Column(self, "count_write"),
                Column(self, "count_fetch"),
                Column(self, "count_insert"),
                Column(self, "count_update"),
                Column(self, "count_delete"),
            ],
            from_=NamedRelationRef(self, stats),
            where=WhereClause(
                self,
                condition=ComparisonPredicate(self, "eq", object_schema, Literal(self, schema)),
            ),
            order_by=OrderByClause(
                self,
                expressions=[
                    (object_schema, "ASC"),
                    (object_name, "ASC"),
                ],
            ),
        )
        return statement.to_sql()

    def format_runtime_metrics_query_statement(
        self, expr: "RuntimeMetricsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the runtime listing from the performance schema's pluggable tables.

        ``performance_schema.setup_instruments`` names what is actually being
        counted on this server, which makes it the honest source for a
        "what is alive" listing: an instrument not enabled produces no rows,
        and therefore no number, rather than a zero that would read as "idle".
        The relation is in the performance schema, not in
        ``information_schema``, so its database is named explicitly.
        """
        from rhosocial.activerecord.backend.expression import Column
        from rhosocial.activerecord.backend.expression.objects import Table

        # No schema filter: ``setup_instruments`` is server-wide and has no
        # schema column, so a filter here would refuse a correct query for a
        # nonsensical reason.
        return self._information_schema_query(
            "setup_instruments",
            [
                Column(self, "NAME").as_("name"),
                Column(self, "ENABLED").as_("value"),
                Column(self, "TIMED").as_("kind"),
            ],
            [],
            [Column(self, "NAME")],
            source=Table(self, "setup_instruments", catalog_name="performance_schema"),
        )

    def format_index_usage_stats_query_statement(
        self, expr: "IndexUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format per-index counters from ``table_io_waits_summary_by_index_usage``.

        ``COUNT_STAR`` is the number of wait events, ``COUNT_FETCH`` the
        fetches and ``COUNT_INSERT/UPDATE/DELETE`` the write shapes; the
        engine does not keep a per-index "rows read" counter, so
        ``rows_read`` stays unmapped rather than being filled with
        ``COUNT_FETCH`` -- a fetch is not a row and the two must not be
        merged into one slot.

        The summary lives in the performance schema, not in
        ``information_schema``, so the relation is named with its own
        database; the schema filter is applied here because the summary is
        server-wide and a caller asking about one database should not receive
        every database's indexes.
        """
        from rhosocial.activerecord.backend.expression import Column
        from rhosocial.activerecord.backend.expression.objects import Table

        params = expr.get_params()
        schema = params.get("schema", "")

        conditions = []
        if schema:
            from rhosocial.activerecord.backend.expression import (
                ComparisonPredicate,
                Literal,
            )

            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "OBJECT_SCHEMA"), Literal(self, schema)
                )
            )

        return self._information_schema_query(
            "table_io_waits_summary_by_index_usage",
            [
                # The common shape's address slots: the parser keys a row by
                # ``table_name`` and ``index_name``, so the catalogue's own
                # uppercase spellings are aliased onto them.
                Column(self, "OBJECT_SCHEMA").as_("schema_name"),
                Column(self, "OBJECT_NAME").as_("table_name"),
                Column(self, "INDEX_NAME").as_("index_name"),
                Column(self, "COUNT_STAR").as_("scans"),
                Column(self, "COUNT_FETCH").as_("rows_fetched"),
            ],
            conditions,
            [
                Column(self, "OBJECT_SCHEMA"),
                Column(self, "OBJECT_NAME"),
                Column(self, "INDEX_NAME"),
            ],
            source=Table(
                self, "table_io_waits_summary_by_index_usage", catalog_name="performance_schema"
            ),
        )

    def format_object_dependency_query_statement(
        self, expr: "ObjectDependencyQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format the foreign-key dependency graph.

        ``referential_constraints`` records the constraint and the tables it
        names, which is exactly one edge per FK -- a partial graph, and the
        partial part is stated on the probe so a reader does not take it for
        the whole one.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        params = expr.get_params()
        schema = params.get("schema", "")
        object_name = params.get("object_name")

        conditions = []
        if schema:
            conditions.append(
                ComparisonPredicate(
                    self,
                    "eq",
                    Column(self, "CONSTRAINT_SCHEMA"),
                    Literal(self, schema),
                )
            )
        if object_name:
            from rhosocial.activerecord.backend.expression import (
                ComparisonPredicate,
                Literal,
            )

            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "TABLE_NAME"), Literal(self, object_name)
                )
            )

        return self._information_schema_query(
            "referential_constraints",
            [
                Column(self, "CONSTRAINT_SCHEMA"),
                Column(self, "CONSTRAINT_NAME"),
                Column(self, "TABLE_NAME").as_("dependent"),
                Column(self, "REFERENCED_TABLE_NAME").as_("referenced"),
                Column(self, "DELETE_RULE").as_("action"),
            ],
            conditions,
            [Column(self, "CONSTRAINT_NAME")],
        )

    def format_ddl_statement_query_statement(
        self, expr: "DDLStatementQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format ``SHOW CREATE TABLE`` -- the engine's own text.

        The engine's result column is literally named ``Create Table``, so
        there is nothing to assemble: this is a read, not a reconstruction,
        which is why ``native`` is True here and False on PostgreSQL.

        Only TABLE is rendered. The engine also answers for VIEW, PROCEDURE,
        FUNCTION and TRIGGER through their own ``SHOW CREATE`` statements, and
        each has a different result column name -- adding them means mapping
        five shapes, which is a question about which ones callers actually
        ask rather than something to guess at now. A caller naming one of the
        others gets ``UnsupportedFeatureError`` rather than the table answer.
        """
        from rhosocial.activerecord.backend.impl.mysql.expression.show import (
            ShowCreateTableStatement,
        )

        params = expr.get_params()
        object_name = params.get("object_name", "")
        object_type = (params.get("object_type") or "TABLE").upper()
        if object_type != "TABLE":
            from rhosocial.activerecord.backend.dialect.exceptions import (
                UnsupportedFeatureError,
            )

            raise UnsupportedFeatureError(
                dialect_name="MySQL",
                feature_name="DDL retrieval for {0!r} objects".format(object_type),
                suggestion=(
                    "MySQL answers natively for TABLE; VIEW, PROCEDURE, "
                    "FUNCTION and TRIGGER each use a different SHOW CREATE "
                    "statement and result column, and are not mapped yet."
                ),
            )
        schema = params.get("schema") or self.default_schema

        return ShowCreateTableStatement(self, object_name, schema=schema).to_sql()

    # ========== Data Profiles (row-shaped answers) ==========

    def supports_column_data_profile(self) -> bool:
        """MySQL answers a column data profile by aggregating the rows.

        There is no per-column statistics catalogue to read.
        ``information_schema`` describes what a column *declares* -- type,
        nullability, default -- and never what its rows hold; ``ANALYZE
        TABLE`` refreshes the optimiser's *index* statistics
        (``information_schema.STATISTICS.CARDINALITY`` is one estimate per
        index prefix) and publishes no per-column distribution. So the answer
        is exact and paid for in time: one ``UNION ALL`` arm per column, each
        one a full scan of the table, which is why the result is labelled
        ``AGGREGATE`` rather than left to look like an estimate of some
        collector's last run.
        """
        return True

    def supports_column_value_sample(self) -> bool:
        """MySQL answers a value listing by aggregating with a limit.

        Nothing is precomputed, so this costs a ``GROUP BY`` over the whole
        column plus a sort of the groups -- the same order as the profile
        itself. That is why the two are separate probes rather than one call
        that would force the cheap half to pay for the dear one.
        """
        return True

    def supports_join_coverage(self) -> bool:
        """MySQL answers overlap by counting distinct values on both sides.

        Exact, and paid for with two scans of each column: one for the
        overlap, one for the denominator. ``COUNT(DISTINCT col)`` is the
        engine's own spelling for the second half, so no separate
        ``SELECT DISTINCT`` pass is needed for it. Answering ``True`` is right
        because the probe asks whether the engine *can* answer, not whether it
        can answer cheaply -- the cost belongs in the docstring, not in a
        False that would claim MySQL cannot measure its own rows.
        """
        return True

    def _user_relation(self, table_name: str, alias: str, schema: "Optional[str]"):
        """A user table as a FROM source, quoted by the dialect.

        The opposite of :meth:`_information_schema_query`'s catalog relation:
        a user table is whatever its owner declared -- mixed case, a space, a
        reserved word -- so the name and the database are left to the
        dialect's identifier renderer, and the alias is what tells the two
        sides of a coverage measurement apart.
        """
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.sources import (
            NamedRelationRef,
        )

        return NamedRelationRef(
            self,
            Table(self, table_name, catalog_name=schema or None),
            alias=alias,
        )

    def _profile_label(self, text: "Optional[str]", alias: str):
        """A constant label as a named select-list entry.

        ``Literal`` is deliberately unaliasable -- a value has nothing to name
        (see :class:`~...expression.core.Literal`) -- so the constant is cast
        to text, which is the smallest node in the tree that produces a named
        result. The cast is not there for its type: it is there so the label
        can be called ``column_name`` or ``source``, which is what the parser
        reads. ``None`` is the same node carrying SQL NULL, which is how the
        empty profile says "the column name is absent" without inventing one.

        The cast target is ``CHAR`` rather than a length-bounded string type
        because MySQL's CAST accepts ``CHAR`` bare and a label has no width to
        declare.
        """
        from rhosocial.activerecord.backend.expression.core import (
            CastExpression,
            Literal,
        )
        from rhosocial.activerecord.backend.expression.types.string import CharType

        return CastExpression(self, Literal(self, text, inline=True), CharType(self), alias=alias)

    def _profile_arm(self, table_name: str, schema: "Optional[str]", column_name: str):
        """One column's arm of the profile, as a node.

        The seven entries are the family's contract: the column's own name,
        the null count, the distinct count, the two endpoints, the row count
        the parser divides by, and the provenance. The null count is a ``SUM``
        over a ``CASE`` so an empty table answers NULL rather than a
        fabricated zero; the distinct count is ``COUNT(DISTINCT ...)``; the
        endpoints are the engine's own ``MIN``/``MAX``; and ``COUNT(*)`` rides
        the same scan as the divisor, so an arm reads its table once.

        ``COUNT(*)`` and the null count share a scan because they are two
        halves of one fraction: the parser divides one by the other, and
        reading the same table twice to get them would double the cost of the
        cheapest part of the answer.
        """
        from rhosocial.activerecord.backend.expression import (
            CaseExpression,
            Column,
            CountFunction,
            FunctionCall,
            IsNullPredicate,
            Literal,
            QueryStatement,
            RowCountWildcard,
            SumFunction,
        )
        from rhosocial.activerecord.backend.expression.objects import Table

        return QueryStatement(
            self,
            select=[
                self._profile_label(column_name, "column_name"),
                SumFunction(
                    self,
                    CaseExpression(
                        self,
                        cases=[
                            (
                                IsNullPredicate(self, Column(self, column_name)),
                                Literal(self, 1, inline=True),
                            )
                        ],
                        else_result=Literal(self, 0, inline=True),
                    ),
                ).as_("null_count"),
                CountFunction(self, Column(self, column_name), distinct=True).as_("distinct_count"),
                FunctionCall(self, "MIN", Column(self, column_name)).as_("min_value"),
                FunctionCall(self, "MAX", Column(self, column_name)).as_("max_value"),
                CountFunction(self, RowCountWildcard(self)).as_("row_count"),
                self._profile_label("aggregate", "source"),
            ],
            from_=Table(self, table_name, catalog_name=schema or None),
        )

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a per-column profile by aggregating the rows themselves.

        MySQL keeps no statistics catalogue to read, so the answer is exact
        and paid for in time, one full scan per column. That is why the result
        is labelled ``AGGREGATE`` -- and the label is projected *into* each
        row rather than stamped onto the result afterwards: a row that came
        back from the server says how it was produced, so a consumer comparing
        this profile with a PostgreSQL estimate can tell the two apart without
        knowing which engine it asked.

        One arm per column, over the column list the expression carries: SQL
        cannot pivot ``SUM(CASE WHEN col IS NULL ...)`` across columns it was
        never told about, so an aggregating dialect genuinely needs that list
        where a catalogue-based one does not.

        The one place in this module where a set operator is written as text.
        Every arm is a real :class:`~...expression.statements.dql.QueryStatement`
        -- the renderer owns its projection, its identifiers and its relation --
        because a ``UNION ALL`` over a column list known only at run time has
        no node to represent it: the column list is a tuple on the expression,
        not an operand in the tree. So each arm is rendered on its own, its
        parameters are concatenated in arm order, and the rendered arms are
        joined by the set operator's word. Nothing else here is text.

        ``null_count`` rather than a fraction: dividing by a row count that
        may legitimately be zero belongs in the parser, not in a SQL
        expression that would then have to guard against it.

        An empty column list answers with no rows. That case cannot arise from
        a real table -- MySQL requires at least one column -- but the branch
        has to render, so it is a statement that selects no rows rather than a
        special-case string.

        One consequence of the union is worth reading before the figures are:
        MySQL resolves *one* result type per column position across every
        arm, so ``min_value`` -- which carries ``code``'s text in one arm and
        ``amount``'s decimal in another -- arrives as text, ``'1.00'`` rather
        than a number. The values are exact; only the Python type is the
        union's. One query per column would keep each type, at the price of a
        round trip per column, which is the loop this family exists to avoid.
        """
        from rhosocial.activerecord.backend.expression import (
            ComparisonPredicate,
            Literal,
            QueryStatement,
            WhereClause,
        )

        params = expr.get_params()
        schema = params.get("schema")

        arms = []
        parameters: "list" = []
        for name in expr.columns:
            sql, arm_parameters = self._profile_arm(params.get("table_name"), schema, name).to_sql()
            arms.append(sql)
            parameters.extend(arm_parameters)

        if not arms:
            return QueryStatement(
                self,
                select=[self._profile_label(None, "column_name")],
                where=WhereClause(
                    self,
                    ComparisonPredicate(
                        self,
                        "eq",
                        Literal(self, 0, inline=True),
                        Literal(self, 1, inline=True),
                    ),
                ),
            ).to_sql()

        return " UNION ALL ".join(arms), tuple(parameters)

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a most-frequent-values listing with a grouped scan.

        Nothing is precomputed in MySQL, so this costs a ``GROUP BY`` over the
        column plus a sort of the groups -- the same order as the profile
        itself, which is why the two are separate probes rather than one call
        that would make the cheap half pay for the dear one.

        ``ORDER BY COUNT(*) DESC`` is what makes the answer "the most
        frequent values" rather than "the first values"; ties break by the
        value so two runs of the same query agree. The ``LIMIT`` is a bind
        parameter, as it is everywhere else in this dialect: keeping it bound
        means the caller's integer is never spliced into statement text, and
        MySQL accepts it once the placeholder reaches it as a number.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            CountFunction,
            GroupByHavingClause,
            LimitOffsetClause,
            OrderByClause,
            QueryStatement,
            RowCountWildcard,
        )
        from rhosocial.activerecord.backend.expression.objects import Table

        relation = Table(self, expr.table_name, catalog_name=expr.schema or None)
        column = Column(self, expr.column_name)

        return QueryStatement(
            self,
            select=[
                column.as_("value"),
                CountFunction(self, RowCountWildcard(self)).as_("count"),
            ],
            from_=relation,
            group_by_having=GroupByHavingClause(self, group_by=[Column(self, expr.column_name)]),
            order_by=OrderByClause(
                self,
                expressions=[
                    (CountFunction(self, RowCountWildcard(self)), "DESC"),
                    (Column(self, expr.column_name), "ASC"),
                ],
            ),
            limit_offset=LimitOffsetClause(self, limit=int(expr.limit)),
        ).to_sql()

    def _coverage_fraction(self, column, source, other_column, other_source):
        """One side of the overlap: the share of *column* the other side holds.

        The numerator counts the *distinct* values of *column* that also occur
        in *other_column*, as a ``COUNT(*)`` over a derived table of those
        distinct values; the denominator counts *column*'s distinct non-NULL
        values. Distinct on both sides is what makes the figure a coverage of
        values rather than of rows -- a key repeated a thousand times that
        matches once would otherwise read as well covered.

        ``IS NOT NULL`` is written on both halves rather than relied upon. In
        the numerator it is load-bearing: a DISTINCT treats a NULL as one
        value, so counting it would credit the tested side with a match it
        does not have. In the divisor ``COUNT(DISTINCT ...)`` skips NULLs on
        its own, but the statement says so explicitly, because the share is of
        the values that could join and that is the fact being measured.
        ``NULLIF(..., 0)`` then makes a column with no value at all answer
        NULL rather than 0, which the parser reads as "no fraction": the
        difference between "nothing matched" and "nothing to match" survives
        to the caller.

        There is no ``* 1.0`` here, unlike PostgreSQL's version of this
        method: MySQL's ``/`` over two integer counts already answers a
        fractional DECIMAL, so multiplying first would add noise and change
        nothing. The division is kept as a plain node division because that is
        the spelling both engines agree on and the one this backend validated
        against the live servers.
        """
        from rhosocial.activerecord.backend.expression import (
            FunctionCall,
            InPredicate,
            Literal,
            LogicalPredicate,
            QueryStatement,
            RowCountWildcard,
            SelectModifier,
            Subquery,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.functions import (
            CountFunction,
        )
        from rhosocial.activerecord.backend.expression.sources import (
            DerivedTableSource,
        )

        overlap = QueryStatement(
            self,
            select=[column],
            from_=source,
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    column.is_not_null(),
                    InPredicate(
                        self,
                        column,
                        Subquery(
                            self,
                            QueryStatement(
                                self,
                                select=[other_column],
                                from_=other_source,
                                where=WhereClause(self, other_column.is_not_null()),
                            ),
                        ),
                    ),
                ),
            ),
            select_modifier=SelectModifier.DISTINCT,
        )
        covered = Subquery(
            self,
            QueryStatement(
                self,
                select=[CountFunction(self, RowCountWildcard(self))],
                from_=DerivedTableSource(self, overlap, alias="covered"),
            ),
        )
        total = Subquery(
            self,
            QueryStatement(
                self,
                select=[
                    FunctionCall(
                        self,
                        "NULLIF",
                        CountFunction(self, column, distinct=True),
                        Literal(self, 0, inline=True),
                    )
                ],
                from_=source,
                where=WhereClause(self, column.is_not_null()),
            ),
        )
        return covered / total

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a two-sided measurement of two columns' value domains.

        Unlike every other statement in this module, this one names two user
        tables rather than one catalogue relation: the question is a relation
        between two objects, so both sides are carried explicitly and their
        identifiers are the dialect's to quote (see :meth:`_user_relation`).
        The aliases ``l`` and ``r`` are what keep the two columns apart in the
        rendered statement, and they are quoted like every other identifier.

        The row carries both fractions because neither is meaningful alone. A
        left share of 1.0 beside a right share of 0.2 says every tested value
        exists on the other side while most of that other domain is
        unaccounted for; a single similarity score would average the two and
        describe neither. A caller deciding whether a join is worth writing
        needs to know which direction is incomplete.

        Both figures are counted over *distinct* values, with NULLs excluded
        from the numerators and the denominators alike -- a NULL is not a value
        that could ever join, so it belongs in neither half of the fraction.
        The denominators are ``NULLIF``-guarded so a column with nothing to
        match answers NULL, which the parser reports as "no measurement"
        instead of a zero overlap that would read as a real answer. See
        :meth:`_coverage_fraction` for both rules in place.

        The cost is the two sides read for their distinct domains plus an
        intersection of the two -- a double scan, and the reason the probe
        belongs behind an explicit call rather than in any automatic pass.

        Collations are not reconciled. MySQL compares the two columns under
        whichever collation applies, so values the database would treat as
        equal may be counted as distinct here, and the fractions are a *lower*
        bound across mismatched collations -- never an upper one.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            QueryStatement,
        )

        params = expr.get_params()
        schema = params.get("schema")

        left_source = self._user_relation(params.get("left_table"), "l", schema)
        right_source = self._user_relation(params.get("right_table"), "r", schema)
        left_column = Column(self, params.get("left_column"), table="l")
        right_column = Column(self, params.get("right_column"), table="r")

        return QueryStatement(
            self,
            select=[
                self._coverage_fraction(left_column, left_source, right_column, right_source).as_(
                    "left_coverage"
                ),
                self._coverage_fraction(right_column, right_source, left_column, left_source).as_(
                    "right_coverage"
                ),
            ],
        ).to_sql()
