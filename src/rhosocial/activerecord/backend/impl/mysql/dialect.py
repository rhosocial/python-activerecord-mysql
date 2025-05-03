import logging
from enum import Enum
from typing import Any, Set, Optional, Tuple, Union, List, Dict

from ...dialect import (
    SQLBuilder,
    SQLExpressionBase, SQLDialectBase, ReturningClauseHandler, ExplainOptions, ExplainType, ExplainFormat,
    AggregateHandler, JsonOperationHandler, CTEHandler
)
from ...errors import ReturningNotSupportedError, GroupingSetNotSupportedError, \
    JsonOperationNotSupportedError, WindowFunctionNotSupportedError, CTENotSupportedError
from ...typing import ConnectionConfig


class MySQLExpression(SQLExpressionBase):
    """MySQL expression implementation"""

    def format(self, dialect: SQLDialectBase) -> str:
        """Format MySQL expression"""
        return self.expression

class MySQLReturningHandler(ReturningClauseHandler):
    """MySQL RETURNING clause handler implementation"""

    def __init__(self, version: tuple):
        """
        Initialize MySQL RETURNING handler with version information.

        Args:
            version: MySQL version tuple (major, minor, patch)
        """
        self._version = version

    @property
    def is_supported(self) -> bool:
        """
        Check if RETURNING clause is supported.

        Note: MySQL does not support RETURNING clause natively in any version.
        The implementation must use alternative approaches like SELECT after DML.

        Returns:
            bool: Always False for MySQL
        """
        # MySQL does not support RETURNING in any version
        return False

    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """
        Format RETURNING clause.

        Always raises ReturningNotSupportedError as MySQL doesn't support RETURNING.

        Args:
            columns: Column names to return (ignored)

        Returns:
            str: Never returns

        Raises:
            ReturningNotSupportedError: Always raised
        """
        # MySQL does not support RETURNING
        raise ReturningNotSupportedError(
            "RETURNING clause is not supported by MySQL. This is a fundamental "
            "limitation of the database engine, not a driver issue."
        )

    def format_advanced_clause(self,
                               columns: Optional[List[str]] = None,
                               expressions: Optional[List[Dict[str, Any]]] = None,
                               aliases: Optional[Dict[str, str]] = None,
                               dialect_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Format advanced RETURNING clause for MySQL.

        Always raises ReturningNotSupportedError as MySQL doesn't support RETURNING.

        If force=True is set in dialect_options, this may attempt to use alternative
        approaches like SELECT LAST_INSERT_ID() or using session variables, but
        these are not equivalent to true RETURNING clause functionality.

        Args:
            columns: List of column names to return (ignored)
            expressions: List of expressions to return (ignored)
            aliases: Dictionary mapping column/expression names to aliases (ignored)
            dialect_options: MySQL-specific options

        Returns:
            str: Never returns

        Raises:
            ReturningNotSupportedError: Always raised unless alternatives implemented
        """
        # Check if we should try alternative approaches
        if dialect_options and dialect_options.get("emulation_strategy") == "select_after":
            # This would require storing table name and conditions for a follow-up SELECT
            # Not fully implemented as this requires significant changes to execute flow
            table_name = dialect_options.get("table_name")
            where_clause = dialect_options.get("where_clause")

            self._emulation_info = {
                "strategy": "select_after",
                "table": table_name,
                "where": where_clause,
                "columns": columns or ["*"]
            }

            # Return empty string as this would be applied separately
            return ""

        # Default behavior: not supported
        raise ReturningNotSupportedError(
            "RETURNING clause is not supported by MySQL. Consider using alternative "
            "approaches like SELECT after INSERT/UPDATE/DELETE or session variables."
        )

    def supports_feature(self, feature: str) -> bool:
        """
        Check if a specific RETURNING feature is supported by MySQL.

        No RETURNING features are natively supported by MySQL.

        Args:
            feature: Feature name

        Returns:
            bool: Always False for MySQL
        """
        # MySQL doesn't support any RETURNING features
        return False

    def get_emulation_strategy(self) -> Optional[Dict[str, Any]]:
        """
        Get information about RETURNING emulation strategy.

        This is used when RETURNING is forced with emulation_strategy in dialect_options.

        Returns:
            Optional[Dict[str, Any]]: Emulation strategy information or None
        """
        return getattr(self, "_emulation_info", None)

# Add driver type enum
class DriverType(Enum):
    MYSQL_CONNECTOR = "mysql-connector"
    PYMYSQL = "pymysql"
    MYSQLCLIENT = "mysqlclient"
    MYSQL_PYTHON = "mysql-python"  # Legacy

# Version boundary constants
MYSQL_5_6_5 = (5, 6, 5)   # JSON format introduced
MYSQL_5_7_0 = (5, 7, 0)   # EXTENDED/PARTITIONS deprecated, FOR CONNECTION added
MYSQL_8_0_0 = (8, 0, 0)   # MySQL 8 base version
MYSQL_8_0_13 = (8, 0, 13) # ANALYZE supported but only with TREE format
MYSQL_8_0_16 = (8, 0, 16) # TREE format introduced
MYSQL_8_0_18 = (8, 0, 18) # Full ANALYZE support
MYSQL_8_3_0 = (8, 3, 0)   # JSON format version 2 support

def _is_version_at_least(current_version, required_version):
    """Check if current version is at least the required version"""
    return current_version >= required_version


class MySQLJsonHandler(JsonOperationHandler):
    """MySQL-specific implementation of JSON operations."""

    def __init__(self, version: tuple):
        """Initialize handler with MySQL version info.

        Args:
            version: MySQL version as (major, minor, patch) tuple
        """
        self._version = version

        # Cache capability detection results
        self._json_supported = None
        self._arrows_supported = None
        self._function_support = {}

    @property
    def supports_json_operations(self) -> bool:
        """Check if MySQL version supports JSON operations.

        MySQL supports JSON from version 5.7.8

        Returns:
            bool: True if JSON operations are supported
        """
        if self._json_supported is None:
            self._json_supported = self._version >= (5, 7, 8)
        return self._json_supported

    @property
    def supports_json_arrows(self) -> bool:
        """Check if MySQL version supports -> and ->> operators.

        MySQL added -> operator in version 5.7.8
        MySQL added ->> operator in version 5.7.13

        Returns:
            bool: True if JSON arrow operators are supported
        """
        if self._arrows_supported is None:
            self._arrows_supported = self._version >= (5, 7, 13)
        return self._arrows_supported

    def format_json_operation(self,
                              column: Union[str, Any],
                              path: Optional[str] = None,
                              operation: str = "extract",
                              value: Any = None,
                              alias: Optional[str] = None) -> str:
        """Format JSON operation according to MySQL syntax.

        This method converts abstract JSON operations into MySQL-specific syntax,
        handling version differences and using alternatives for unsupported functions.

        Args:
            column: JSON column name or expression
            path: JSON path (e.g. '$.name')
            operation: Operation type (extract, text, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            str: Formatted MySQL JSON operation

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported by MySQL version
        """
        if not self.supports_json_operations:
            raise JsonOperationNotSupportedError(
                f"JSON operations are not supported in MySQL {'.'.join(map(str, self._version))}"
            )

        # Handle column formatting
        col = str(column)

        # Default path handling
        if not path:
            path = "$"  # Root path if none provided
        elif not path.startswith('$'):
            path = f"$.{path}"  # Auto-prefix with root if not already

        # Use shorthand operators if available for extract operations
        if self.supports_json_arrows:
            if operation == "extract":
                expr = f"{col}->{path}"
                return f"{expr} as {alias}" if alias else expr
            elif operation == "text":
                expr = f"{col}->>{path}"
                return f"{expr} as {alias}" if alias else expr

        # Function-based approach
        if operation == "extract":
            expr = f"JSON_EXTRACT({col}, '{path}')"

        elif operation == "text":
            if self._version >= (5, 7, 13):  # JSON_UNQUOTE added in 5.7.13
                expr = f"JSON_UNQUOTE(JSON_EXTRACT({col}, '{path}'))"
            else:
                # Fallback for older versions
                expr = f"CAST(JSON_EXTRACT({col}, '{path}') AS CHAR)"

        elif operation == "contains":
            # Check if path contains value
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_CONTAINS({col}, '{json_value}', '{path}')"
            elif isinstance(value, str):
                expr = f"JSON_CONTAINS({col}, '\"{value}\"', '{path}')"
            else:
                # For numeric/boolean comparison
                expr = f"JSON_CONTAINS({col}, '{value}', '{path}')"

        elif operation == "exists":
            expr = f"JSON_CONTAINS_PATH({col}, 'one', '{path}')"

        elif operation == "type":
            expr = f"JSON_TYPE(JSON_EXTRACT({col}, '{path}'))"

        elif operation == "remove":
            expr = f"JSON_REMOVE({col}, '{path}')"

        elif operation == "insert":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_INSERT({col}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                expr = f"JSON_INSERT({col}, '{path}', '\"{value}\"')"
            else:
                expr = f"JSON_INSERT({col}, '{path}', {value})"

        elif operation == "replace":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_REPLACE({col}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                expr = f"JSON_REPLACE({col}, '{path}', '\"{value}\"')"
            else:
                expr = f"JSON_REPLACE({col}, '{path}', {value})"

        elif operation == "set":
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                expr = f"JSON_SET({col}, '{path}', CAST('{json_value}' AS JSON))"
            elif isinstance(value, str):
                expr = f"JSON_SET({col}, '{path}', '\"{value}\"')"
            else:
                expr = f"JSON_SET({col}, '{path}', {value})"

        elif operation == "array_length":
            expr = f"JSON_LENGTH(JSON_EXTRACT({col}, '{path}'))"

        elif operation == "keys":
            expr = f"JSON_KEYS(JSON_EXTRACT({col}, '{path}'))"

        else:
            # Default to extract if operation not recognized
            expr = f"JSON_EXTRACT({col}, '{path}')"

        if alias:
            return f"{expr} as {alias}"
        return expr

    def supports_json_function(self, function_name: str) -> bool:
        """Check if specific JSON function is supported in this MySQL version.

        Args:
            function_name: Name of JSON function to check (e.g., "json_extract")

        Returns:
            bool: True if function is supported
        """
        # Cache results for performance
        if function_name in self._function_support:
            return self._function_support[function_name]

        # All functions require JSON support
        if not self.supports_json_operations:
            self._function_support[function_name] = False
            return False

        # Define version requirements for each function
        function_versions = {
            # Core JSON functions available since 5.7.8
            "json_extract": (5, 7, 8),
            "json_insert": (5, 7, 8),
            "json_replace": (5, 7, 8),
            "json_set": (5, 7, 8),
            "json_remove": (5, 7, 8),
            "json_type": (5, 7, 8),
            "json_valid": (5, 7, 8),
            "json_quote": (5, 7, 8),
            "json_contains": (5, 7, 8),
            "json_contains_path": (5, 7, 8),
            "json_array": (5, 7, 8),
            "json_object": (5, 7, 8),
            "json_array_length": (5, 7, 8),
            "json_array_append": (5, 7, 8),
            "json_array_insert": (5, 7, 8),
            "json_depth": (5, 7, 8),
            "json_keys": (5, 7, 8),
            "json_length": (5, 7, 8),
            "json_merge": (5, 7, 8),
            "json_merge_patch": (5, 7, 9),
            "json_merge_preserve": (5, 7, 9),
            "json_pretty": (5, 7, 22),
            "json_search": (5, 7, 8),

            # Arrow operators
            "->": (5, 7, 8),  # Added in 5.7.8
            "->>": (5, 7, 13)  # Added in 5.7.13
        }

        # Check if function is supported based on version
        required_version = function_versions.get(function_name.lower())
        if required_version:
            is_supported = self._version >= required_version
        else:
            # Unknown function, assume not supported
            is_supported = False

        # Cache result
        self._function_support[function_name] = is_supported
        return is_supported


class MySQLCTEHandler(CTEHandler):
    """MySQL-specific CTE handler."""

    def __init__(self, version: tuple):
        self._version = version

    @property
    def is_supported(self) -> bool:
        # CTEs are supported in MySQL 8.0+
        return self._version >= (8, 0, 0)

    @property
    def supports_recursive(self) -> bool:
        return self.is_supported

    @property
    def supports_cte_in_dml(self) -> bool:
        return self.is_supported

    @property
    def supports_materialized_hint(self) -> bool:
        """Check if MATERIALIZED/NOT MATERIALIZED hints are supported.

        MySQL does not support materialization hints.

        Returns:
            bool: Always False for MySQL
        """
        return False

    @property
    def supports_compound_recursive(self) -> bool:
        """Check if compound queries in recursive CTEs are supported.

        MySQL supports compound queries in recursive CTEs since version 8.0.

        Returns:
            bool: True if MySQL version is 8.0 or higher
        """
        return self.is_supported

    @property
    def supports_multiple_ctes(self) -> bool:
        """Check if multiple CTEs can be defined in a single query.

        MySQL supports multiple CTEs since version 8.0.

        Returns:
            bool: True if MySQL version is 8.0 or higher
        """
        return self.is_supported

    def format_cte(self,
                   name: str,
                   query: str,
                   columns: Optional[List[str]] = None,
                   recursive: bool = False,
                   materialized: Optional[bool] = None) -> str:
        """Format MySQL CTE."""
        if not self.is_supported:
            raise CTENotSupportedError("CTEs not supported in MySQL versions before 8.0")

        name = self.validate_cte_name(name)

        # Add column definitions if provided
        column_def = ""
        if columns:
            column_def = f"({', '.join(columns)})"

        # MySQL doesn't support materialization hints
        if materialized is not None:
            logging.warning("Materialization hints not supported in MySQL, ignoring")

        return f"{name}{column_def} AS ({query})"

    def format_with_clause(self,
                           ctes: List[Dict[str, Any]],
                           recursive: bool = False) -> str:
        """Format MySQL WITH clause."""
        if not self.is_supported:
            raise CTENotSupportedError("CTEs not supported in MySQL versions before 8.0")

        if not ctes:
            return ""

        # MySQL requires RECURSIVE keyword if any CTE is recursive
        any_recursive = recursive or any(cte.get('recursive', False) for cte in ctes)
        recursive_keyword = "RECURSIVE " if any_recursive else ""

        formatted_ctes = []
        for cte in ctes:
            formatted_ctes.append(self.format_cte(
                name=cte['name'],
                query=cte['query'],
                columns=cte.get('columns'),
                recursive=cte.get('recursive', False),
                materialized=cte.get('materialized')
            ))

        return f"WITH {recursive_keyword}{', '.join(formatted_ctes)}"


class MySQLDialect(SQLDialectBase):
    """MySQL dialect implementation"""

    def __init__(self, config: ConnectionConfig):
        """Initialize MySQL dialect

        Args:
            config: Database connection configuration
        """
        # Parse version string like "8.0.26" into tuple (8, 0, 26)
        # version_str = getattr(config, 'version', '8.0.0')
        # version = tuple(map(int, version_str.split('.')))

        # Use a default version initially
        # The actual version will be updated by the backend after connection

        version = getattr(config, 'version', (8, 0, 0))
        super().__init__(version)

        if hasattr(config, 'driver_type') and config.driver_type:
            self._driver_type = config.driver_type
        else:
            self._driver_type = DriverType.MYSQL_CONNECTOR

        # Initialize handlers
        self._returning_handler = MySQLReturningHandler(version)
        self._aggregate_handler = MySQLAggregateHandler(version)  # Initialize aggregate handler
        self._json_operation_handler = MySQLJsonHandler(version)  # Initialize JSON handler
        self._cte_handler = MySQLCTEHandler(version)

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format MySQL expression"""
        if not isinstance(expr, MySQLExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get MySQL parameter placeholder"""
        return "%s"

    def format_string_literal(self, value: str) -> str:
        """Quote string literal

        MySQL uses single quotes for string literals
        """
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    def format_identifier(self, identifier: str) -> str:
        """Quote identifier (table/column name)

        MySQL uses backticks for identifiers
        """
        if '`' in identifier:
            escaped = identifier.replace('`', '``')
            return f"`{escaped}`"
        return f"`{identifier}`"

    def format_limit_offset(self, limit: Optional[int] = None,
                            offset: Optional[int] = None) -> str:
        """Format LIMIT and OFFSET clause

        MySQL requires LIMIT when using OFFSET
        """
        if limit is None and offset is not None:
            return f"LIMIT 18446744073709551615 OFFSET {offset}"  # MySQL maximum value
        elif limit is not None:
            if offset is not None:
                return f"LIMIT {limit} OFFSET {offset}"
            return f"LIMIT {limit}"
        return ""

    def get_parameter_placeholder(self, position: int) -> str:
        """Get MySQL parameter placeholder

        MySQL uses %s for all parameters regardless of position
        """
        if self._driver_type in (DriverType.MYSQL_CONNECTOR, DriverType.PYMYSQL, DriverType.MYSQLCLIENT):
            return "%s"
        elif self._driver_type == DriverType.MYSQL_PYTHON:
            return "?"

        # Default to %s as it's most widely supported
        return "%s"


    def format_like_pattern(self, pattern: str) -> str:
        """Format LIKE pattern by escaping % characters

        Args:
            pattern: Original LIKE pattern

        Returns:
            str: Escaped pattern
        """
        return pattern.replace("%", "%%")

    def format_explain(self, sql: str, options: Optional[ExplainOptions] = None) -> str:
        """Format MySQL EXPLAIN statement according to dialect rules and version support

        Args:
            sql: SQL to explain
            options: Configuration for EXPLAIN output
                    Defaults are database-appropriate if not specified

        Returns:
            str: Formatted EXPLAIN statement

        Raises:
            ValueError: If an unsupported format or combination is requested
        """
        if not options:
            options = ExplainOptions()

        # Get version components for feature detection
        current_version = self.version

        # Start with basic EXPLAIN
        parts = ["EXPLAIN"]

        # Handle ANALYZE option
        if options.type == ExplainType.ANALYZE:
            if _is_version_at_least(current_version, MYSQL_8_0_18):
                # 8.0.18+ fully supports ANALYZE
                parts.append("ANALYZE")
            elif _is_version_at_least(current_version, MYSQL_8_0_13):
                # 8.0.13-8.0.17 only supports ANALYZE with TREE format
                parts.append("ANALYZE")

                # Check if TREE format is needed but not requested
                if options.format != ExplainFormat.TREE:
                    if options.format == ExplainFormat.JSON:
                        # If JSON format was requested but TREE is required, raise an error
                        raise ValueError(
                            "MySQL 8.0.13-8.0.17 only supports TREE format with EXPLAIN ANALYZE"
                        )
                    # Force TREE format for ANALYZE in MySQL 8.0.13-8.0.17
                    options.format = ExplainFormat.TREE
            else:
                # Not supported in this version
                major, minor, patch = current_version
                raise ValueError(
                    f"EXPLAIN ANALYZE requires MySQL 8.0.13+. Current version: {major}.{minor}.{patch}"
                )

        # Handle verbose (EXTENDED) option - deprecated in 5.7+
        if options.verbose:
            if _is_version_at_least(current_version, MYSQL_5_7_0):
                # In 5.7+, EXTENDED is deprecated but information is included by default
                # No need to add anything, just add a warning comment
                parts.append("/* Note: EXTENDED option is deprecated in MySQL 5.7+ */")
            elif _is_version_at_least(current_version, (5, 6, 0)):
                # In 5.6.x, EXTENDED is still a valid keyword
                parts[0] = "EXPLAIN EXTENDED"

        # Handle PARTITIONS option - deprecated in 5.7+
        if getattr(options, 'partitions', False):
            if _is_version_at_least(current_version, MYSQL_5_7_0):
                # In 5.7+, PARTITIONS is deprecated but information is included by default
                # No need to add anything, just add a warning comment
                parts.append("/* Note: PARTITIONS option is deprecated in MySQL 5.7+ */")
            elif _is_version_at_least(current_version, (5, 1, 0)):
                # In 5.1.x-5.6.x, PARTITIONS is a valid keyword
                parts[0] = "EXPLAIN PARTITIONS"

        # Handle FORMAT option
        if options.format != ExplainFormat.TEXT:
            if options.format == ExplainFormat.JSON:
                if _is_version_at_least(current_version, MYSQL_5_6_5):
                    # Handle JSON format version 2 in MySQL 8.3+
                    if _is_version_at_least(current_version, MYSQL_8_3_0):
                        json_version = getattr(options, 'json_version', 1)
                        if json_version == 2:
                            # Need to set system variable separately
                            parts.append("/* SET explain_json_format_version = 2 before executing this */")

                    parts.append("FORMAT=JSON")
                else:
                    major, minor, patch = current_version
                    raise ValueError(f"JSON format requires MySQL 5.6.5+. Current version: {major}.{minor}.{patch}")

            elif options.format == ExplainFormat.TREE:
                if _is_version_at_least(current_version, MYSQL_8_0_16):
                    parts.append("FORMAT=TREE")
                else:
                    major, minor, patch = current_version
                    raise ValueError(f"TREE format requires MySQL 8.0.16+. Current version: {major}.{minor}.{patch}")

            else:
                # Unsupported format
                major, minor, patch = current_version
                supported_formats = ["TEXT"]

                if _is_version_at_least(current_version, MYSQL_5_6_5):
                    supported_formats.append("JSON")

                if _is_version_at_least(current_version, MYSQL_8_0_16):
                    supported_formats.append("TREE")

                raise ValueError(
                    f"Unsupported EXPLAIN format: {options.format}. "
                    f"MySQL {major}.{minor}.{patch} supports: {', '.join(supported_formats)}"
                )

        # Handle FOR CONNECTION (MySQL 5.7+)
        if _is_version_at_least(current_version, MYSQL_5_7_0):
            connection_id = getattr(options, 'connection_id', None)
            if connection_id is not None:
                return f"EXPLAIN FOR CONNECTION {connection_id}"

        # Add the SQL to explain
        parts.append(sql)
        return " ".join(parts)

    @property
    def supported_formats(self) -> Set[ExplainFormat]:
        """Get supported EXPLAIN output formats for current MySQL version

        Returns:
            Set[ExplainFormat]: Set of supported formats
        """
        current_version = self._version

        # All versions support TEXT format
        formats = {ExplainFormat.TEXT}

        # MySQL 5.6.5+ supports JSON format
        if _is_version_at_least(current_version, MYSQL_5_6_5):
            formats.add(ExplainFormat.JSON)

        # MySQL 8.0.16+ supports TREE format
        if _is_version_at_least(current_version, MYSQL_8_0_16):
            formats.add(ExplainFormat.TREE)

        return formats

    def create_expression(self, expression: str) -> MySQLExpression:
        """Create MySQL expression"""
        return MySQLExpression(expression)

class MySQLSQLBuilder(SQLBuilder):
    """MySQL specific SQL Builder

    Extends the base SQLBuilder to handle MySQL's %s placeholder syntax
    instead of the default ? placeholder.
    """

    def __init__(self, dialect: SQLDialectBase):
        """Initialize MySQL SQL builder

        Args:
            dialect: MySQL dialect instance
        """
        super().__init__(dialect)

    def build(self, sql: str, params: Optional[Union[Tuple, List, Dict]] = None) -> Tuple[str, Tuple]:
        """Build SQL statement with parameters for MySQL

        All percent sign placeholders (%s) in the SQL statement are treated as parameter
        placeholders and must have corresponding parameters. Note that any literal %
        characters in the query must be escaped as %%.

        Args:
            sql: SQL statement with %s placeholders
            params: Parameter values

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)

        Raises:
            ValueError: If parameter count doesn't match placeholder count
        """
        if not params:
            return sql, ()

        # Convert params to tuple if needed
        if isinstance(params, (list, dict)):
            params = tuple(params)

        # First pass: collect information about parameters
        final_params = []
        expr_positions = {}  # Maps original position to expression
        param_count = 0

        for i, param in enumerate(params):
            if isinstance(param, SQLExpressionBase):
                expr_positions[i] = self.dialect.format_expression(param)
            else:
                final_params.append(param)
                param_count += 1

        # Second pass: build SQL with correct placeholders
        result = []
        current_pos = 0
        param_position = 0  # Counter for regular parameters
        placeholder_count = 0  # Total placeholder counter

        while True:
            # Find next placeholder (for MySQL it's %s)
            placeholder_pos = sql.find('%s', current_pos)
            if placeholder_pos == -1:
                # No more placeholders, add remaining SQL
                result.append(sql[current_pos:])
                break

            # Add SQL up to placeholder
            result.append(sql[current_pos:placeholder_pos])

            # Check if this position corresponds to an expression
            if placeholder_count in expr_positions:
                # Add the formatted expression
                result.append(expr_positions[placeholder_count])
            else:
                # Add a parameter placeholder with correct position
                result.append(self.dialect.get_parameter_placeholder(param_position))
                param_position += 1

            current_pos = placeholder_pos + 2  # Skip '%s'
            placeholder_count += 1

        # Verify parameter count
        if placeholder_count != len(params):
            raise ValueError(
                f"Parameter count mismatch: SQL needs {placeholder_count} "
                f"parameters but {len(params)} were provided"
            )

        return ''.join(result), tuple(final_params)


class MySQLAggregateHandler(AggregateHandler):
    """MySQL-specific aggregate functionality handler."""

    # MySQL version constants
    MYSQL_5_7_0 = (5, 7, 0)  # Basic window functions support
    MYSQL_8_0_0 = (8, 0, 0)  # Full window function support
    MYSQL_8_0_2 = (8, 0, 2)  # Advanced window frame support

    def __init__(self, version: tuple):
        """Initialize with MySQL version.

        Args:
            version: MySQL version tuple (major, minor, patch)
        """
        super().__init__(version)

    @property
    def supports_window_functions(self) -> bool:
        """Check if MySQL supports window functions.

        MySQL supports window functions from version 8.0.0
        MariaDB supports window functions from version 10.2.0
        """
        return self._version >= self.MYSQL_8_0_0

    @property
    def supports_json_operations(self) -> bool:
        """Check if MySQL supports JSON operations.

        MySQL supports JSON since version 5.7.8
        """
        return self._version >= (5, 7, 8)

    @property
    def supports_advanced_grouping(self) -> bool:
        """Check if MySQL supports advanced grouping.

        MySQL supports ROLLUP but not CUBE or GROUPING SETS.
        """
        return True  # MySQL supports WITH ROLLUP syntax

    def format_window_function(self,
                               expr: str,
                               partition_by: Optional[List[str]] = None,
                               order_by: Optional[List[str]] = None,
                               frame_type: Optional[str] = None,
                               frame_start: Optional[str] = None,
                               frame_end: Optional[str] = None,
                               exclude_option: Optional[str] = None) -> str:
        """Format window function SQL for MySQL.

        Args:
            expr: Base expression for window function
            partition_by: PARTITION BY columns
            order_by: ORDER BY columns
            frame_type: Window frame type (ROWS/RANGE only, GROUPS not supported)
            frame_start: Frame start specification
            frame_end: Frame end specification
            exclude_option: Frame exclusion option (not supported in MySQL)

        Returns:
            str: Formatted window function SQL

        Raises:
            WindowFunctionNotSupportedError: If window functions not supported or using unsupported features
        """
        if not self.supports_window_functions:
            raise WindowFunctionNotSupportedError(
                f"Window functions not supported in MySQL {'.'.join(map(str, self._version))}. "
                f"Requires MySQL 8.0.0 or higher."
            )

        window_parts = []

        if partition_by:
            window_parts.append(f"PARTITION BY {', '.join(partition_by)}")

        if order_by:
            window_parts.append(f"ORDER BY {', '.join(order_by)}")

        # Build frame clause
        frame_clause = []
        if frame_type:
            if frame_type == "GROUPS" and self._version < self.MYSQL_8_0_2:
                raise WindowFunctionNotSupportedError(
                    f"GROUPS frame type requires MySQL 8.0.2 or higher. Current version: {'.'.join(map(str, self._version))}"
                )

            frame_clause.append(frame_type)

            if frame_start:
                if frame_end:
                    frame_clause.append(f"BETWEEN {frame_start} AND {frame_end}")
                else:
                    frame_clause.append(frame_start)

        if frame_clause:
            window_parts.append(" ".join(frame_clause))

        if exclude_option:
            raise WindowFunctionNotSupportedError("EXCLUDE options not supported in MySQL")

        window_clause = " ".join(window_parts)
        return f"{expr} OVER ({window_clause})"

    def format_json_operation(self,
                              column: str,
                              path: str,
                              operation: str = "extract",
                              value: Any = None) -> str:
        """Format JSON operation SQL for MySQL.

        Args:
            column: JSON column name
            path: JSON path string
            operation: Operation type (extract, contains, exists)
            value: Value for contains operation

        Returns:
            str: Formatted JSON operation SQL

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported
            ValueError: For unsupported operations
        """
        if not self.supports_json_operations:
            raise JsonOperationNotSupportedError(
                f"JSON operations not supported in MySQL {'.'.join(map(str, self._version))}. "
                f"Requires MySQL 5.7.8 or higher."
            )

        # MySQL uses JSON_EXTRACT, JSON_CONTAINS, etc.
        if operation == "extract":
            return f"JSON_EXTRACT({column}, '{path}')"
        elif operation == "contains":
            if value is None:
                raise ValueError("Value is required for 'contains' operation")

            # For JSON value comparison
            if isinstance(value, (dict, list)):
                # Convert to JSON string
                import json
                json_value = json.dumps(value)
                return f"JSON_CONTAINS({column}, '{json_value}', '{path}')"
            elif isinstance(value, str):
                return f"JSON_CONTAINS({column}, '\"{value}\"', '{path}')"
            else:
                # For numeric/boolean comparison
                return f"JSON_CONTAINS({column}, '{value}', '{path}')"
        elif operation == "exists":
            return f"JSON_CONTAINS_PATH({column}, 'one', '{path}')"
        else:
            raise ValueError(f"Unsupported JSON operation: {operation}")

    def format_grouping_sets(self,
                             type_name: str,
                             columns: List[Union[str, List[str]]]) -> str:
        """Format grouping sets SQL for MySQL.

        MySQL only supports ROLLUP with different syntax: GROUP BY col1, col2 WITH ROLLUP

        Args:
            type_name: Grouping type (CUBE, ROLLUP, GROUPING SETS)
            columns: Columns to group by

        Raises:
            GroupingSetNotSupportedError: If grouping type not supported in MySQL
        """
        if type_name == "ROLLUP":
            # MySQL uses different syntax for ROLLUP
            if isinstance(columns[0], list):
                # Flatten nested lists
                flat_columns = []
                for col_group in columns:
                    if isinstance(col_group, list):
                        flat_columns.extend(col_group)
                    else:
                        flat_columns.append(col_group)

                return f"{', '.join(flat_columns)} WITH ROLLUP"
            else:
                return f"{', '.join(columns)} WITH ROLLUP"
        elif type_name in ("CUBE", "GROUPING SETS"):
            raise GroupingSetNotSupportedError(
                f"{type_name} not supported in MySQL. Only ROLLUP is available using WITH ROLLUP syntax."
            )
        else:
            raise GroupingSetNotSupportedError(f"Unknown grouping type: {type_name}")