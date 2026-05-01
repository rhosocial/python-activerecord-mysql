# src/rhosocial/activerecord/backend/impl/mysql/protocols.py
"""MySQL dialect-specific protocol definitions.

This module defines protocols for features exclusive to MySQL,
which are not part of the SQL standard and not supported by other
mainstream databases.

Note: MySQL-specific protocols extend generic protocols to avoid interface overlap.
When a MySQL protocol extends a generic protocol, dialects only need to implement
the MySQL-specific protocol - isinstance checks for the generic protocol will still work.
"""
from typing import Protocol, runtime_checkable, Tuple, Any, Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from rhosocial.activerecord.backend.dialect.protocols import (
    JSONSupport,
    LockingSupport,
    TableSupport,
)


@runtime_checkable
class MySQLDMLOperationSupport(Protocol):
    """MySQL-specific DML operations protocol.

    Feature Source: MySQL native (not SQL standard)

    MySQL DML features beyond SQL standard:
    - INSERT IGNORE: Silently ignore rows that would cause duplicate key errors
    - REPLACE INTO: Delete and re-insert on duplicate key (changes AUTO_INCREMENT)
    - LOAD DATA INFILE: High-performance bulk data import

    Official Documentation:
    - INSERT: https://dev.mysql.com/doc/refman/8.0/en/insert.html
    - REPLACE: https://dev.mysql.com/doc/refman/8.0/en/replace.html
    - LOAD DATA: https://dev.mysql.com/doc/refman/8.0/en/load-data.html

    Version Requirements:
    - INSERT IGNORE: All MySQL versions
    - REPLACE INTO: All MySQL versions
    - LOAD DATA INFILE: All MySQL versions

    Usage:
        INSERT IGNORE is supported via dialect_options in InsertExpression:
        ```python
        InsertExpression(
            dialect,
            into='users',
            source=ValuesSource(...),
            dialect_options={'ignore': True}  # Generates INSERT IGNORE
        )
        ```
    """

    def supports_insert_ignore(self) -> bool:
        """Whether INSERT IGNORE is supported.

        MySQL supports INSERT IGNORE to silently ignore rows that would
        cause duplicate key errors instead of raising an error.
        """
        ...

    def supports_replace_into(self) -> bool:
        """Whether REPLACE INTO is supported.

        MySQL supports REPLACE INTO which deletes and re-inserts on
        duplicate key. Note: AUTO_INCREMENT value changes on replacement.
        """
        ...

    def supports_load_data(self) -> bool:
        """Whether LOAD DATA INFILE is supported.

        MySQL supports LOAD DATA INFILE for high-performance bulk data
        import from files. LOCAL variant reads files from the client.
        """
        ...

    def format_load_data_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format LOAD DATA INFILE statement.

        Args:
            expr: MySQLLoadDataExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_on_conflict_clause(self, expr: Any) -> Tuple[str, tuple]:
        """Format ON DUPLICATE KEY UPDATE clause (MySQL upsert).

        MySQL uses ON DUPLICATE KEY UPDATE instead of the SQL-standard
        ON CONFLICT clause for upsert operations.

        Args:
            expr: OnConflictExpression or equivalent instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLTriggerSupport(Protocol):
    """MySQL trigger DDL protocol.

    Feature Source: Native support (no extension required)

    MySQL triggers:
    - BEFORE/AFTER: Timing
    - INSERT/UPDATE/DELETE: Event
    - FOR EACH ROW: Level (only row-level triggers supported)
    - NEW/OLD: Row references

    Official Documentation:
    - CREATE TRIGGER: https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html

    Version Requirements:
    - Triggers: MySQL 5.0.2+
    - Trigger IF EXISTS: MySQL 8.0.4+
    """

    def supports_trigger(self) -> bool:
        """Whether triggers are supported."""
        ...

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported (MySQL 8.0.4+)."""
        ...

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MySQL does NOT support INSTEAD OF triggers (only BEFORE/AFTER).
        This method always returns False for MySQL.
        """
        ...

    def supports_statement_trigger(self) -> bool:
        """Whether statement-level triggers are supported.

        MySQL only supports row-level triggers (FOR EACH ROW).
        This method always returns False for MySQL.
        """
        ...

    def supports_trigger_referencing(self) -> bool:
        """Whether trigger referencing (NEW/OLD) is supported.

        MySQL supports NEW and OLD row references in triggers.
        """
        ...

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition on triggers is supported.

        MySQL does NOT support WHEN condition on triggers.
        This method always returns False for MySQL.
        """
        ...

    def format_create_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement.

        Args:
            expr: CreateTriggerExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_drop_trigger_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement.

        Args:
            expr: DropTriggerExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLTableSupport(TableSupport, Protocol):
    """MySQL table DDL protocol.

    Feature Source: Native support (no extension required)

    MySQL table features beyond SQL standard:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    - Row format options

    Official Documentation:
    - CREATE TABLE: https://dev.mysql.com/doc/refman/8.0/en/create-table.html
    - CREATE TABLE ... LIKE: https://dev.mysql.com/doc/refman/8.0/en/create-table-like.html

    Version Requirements:
    - Basic features: All versions
    - Various storage engines: MySQL 5.5+
    """

    def supports_table_like_syntax(self) -> bool:
        """Whether CREATE TABLE ... LIKE is supported.

        MySQL supports copying table structure with LIKE syntax.
        """
        ...

    def supports_inline_index(self) -> bool:
        """Whether inline index definitions are supported.

        MySQL allows INDEX/KEY definitions within CREATE TABLE.
        """
        ...

    def supports_storage_engine_option(self) -> bool:
        """Whether ENGINE option is supported.

        MySQL supports multiple storage engines (InnoDB, MyISAM, etc.).
        """
        ...

    def supports_charset_option(self) -> bool:
        """Whether CHARSET/COLLATE options are supported.

        MySQL supports character set and collation at table level.
        """
        ...

    def format_create_table_statement(
        self,
        expr,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement.

        Note: Generic TableSupport protocol defines this interface.
        This MySQL-specific version documents available options.

        Args:
            expr: CreateTableExpression instance
            dialect_options: MySQL-specific options:
                - 'engine': Storage engine (InnoDB, MyISAM, etc.)
                - 'charset': Character set
                - 'collate': Collation
                - 'auto_increment': Initial AUTO_INCREMENT value
                - 'row_format': Row format (DYNAMIC, COMPACT, etc.)
                Example: dialect_options={'engine': 'InnoDB', 'charset': 'utf8mb4'}
        """
        ...


@runtime_checkable
class MySQLSetTypeSupport(Protocol):
    """MySQL SET type protocol.

    Feature Source: MySQL native (not SQL standard)

    MySQL SET features:
    - String object with zero or more values from predefined list
    - Stored as integer (bit flags) internally
    - Maximum 64 members
    - Supports FIND_IN_SET, LIKE operations
    - Automatically sorted on storage

    Official Documentation:
    - SET Type: https://dev.mysql.com/doc/refman/8.0/en/set.html

    Version Requirements:
    - All MySQL versions
    """

    def supports_set_type(self) -> bool:
        """Whether SET type is supported."""
        ...

    def format_set_literal(
        self,
        values: List[str],
        column_values: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format SET type literal.

        Args:
            values: Allowed values for the SET type
            column_values: Values being inserted/compared

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_find_in_set(
        self,
        value: str,
        set_column: str
    ) -> Tuple[str, tuple]:
        """Format FIND_IN_SET function call.

        Args:
            value: Value to search for
            set_column: SET column or expression to search in

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_set_contains(
        self,
        column: str,
        values: List[str]
    ) -> Tuple[str, tuple]:
        """Format SET contains check expression.

        Args:
            column: SET column name
            values: Values to check for containment

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLJSONFunctionSupport(JSONSupport, Protocol):
    """MySQL JSON function protocol.

    Feature Source: MySQL 5.7+

    MySQL JSON functions:
    - JSON_ARRAY, JSON_OBJECT
    - JSON_EXTRACT, JSON_SET, JSON_REMOVE
    - JSON_SEARCH, JSON_CONTAINS, JSON_KEYS

    Official Documentation:
    - JSON Functions: https://dev.mysql.com/doc/refman/8.0/en/json-functions.html

    Version Requirements:
    - JSON type: MySQL 5.7+
    - JSONTABLE: MySQL 8.0.4+
    """

    def supports_json_type(self) -> bool:
        """Whether JSON data type is supported (MySQL 5.7+)."""
        ...

    def supports_json_merge_patch(self) -> bool:
        """Whether JSON_MERGE_PATCH is supported (MySQL 8.0.3+)."""
        ...

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE is supported (MySQL 8.0.4+)."""
        ...

    def supports_json_function(self, function_name: str) -> bool:
        """Whether a specific JSON function is supported.

        Args:
            function_name: Name of the JSON function (e.g. 'json_extract')

        Returns:
            True if the function is supported
        """
        ...

    def format_json_extract(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function call.

        Args:
            json_doc: JSON document or column
            path: JSON path expression
            paths: Additional path expressions (MySQL 5.7.9+ multi-path)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_unquote(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function call.

        Args:
            json_val: JSON value to unquote

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_object(
        self,
        key_value_pairs: List[Tuple[str, Any]]
    ) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function call.

        Args:
            key_value_pairs: List of (key, value) tuples

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_array(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function call.

        Args:
            values: Values to include in the JSON array

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_contains(
        self,
        target: str,
        candidate: str,
        path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function call.

        Args:
            target: JSON document or column to search in
            candidate: JSON value to search for
            path: Optional path within the target document

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_set(
        self,
        json_doc: str,
        path: str,
        value: Any,
        path_value_pairs: Optional[List[Tuple[str, Any]]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_SET function call.

        Args:
            json_doc: JSON document or column
            path: JSON path expression
            value: Value to set at the path
            path_value_pairs: Additional (path, value) pairs

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_remove(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_REMOVE function call.

        Args:
            json_doc: JSON document or column
            path: JSON path to remove
            paths: Additional paths to remove

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_type(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_TYPE function call.

        Args:
            json_val: JSON value to type-check

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_valid(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_VALID function call.

        Args:
            json_val: Value to check for valid JSON

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_search(
        self,
        json_doc: str,
        search_str: str,
        path: Optional[str] = None,
        all: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON_SEARCH function call.

        Args:
            json_doc: JSON document or column to search in
            search_str: Search string (supports % and _ wildcards)
            path: Optional path to search within
            all: If True, return all matches; if False, return first match

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLSpatialSupport(Protocol):
    """MySQL spatial data type protocol.

    Feature Source: MySQL 5.7+ with InnoDB, all versions with MyISAM

    MySQL spatial features:
    - SPATIAL data types: GEOMETRY, POINT, LINESTRING, POLYGON, etc.
    - Spatial indexes (only for MyISAM with NOT NULL)
    - SPATIAL KEY/MULTIPLE KEY for indexes

    Official Documentation:
    - Spatial Data Types: https://dev.mysql.com/doc/refman/8.0/en/spatial-type.html

    Version Requirements:
    - Basic spatial types: MySQL 5.7+ (InnoDB), all versions (MyISAM)
    - Spatial index restrictions: MySQL 5.7.5+ for correct SRID handling
    """

    def supports_spatial_type(self, type_name: str) -> bool:
        """Whether a specific spatial data type is supported.

        Args:
            type_name: Spatial type name (e.g. 'POINT', 'LINESTRING')

        Returns:
            True if the spatial type is supported
        """
        ...

    def supports_spatial_index(self) -> bool:
        """Whether SPATIAL index is supported."""
        ...

    def supports_geojson(self) -> bool:
        """Whether GeoJSON functions (ST_AsGeoJSON) are supported (MySQL 5.7+)."""
        ...

    def supports_geometry_type(self) -> bool:
        """Whether GEOMETRY type is supported."""
        ...

    def supports_point_type(self) -> bool:
        """Whether POINT type is supported."""
        ...

    def supports_curve_type(self) -> bool:
        """Whether curve types (LINESTRING, MULTILINESTRING) are supported."""
        ...

    def supports_surface_type(self) -> bool:
        """Whether surface types (POLYGON, MULTIPOLYGON) are supported."""
        ...

    def supports_geometry_collection_type(self) -> bool:
        """Whether GEOMETRYCOLLECTION is supported."""
        ...

    def format_spatial_literal(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format spatial literal from WKT.

        Args:
            wkt: Well-Known Text representation
            srid: Optional Spatial Reference System Identifier

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_geom_from_text(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromText function call.

        Args:
            wkt: Well-Known Text representation
            srid: Optional Spatial Reference System Identifier

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_geom_from_wkb(
        self,
        wkb: bytes,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromWKB function call.

        Args:
            wkb: Well-Known Binary representation
            srid: Optional Spatial Reference System Identifier

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_as_text(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsText function call.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_as_geojson(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function call.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_distance(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Distance function call.

        Args:
            geom1: First geometry
            geom2: Second geometry

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_within(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Within function call.

        Args:
            geom1: Geometry to test
            geom2: Geometry to test against

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_contains(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Contains function call.

        Args:
            geom1: Geometry to test
            geom2: Geometry to test against

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_create_spatial_index(
        self,
        index_name: str,
        table_name: str,
        column: str
    ) -> Tuple[str, tuple]:
        """Format CREATE SPATIAL INDEX statement.

        Args:
            index_name: Index name
            table_name: Table name
            column: Column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLVectorSupport(Protocol):
    """MySQL vector data type protocol.

    Feature Source: MySQL 8.0+ (optional feature in 8.0.16+, GA in 8.0.17+)

    MySQL vector features:
    - VECTOR data type for embedding vectors
    - Vector operations and functions

    Official Documentation:
    - Vector Type: https://dev.mysql.com/doc/refman/8.0/en/vector-type.html

    Version Requirements:
    - VECTOR type: MySQL 8.0.16+ (experimental), 8.0.17+ (GA)
    """

    def supports_vector_type(self) -> bool:
        """Whether VECTOR data type is supported (MySQL 8.0.17+)."""
        ...

    def supports_vector_index(self) -> bool:
        """Whether vector index is supported (MySQL 8.0.17+)."""
        ...

    def get_max_vector_dimension(self) -> int:
        """Get the maximum supported vector dimension.

        Returns:
            Maximum number of dimensions supported for VECTOR type
        """
        ...

    def format_vector_literal(self, values: List[float]) -> Tuple[str, tuple]:
        """Format vector literal from a list of float values.

        Args:
            values: List of float values representing the vector

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_string_to_vector(self, vector_str: str) -> Tuple[str, tuple]:
        """Format STRING_TO_VECTOR function call.

        Args:
            vector_str: String representation of a vector

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_vector_to_string(self, vector_col: str) -> Tuple[str, tuple]:
        """Format VECTOR_TO_STRING function call.

        Args:
            vector_col: Vector column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_vector_dim(self, vector_col: str) -> Tuple[str, tuple]:
        """Format VECTOR_DIM function call to get vector dimension.

        Args:
            vector_col: Vector column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_distance_euclidean(
        self,
        vector1: str,
        vector2: str
    ) -> Tuple[str, tuple]:
        """Format EUCLIDEAN_DISTANCE function call.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_distance_cosine(
        self,
        vector1: str,
        vector2: str
    ) -> Tuple[str, tuple]:
        """Format COSINE_DISTANCE function call.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_distance_dot(
        self,
        vector1: str,
        vector2: str
    ) -> Tuple[str, tuple]:
        """Format DOT_PRODUCT function call.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_create_vector_index(
        self,
        index_name: str,
        table_name: str,
        column: str
    ) -> Tuple[str, tuple]:
        """Format CREATE VECTOR INDEX statement.

        Args:
            index_name: Index name
            table_name: Table name
            column: Column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLFullTextSearchSupport(Protocol):
    """MySQL full-text search protocol.

    Note: Most interfaces are defined in generic IndexSupport protocol.
    This protocol only defines MySQL-specific interfaces.

    Feature Source: MySQL 5.6+

    MySQL full-text features:
    - FULLTEXT index on CHAR, VARCHAR, TEXT columns
    - FULLTEXT index on multiple columns
    - Natural language, Boolean, Query expansion modes
    - IN NATURAL LANGUAGE MODE, IN BOOLEAN MODE, WITH QUERY EXPANSION
    - Stopwords, minimum word length

    Official Documentation:
    - Full-Text Search Functions: https://dev.mysql.com/doc/refman/8.0/en/fulltext-search.html

    Version Requirements:
    - FULLTEXT index: MySQL 5.6+ (InnoDB), all versions (MyISAM)
    - FULLTEXT parser: MySQL 5.1+
    - IN BOOLEAN MODE: MySQL 5.6+
    - WITH QUERY EXPANSION: MySQL 5.6.7+
    """

    def supports_fulltext_index(self) -> bool:
        """Whether FULLTEXT index is supported (MySQL 5.6+ InnoDB)."""
        ...

    def supports_fulltext_parser(self) -> bool:
        """Whether custom full-text parser plugins are supported (MySQL 5.1+)."""
        ...

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether query expansion mode is supported (MySQL 5.6.7+)."""
        ...

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format MATCH ... AGAINST expression.

        Args:
            columns: Column names to search
            search_string: Search string
            mode: Search mode (None, 'NATURAL_LANGUAGE', 'BOOLEAN', 'QUERY_EXPANSION')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fulltext_index_options(
        self,
        index_name: str,
        columns: List[str],
        index_type: Optional[str] = None,
        parser_name: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format FULLTEXT index options.

        Args:
            index_name: Index name (usually 'FULLTEXT')
            columns: Indexed columns
            index_type: Index type (BTREE, HASH - ignored for FULLTEXT)
            parser_name: Parser name for full-text search

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLLockingSupport(LockingSupport, Protocol):
    """MySQL row-level locking protocol.

    Feature Source: MySQL native (FOR UPDATE all versions, FOR SHARE MySQL 8.0+)

    MySQL locking features beyond SQL standard:
    - FOR SHARE: Shared lock (MySQL 8.0+, replaces LOCK IN SHARE MODE)
    - NOWAIT: Fail immediately if rows are locked (MySQL 8.0+)
    - SKIP LOCKED: Skip locked rows (MySQL 8.0+)

    Note: MySQL does NOT support PostgreSQL's FOR NO KEY UPDATE or
    FOR KEY SHARE lock strengths.

    Official Documentation:
    - SELECT ... FOR UPDATE: https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html
    - LOCK IN SHARE MODE: https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html

    Version Requirements:
    - FOR UPDATE: All MySQL versions
    - FOR SHARE (replacing LOCK IN SHARE MODE): MySQL 8.0+
    - NOWAIT: MySQL 8.0+
    - SKIP LOCKED: MySQL 8.0+
    """

    def supports_for_share(self) -> bool:
        """Whether FOR SHARE clause is supported (MySQL 8.0+)."""
        ...

    def supports_for_update_nowait(self) -> bool:
        """Whether FOR UPDATE NOWAIT is supported (MySQL 8.0+)."""
        ...

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported (MySQL 8.0+)."""
        ...

    def format_for_update_clause(self, clause: Any) -> Tuple[str, tuple]:
        """Format MySQL-specific FOR UPDATE clause.

        Args:
            clause: MySQLForUpdateClause instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLModifyColumnSupport(Protocol):
    """MySQL MODIFY COLUMN and CHANGE COLUMN protocol.

    Feature Source: MySQL native (not SQL standard)

    MySQL ALTER TABLE features beyond SQL standard:
    - MODIFY COLUMN: Redefine a column with new specification (name unchanged)
    - CHANGE COLUMN: Rename and redefine a column in one operation
    - FIRST/AFTER: Column positioning within the table

    Official Documentation:
    - ALTER TABLE: https://dev.mysql.com/doc/refman/8.0/en/alter-table.html

    Version Requirements:
    - MODIFY COLUMN: All MySQL versions
    - CHANGE COLUMN: All MySQL versions
    """

    def supports_modify_column(self) -> bool:
        """Whether MODIFY COLUMN is supported."""
        ...

    def supports_change_column(self) -> bool:
        """Whether CHANGE COLUMN is supported."""
        ...

    def format_modify_column_action(self, action) -> Tuple[str, tuple]:
        """Format MODIFY COLUMN action for ALTER TABLE.

        Args:
            action: ModifyColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_change_column_action(self, action) -> Tuple[str, tuple]:
        """Format CHANGE COLUMN action for ALTER TABLE.

        Args:
            action: ChangeColumn action instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...