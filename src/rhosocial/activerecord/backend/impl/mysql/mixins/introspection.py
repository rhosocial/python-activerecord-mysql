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
    )


#: MySQL's own metadata databases. A caller asking for "user tables" does not
#: mean these four, so they are excluded unless system objects were requested.
SYSTEM_SCHEMAS = ("information_schema", "performance_schema", "mysql", "sys")


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
        """Build a SELECT over one ``information_schema`` relation.

        Each formatter below supplies only what varies -- the relation, the
        projection, the conjunction and the ordering -- and the shape lives
        here. The relation is a :class:`Table` carrying its database in the
        catalog slot, because MySQL's only namespace level is the database and
        putting ``information_schema`` in ``schema_name`` would be refused
        rather than silently dropped.

        Args:
            relation: The ``information_schema`` relation being read.
            projections: The select list, in order.
            conditions: Conditions to AND together.
            order_by: The ordering expressions, or ``None`` for no ORDER BY.
            source: A pre-built FROM source (a join, for the foreign-key
                query), or ``None`` to read *relation* directly.

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
            "where": WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
        }
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
                Column(self, "DATA_LENGTH"),
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
