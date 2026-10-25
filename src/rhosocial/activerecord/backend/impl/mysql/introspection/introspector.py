# src/rhosocial/activerecord/backend/impl/mysql/introspection/introspector.py
"""
MySQL concrete introspectors.

Implements SyncAbstractIntrospector and AsyncAbstractIntrospector for MySQL
databases using the information_schema system tables for metadata queries.

The introspectors are exposed via ``backend.introspector`` and also provide
MySQL-specific access through ``backend.introspector.show``.

Architecture:
  - SQL generation: Delegated to MySQLIntrospectionMixin.format_*_query()
    methods in the Dialect layer via Expression.to_sql()
  - Query execution: Handled by IntrospectorExecutor
  - Result parsing: parse_* methods in this module (pure Python, no I/O)

Key behaviours:
  - Queries information_schema.TABLES, COLUMNS, STATISTICS,
    KEY_COLUMN_USAGE, REFERENTIAL_CONSTRAINTS, VIEWS, TRIGGERS
  - MySQL-only families: ``list_table_options`` / ``get_table_options``
    (storage options from TABLES) and ``list_partitions`` (from PARTITIONS)
  - parse_* methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- SyncMySQLIntrospector: for synchronous backends
- AsyncMySQLIntrospector: for asynchronous backends
"""

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.introspection import (
        MySQLPartitionListQueryStatement,
        MySQLTableOptionsInfoQueryStatement,
        MySQLTableOptionsListQueryStatement,
    )

from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    SyncAbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.cache import IntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    IntrospectionDatabaseInfo,
    IntrospectionTableInfo,
    TableType,
    IntrospectionColumnInfo,
    ColumnNullable,
    IndexInfo,
    IndexColumnInfo,
    IndexType,
    IntrospectionForeignKeyInfo,
    ReferentialAction,
    IntrospectionViewInfo,
    IntrospectionTriggerInfo,
    IntrospectionScope,
)
from rhosocial.activerecord.backend.expression.types import DataType
from .types import MySQLPartitionInfo, MySQLTableOptions
from .show_introspector import (
    SyncShowIntrospector,
    AsyncShowIntrospector,
)
from .status_introspector import (
    SyncMySQLStatusIntrospector,
    AsyncMySQLStatusIntrospector,
)


class MySQLIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared MySQL-specific introspection logic.

    Both SyncMySQLIntrospector and AsyncMySQLIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - MySQL version detection
    - parse_* implementations

    SQL generation is delegated to the Dialect layer via Expression.to_sql()
    which calls MySQLIntrospectionMixin.format_*_query() methods.
    """

    @property
    def default_schema(self) -> str:
        """Return the MySQL database name from the backend config."""
        if hasattr(self._backend, "config") and hasattr(self._backend.config, "database"):
            return self._backend.config.database or ""
        return ""

    def _get_version(self) -> tuple:
        """Return the MySQL server version tuple from the backend."""
        return getattr(self._backend, "_version", (8, 0, 0))

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def parse_database_info(self, rows: List[Dict[str, Any]]) -> IntrospectionDatabaseInfo:
        version = self._get_version()
        version_str = ".".join(str(v) for v in version)
        db_name = self.default_schema

        db_row = rows[0] if rows else {}

        return IntrospectionDatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version,
            vendor="MySQL",
            encoding=db_row.get("DEFAULT_CHARACTER_SET_NAME"),
            collation=db_row.get("DEFAULT_COLLATION_NAME"),
        )

    def parse_tables(self, rows: List[Dict[str, Any]], schema: Optional[str]) -> List[IntrospectionTableInfo]:
        target_db = schema if schema is not None else self.default_schema
        table_type_map = {
            "BASE TABLE": TableType.BASE_TABLE,
            "VIEW": TableType.VIEW,
            "SYSTEM VIEW": TableType.SYSTEM_TABLE,
        }
        tables = []
        for row in rows:
            t_type = table_type_map.get(row.get("TABLE_TYPE", "BASE TABLE"), TableType.BASE_TABLE)
            tables.append(
                IntrospectionTableInfo(
                    name=row["TABLE_NAME"],
                    schema=target_db,
                    table_type=t_type,
                    comment=row.get("TABLE_COMMENT"),
                    row_count=row.get("TABLE_ROWS"),
                    size_bytes=row.get("DATA_LENGTH"),
                    auto_increment=row.get("AUTO_INCREMENT"),
                    create_time=str(row["CREATE_TIME"]) if row.get("CREATE_TIME") else None,
                    update_time=str(row["UPDATE_TIME"]) if row.get("UPDATE_TIME") else None,
                )
            )
        return tables

    def parse_columns(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IntrospectionColumnInfo]:
        columns = []
        for row in rows:
            nullable = ColumnNullable.NULLABLE if row.get("IS_NULLABLE") == "YES" else ColumnNullable.NOT_NULL
            col_type = row.get("COLUMN_TYPE") or row.get("DATA_TYPE") or "VARCHAR"
            parsed = DataType.parse_data_type_str(self._backend.dialect, col_type)
            columns.append(
                IntrospectionColumnInfo(
                    name=row["COLUMN_NAME"],
                    table_name=table_name,
                    schema=schema,
                    ordinal_position=row["ORDINAL_POSITION"],
                    data_type=col_type.split("(")[0].lower(),
                    data_type_full=col_type,
                    parsed_data_type=parsed,
                    nullable=nullable,
                    default_value=row.get("COLUMN_DEFAULT"),
                    is_primary_key=row.get("COLUMN_KEY") == "PRI",
                    is_unique=row.get("COLUMN_KEY") == "UNI",
                    is_auto_increment="auto_increment" in (row.get("EXTRA") or "").lower(),
                    comment=row.get("COLUMN_COMMENT"),
                    character_maximum_length=row.get("CHARACTER_MAXIMUM_LENGTH"),
                    numeric_precision=row.get("NUMERIC_PRECISION"),
                    numeric_scale=row.get("NUMERIC_SCALE"),
                    charset=row.get("CHARACTER_SET_NAME"),
                    collation=row.get("COLLATION_NAME"),
                )
            )
        return columns

    def parse_indexes(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IndexInfo]:
        index_type_map = {
            "BTREE": IndexType.BTREE,
            "HASH": IndexType.HASH,
            "FULLTEXT": IndexType.FULLTEXT,
            "SPATIAL": IndexType.SPATIAL,
            "RTREE": IndexType.SPATIAL,
        }
        index_map: Dict[str, IndexInfo] = {}
        for row in rows:
            idx_name = row.get("INDEX_NAME") or row.get("Key_name", "")
            if idx_name not in index_map:
                idx_type_str = (row.get("INDEX_TYPE") or "BTREE").upper()
                index_map[idx_name] = IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=schema,
                    is_unique=int(row.get("NON_UNIQUE", row.get("Non_unique", 1))) == 0,
                    is_primary=idx_name == "PRIMARY",
                    index_type=index_type_map.get(idx_type_str, IndexType.BTREE),
                    columns=[],
                )
            index_map[idx_name].columns.append(
                IndexColumnInfo(
                    name=row.get("COLUMN_NAME") or row.get("Column_name", ""),
                    ordinal_position=int(row.get("SEQ_IN_INDEX") or row.get("Seq_in_index", 1)),
                    is_descending=False,
                )
            )
        return list(index_map.values())

    def parse_foreign_keys(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IntrospectionForeignKeyInfo]:
        action_map = {
            "NO_ACTION": ReferentialAction.NO_ACTION,
            "NO ACTION": ReferentialAction.NO_ACTION,
            "RESTRICT": ReferentialAction.RESTRICT,
            "CASCADE": ReferentialAction.CASCADE,
            "SET_NULL": ReferentialAction.SET_NULL,
            "SET NULL": ReferentialAction.SET_NULL,
            "SET_DEFAULT": ReferentialAction.SET_DEFAULT,
            "SET DEFAULT": ReferentialAction.SET_DEFAULT,
        }
        fk_map: Dict[str, IntrospectionForeignKeyInfo] = {}
        for row in rows:
            fk_name = row.get("CONSTRAINT_NAME", "")
            if fk_name not in fk_map:
                on_update_raw = (row.get("UPDATE_RULE") or "NO ACTION").upper()
                on_delete_raw = (row.get("DELETE_RULE") or "NO ACTION").upper()
                fk_map[fk_name] = IntrospectionForeignKeyInfo(
                    name=fk_name,
                    table_name=table_name,
                    schema=schema,
                    referenced_table=row.get("REFERENCED_TABLE_NAME", ""),
                    on_update=action_map.get(on_update_raw, ReferentialAction.NO_ACTION),
                    on_delete=action_map.get(on_delete_raw, ReferentialAction.NO_ACTION),
                    columns=[],
                    referenced_columns=[],
                )
            fk_map[fk_name].columns.append(row.get("COLUMN_NAME", ""))
            fk_map[fk_name].referenced_columns.append(row.get("REFERENCED_COLUMN_NAME", ""))
        return list(fk_map.values())

    def parse_views(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionViewInfo]:
        return [
            IntrospectionViewInfo(
                name=row.get("TABLE_NAME", row.get("VIEW_NAME", "")),
                schema=schema,
                definition=row.get("VIEW_DEFINITION"),
                check_option=row.get("CHECK_OPTION"),
                is_updatable=row.get("IS_UPDATABLE") == "YES",
            )
            for row in rows
        ]

    def parse_view_info(
        self,
        rows: List[Dict[str, Any]],
        view_name: str,
        schema: str,
    ) -> Optional[IntrospectionViewInfo]:
        if not rows:
            return None
        row = rows[0]
        return IntrospectionViewInfo(
            name=row.get("TABLE_NAME", row.get("VIEW_NAME", view_name)),
            schema=schema,
            definition=row.get("VIEW_DEFINITION"),
            check_option=row.get("CHECK_OPTION"),
            is_updatable=row.get("IS_UPDATABLE") == "YES",
        )

    def parse_triggers(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionTriggerInfo]:
        return [
            IntrospectionTriggerInfo(
                name=row.get("TRIGGER_NAME", ""),
                table_name=row.get("EVENT_OBJECT_TABLE", ""),
                schema=schema,
                timing=row.get("ACTION_TIMING"),
                events=[row["EVENT_MANIPULATION"]] if row.get("EVENT_MANIPULATION") else [],
                definition=row.get("ACTION_STATEMENT"),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # Table storage options and partitions — statement factories
    #
    # Neither family has a scope of its own in IntrospectionScope, and
    # neither is the same question as "what tables are there". Both are
    # therefore asked in IntrospectionScope.TABLE and kept apart from the
    # table list (and from each other) by a distinct ``extra`` namespace,
    # which is exactly what ``extra`` exists for.
    #
    # Each factory returns a statement object and renders nothing: the
    # dialect's ``format_*_query_statement`` decides the SQL, so nothing
    # here spells it and no helper is private.
    # ------------------------------------------------------------------ #

    def table_options_list_statement(
        self, *, schema: Optional[str]
    ) -> "MySQLTableOptionsListQueryStatement":
        """Return the statement that lists every base table's storage options.

        ``DATA_LENGTH`` and ``INDEX_LENGTH`` are reported in bytes; see
        :class:`MySQLTableOptions` for the caveat about InnoDB estimates.
        """
        from ..expression.introspection import MySQLTableOptionsListQueryStatement

        target_db = schema if schema is not None else self.default_schema
        return MySQLTableOptionsListQueryStatement(self.dialect, schema=target_db)

    def table_options_info_statement(
        self, *, table_name: str, schema: Optional[str]
    ) -> "MySQLTableOptionsInfoQueryStatement":
        """Return the statement that reads one base table's storage options."""
        from ..expression.introspection import MySQLTableOptionsInfoQueryStatement

        target_db = schema if schema is not None else self.default_schema
        return MySQLTableOptionsInfoQueryStatement(
            self.dialect, table_name=table_name, schema=target_db
        )

    def partition_list_statement(
        self, *, table_name: str, schema: Optional[str]
    ) -> "MySQLPartitionListQueryStatement":
        """Return the statement that lists one table's partitions.

        Rows without a ``PARTITION_NAME`` describe a non-partitioned table
        and are not partitions, so the predicate excludes them rather than
        filtering after the fact: an empty result then means exactly "this
        table is not partitioned".
        """
        from ..expression.introspection import MySQLPartitionListQueryStatement

        target_db = schema if schema is not None else self.default_schema
        return MySQLPartitionListQueryStatement(
            self.dialect, table_name=table_name, schema=target_db
        )

    # ------------------------------------------------------------------ #
    # Table storage options and partitions — parsing
    # ------------------------------------------------------------------ #

    def parse_table_options(self, rows: List[Dict[str, Any]]) -> List[MySQLTableOptions]:
        return [
            MySQLTableOptions(
                schema=row.get("TABLE_SCHEMA", ""),
                table_name=row["TABLE_NAME"],
                engine=row.get("ENGINE"),
                row_format=row.get("ROW_FORMAT"),
                table_collation=row.get("TABLE_COLLATION"),
                auto_increment=row.get("AUTO_INCREMENT"),
                table_comment=row.get("TABLE_COMMENT"),
                create_options=row.get("CREATE_OPTIONS"),
                data_length=row.get("DATA_LENGTH"),
                index_length=row.get("INDEX_LENGTH"),
            )
            for row in rows
        ]

    def parse_partitions(self, rows: List[Dict[str, Any]]) -> List[MySQLPartitionInfo]:
        return [
            MySQLPartitionInfo(
                schema=row.get("TABLE_SCHEMA", ""),
                table_name=row.get("TABLE_NAME", ""),
                partition_name=row.get("PARTITION_NAME"),
                partition_method=row.get("PARTITION_METHOD"),
                partition_expression=row.get("PARTITION_EXPRESSION"),
                partition_description=row.get("PARTITION_DESCRIPTION"),
                partition_ordinal_position=row.get("PARTITION_ORDINAL_POSITION"),
                subpartition_name=row.get("SUBPARTITION_NAME"),
                subpartition_ordinal_position=row.get("SUBPARTITION_ORDINAL_POSITION"),
                table_rows=row.get("TABLE_ROWS"),
                data_length=row.get("DATA_LENGTH"),
                index_length=row.get("INDEX_LENGTH"),
            )
            for row in rows
        ]


