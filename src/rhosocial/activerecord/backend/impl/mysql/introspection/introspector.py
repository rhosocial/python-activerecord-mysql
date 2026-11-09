# src/rhosocial/activerecord/backend/impl/mysql/introspection/introspector.py
"""
MySQL concrete introspectors.

Implements AbstractIntrospector and AsyncAbstractIntrospector for MySQL
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
- MySQLIntrospector: for synchronous backends
- AsyncMySQLIntrospector: for asynchronous backends
"""

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.introspection import (
        MySQLPartitionListQueryStatement,
        MySQLTableOptionsInfoQueryStatement,
        MySQLTableOptionsListQueryStatement,
        MySQLRoutineListQueryStatement,
        MySQLRoutineInfoQueryStatement,
        MySQLConstraintListQueryStatement,
    )

from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    AbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.cache import IntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import (
    IntrospectorExecutor,
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
    DDLStatement,
)
from rhosocial.activerecord.backend.expression.types import DataType
from .types import (
    MySQLPartitionInfo,
    MySQLTableOptions,
    MySQLRoutineInfo,
    MySQLRoutineParameter,
    MySQLConstraintInfo,
)
from .show_introspector import (
    ShowIntrospector,
    AsyncShowIntrospector,
)
from .status_introspector import (
    MySQLStatusIntrospector,
    AsyncMySQLStatusIntrospector,
)


class MySQLIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared MySQL-specific introspection logic.

    Both MySQLIntrospector and AsyncMySQLIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - The version a database record reports (``server_version``)
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

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def parse_database_info(self, rows: List[Dict[str, Any]]) -> IntrospectionDatabaseInfo:
        """Turn the schema row into a database record.

        The version comes from :attr:`server_version`, not from the strict
        ``dialect.version`` or a backend private: a parser has no connection
        to ask, and refusing to describe a database until
        ``introspect_and_adapt()`` has run would make the answer depend on a
        step the caller did not need. An unresolved version is reported as
        the literal ``"unknown"`` with ``(0, 0, 0)`` -- distinguishable from
        a server that really is 0.0.0 -- rather than a fabricated ``8.0.0``.

        ``encoding`` and ``collation`` are the two columns the statement
        selects. ``table_count`` and ``size_bytes`` are not among them: they
        live in ``information_schema.TABLES``, so they stay ``None`` rather
        than being guessed here.
        """
        version = self.server_version
        db_row = rows[0] if rows else {}

        return IntrospectionDatabaseInfo(
            name=self.default_schema,
            version=".".join(str(part) for part in version) if version else "unknown",
            version_tuple=tuple(version) if version else (0, 0, 0),
            vendor="MySQL",
            encoding=db_row.get("DEFAULT_CHARACTER_SET_NAME"),
            collation=db_row.get("DEFAULT_COLLATION_NAME"),
        )

    def parse_tables(self, rows: List[Dict[str, Any]], schema: Optional[str]) -> List[IntrospectionTableInfo]:
        """Turn the catalogue rows into table records, storage split included.

        The three storage slots answer different questions and are all filled
        from the server's own accounting: ``data_size_bytes`` is what the rows
        occupy, ``index_size_bytes`` what the indexes occupy, and
        ``size_bytes`` their sum -- ``None`` when the server reports neither,
        which is an answer rather than a fabricated 0. ``MySQLTableOptions``
        carries the same two numbers beside the engine and row format, with
        the caveat about InnoDB estimates.
        """
        target_db = schema if schema is not None else self.default_schema
        table_type_map = {
            "BASE TABLE": TableType.BASE_TABLE,
            "VIEW": TableType.VIEW,
            "SYSTEM VIEW": TableType.SYSTEM_TABLE,
        }
        tables = []
        for row in rows:
            t_type = table_type_map.get(row.get("TABLE_TYPE", "BASE TABLE"), TableType.BASE_TABLE)
            data_length = row.get("DATA_LENGTH")
            index_length = row.get("INDEX_LENGTH")
            if data_length is None and index_length is None:
                total_length = None
            else:
                total_length = (data_length or 0) + (index_length or 0)
            tables.append(
                IntrospectionTableInfo(
                    name=row["TABLE_NAME"],
                    schema=target_db,
                    table_type=t_type,
                    comment=row.get("TABLE_COMMENT"),
                    row_count=row.get("TABLE_ROWS"),
                    size_bytes=total_length,
                    data_size_bytes=data_length,
                    index_size_bytes=index_length,
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

    def parse_ddl_statements(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[DDLStatement]:
        """Project ``SHOW CREATE TABLE`` rows into the engine's own DDL.

        ``SHOW CREATE`` names its result columns after the object --
        ``Table`` and ``Create Table`` -- rather than after the concept, so
        the common spellings a catalogue-reading parser looks for (``ddl``,
        ``sql``, ``definition``) are simply not in the row and the table the
        engine had just described would be reported as having no DDL. The text
        is the engine's own retrieval, never an assembly, which is what
        ``native`` says. Only the TABLE flavour is read because only it is
        formatted; see the dialect's ``format_ddl_statement_query_statement``.
        """
        found: List[DDLStatement] = []
        for row in rows or []:
            ddl = row.get("Create Table")
            if not ddl:
                continue
            found.append(
                DDLStatement(
                    schema=schema,
                    object_type="TABLE",
                    object_name=str(row.get("Table") or ""),
                    ddl=str(ddl),
                    native=True,
                )
            )
        return found

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

    def routine_list_statement(
        self, *, schema: Optional[str]
    ) -> "MySQLRoutineListQueryStatement":
        """Return the statement that lists every routine in a database."""
        from ..expression.introspection import MySQLRoutineListQueryStatement

        target_db = schema if schema is not None else self.default_schema
        return MySQLRoutineListQueryStatement(self.dialect, schema=target_db)

    def routine_info_statement(
        self,
        *,
        routine_name: str,
        schema: Optional[str],
        kind: Optional[str] = None,
    ) -> "MySQLRoutineInfoQueryStatement":
        """Return the statement that reads one routine, optionally by kind."""
        from ..expression.introspection import MySQLRoutineInfoQueryStatement

        target_db = schema if schema is not None else self.default_schema
        return MySQLRoutineInfoQueryStatement(
            self.dialect, routine_name=routine_name, kind=kind, schema=target_db
        )

    def constraint_list_statement(
        self, *, table_name: Optional[str], schema: Optional[str]
    ) -> "MySQLConstraintListQueryStatement":
        """Return the statement that lists constraints, for one table or all."""
        from ..expression.introspection import MySQLConstraintListQueryStatement

        target_db = schema if schema is not None else self.default_schema
        return MySQLConstraintListQueryStatement(
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

    # ------------------------------------------------------------------ #
    # Routines and constraints — parsing
    # ------------------------------------------------------------------ #

    def parse_routines(self, rows: List[Dict[str, Any]]) -> List[MySQLRoutineInfo]:
        """Group the routine/parameter join into one record per routine.

        The join returns one row per argument, plus an argument-less row for a
        routine that takes none; the key is ``(schema, name, kind)`` because
        MySQL keeps procedures and functions in separate namespaces. Ordinal
        zero is a function's return value, not an argument, so it fills
        ``return_type`` and is left out of ``parameters``.
        """
        grouped: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            key = (
                row.get("ROUTINE_SCHEMA", ""),
                row.get("ROUTINE_NAME", ""),
                row.get("ROUTINE_TYPE", ""),
            )
            entry = grouped.get(key)
            if entry is None:
                entry = {"row": row, "parameters": []}
                grouped[key] = entry

            ordinal = row.get("PARAM_ORDINAL_POSITION")
            if ordinal is None:
                continue
            ordinal = int(ordinal)
            if ordinal == 0:
                # The function's return value; the routine row's own DTD is
                # the same fact, so this is only a fallback when the parameter
                # relation did not report it.
                if not entry.get("return_type"):
                    entry["return_type"] = (
                        row.get("PARAM_DTD_IDENTIFIER")
                        or row.get("PARAM_DATA_TYPE")
                        or None
                    )
                continue
            entry["parameters"].append(
                MySQLRoutineParameter(
                    ordinal_position=ordinal,
                    mode=row.get("PARAMETER_MODE"),
                    name=row.get("PARAMETER_NAME"),
                    data_type=row.get("PARAM_DATA_TYPE"),
                    data_type_full=row.get("PARAM_DTD_IDENTIFIER")
                    or row.get("PARAM_DATA_TYPE"),
                )
            )

        routines: List[MySQLRoutineInfo] = []
        for entry in grouped.values():
            row = entry["row"]
            kind = (row.get("ROUTINE_TYPE") or "").upper()
            return_type = entry.get("return_type")
            if kind == "FUNCTION":
                return_type = return_type or row.get("DTD_IDENTIFIER") or row.get("DATA_TYPE")
            else:
                return_type = None
            deterministic_raw = row.get("IS_DETERMINISTIC")
            deterministic = (
                None
                if deterministic_raw is None
                else str(deterministic_raw).upper() == "YES"
            )
            language = row.get("EXTERNAL_LANGUAGE") or row.get("ROUTINE_BODY") or None
            routines.append(
                MySQLRoutineInfo(
                    schema=row.get("ROUTINE_SCHEMA", ""),
                    name=row.get("ROUTINE_NAME", ""),
                    kind=kind,
                    parameters=tuple(
                        sorted(entry["parameters"], key=lambda p: p.ordinal_position)
                    ),
                    return_type=return_type or None,
                    language=language,
                    is_deterministic=deterministic,
                    sql_data_access=row.get("SQL_DATA_ACCESS"),
                    security_type=row.get("SECURITY_TYPE"),
                    comment=row.get("ROUTINE_COMMENT"),
                    definer=row.get("DEFINER"),
                    created=str(row["CREATED"]) if row.get("CREATED") else None,
                    last_altered=(
                        str(row["LAST_ALTERED"]) if row.get("LAST_ALTERED") else None
                    ),
                    sql_mode=row.get("SQL_MODE"),
                )
            )
        return routines

    def parse_constraints(self, rows: List[Dict[str, Any]]) -> List[MySQLConstraintInfo]:
        """Group the constraint join into one record per constraint.

        The key includes the constraint type because MySQL keeps the kinds in
        separate namespaces: a ``UNIQUE`` index and a ``CHECK`` constraint can
        share a name. The CHECK expression is only read for a ``CHECK`` row --
        a name collision would otherwise attach another table's clause to a
        unique key. ``columns`` is ordered by the catalogue's ordinal so the
        declaration order survives into the result.
        """
        grouped: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            constraint_type = (row.get("CONSTRAINT_TYPE") or "").upper()
            key = (
                row.get("CONSTRAINT_SCHEMA", ""),
                row.get("TABLE_NAME", ""),
                row.get("CONSTRAINT_NAME", ""),
                constraint_type,
            )
            entry = grouped.get(key)
            if entry is None:
                enforced_raw = row.get("ENFORCED")
                entry = {
                    "row": row,
                    "columns": [],
                    "expression": (
                        row.get("CHECK_CLAUSE") if constraint_type == "CHECK" else None
                    ),
                    "enforced": (
                        None
                        if enforced_raw is None
                        else str(enforced_raw).upper() == "YES"
                    ),
                }
                grouped[key] = entry

            column_name = row.get("COLUMN_NAME")
            if column_name:
                ordinal = row.get("ORDINAL_POSITION")
                entry["columns"].append(
                    (int(ordinal) if ordinal is not None else len(entry["columns"]), column_name)
                )

        constraints: List[MySQLConstraintInfo] = []
        for entry in grouped.values():
            row = entry["row"]
            columns = tuple(
                name for _ordinal, name in sorted(entry["columns"], key=lambda pair: pair[0])
            )
            constraints.append(
                MySQLConstraintInfo(
                    schema=row.get("CONSTRAINT_SCHEMA", ""),
                    table_name=row.get("TABLE_NAME", ""),
                    name=row.get("CONSTRAINT_NAME", ""),
                    constraint_type=(row.get("CONSTRAINT_TYPE") or "").upper(),
                    columns=columns,
                    expression=entry["expression"],
                    enforced=entry["enforced"],
                )
            )
        return constraints


class MySQLIntrospector(MySQLIntrospectorMixin, AbstractIntrospector):
    """Synchronous introspector for MySQL backends.

    In addition to the standard AbstractIntrospector interface, exposes the
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
        executor: IntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._show_instance: Optional[ShowIntrospector] = None
        self._status_instance: Optional[MySQLStatusIntrospector] = None

    @property
    def show(self) -> ShowIntrospector:
        """MySQL-specific SHOW sub-introspector (lazily created)."""
        if self._show_instance is None:
            self._show_instance = ShowIntrospector(self._backend, self._executor)
        return self._show_instance

    @property
    def status(self) -> MySQLStatusIntrospector:
        """MySQL status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = MySQLStatusIntrospector(self._backend)
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

    # ------------------------------------------------------------------ #
    # MySQL-specific: routines and constraints
    # ------------------------------------------------------------------ #

    def list_routines(self, schema: Optional[str] = None) -> List[MySQLRoutineInfo]:
        """List every procedure and function in *schema*.

        Each record carries its arguments and, for a function, its return
        type. A procedure and a function may share a name; both are listed and
        told apart by ``kind``.
        """
        key = self._cache.key(
            IntrospectionScope.DATABASE, schema=schema, extra="routines"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_list_statement(schema=schema).to_sql()
        result = self.parse_routines(self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    def get_routine_info(
        self,
        routine_name: str,
        schema: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Optional[MySQLRoutineInfo]:
        """Return one routine by name, or ``None`` when no such routine exists.

        ``kind`` narrows a name that exists as both a procedure and a function;
        without it the first matching kind in the engine's ordering is
        returned, which is why the parameter exists on the question.
        """
        key = self._cache.key(
            IntrospectionScope.DATABASE,
            routine_name,
            schema=schema,
            extra=f"routine:{kind or '*'}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_info_statement(
            routine_name=routine_name, schema=schema, kind=kind
        ).to_sql()
        result = next(iter(self.parse_routines(self._executor.execute(sql, params))), None)
        if result is not None:
            self._cache.set(key, result)
        return result

    def list_constraints(
        self, table_name: Optional[str] = None, schema: Optional[str] = None
    ) -> List[MySQLConstraintInfo]:
        """List table constraints, for one table or for the whole database.

        The family follows the server's capability: CHECK constraints exist
        from MySQL 8.0.16, and below that floor the CLI refuses the family
        before this method runs.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name or "*",
            schema=schema,
            extra="constraints",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.constraint_list_statement(
            table_name=table_name, schema=schema
        ).to_sql()
        result = self.parse_constraints(self._executor.execute(sql, params))
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

    # ------------------------------------------------------------------ #
    # MySQL-specific: routines and constraints
    # ------------------------------------------------------------------ #

    async def list_routines(self, schema: Optional[str] = None) -> List[MySQLRoutineInfo]:
        """List every procedure and function in *schema* asynchronously.

        Each record carries its arguments and, for a function, its return
        type. A procedure and a function may share a name; both are listed and
        told apart by ``kind``.
        """
        key = self._cache.key(
            IntrospectionScope.DATABASE, schema=schema, extra="routines"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_list_statement(schema=schema).to_sql()
        result = self.parse_routines(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    async def get_routine_info(
        self,
        routine_name: str,
        schema: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Optional[MySQLRoutineInfo]:
        """Return one routine by name asynchronously, or ``None``.

        ``kind`` narrows a name that exists as both a procedure and a function;
        without it the first matching kind in the engine's ordering is
        returned, which is why the parameter exists on the question.
        """
        key = self._cache.key(
            IntrospectionScope.DATABASE,
            routine_name,
            schema=schema,
            extra=f"routine:{kind or '*'}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.routine_info_statement(
            routine_name=routine_name, schema=schema, kind=kind
        ).to_sql()
        rows = await self._executor.execute(sql, params)
        result = next(iter(self.parse_routines(rows)), None)
        if result is not None:
            self._cache.set(key, result)
        return result

    async def list_constraints(
        self, table_name: Optional[str] = None, schema: Optional[str] = None
    ) -> List[MySQLConstraintInfo]:
        """List table constraints asynchronously, for one table or all.

        The family follows the server's capability: CHECK constraints exist
        from MySQL 8.0.16, and below that floor the CLI refuses the family
        before this method runs.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE,
            table_name or "*",
            schema=schema,
            extra="constraints",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.constraint_list_statement(
            table_name=table_name, schema=schema
        ).to_sql()
        result = self.parse_constraints(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result
