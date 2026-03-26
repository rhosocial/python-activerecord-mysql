# src/rhosocial/activerecord/backend/impl/mysql/async_introspection.py
"""
MySQL asynchronous database introspection implementation.

This module provides async MySQL-specific introspection using information_schema
system tables. It mirrors the sync introspection but uses async/await for I/O.
"""

from typing import Optional, List, Dict

from rhosocial.activerecord.backend.introspection.mixins import AsyncIntrospectionMixin
from rhosocial.activerecord.backend.introspection.types import (
    DatabaseInfo, TableInfo, ColumnInfo, IndexInfo,
    IndexColumnInfo, ForeignKeyInfo, ViewInfo, TriggerInfo, TableType,
    ColumnNullable, IndexType, ReferentialAction
)


class AsyncMySQLIntrospectionMixin(AsyncIntrospectionMixin):
    """
    MySQL async introspection implementation.

    Uses MySQL's information_schema for database introspection.
    Provides comprehensive metadata access including tables, columns,
    indexes, foreign keys, and views.
    """

    def _get_connection(self):
        """Get database connection (must be set by backend)."""
        if not hasattr(self, '_connection') or self._connection is None:
            raise RuntimeError("Database connection not initialized")
        return self._connection

    def _get_database_name(self) -> str:
        """Get database name from config."""
        if hasattr(self, 'config') and hasattr(self.config, 'database'):
            return self.config.database
        return 'unknown'

    async def _execute_introspection_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute introspection query asynchronously and return results as list of dicts."""
        conn = self._get_connection()
        cursor = await conn.cursor()
        try:
            await cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = []
            rows = await cursor.fetchall()
            for row in rows:
                results.append(dict(zip(columns, row)))
            return results
        finally:
            await cursor.close()

    # ========== Abstract Method Implementations ==========

    async def _query_database_info(self) -> DatabaseInfo:
        """Query MySQL database information asynchronously."""
        # Get version
        rows = await self._execute_introspection_query("SELECT VERSION()")
        version_str = rows[0]['VERSION()'] if rows else '5.7.0'
        version_parts = version_str.split('.')[0:3]
        version_tuple = (
            int(version_parts[0]),
            int(version_parts[1].split('-')[0]) if len(version_parts) > 1 else 0,
            int(version_parts[2].split('-')[0]) if len(version_parts) > 2 else 0
        )

        # Get database information
        db_name = self._get_database_name()
        rows = await self._execute_introspection_query("""
            SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME,
                   DEFAULT_COLLATION_NAME
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME = %s
        """, (db_name,))

        db_row = rows[0] if rows else {}

        return DatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version_tuple,
            vendor="MySQL",
            encoding=db_row.get('DEFAULT_CHARACTER_SET_NAME'),
            collation=db_row.get('DEFAULT_COLLATION_NAME'),
        )

    async def _query_tables(self, schema: Optional[str] = None,
                            include_system: bool = False,
                            table_type: Optional[str] = None) -> List[TableInfo]:
        """Query table list asynchronously."""
        db_name = schema or self._get_database_name()

        sql = """
            SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT,
                   TABLE_ROWS, DATA_LENGTH, AUTO_INCREMENT,
                   CREATE_TIME, UPDATE_TIME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
        """
        rows = await self._execute_introspection_query(sql, (db_name,))

        tables = []
        for row in rows:
            # Parse table type
            table_type_map = {
                'BASE TABLE': TableType.BASE_TABLE,
                'VIEW': TableType.VIEW,
                'SYSTEM VIEW': TableType.SYSTEM_TABLE,
            }
            parsed_type = table_type_map.get(row['TABLE_TYPE'], TableType.BASE_TABLE)

            # Skip system tables
            if not include_system and parsed_type == TableType.SYSTEM_TABLE:
                continue

            tables.append(TableInfo(
                name=row['TABLE_NAME'],
                table_type=parsed_type,
                comment=row.get('TABLE_COMMENT'),
                row_count=row.get('TABLE_ROWS'),
                size_bytes=row.get('DATA_LENGTH'),
                auto_increment=row.get('AUTO_INCREMENT'),
                create_time=str(row['CREATE_TIME']) if row.get('CREATE_TIME') else None,
                update_time=str(row['UPDATE_TIME']) if row.get('UPDATE_TIME') else None,
            ))

        return tables

    async def _query_table_info(self, table_name: str,
                                 schema: Optional[str]) -> Optional[TableInfo]:
        """Query table details asynchronously."""
        tables = await self._query_tables(schema, False)
        table = next((t for t in tables if t.name == table_name), None)
        if not table:
            return None

        table.columns = await self._query_columns(table_name, schema)
        table.indexes = await self._query_indexes(table_name, schema)
        table.foreign_keys = await self._query_foreign_keys(table_name, schema)

        return table

    async def _query_columns(self, table_name: str,
                              schema: Optional[str]) -> List[ColumnInfo]:
        """Query column information asynchronously."""
        db_name = schema or self._get_database_name()

        sql = """
            SELECT COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE,
                   IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY,
                   EXTRA, COLUMN_COMMENT, CHARACTER_MAXIMUM_LENGTH,
                   NUMERIC_PRECISION, NUMERIC_SCALE,
                   CHARACTER_SET_NAME, COLLATION_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        rows = await self._execute_introspection_query(sql, (db_name, table_name))

        columns = []
        for row in rows:
            nullable = (ColumnNullable.NULLABLE if row['IS_NULLABLE'] == 'YES'
                       else ColumnNullable.NOT_NULL)

            col = ColumnInfo(
                name=row['COLUMN_NAME'],
                table_name=table_name,
                ordinal_position=row['ORDINAL_POSITION'],
                data_type=row['COLUMN_TYPE'].split('(')[0],
                data_type_full=row['COLUMN_TYPE'],
                nullable=nullable,
                default_value=row.get('COLUMN_DEFAULT'),
                is_primary_key=row.get('COLUMN_KEY') == 'PRI',
                is_unique=row.get('COLUMN_KEY') == 'UNI',
                is_auto_increment='auto_increment' in (row.get('EXTRA') or '').lower(),
                comment=row.get('COLUMN_COMMENT'),
                character_maximum_length=row.get('CHARACTER_MAXIMUM_LENGTH'),
                numeric_precision=row.get('NUMERIC_PRECISION'),
                numeric_scale=row.get('NUMERIC_SCALE'),
                charset=row.get('CHARACTER_SET_NAME'),
                collation=row.get('COLLATION_NAME'),
            )
            columns.append(col)

        return columns

    async def _query_indexes(self, table_name: str,
                              schema: Optional[str]) -> List[IndexInfo]:
        """Query index information asynchronously."""
        db_name = schema or self._get_database_name()

        sql = """
            SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX,
                   NON_UNIQUE, INDEX_TYPE, SUB_PART
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        rows = await self._execute_introspection_query(sql, (db_name, table_name))

        # Group by index name
        index_map: Dict[str, IndexInfo] = {}
        for row in rows:
            idx_name = row['INDEX_NAME']

            if idx_name not in index_map:
                # Parse index type
                index_type_str = (row.get('INDEX_TYPE') or 'BTREE').upper()
                index_type_map = {
                    'BTREE': IndexType.BTREE,
                    'HASH': IndexType.HASH,
                    'FULLTEXT': IndexType.FULLTEXT,
                    'SPATIAL': IndexType.SPATIAL,
                    'RTREE': IndexType.SPATIAL,
                }
                index_type = index_type_map.get(index_type_str, IndexType.BTREE)

                index_map[idx_name] = IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    is_unique=row['NON_UNIQUE'] == 0,
                    is_primary=idx_name == 'PRIMARY',
                    index_type=index_type,
                    columns=[]
                )

            index_map[idx_name].columns.append(IndexColumnInfo(
                name=row['COLUMN_NAME'],
                ordinal_position=row['SEQ_IN_INDEX'],
                is_descending=False
            ))

        return list(index_map.values())

    async def _query_foreign_keys(self, table_name: str,
                                   schema: Optional[str]) -> List[ForeignKeyInfo]:
        """Query foreign key information asynchronously."""
        db_name = schema or self._get_database_name()

        sql = """
            SELECT kcu.CONSTRAINT_NAME, kcu.COLUMN_NAME,
                   kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME,
                   rc.UPDATE_RULE, rc.DELETE_RULE
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE kcu.TABLE_SCHEMA = %s
                AND kcu.TABLE_NAME = %s
                AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
        """
        rows = await self._execute_introspection_query(sql, (db_name, table_name))

        # Group by foreign key name
        fk_map: Dict[str, ForeignKeyInfo] = {}
        for row in rows:
            fk_name = row['CONSTRAINT_NAME']

            if fk_name not in fk_map:
                # Parse referential actions
                on_update_str = (row.get('UPDATE_RULE') or 'NO ACTION').upper().replace(' ', '_')
                on_delete_str = (row.get('DELETE_RULE') or 'NO ACTION').upper().replace(' ', '_')

                on_update = getattr(ReferentialAction, on_update_str, ReferentialAction.NO_ACTION)
                on_delete = getattr(ReferentialAction, on_delete_str, ReferentialAction.NO_ACTION)

                fk_map[fk_name] = ForeignKeyInfo(
                    name=fk_name,
                    table_name=table_name,
                    referenced_table=row['REFERENCED_TABLE_NAME'],
                    on_update=on_update,
                    on_delete=on_delete,
                    columns=[],
                    referenced_columns=[]
                )

            fk_map[fk_name].columns.append(row['COLUMN_NAME'])
            fk_map[fk_name].referenced_columns.append(row['REFERENCED_COLUMN_NAME'])

        return list(fk_map.values())

    async def _query_views(self, schema: Optional[str],
                            include_system: bool) -> List[ViewInfo]:
        """Query view list asynchronously."""
        db_name = schema or self._get_database_name()

        sql = """
            SELECT TABLE_NAME, VIEW_DEFINITION, CHECK_OPTION,
                   IS_UPDATABLE
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = %s
        """
        rows = await self._execute_introspection_query(sql, (db_name,))

        return [
            ViewInfo(
                name=row['TABLE_NAME'],
                definition=row.get('VIEW_DEFINITION'),
                check_option=row.get('CHECK_OPTION'),
                is_updatable=row.get('IS_UPDATABLE') == 'YES',
            )
            for row in rows
        ]

    async def _query_view_info(self, view_name: str,
                                schema: Optional[str]) -> Optional[ViewInfo]:
        """Query view details asynchronously."""
        views = await self._query_views(schema, False)
        return next((v for v in views if v.name == view_name), None)

    async def _query_triggers(self, table_name: Optional[str] = None,
                               schema: Optional[str] = None) -> List[TriggerInfo]:
        """Query trigger list asynchronously."""
        db_name = schema or self._get_database_name()

        sql = """
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE,
                   ACTION_TIMING, ACTION_STATEMENT
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = %s
        """
        params = [db_name]

        if table_name:
            sql += " AND EVENT_OBJECT_TABLE = %s"
            params.append(table_name)

        rows = await self._execute_introspection_query(sql, tuple(params))

        return [
            TriggerInfo(
                name=row['TRIGGER_NAME'],
                table_name=row['EVENT_OBJECT_TABLE'],
                timing=row.get('ACTION_TIMING'),
                events=[row.get('EVENT_MANIPULATION')] if row.get('EVENT_MANIPULATION') else [],
                definition=row.get('ACTION_STATEMENT'),
            )
            for row in rows
        ]
