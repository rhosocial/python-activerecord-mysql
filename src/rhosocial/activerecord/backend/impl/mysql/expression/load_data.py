# src/rhosocial/activerecord/backend/impl/mysql/expression/load_data.py
"""
MySQL-specific LOAD DATA expression.

This module provides MySQLLoadDataExpression and LoadDataOptions for
MySQL's LOAD DATA INFILE functionality.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class LoadDataOptions(BaseExpression):
    """Options for LOAD DATA INFILE statement, as a node.

    A clause node rather than a plain dataclass: ``options`` is a
    constructor parameter of :class:`MySQLLoadDataExpression`, and a
    parameter is either a language-neutral scalar or an expression
    instance (§10) -- those are the two forms an artifact can carry, and a
    dataclass is neither. Being a node is also what makes the bundle
    readable back: the artifact carries a nested ``load_data_options``
    node and the reader rebuilds it by name, exactly like any other
    clause.

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

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        local: bool = True,
        replace: bool = False,
        ignore: bool = False,
        character_set: Optional[str] = None,
        fields_terminated_by: Optional[str] = None,
        fields_enclosed_by: Optional[str] = None,
        fields_escaped_by: Optional[str] = None,
        lines_starting_by: Optional[str] = None,
        lines_terminated_by: Optional[str] = None,
        ignore_lines: Optional[int] = None,
        column_list: Optional[List[str]] = None,
        set_assignments: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.local: bool = local
        self.replace: bool = replace
        self.ignore: bool = ignore
        self.character_set: Optional[str] = character_set
        self.fields_terminated_by: Optional[str] = fields_terminated_by
        self.fields_enclosed_by: Optional[str] = fields_enclosed_by
        self.fields_escaped_by: Optional[str] = fields_escaped_by
        self.lines_starting_by: Optional[str] = lines_starting_by
        self.lines_terminated_by: Optional[str] = lines_terminated_by
        self.ignore_lines: Optional[int] = ignore_lines
        self.column_list: Optional[List[str]] = (
            list(column_list) if column_list is not None else None
        )
        self.set_assignments: Optional[Dict[str, Any]] = (
            dict(set_assignments) if set_assignments is not None else None
        )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression.

        No dialect defines a standalone entry for this clause: the LOAD
        DATA statement's own formatter renders the options inline, reading
        the fields declared here. The clause travels as a node so the
        statement's parameters can carry it, not because it renders
        standing alone.
        """
        return "format_load_data_options"


class MySQLLoadDataExpression(BaseExpression):
    """MySQL LOAD DATA INFILE expression.

    Collects parameters for LOAD DATA [LOCAL] INFILE statement.
    The actual SQL formatting is done by MySQLDialect.format_mysql_load_data_expression().

    Attributes:
        file_path: Path to the data file
        table: Target table, as a schema object
        options: Load options
    """

    def __init__(
        self,
        dialect: "SQLDialectBase", file_path: str, table: "Table", options: Optional[LoadDataOptions] = None
    ):
        """Initialize LOAD DATA expression.

        Args:
            dialect: SQL dialect
            file_path: Path to the data file
            table: Target table as a
                :class:`~rhosocial.activerecord.backend.expression.objects.Table`.
                Supplying an object rather than a bare string is what makes
                ``LOAD DATA ... INTO TABLE `other_db`.`users``` expressible;
                a string can only ever mean the session's current database.
            options: Load options (default: LoadDataOptions(dialect))
        """
        super().__init__(dialect)
        self.file_path = file_path
        self.table = table
        self.options = options or LoadDataOptions(dialect)

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

        if not isinstance(self.table, Table):
            raise TypeError(
                f"table must be a Table object, got {type(self.table).__name__}; "
                f"pass Table(self.dialect, 'users', catalog_name='app') to qualify the name"
            )

        if not isinstance(self.options, LoadDataOptions):
            raise TypeError(f"options must be LoadDataOptions, got {type(self.options)}")

        if self.options.replace and self.options.ignore:
            raise ValueError("Cannot use both REPLACE and IGNORE in LOAD DATA")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_mysql_load_data_expression"