class SyncMySQLIntrospector(MySQLIntrospectorMixin, SyncAbstractIntrospector):
    """Synchronous introspector for MySQL backends.

    In addition to the standard SyncAbstractIntrospector interface, exposes the
    ``.show`` sub-introspector for direct SHOW command access::

        # Standard API
        tables = backend.introspector.list_tables()

        # MySQL-specific
        create_sql = backend.introspector.show.create_table("users")
        variables  = backend.introspector.show.variables(like="max_%")
    """

    def __init__(
        self,
        backend: Any,
        executor: SyncIntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._show_instance: Optional[SyncShowIntrospector] = None
        self._status_instance: Optional[SyncMySQLStatusIntrospector] = None

    @property
    def show(self) -> SyncShowIntrospector:
        """MySQL-specific SHOW sub-introspector (lazily created)."""
        if self._show_instance is None:
            self._show_instance = SyncShowIntrospector(self._backend, self._executor)
        return self._show_instance

    @property
    def status(self) -> SyncMySQLStatusIntrospector:
        """MySQL status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = SyncMySQLStatusIntrospector(self._backend)
        return self._status_instance

    # ------------------------------------------------------------------ #
    # get_table_info override
    # ------------------------------------------------------------------ #

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        key = self._cache.key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        tables = self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        table = copy.copy(table)
        table.columns = self.list_columns(table_name, schema)
        table.indexes = self.list_indexes(table_name, schema)
        table.foreign_keys = self.list_foreign_keys(table_name, schema)
        self._cache.set(key, table)
        return table

    # ------------------------------------------------------------------ #
    # MySQL-specific: table storage options and partitions
    # ------------------------------------------------------------------ #

    def list_table_options(self, schema: Optional[str] = None) -> List[MySQLTableOptions]:
        """List storage options for every base table in *schema*.

        Answers from ``information_schema.TABLES``: engine, row format,
        collation, auto-increment counter, comment, extra create options
        and the server's data/index byte accounting.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, schema=schema, extra="table_options"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.table_options_list_statement(schema=schema).to_sql()
        result = self.parse_table_options(self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    def get_table_options(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[MySQLTableOptions]:
        """Return storage options for one base table, or ``None``.

        ``None`` covers both "no such table" and "that name is a view":
        a view has no storage engine, and reporting a half-empty record
        as if it were a table would be worse than saying nothing.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema, extra="table_options"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.table_options_info_statement(table_name=table_name, schema=schema).to_sql()
        result = next(iter(self.parse_table_options(self._executor.execute(sql, params))), None)
        if result is not None:
            self._cache.set(key, result)
        return result

    def list_partitions(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[MySQLPartitionInfo]:
        """List the partitions of one table, from ``information_schema.PARTITIONS``.

        Returns an empty list for a table that is not partitioned.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema, extra="partitions"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.partition_list_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_partitions(self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result


class AsyncMySQLIntrospector(MySQLIntrospectorMixin, AsyncAbstractIntrospector):
    """Asynchronous introspector for MySQL backends.

    In addition to the standard AsyncAbstractIntrospector interface, exposes the
    ``.show`` sub-introspector for direct SHOW command access::

        # Standard API
        tables = await backend.introspector.list_tables()

        # MySQL-specific
        create_sql = await backend.introspector.show.create_table("users")
        variables  = await backend.introspector.show.variables(like="max_%")
    """

    def __init__(
        self,
        backend: Any,
        executor: AsyncIntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._show_instance: Optional[AsyncShowIntrospector] = None
        self._status_instance: Optional[AsyncMySQLStatusIntrospector] = None

    @property
    def show(self) -> AsyncShowIntrospector:
        """MySQL-specific SHOW sub-introspector (lazily created)."""
        if self._show_instance is None:
            self._show_instance = AsyncShowIntrospector(self._backend, self._executor)
        return self._show_instance

    @property
    def status(self) -> AsyncMySQLStatusIntrospector:
        """MySQL status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = AsyncMySQLStatusIntrospector(self._backend)
        return self._status_instance

    # ------------------------------------------------------------------ #
    # get_table_info override
    # ------------------------------------------------------------------ #

    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        key = self._cache.key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        tables = await self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        table = copy.copy(table)
        table.columns = await self.list_columns(table_name, schema)
        table.indexes = await self.list_indexes(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys(table_name, schema)
        self._cache.set(key, table)
        return table

    # ------------------------------------------------------------------ #
    # MySQL-specific: table storage options and partitions
    # ------------------------------------------------------------------ #

    async def list_table_options(self, schema: Optional[str] = None) -> List[MySQLTableOptions]:
        """List storage options for every base table in *schema*.

        Answers from ``information_schema.TABLES``: engine, row format,
        collation, auto-increment counter, comment, extra create options
        and the server's data/index byte accounting.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, schema=schema, extra="table_options"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.table_options_list_statement(schema=schema).to_sql()
        result = self.parse_table_options(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    async def get_table_options(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[MySQLTableOptions]:
        """Return storage options for one base table, or ``None``.

        ``None`` covers both "no such table" and "that name is a view":
        a view has no storage engine, and reporting a half-empty record
        as if it were a table would be worse than saying nothing.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema, extra="table_options"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.table_options_info_statement(table_name=table_name, schema=schema).to_sql()
        rows = await self._executor.execute(sql, params)
        result = next(iter(self.parse_table_options(rows)), None)
        if result is not None:
            self._cache.set(key, result)
        return result

    async def list_partitions(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[MySQLPartitionInfo]:
        """List the partitions of one table, from ``information_schema.PARTITIONS``.

        Returns an empty list for a table that is not partitioned.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE, table_name, schema=schema, extra="partitions"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.partition_list_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_partitions(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result
