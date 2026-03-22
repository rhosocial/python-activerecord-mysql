"""MySQL dialect-specific Mixin implementations."""
import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.transaction import IsolationLevel


class MySQLTransactionMixin:
    """MySQL transaction common functionality.

    Provides shared isolation level management for both sync and async
    MySQL transaction managers.
    """

    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
    }

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set transaction isolation level."""
        from rhosocial.activerecord.backend.transaction import IsolationLevelError
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        if level is not None and level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level


class MySQLBackendMixin:
    """MySQL backend common functionality.

    Provides shared non-I/O methods for both sync and async MySQL backends.
    This mixin assumes the following attributes exist in the class:
    - self._version: MySQL server version tuple
    - self._dialect: MySQLDialect instance (lazy loaded)
    - self._transaction_manager: Transaction manager instance
    - self._connection: Database connection
    - self.adapter_registry: Type adapter registry
    - self.config: Connection configuration
    - self._logger: Logger instance
    """

    def _register_mysql_adapters(self):
        """Register MySQL-specific type adapters."""
        from .adapters import (
            MySQLBlobAdapter,
            MySQLBooleanAdapter,
            MySQLDateAdapter,
            MySQLDatetimeAdapter,
            MySQLDecimalAdapter,
            MySQLEnumAdapter,
            MySQLJSONAdapter,
            MySQLSetAdapter,
            MySQLTimeAdapter,
            MySQLUUIDAdapter,
        )

        mysql_adapters = [
            MySQLBlobAdapter(),
            MySQLBooleanAdapter(),
            MySQLDateAdapter(),
            MySQLDatetimeAdapter(self._version),
            MySQLDecimalAdapter(),
            MySQLEnumAdapter(use_int_storage=False),  # Default to string representation
            MySQLJSONAdapter(),
            MySQLSetAdapter(),  # MySQL SET type support
            MySQLTimeAdapter(),
            MySQLUUIDAdapter(),
        ]

        for adapter in mysql_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    # Use allow_override=True to replace default adapters with MySQL-specific ones
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)

        self.log(logging.DEBUG, "Registered MySQL-specific type adapters")

    @property
    def dialect(self):
        """Get the MySQL dialect instance (lazy loads with configured version)."""
        from .dialect import MySQLDialect
        if self._dialect is None:
            self._dialect = MySQLDialect(self._version)
        return self._dialect

    @property
    def transaction_manager(self):
        """Get the MySQL transaction manager."""
        # Update the transaction manager's connection if needed
        if self._transaction_manager:
            self._transaction_manager._connection = self._connection
        return self._transaction_manager

    def requires_manual_commit(self) -> bool:
        """Check if manual commit is required for this database."""
        return not getattr(self.config, 'autocommit', True)

    def _check_returning_compatibility(self, _returning_clause):
        """Check if RETURNING clause is compatible with this MySQL version.

        Args:
            _returning_clause: Unused parameter (MySQL doesn't support RETURNING).
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        # MySQL does not support RETURNING clause
        if self.dialect.supports_returning_clause():
            return True
        else:
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                "MySQL does not support RETURNING clause. "
                "Consider using LAST_INSERT_ID() or alternative approaches."
            )

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """
        [Backend Implementation] Provides default type adapter suggestions for MySQL.

        This method defines a curated set of type adapter suggestions for common Python
        types, mapping them to their typical MySQL-compatible representations as
        demonstrated in test fixtures. It explicitly retrieves necessary `SQLTypeAdapter`
        instances from the backend's `adapter_registry`. If an adapter for a specific
        (Python type, DB driver type) pair is not registered, no suggestion will be
        made for that Python type.

        Returns:
            Dict[Type, Tuple[SQLTypeAdapter, Type]]: A dictionary where keys are
            original Python types (`TypeRegistry`'s `py_type`), and values are
            tuples containing a `SQLTypeAdapter` instance and the target
            Python type (`TypeRegistry`'s `db_type`) expected by the driver.
        """
        from datetime import date, datetime, time
        from decimal import Decimal
        from uuid import UUID
        from enum import Enum

        suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]] = {}

        # Define a list of desired Python type to DB driver type mappings.
        # This list reflects types seen in test fixtures and common usage,
        # along with their preferred database-compatible Python types for the driver.
        # Types that are natively compatible with the DB driver (e.g., Python str, int, float)
        # and for which no specific conversion logic is needed are omitted from this list.
        # The consuming layer should assume pass-through behavior for any Python type
        # that does not have an explicit adapter suggestion.
        #
        # Exception: If a user requires specific processing for a natively compatible type
        # (e.g., custom serialization/deserialization for JSON strings beyond basic conversion),
        # they would need to implement and register their own specialized adapter.
        # This backend's default suggestions do not cater to such advanced processing needs.
        type_mappings = [
            (bool, int),        # Python bool -> DB driver int (MySQL TINYINT)
            # Why str for date/time?
            # MySQL accepts string representations of dates/times and converts them appropriately.
            (datetime, str),    # Python datetime -> DB driver str (MySQL DATETIME/TIMESTAMP)
            (date, str),        # Python date -> DB driver str (MySQL DATE)
            (time, str),        # Python time -> DB driver str (MySQL TIME)
            (Decimal, float),   # Python Decimal -> DB driver float (MySQL DECIMAL)
            (UUID, str),        # Python UUID -> DB driver str (MySQL CHAR/VARCHAR/BINARY)
            (dict, str),        # Python dict -> DB driver str (MySQL TEXT for JSON)
            (list, str),        # Python list -> DB driver str (MySQL TEXT for JSON)
            (Enum, str),        # Python Enum -> DB driver str (MySQL TEXT/VARCHAR)
            (set, str),         # Python set -> DB driver str (MySQL SET)
            (frozenset, str),   # Python frozenset -> DB driver str (MySQL SET)
        ]

        # Iterate through the defined mappings and retrieve adapters from the registry.
        for py_type, db_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter:
                suggestions[py_type] = (adapter, db_type)
            else:
                # Log a debug message if a specific adapter is expected but not found.
                self.log(
                    logging.DEBUG,
                    f"No adapter found for ({py_type.__name__}, {db_type.__name__}). "
                    "Suggestion will not be provided for this type."
                )

        return suggestions

    def log(self, level: int, message: str):
        """Log a message with the specified level."""
        if hasattr(self, '_logger') and self._logger:
            self._logger.log(level, message)
        else:
            # Fallback logging
            print(f"[{logging.getLevelName(level)}] {message}")


