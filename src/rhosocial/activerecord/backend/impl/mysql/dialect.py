import uuid
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Any, Set, Optional, Tuple, Union, List, Dict

from .types import MYSQL_TYPE_MAPPINGS
from ...dialect import (
    TypeMapper, ValueMapper, DatabaseType, SQLBuilder,
    SQLExpressionBase, SQLDialectBase, ReturningClauseHandler, ExplainOptions, ExplainType, ExplainFormat
)
from ...errors import TypeConversionError, ReturningNotSupportedError
from ...helpers import (
    safe_json_dumps, parse_datetime, convert_datetime,
    array_converter, safe_json_loads
)
from ...typing import ConnectionConfig

class MySQLTypeMapper(TypeMapper):
    """MySQL type mapper implementation"""

    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get MySQL column type definition

        Args:
            db_type: Generic database type
            **params: Type parameters (length, precision, etc.)

        Returns:
            str: MySQL column type definition

        Raises:
            ValueError: If type is not supported
        """
        if db_type not in MYSQL_TYPE_MAPPINGS:
            raise ValueError(f"Unsupported type: {db_type}")

        mapping = MYSQL_TYPE_MAPPINGS[db_type]
        if mapping.format_func:
            return mapping.format_func(mapping.db_type, params)
        return mapping.db_type

    def get_placeholder(self, db_type: Optional[DatabaseType] = None) -> str:
        """Get parameter placeholder

        Note: MySQL uses %s for all parameter types
        """
        return "%s"

class MySQLValueMapper(ValueMapper):
    """MySQL value mapper implementation"""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        # Define basic type converters
        self._base_converters = {
            int: int,
            float: float,
            Decimal: str,
            bool: lambda x: 1 if x else 0,
            uuid.UUID: str,
            date: lambda x: convert_datetime(x, format="%Y-%m-%d"),
            time: lambda x: convert_datetime(x, format="%H:%M:%S"),
            datetime: lambda x: convert_datetime(x, timezone=self.config.timezone),
            dict: safe_json_dumps,
            list: array_converter,
            tuple: array_converter,
        }

        # Define database type converters
        self._db_type_converters = {
            DatabaseType.BOOLEAN: lambda v: 1 if v else 0,
            DatabaseType.DATE: lambda v: convert_datetime(v, format="%Y-%m-%d"),
            DatabaseType.TIME: lambda v: convert_datetime(v, format="%H:%M:%S"),
            DatabaseType.DATETIME: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.TIMESTAMP: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.JSON: safe_json_dumps,
            DatabaseType.ARRAY: array_converter,
            DatabaseType.UUID: str,
            DatabaseType.DECIMAL: str,
        }

        # Define Python type conversions after database read
        self._from_python_converters = {
            DatabaseType.BOOLEAN: {
                int: bool,
                str: lambda v: v.lower() in ('true', '1', 'yes', 'on'),
                bool: lambda v: v,
            },
            DatabaseType.DATE: {
                str: lambda v: v,
                datetime: lambda v: v.date(),
                date: lambda v: v,
            },
            DatabaseType.TIME: {
                str: lambda v: v,
                datetime: lambda v: v.time(),
                time: lambda v: v,
            },
            DatabaseType.DATETIME: {
                str: lambda v: parse_datetime(v),
                int: lambda v: datetime.fromtimestamp(v),
                float: lambda v: datetime.fromtimestamp(v),
                datetime: lambda v: v,
            },
            DatabaseType.TIMESTAMP: {
                str: lambda v: parse_datetime(v),
                int: lambda v: datetime.fromtimestamp(v),
                float: lambda v: datetime.fromtimestamp(v),
                datetime: lambda v: v,
            },
            DatabaseType.JSON: {
                str: safe_json_loads,
                dict: lambda v: v,
                list: lambda v: v,
            },
            DatabaseType.ARRAY: {
                str: safe_json_loads,
                list: lambda v: v,
                tuple: list,
            },
            DatabaseType.UUID: {
                str: uuid.UUID,
                uuid.UUID: lambda v: v,
            },
            DatabaseType.DECIMAL: {
                str: Decimal,
                int: Decimal,
                float: Decimal,
                Decimal: lambda v: v,
            },
            DatabaseType.INTEGER: {
                str: int,
                float: int,
                bool: int,
                int: lambda v: v,
            },
            DatabaseType.FLOAT: {
                str: float,
                int: float,
                float: lambda v: v,
            },
            DatabaseType.TEXT: {
                str: lambda v: v,
                int: str,
                float: str,
                bool: str,
                datetime: str,
                date: str,
                time: str,
                uuid.UUID: str,
                Decimal: str,
            },
            DatabaseType.BLOB: {
                str: lambda v: v.encode(),
                bytes: lambda v: v,
                bytearray: bytes,
            }
        }

    def to_database(self, value: Any, db_type: Optional[DatabaseType] = None) -> Any:
        """Convert Python value to MySQL storage value

        Args:
            value: Python value
            db_type: Target database type

        Returns:
            Any: Converted value suitable for MySQL

        Raises:
            TypeConversionError: If type conversion fails
        """
        if value is None:
            return None

        try:
            # First try basic type conversion
            if db_type is None:
                value_type = type(value)
                if value_type in self._base_converters:
                    return self._base_converters[value_type](value)

            # Then try database type conversion
            if db_type in self._db_type_converters:
                return self._db_type_converters[db_type](value)

            # Special handling for numeric types
            if db_type in (DatabaseType.TINYINT, DatabaseType.SMALLINT,
                           DatabaseType.INTEGER, DatabaseType.BIGINT):
                return int(value)
            if db_type in (DatabaseType.FLOAT, DatabaseType.DOUBLE):
                return float(value)

            # Default to original value
            return value

        except Exception as e:
            raise TypeConversionError(
                f"Failed to convert {type(value)} to {db_type}: {str(e)}"
            )

    def from_database(self, value: Any, db_type: DatabaseType) -> Any:
        """Convert MySQL storage value to Python value

        Args:
            value: MySQL storage value
            db_type: Source database type

        Returns:
            Any: Converted Python value

        Raises:
            TypeConversionError: If type conversion fails
        """
        if value is None:
            return None

        try:
            # Get current Python type
            current_type = type(value)

            # Get converter mapping for target type
            type_converters = self._from_python_converters.get(db_type)
            if type_converters:
                # Find converter for current Python type
                converter = type_converters.get(current_type)
                if converter:
                    return converter(value)

                # If no direct converter, try indirect conversion via string
                if current_type != str and str in type_converters:
                    return type_converters[str](str(value))

            # Return original value if no converter found
            return value

        except Exception as e:
            raise TypeConversionError(
                f"Failed to convert MySQL value {value} ({type(value)}) to {db_type}: {str(e)}"
            )

class MySQLExpression(SQLExpressionBase):
    """MySQL expression implementation"""

    def format(self, dialect: SQLDialectBase) -> str:
        """Format MySQL expression"""
        return self.expression

class MySQLReturningHandler(ReturningClauseHandler):
    """MySQL RETURNING clause handler implementation"""

    def __init__(self, version: tuple):
        """Initialize MySQL RETURNING handler

        Args:
            version: MySQL version tuple
        """
        self._version = version

    @property
    def is_supported(self) -> bool:
        """Check if RETURNING clause is supported

        Note: MySQL does not support RETURNING clause in any version
        """
        # MySQL does not support RETURNING in any version
        return False

    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        """Format RETURNING clause

        Args:
            columns: Column names to return. None means all columns.

        Returns:
            str: Formatted RETURNING clause

        Raises:
            ReturningNotSupportedError: Always raises as MySQL doesn't support RETURNING
        """
        # MySQL does not support RETURNING
        raise ReturningNotSupportedError("MySQL does not support RETURNING clause in any version")

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
        version = getattr(config, 'version', (8, 0, 0))
        super().__init__(version)
        if config.version:
            self._version = config.version

        if config.driver_type:
            self._driver_type = config.driver_type
        else:
            self._driver_type = DriverType.MYSQL_CONNECTOR

        # Initialize handlers
        self._type_mapper = MySQLTypeMapper()
        self._value_mapper = MySQLValueMapper(config)
        self._returning_handler = MySQLReturningHandler(version)

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format MySQL expression"""
        if not isinstance(expr, MySQLExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get MySQL parameter placeholder"""
        return self._type_mapper.get_placeholder(None)

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