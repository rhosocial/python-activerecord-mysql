# src/rhosocial/activerecord/backend/impl/mysql/protocols.py
"""MySQL dialect-specific protocol definitions.

This module defines protocols for features exclusive to MySQL,
which are not part of the SQL standard and not supported by other
mainstream databases.
"""
from typing import Protocol, runtime_checkable, Tuple, Any, Optional, List


@runtime_checkable
class MySQLTriggerSupport(Protocol):
    """MySQL trigger DDL protocol.

    Feature Source: Native support (no extension required)

    MySQL trigger features and restrictions:
    - FOR EACH ROW only (no FOR EACH STATEMENT)
    - No INSTEAD OF triggers
    - No WHEN condition
    - No REFERENCING clause
    - Single event per trigger (no OR syntax)
    - Trigger body is BEGIN...END block
    - Requires same definer as table

    Official Documentation:
    - CREATE TRIGGER: https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html
    - Trigger Restrictions: https://dev.mysql.com/doc/refman/8.0/en/trigger-restrictions.html

    Version Requirements:
    - Basic triggers: MySQL 5.0+
    - Multiple triggers per event: MySQL 5.7+
    """

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MySQL does NOT support INSTEAD OF triggers.
        """
        ...

    def supports_statement_trigger(self) -> bool:
        """Whether FOR EACH STATEMENT triggers are supported.

        MySQL does NOT support FOR EACH STATEMENT triggers.
        Only FOR EACH ROW is supported.
        """
        ...

    def supports_trigger_referencing(self) -> bool:
        """Whether REFERENCING clause is supported.

        MySQL does NOT support REFERENCING clause.
        OLD and NEW are implicit references.
        """
        ...

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition is supported.

        MySQL does NOT support WHEN condition in triggers.
        """
        ...

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported.

        MySQL 5.7+ supports IF NOT EXISTS.
        """
        ...

    def format_create_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement (MySQL syntax)."""
        ...

    def format_drop_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement (MySQL syntax)."""
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

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement (MySQL syntax)."""
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
        """Format SET literal value.
        
        Args:
            values: Values to include in the SET
            column_values: Allowed values for the column (for validation)
        
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
    
    def format_find_in_set(
        self,
        value: str,
        set_column: str
    ) -> Tuple[str, tuple]:
        """Format FIND_IN_SET function.
        
        Args:
            value: Value to find
            set_column: SET column name
        
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
    
    def format_set_contains(
        self,
        column: str,
        values: List[str]
    ) -> Tuple[str, tuple]:
        """Format SET contains check.

        Checks if all values are present in the SET column.

        Args:
            column: SET column name
            values: Values to check for

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLJSONFunctionSupport(Protocol):
    """MySQL JSON function protocol.

    Feature Source: MySQL 5.7.8+

    MySQL JSON functions beyond SQL standard:
    - JSON_EXTRACT: Extract data from JSON documents
    - JSON_UNQUOTE: Unquote JSON value
    - JSON_OBJECT: Create JSON object
    - JSON_ARRAY: Create JSON array
    - JSON_MERGE_PRESERVE: Merge JSON documents
    - JSON_MERGE_PATCH: Merge with patch logic
    - JSON_CONTAINS: Check if JSON contains value
    - JSON_SEARCH: Search in JSON
    - JSON_SET: Set value in JSON
    - JSON_INSERT: Insert value into JSON
    - JSON_REPLACE: Replace value in JSON
    - JSON_REMOVE: Remove data from JSON
    - JSON_TYPE: Get type of JSON value
    - JSON_VALID: Validate JSON
    - JSON_SCHEMA_VALID: Validate against JSON schema (MySQL 8.0.17+)

    Official Documentation:
    - JSON Functions: https://dev.mysql.com/doc/refman/8.0/en/json-functions.html

    Version Requirements:
    - JSON type and basic functions: MySQL 5.7.8+
    - JSON_MERGE_PATCH: MySQL 8.0.3+
    - JSON_TABLE: MySQL 8.0.4+
    - JSON_VALUE: MySQL 8.0.21+
    - JSON schema validation: MySQL 8.0.17+
    """

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported.

        Args:
            function_name: Name of JSON function (e.g., 'JSON_TABLE', 'JSON_VALUE')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class MySQLSpatialSupport(Protocol):
    """MySQL spatial data type protocol.

    Feature Source: MySQL 5.7+ (OpenGIS compliant)

    MySQL spatial features:
    - GEOMETRY: Base type for all spatial values
    - POINT: A point in 2D/3D/4D space
    - LINESTRING: A sequence of points forming a line
    - POLYGON: A closed area with one or more rings
    - MULTIPOINT, MULTILINESTRING, MULTIPOLYGON: Collections
    - GEOMETRYCOLLECTION: Heterogeneous collection

    Format Support:
    - WKT (Well-Known Text): 'POINT(1 1)'
    - WKB (Well-Known Binary): Binary format
    - GeoJSON: JSON-based format (MySQL 5.7.5+)

    Official Documentation:
    - Spatial Types: https://dev.mysql.com/doc/refman/8.0/en/spatial-types.html
    - Spatial Functions: https://dev.mysql.com/doc/refman/8.0/en/spatial-functions.html

    Version Requirements:
    - Basic spatial types: MySQL 5.7+
    - GeoJSON support: MySQL 5.7.5+
    - Improved SRID handling: MySQL 8.0+
    """

    def supports_spatial_type(self, type_name: str) -> bool:
        """Check if specific spatial type is supported.

        Args:
            type_name: Name of spatial type (e.g., 'POINT', 'GEOMETRY')

        Returns:
            True if type is supported in current MySQL version
        """
        ...

    def supports_spatial_index(self) -> bool:
        """Whether SPATIAL indexes are supported.

        MySQL 5.7+ supports SPATIAL indexes for spatial columns.
        """
        ...

    def supports_geojson(self) -> bool:
        """Whether GeoJSON functions are supported.

        MySQL 5.7.5+ supports ST_AsGeoJSON and ST_GeomFromGeoJSON.
        """
        ...

    def format_spatial_literal(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format spatial literal from WKT.

        Args:
            wkt: Well-Known Text representation (e.g., 'POINT(1 1)')
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
        """Format ST_GeomFromText function.

        Args:
            wkt: Well-Known Text representation
            srid: Optional SRID

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_geom_from_wkb(
        self,
        wkb: bytes,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromWKB function.

        Args:
            wkb: Well-Known Binary representation
            srid: Optional SRID

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_as_text(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsText function.

        Args:
            geom: Geometry column or expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_st_as_geojson(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function (MySQL 5.7.5+).

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
        """Format ST_Distance function.

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
        """Format ST_Within function.

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
        """Format ST_Contains function.

        Args:
            geom1: Geometry to test against
            geom2: Geometry to test

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
            index_name: Name of the index
            table_name: Name of the table
            column: Spatial column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_extract(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function.

        Args:
            json_doc: JSON document or column name
            path: JSON path expression
            paths: Additional paths for multiple extraction (optional)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_unquote(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function.

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
        """Format JSON_OBJECT function.

        Args:
            key_value_pairs: List of (key, value) tuples

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_array(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function.

        Args:
            values: List of values

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
        """Format JSON_CONTAINS function.

        Args:
            target: JSON document or column to search in
            candidate: JSON value to search for
            path: Optional path within target to search

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
        """Format JSON_SET function.

        Args:
            json_doc: JSON document or column name
            path: JSON path expression
            value: Value to set
            path_value_pairs: Additional (path, value) pairs (optional)

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
        """Format JSON_REMOVE function.

        Args:
            json_doc: JSON document or column name
            path: JSON path to remove
            paths: Additional paths to remove (optional)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_type(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_TYPE function.

        Args:
            json_val: JSON value to check type

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_json_valid(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_VALID function.

        Args:
            json_val: Value to validate as JSON

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
        """Format JSON_SEARCH function.

        Args:
            json_doc: JSON document or column name
            search_str: String to search for
            path: Optional path to search within
            all: If True, return all matches; if False, return first match

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
