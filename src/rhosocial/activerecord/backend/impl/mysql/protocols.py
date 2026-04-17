# src/rhosocial/activerecord/backend/impl/mysql/protocols.py
"""MySQL dialect-specific protocol definitions.

This module defines protocols for features exclusive to MySQL,
which are not part of the SQL standard and not supported by other
mainstream databases.
"""
from typing import Protocol, runtime_checkable, Tuple, Any, Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    pass


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
            expr: LoadDataExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_table_expression(
        self,
        expr: Any,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_TABLE expression.

        Note: Generic JSONSupport protocol defines supports_json_table() with dialect_options.
        This MySQL-specific version documents available options.

        Args:
            expr: JSONTableExpression instance
            dialect_options: MySQL-specific options:
                - 'on_error': How to handle errors ('IGNORE' to skip row on error)
                Example: dialect_options={'on_error': 'IGNORE'}

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


@runtime_checkable
class MySQLTableSupport(Protocol):
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


@runtime_checkable
class MySQLJSONFunctionSupport(Protocol):
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

    def supports_spatial_type(self) -> bool:
        """Whether spatial data types are supported."""
        ...

    def supports_spatial_index(self) -> bool:
        """Whether SPATIAL index is supported."""
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
class MySQLLockingSupport(Protocol):
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

    def format_mysql_for_update_clause(self, clause: Any) -> Tuple[str, tuple]:
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