class MySQLTriggerMixin:
    """MySQL trigger DDL implementation.

    MySQL trigger restrictions:
    - FOR EACH ROW only (no FOR EACH STATEMENT)
    - No INSTEAD OF triggers
    - No WHEN condition
    - No REFERENCING clause
    - Single event per trigger
    """

    def supports_instead_of_trigger(self) -> bool:
        """MySQL does NOT support INSTEAD OF triggers."""
        return False

    def supports_statement_trigger(self) -> bool:
        """MySQL does NOT support FOR EACH STATEMENT triggers."""
        return False

    def supports_trigger_referencing(self) -> bool:
        """MySQL does NOT support REFERENCING clause."""
        return False

    def supports_trigger_when(self) -> bool:
        """MySQL does NOT support WHEN condition."""
        return False

    def supports_trigger_if_not_exists(self) -> bool:
        """MySQL 5.7+ supports IF NOT EXISTS."""
        return self.version >= (5, 7, 0)

    def format_create_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement (MySQL syntax).

        MySQL differences from SQL:1999:
        - Does not support INSTEAD OF triggers
        - Does not support FOR EACH STATEMENT
        - Does not support WHEN condition
        - Does not support REFERENCING clause
        - Uses trigger body directly instead of function call
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if expr.timing.value == "INSTEAD OF":
            raise UnsupportedFeatureError(
                self.name,
                "INSTEAD OF triggers (MySQL does not support this feature)"
            )

        if expr.level and expr.level.value == "FOR EACH STATEMENT":
            raise UnsupportedFeatureError(
                self.name,
                "FOR EACH STATEMENT triggers (MySQL only supports FOR EACH ROW)"
            )

        if expr.condition:
            raise UnsupportedFeatureError(
                self.name,
                "WHEN condition in triggers (MySQL does not support this feature)"
            )

        if expr.referencing:
            raise UnsupportedFeatureError(
                self.name,
                "REFERENCING clause in triggers (MySQL does not support this feature)"
            )

        if len(expr.events) > 1:
            raise UnsupportedFeatureError(
                self.name,
                "multiple trigger events (MySQL only supports single event)"
            )

        if expr.update_columns:
            raise UnsupportedFeatureError(
                self.name,
                "UPDATE OF column_list (MySQL does not support this syntax)"
            )

        parts = ["CREATE TRIGGER"]

        if expr.if_not_exists and self.supports_trigger_if_not_exists():
            parts.append("IF NOT EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        parts.append(expr.timing.value)

        if expr.events:
            parts.append(expr.events[0].value)

        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))

        parts.append("FOR EACH ROW")

        if expr.function_name:
            parts.append("CALL")
            parts.append(self.format_identifier(expr.function_name))

        return " ".join(parts), ()

    def format_drop_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement (MySQL syntax)."""
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()


class MySQLTableMixin:
    """MySQL table DDL implementation.

    MySQL-specific features:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    """

    def supports_table_like_syntax(self) -> bool:
        """MySQL supports CREATE TABLE ... LIKE syntax."""
        return True

    def supports_inline_index(self) -> bool:
        """MySQL allows inline INDEX/KEY definitions."""
        return True

    def supports_storage_engine_option(self) -> bool:
        """MySQL supports multiple storage engines."""
        return True

    def supports_charset_option(self) -> bool:
        """MySQL supports CHARSET/COLLATE at table level."""
        return True

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement for MySQL.

        Handles MySQL-specific syntax including:
        - LIKE syntax (copying table structure)
        - Inline index definitions
        - Storage options (ENGINE, CHARSET, COLLATE)
        - Table-level comments
        - AUTO_INCREMENT in column definitions
        """
        if 'like_table' in expr.dialect_options:
            return self._format_create_table_like(expr)

        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraintType, TableConstraintType
        )

        all_params: List[Any] = []

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self._format_column_definition_mysql(col_def, ColumnConstraintType)
            column_parts.append(col_sql)
            all_params.extend(col_params)

        for t_const in expr.table_constraints:
            const_sql, const_params = self._format_table_constraint_mysql(t_const, TableConstraintType)
            column_parts.append(const_sql)
            all_params.extend(const_params)

        for idx_def in expr.indexes:
            idx_sql = self._format_inline_index_mysql(idx_def)
            column_parts.append(idx_sql)

        parts.append(f"({', '.join(column_parts)})")

        if expr.storage_options:
            storage_sql = self._format_storage_options_mysql(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)

        if 'comment' in expr.dialect_options:
            parts.append(f"COMMENT '{expr.dialect_options['comment']}'")

        return ' '.join(parts), tuple(all_params)

    def _format_create_table_like(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement."""
        like_table = expr.dialect_options['like_table']

        parts = ["CREATE TABLE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.table_name))

        if isinstance(like_table, tuple):
            schema, table = like_table
            like_table_str = f"{self.format_identifier(schema)}.{self.format_identifier(table)}"
        else:
            like_table_str = self.format_identifier(like_table)

        parts.append(f"LIKE {like_table_str}")
        return ' '.join(parts), ()

    def _format_column_definition_mysql(
        self,
        col_def,
        ColumnConstraintType
    ) -> Tuple[str, List[Any]]:
        """Format a single column definition with MySQL-specific syntax."""
        parts = [self.format_identifier(col_def.name), col_def.data_type]
        params: List[Any] = []

        constraint_parts = []
        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                constraint_parts.append("PRIMARY KEY")
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                constraint_parts.append("NOT NULL")
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                constraint_parts.append("UNIQUE")
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is not None:
                    constraint_parts.append(f"DEFAULT {constraint.default_value}")
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                constraint_parts.append("NULL")

            if constraint.is_auto_increment:
                constraint_parts.append("AUTO_INCREMENT")

        if constraint_parts:
            parts.append(' '.join(constraint_parts))

        if col_def.comment:
            parts.append(f"COMMENT '{col_def.comment}'")

        return ' '.join(parts), params

    def _format_table_constraint_mysql(
        self,
        t_const,
        TableConstraintType
    ) -> Tuple[str, List[Any]]:
        """Format a table-level constraint."""
        parts = []
        params: List[Any] = []

        if t_const.name:
            parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")

        if t_const.constraint_type == TableConstraintType.PRIMARY_KEY:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.UNIQUE:
            if t_const.columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                parts.append(f"UNIQUE ({cols_str})")
        elif t_const.constraint_type == TableConstraintType.FOREIGN_KEY:
            if t_const.columns and t_const.foreign_key_table and t_const.foreign_key_columns:
                cols_str = ', '.join(self.format_identifier(c) for c in t_const.columns)
                ref_cols_str = ', '.join(self.format_identifier(c) for c in t_const.foreign_key_columns)
                parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {self.format_identifier(t_const.foreign_key_table)} ({ref_cols_str})")

        return ' '.join(parts), params

    def _format_inline_index_mysql(self, idx_def) -> str:
        """Format an inline index definition (MySQL-specific)."""
        parts = []

        if idx_def.unique:
            parts.append("UNIQUE")

        parts.append("INDEX")
        parts.append(self.format_identifier(idx_def.name))

        cols_str = ', '.join(self.format_identifier(c) for c in idx_def.columns)
        parts.append(f"({cols_str})")

        if idx_def.type:
            parts.append(f"USING {idx_def.type}")

        return ' '.join(parts)

    def _format_storage_options_mysql(self, storage_options: Dict[str, Any]) -> str:
        """Format storage options for MySQL.

        Args:
            storage_options: Dict with keys like 'ENGINE', 'DEFAULT CHARSET', 'COLLATE'

        Returns:
            Formatted storage options string (e.g., "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
        """
        parts = []
        for key, value in storage_options.items():
            parts.append(f"{key}={value}")
        return ' '.join(parts)


class MySQLSetTypeMixin:
    """MySQL SET type implementation.

    MySQL SET type features:
    - String object with zero or more values from predefined list
    - Stored as integer (bit flags) internally
    - Maximum 64 members
    - Supports FIND_IN_SET, LIKE operations
    - Automatically sorted on storage

    Version Requirements:
    - All MySQL versions
    """

    def supports_set_type(self) -> bool:
        """MySQL supports SET type in all versions."""
        return True

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

        Raises:
            ValueError: If values exceed 64 members or contain invalid values
        """
        if len(values) > 64:
            raise ValueError("MySQL SET type supports maximum 64 members")

        if column_values is not None:
            invalid_values = [v for v in values if v not in column_values]
            if invalid_values:
                raise ValueError(
                    f"Invalid SET values: {invalid_values}. "
                    f"Allowed values: {column_values}"
                )

        if not values:
            return "'", ()

        sorted_values = sorted(values)
        literal = ','.join(sorted_values)
        return "%s", (literal,)

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
        return f"FIND_IN_SET(%s, {self.format_identifier(set_column)}) > 0", (value,)

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
        conditions = []
        params: List[str] = []

        for value in values:
            conditions.append(f"FIND_IN_SET(%s, {self.format_identifier(column)}) > 0")
            params.append(value)

        return " AND ".join(conditions), tuple(params)


class MySQLJSONFunctionMixin:
    """MySQL JSON function implementation.

    MySQL JSON functions (since 5.7.8+):
    - JSON_EXTRACT: Extract data from JSON documents
    - JSON_UNQUOTE: Unquote JSON value
    - JSON_OBJECT: Create JSON object
    - JSON_ARRAY: Create JSON array
    - JSON_CONTAINS: Check if JSON contains value
    - JSON_SEARCH: Search in JSON
    - JSON_SET: Set value in JSON
    - JSON_INSERT: Insert value into JSON
    - JSON_REPLACE: Replace value in JSON
    - JSON_REMOVE: Remove data from JSON
    - JSON_TYPE: Get type of JSON value
    - JSON_VALID: Validate JSON

    Version Requirements:
    - JSON type and basic functions: MySQL 5.7.8+
    - JSON_MERGE_PATCH: MySQL 8.0.3+
    - JSON_TABLE: MySQL 8.0.4+
    - JSON_VALUE: MySQL 8.0.21+
    """

    # Function version requirements
    _JSON_FUNCTION_VERSIONS = {
        'JSON_TABLE': (8, 0, 4),
        'JSON_VALUE': (8, 0, 21),
        'JSON_SCHEMA_VALID': (8, 0, 17),
        'JSON_MERGE_PATCH': (8, 0, 3),
    }

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported."""
        if function_name in self._JSON_FUNCTION_VERSIONS:
            return self.version >= self._JSON_FUNCTION_VERSIONS[function_name]
        # Basic JSON functions are supported since 5.7.8
        return self.version >= (5, 7, 8)

    def format_json_extract(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function."""
        all_paths = [path]
        if paths:
            all_paths.extend(paths)

        path_placeholders = ', '.join(['%s' for _ in all_paths])
        return f"JSON_EXTRACT({json_doc}, {path_placeholders})", tuple(all_paths)

    def format_json_unquote(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_UNQUOTE function."""
        return f"JSON_UNQUOTE({json_val})", ()

    def format_json_object(
        self,
        key_value_pairs: List[Tuple[str, Any]]
    ) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function."""
        if not key_value_pairs:
            return "JSON_OBJECT()", ()

        parts = []
        params: List[Any] = []

        for key, value in key_value_pairs:
            parts.append('%s')
            parts.append('%s')
            params.append(key)
            params.append(value)

        return f"JSON_OBJECT({', '.join(parts)})", tuple(params)

    def format_json_array(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function."""
        if not values:
            return "JSON_ARRAY()", ()

        placeholders = ', '.join(['%s' for _ in values])
        return f"JSON_ARRAY({placeholders})", tuple(values)

    def format_json_contains(
        self,
        target: str,
        candidate: str,
        path: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function."""
        if path:
            return f"JSON_CONTAINS({target}, %s, %s)", (candidate, path)
        return f"JSON_CONTAINS({target}, %s)", (candidate,)

    def format_json_set(
        self,
        json_doc: str,
        path: str,
        value: Any,
        path_value_pairs: Optional[List[Tuple[str, Any]]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_SET function."""
        all_pairs = [(path, value)]
        if path_value_pairs:
            all_pairs.extend(path_value_pairs)

        parts = []
        params: List[Any] = []

        for p, v in all_pairs:
            parts.append('%s')
            parts.append('%s')
            params.append(p)
            params.append(v)

        return f"JSON_SET({json_doc}, {', '.join(parts)})", tuple(params)

    def format_json_remove(
        self,
        json_doc: str,
        path: str,
        paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_REMOVE function."""
        all_paths = [path]
        if paths:
            all_paths.extend(paths)

        path_placeholders = ', '.join(['%s' for _ in all_paths])
        return f"JSON_REMOVE({json_doc}, {path_placeholders})", tuple(all_paths)

    def format_json_type(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_TYPE function."""
        return f"JSON_TYPE({json_val})", ()

    def format_json_valid(self, json_val: str) -> Tuple[str, tuple]:
        """Format JSON_VALID function."""
        return f"JSON_VALID({json_val})", ()

    def format_json_search(
        self,
        json_doc: str,
        search_str: str,
        path: Optional[str] = None,
        all: bool = False
    ) -> Tuple[str, tuple]:
        """Format JSON_SEARCH function."""
        one_or_all = "'all'" if all else "'one'"
        if path:
            return f"JSON_SEARCH({json_doc}, {one_or_all}, %s, NULL, %s)", (search_str, path)
        return f"JSON_SEARCH({json_doc}, {one_or_all}, %s)", (search_str,)


class MySQLSpatialMixin:
    """MySQL spatial data type implementation.

    MySQL spatial types (since 5.7+):
    - GEOMETRY: Base type for all spatial values
    - POINT: A point in 2D/3D/4D space
    - LINESTRING: A sequence of points forming a line
    - POLYGON: A closed area with one or more rings
    - MULTIPOINT, MULTILINESTRING, MULTIPOLYGON: Collections
    - GEOMETRYCOLLECTION: Heterogeneous collection

    Version Requirements:
    - Basic spatial types: MySQL 5.7+
    - GeoJSON support: MySQL 5.7.5+
    - Improved SRID handling: MySQL 8.0+
    """

    def supports_spatial_type(self, type_name: str) -> bool:
        """Check if specific spatial type is supported."""
        valid_types = {
            'GEOMETRY', 'POINT', 'LINESTRING', 'POLYGON',
            'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON',
            'GEOMETRYCOLLECTION'
        }
        if type_name.upper() not in valid_types:
            return False
        # All spatial types require MySQL 5.7+
        return self.version >= (5, 7, 0)

    def supports_spatial_index(self) -> bool:
        """Whether SPATIAL indexes are supported."""
        return self.version >= (5, 7, 0)

    def supports_geojson(self) -> bool:
        """Whether GeoJSON functions are supported."""
        return self.version >= (5, 7, 5)

    def format_spatial_literal(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format spatial literal from WKT."""
        if srid is not None:
            return f"ST_GeomFromText(%s, %s)", (wkt, srid)
        return f"ST_GeomFromText(%s)", (wkt,)

    def format_st_geom_from_text(
        self,
        wkt: str,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromText function."""
        if srid is not None:
            return f"ST_GeomFromText(%s, %s)", (wkt, srid)
        return f"ST_GeomFromText(%s)", (wkt,)

    def format_st_geom_from_wkb(
        self,
        wkb: bytes,
        srid: Optional[int] = None
    ) -> Tuple[str, tuple]:
        """Format ST_GeomFromWKB function."""
        if srid is not None:
            return f"ST_GeomFromWKB(%s, %s)", (wkb, srid)
        return f"ST_GeomFromWKB(%s)", (wkb,)

    def format_st_as_text(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsText function."""
        return f"ST_AsText({geom})", ()

    def format_st_as_geojson(self, geom: str) -> Tuple[str, tuple]:
        """Format ST_AsGeoJSON function (MySQL 5.7.5+)."""
        if not self.supports_geojson():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "GeoJSON functions (requires MySQL 5.7.5+)")
        return f"ST_AsGeoJSON({geom})", ()

    def format_st_distance(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Distance function."""
        return f"ST_Distance({geom1}, {geom2})", ()

    def format_st_within(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Within function."""
        return f"ST_Within({geom1}, {geom2})", ()

    def format_st_contains(
        self,
        geom1: str,
        geom2: str
    ) -> Tuple[str, tuple]:
        """Format ST_Contains function."""
        return f"ST_Contains({geom1}, {geom2})", ()

    def format_create_spatial_index(
        self,
        index_name: str,
        table_name: str,
        column: str
    ) -> Tuple[str, tuple]:
        """Format CREATE SPATIAL INDEX statement."""
        if not self.supports_spatial_index():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "SPATIAL indexes (requires MySQL 5.7+)")
        return (
            f"CREATE SPATIAL INDEX {self.format_identifier(index_name)} "
            f"ON {self.format_identifier(table_name)} "
            f"({self.format_identifier(column)})",
            ()
        )


class MySQLVectorMixin:
    """MySQL vector data type implementation.

    MySQL VECTOR type (since 9.0+) features:
    - Multi-dimensional vector storage for AI/ML applications
    - Similarity search with distance functions
    - Maximum 16,384 dimensions
    - Binary storage format for optimized operations
    - VECTOR indexes for fast similarity search

    Version Requirements:
    - VECTOR type: MySQL 9.0+
    - VECTOR indexes: MySQL 9.0.1+
    """

    # Maximum dimension supported by MySQL 9.0
    MAX_VECTOR_DIMENSION = 16384

    def supports_vector_type(self) -> bool:
        """VECTOR type is supported since MySQL 9.0."""
        return self.version >= (9, 0, 0)

    def supports_vector_index(self) -> bool:
        """VECTOR indexes are supported since MySQL 9.0.1."""
        return self.version >= (9, 0, 1)

    def get_max_vector_dimension(self) -> int:
        """Get maximum supported vector dimension."""
        return self.MAX_VECTOR_DIMENSION

    def format_vector_literal(
        self,
        values: List[float]
    ) -> Tuple[str, tuple]:
        """Format VECTOR literal value.

        Args:
            values: List of float values representing the vector

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if len(values) > self.MAX_VECTOR_DIMENSION:
            raise ValueError(
                f"Vector dimension {len(values)} exceeds maximum "
                f"supported dimension {self.MAX_VECTOR_DIMENSION}"
            )
        # Use STRING_TO_VECTOR for literal creation
        vector_str = '[' + ','.join(str(v) for v in values) + ']'
        return "STRING_TO_VECTOR(%s)", (vector_str,)

    def format_string_to_vector(
        self,
        vector_str: str
    ) -> Tuple[str, tuple]:
        """Format STRING_TO_VECTOR function.

        Args:
            vector_str: String representation of vector (e.g., '[1.0,2.0,3.0]')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return "STRING_TO_VECTOR(%s)", (vector_str,)

    def format_vector_to_string(
        self,
        vector_col: str
    ) -> Tuple[str, tuple]:
        """Format VECTOR_TO_STRING function.

        Args:
            vector_col: VECTOR column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"VECTOR_TO_STRING({vector_col})", ()

    def format_vector_dim(
        self,
        vector_col: str
    ) -> Tuple[str, tuple]:
        """Format VECTOR_DIM function.

        Args:
            vector_col: VECTOR column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"VECTOR_DIM({vector_col})", ()

    def format_distance_euclidean(
        self,
        vector1: str,
        vector2: str
    ) -> Tuple[str, tuple]:
        """Format DISTANCE_EUCLIDEAN function.

        Args:
            vector1: First vector (column or literal)
            vector2: Second vector (column or literal)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"DISTANCE_EUCLIDEAN({vector1}, {vector2})", ()

    def format_distance_cosine(
        self,
        vector1: str,
        vector2: str
    ) -> Tuple[str, tuple]:
        """Format DISTANCE_COSINE function.

        Args:
            vector1: First vector (column or literal)
            vector2: Second vector (column or literal)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"DISTANCE_COSINE({vector1}, {vector2})", ()

    def format_distance_dot(
        self,
        vector1: str,
        vector2: str
    ) -> Tuple[str, tuple]:
        """Format DISTANCE_DOT function.

        Args:
            vector1: First vector (column or literal)
            vector2: Second vector (column or literal)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return f"DISTANCE_DOT({vector1}, {vector2})", ()

    def format_create_vector_index(
        self,
        index_name: str,
        table_name: str,
        column: str
    ) -> Tuple[str, tuple]:
        """Format CREATE VECTOR INDEX statement.

        Note: MySQL uses CREATE INDEX with VECTOR keyword, not CREATE VECTOR INDEX.

        Args:
            index_name: Name of the vector index
            table_name: Name of the table
            column: VECTOR column name

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if not self.supports_vector_index():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(self.name, "VECTOR indexes (requires MySQL 9.0.1+)")
        # MySQL 9.0.1+ syntax for vector index
        return (
            f"CREATE VECTOR INDEX {self.format_identifier(index_name)} "
            f"ON {self.format_identifier(table_name)} "
            f"({self.format_identifier(column)})",
            ()
        )
