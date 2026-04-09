# src/rhosocial/activerecord/backend/impl/mysql/expressions.py
"""
MySQL-specific expression classes.

This module contains expression classes for MySQL-specific SQL syntax
that is not part of the SQL standard.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


@dataclass
class LoadDataOptions:
    """Options for LOAD DATA INFILE statement.

    Attributes:
        local: Use LOCAL keyword (client-side file)
        replace: Use REPLACE mode (replace existing rows on duplicate key)
        ignore: Use IGNORE mode (ignore duplicate key errors)
        character_set: Character set of the file
        fields_terminated_by: Field terminator string (default: tab)
        fields_enclosed_by: Field enclosure character
        fields_escaped_by: Escape character
        lines_starting_by: Line prefix to skip
        lines_terminated_by: Line terminator string
        ignore_lines: Number of lines to skip at start
        column_list: List of column names for mapping
        set_assignments: SET clause for column transformations
    """
    local: bool = True
    replace: bool = False
    ignore: bool = False
    character_set: Optional[str] = None
    fields_terminated_by: Optional[str] = None
    fields_enclosed_by: Optional[str] = None
    fields_escaped_by: Optional[str] = None
    lines_starting_by: Optional[str] = None
    lines_terminated_by: Optional[str] = None
    ignore_lines: Optional[int] = None
    column_list: Optional[List[str]] = None
    set_assignments: Optional[Dict[str, Any]] = None


class LoadDataExpression(BaseExpression):
    """MySQL LOAD DATA INFILE expression.

    Collects parameters for LOAD DATA [LOCAL] INFILE statement.
    The actual SQL formatting is done by MySQLDialect.format_load_data_statement().

    Attributes:
        file_path: Path to the data file
        table: Target table name
        options: Load options
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        file_path: str,
        table: str,
        options: Optional[LoadDataOptions] = None
    ):
        """Initialize LOAD DATA expression.

        Args:
            dialect: SQL dialect
            file_path: Path to the data file
            table: Target table name
            options: Load options (default: LoadDataOptions())
        """
        super().__init__(dialect)
        self.file_path = file_path
        self.table = table
        self.options = options or LoadDataOptions()

    def validate(self, strict: bool = True) -> None:
        """Validate expression parameters.

        Args:
            strict: Enable strict validation (unused but required by base class)

        Raises:
            ValueError: If both replace and ignore are True
            TypeError: If parameters have wrong types
        """
        if not strict:
            return

        if not isinstance(self.file_path, str):
            raise TypeError(f"file_path must be str, got {type(self.file_path)}")

        if not isinstance(self.table, str):
            raise TypeError(f"table must be str, got {type(self.table)}")

        if not isinstance(self.options, LoadDataOptions):
            raise TypeError(f"options must be LoadDataOptions, got {type(self.options)}")

        if self.options.replace and self.options.ignore:
            raise ValueError("Cannot use both REPLACE and IGNORE in LOAD DATA")

    def to_sql(self):
        """Generate SQL by delegating to dialect's format method.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.dialect.format_load_data_statement(self)


@dataclass
class JSONTableColumn:
    """Column definition for JSON_TABLE.

    Attributes:
        name: Column name
        type: SQL data type (e.g., 'VARCHAR(255)', 'INT')
        path: JSON path expression for the column value
        ordinality: If True, use FOR ORDINALITY (row number)
        exists: If True, use EXISTS (boolean for path existence)
        error_handling: Error handling mode ('NULL', 'ERROR', 'DEFAULT')
        default_value: Default value when error handling is 'DEFAULT'
    """
    name: str
    type: Optional[str] = None
    path: Optional[str] = None
    ordinality: bool = False
    exists: bool = False
    error_handling: Optional[str] = None  # 'NULL', 'ERROR', 'DEFAULT'
    default_value: Optional[Any] = None


@dataclass
class NestedPath:
    """NESTED PATH definition for JSON_TABLE.

    Attributes:
        path: JSON path expression for nested data
        columns: List of column definitions within this nested path
        alias: Optional alias for the nested table
    """
    path: str
    columns: List['JSONTableColumn']
    alias: Optional[str] = None


class JSONTableExpression(BaseExpression):
    """MySQL JSON_TABLE expression.

    Generates JSON_TABLE function for converting JSON data to relational format.
    Supported in MySQL 8.0.4+.

    Attributes:
        json_doc: JSON document string or expression
        path: JSON path expression for the root array/object
        columns: List of column definitions
        nested_paths: Optional list of NESTED PATH definitions
        alias: Table alias
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        json_doc: str,
        path: str,
        columns: List[JSONTableColumn],
        nested_paths: Optional[List[NestedPath]] = None,
        alias: Optional[str] = None
    ):
        """Initialize JSON_TABLE expression.

        Args:
            dialect: SQL dialect
            json_doc: JSON document string or expression
            path: JSON path expression for the root
            columns: List of column definitions
            nested_paths: Optional list of NESTED PATH definitions
            alias: Table alias
        """
        super().__init__(dialect)
        self.json_doc = json_doc
        self.path = path
        self.columns = columns
        self.nested_paths = nested_paths or []
        self.alias = alias

    def validate(self, strict: bool = True) -> None:
        """Validate expression parameters.

        Args:
            strict: Enable strict validation

        Raises:
            TypeError: If parameters have wrong types
            ValueError: If column definitions are invalid
        """
        if not strict:
            return

        if not isinstance(self.json_doc, str):
            raise TypeError(f"json_doc must be str, got {type(self.json_doc)}")

        if not isinstance(self.path, str):
            raise TypeError(f"path must be str, got {type(self.path)}")

        if not isinstance(self.columns, list):
            raise TypeError(f"columns must be list, got {type(self.columns)}")

        for col in self.columns:
            if not isinstance(col, JSONTableColumn):
                raise TypeError(f"columns must contain JSONTableColumn, got {type(col)}")

        for nested in self.nested_paths:
            if not isinstance(nested, NestedPath):
                raise TypeError(f"nested_paths must contain NestedPath, got {type(nested)}")

    def to_sql(self):
        """Generate SQL by delegating to dialect's format method.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.dialect.format_json_table_expression(self)