# src/rhosocial/activerecord/backend/impl/mysql/mixins/json.py
from typing import Any, List, Optional, Tuple, Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.advanced_functions import (
        JSONDocumentExpression,
        JSONTextExpression,
    )

    #: What the two formatters below accept. Core used to have one class for
    #: both JSON access operators; it now has one per operator, and MySQL renders
    #: ``->`` and ``->>`` from these same two methods, so the parameter is a
    #: union rather than either class alone.
    #:
    #: The union is spelled out even though ``JSONTextExpression`` subclasses
    #: ``JSONDocumentExpression`` and a checker would collapse it. That
    #: inheritance exists so a text access keeps the accessors that let a path
    #: chain continue; it is not a claim that ``->>`` yields a document.
    #:
    #: It covers the two operators core actually split. It does not cover an
    #: arbitrary infix operator -- ``=``, ``@>`` and the like -- which both
    #: formatters below still emit, because core has no class for one: the old
    #: single class was "JSON access by whatever operator you named", and only
    #: ``->`` and ``->>`` had a result type worth naming a class after. A
    #: non-arrow operation says nothing about what comes back, so no class
    #: asserts anything for it and the ``operation`` field alone decides.
    JSONPathNode = Union["JSONDocumentExpression", "JSONTextExpression"]


class MySQLJSONFunctionMixin:
    """MySQL JSON function implementation."""

    _JSON_FUNCTION_VERSIONS = {
        "JSON_TABLE": (8, 0, 4),
        "JSON_VALUE": (8, 0, 21),
        "JSON_SCHEMA_VALID": (8, 0, 17),
        "JSON_MERGE_PATCH": (8, 0, 3),
    }

    def supports_json_type(self) -> bool:
        return self.version >= (5, 7, 8)

    def supports_json_path(self) -> bool:
        """Whether a JSON path can be read on this server.

        Gate is 5.7.0, where JSON_EXTRACT appeared, not 5.7.8 where the native
        JSON type did. Between those two versions the server reads a path
        perfectly well and has no JSON column type, so gating on the type
        would refuse queries it answers.
        """
        return self.version >= (5, 7, 0)

    def supports_json_merge_patch(self) -> bool:
        return self.version >= (8, 0, 3)

    def supports_json_table(self) -> bool:
        return self.version >= (8, 0, 4)

    def supports_json_function(self, function_name: str) -> bool:
        if function_name in self._JSON_FUNCTION_VERSIONS:
            return self.version >= self._JSON_FUNCTION_VERSIONS[function_name]
        return self.version >= (5, 7, 8)

    def format_json_extract(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONExtractExpression` node."""
        sql, params = self._format_json_extract_parts(expr.json_column, expr.path)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_extract_parts(
        self, json_doc: str, path: str, paths: Optional[List[str]] = None
    ) -> Tuple[str, tuple]:
        """Format JSON_EXTRACT function."""
        all_paths = [path]
        if paths:
            all_paths.extend(paths)
        path_placeholders = ", ".join([self.p() for _ in all_paths])
        return f"JSON_EXTRACT({json_doc}, {path_placeholders})", tuple(all_paths)

    def format_json_unquote(self, expr) -> Tuple[str, tuple]:
        """Format MySQLJSONUnquoteExpression or a raw JSON value string."""
        from ..expression.json import MySQLJSONUnquoteExpression

        if isinstance(expr, MySQLJSONUnquoteExpression):
            sql = f"JSON_UNQUOTE({self.get_parameter_placeholder()})"
            params: Tuple = (expr.json_val,)
            alias = expr.alias
        else:
            sql = f"JSON_UNQUOTE({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_json_object(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONObjectExpression` node."""
        sql, params = self._format_json_object_parts(expr.pairs)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_object_parts(self, key_value_pairs: List[Tuple[str, Any]]) -> Tuple[str, tuple]:
        """Format JSON_OBJECT function."""
        if not key_value_pairs:
            return "JSON_OBJECT()", ()

        parts = []
        params: List[Any] = []

        for key, value in key_value_pairs:
            parts.append(self.p())
            parts.append(self.p())
            params.append(key)
            params.append(value)

        return f"JSON_OBJECT({', '.join(parts)})", tuple(params)

    def format_json_array(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONArrayExpression` node."""
        sql, params = self._format_json_array_parts(expr.values)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_array_parts(self, values: List[Any]) -> Tuple[str, tuple]:
        """Format JSON_ARRAY function."""
        if not values:
            return "JSON_ARRAY()", ()
        placeholders = ", ".join([self.p() for _ in values])
        return f"JSON_ARRAY({placeholders})", tuple(values)

    def format_json_contains(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONContainsExpression` node."""
        sql, params = self._format_json_contains_parts(expr.json_column, expr.value, expr.path)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def _format_json_contains_parts(self, target: str, candidate: str, path: Optional[str] = None) -> Tuple[str, tuple]:
        """Format JSON_CONTAINS function."""
        if path:
            return f"JSON_CONTAINS({target}, {self.p()}, {self.p()})", (candidate, path)
        return f"JSON_CONTAINS({target}, {self.p()})", (candidate,)

    def format_json_set(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONSetExpression` node."""
        from ..expression.json import MySQLJSONSetExpression

        if not isinstance(expr, MySQLJSONSetExpression):
            raise TypeError(
                f"format_json_set expects MySQLJSONSetExpression, got {type(expr).__name__}"
            )

        all_pairs = [(expr.path, expr.value)] + (expr.path_value_pairs or [])
        placeholders = ", ".join(
            [f"{self.get_parameter_placeholder()}, {self.get_parameter_placeholder()}" for _ in all_pairs]
        )
        params = []
        for p, v in all_pairs:
            params.extend([p, v])
        sql = f"JSON_SET({expr.json_doc}, {placeholders})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(params)

    def format_json_remove(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONRemoveExpression` node."""
        from ..expression.json import MySQLJSONRemoveExpression

        if not isinstance(expr, MySQLJSONRemoveExpression):
            raise TypeError(
                f"format_json_remove expects MySQLJSONRemoveExpression, got {type(expr).__name__}"
            )

        all_paths = [expr.path] + (expr.paths or [])
        placeholders = ", ".join([self.get_parameter_placeholder()] * len(all_paths))
        sql = f"JSON_REMOVE({expr.json_doc}, {placeholders})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(all_paths)

    def format_json_type(self, expr) -> Tuple[str, tuple]:
        """Format MySQLJSONTypeExpression or a raw JSON value string."""
        from ..expression.json import MySQLJSONTypeExpression

        if isinstance(expr, MySQLJSONTypeExpression):
            sql = f"JSON_TYPE({self.get_parameter_placeholder()})"
            params: Tuple = (expr.json_val,)
            alias = expr.alias
        else:
            sql = f"JSON_TYPE({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_json_valid(self, expr) -> Tuple[str, tuple]:
        """Format MySQLJSONValidExpression or a raw JSON value string."""
        from ..expression.json import MySQLJSONValidExpression

        if isinstance(expr, MySQLJSONValidExpression):
            sql = f"JSON_VALID({self.get_parameter_placeholder()})"
            params: Tuple = (expr.json_val,)
            alias = expr.alias
        else:
            sql = f"JSON_VALID({expr})"
            params = ()
            alias = None
        if alias:
            sql = f"{sql} AS {self.format_identifier(alias)}"
        return sql, params

    def format_json_search(self, expr) -> Tuple[str, tuple]:
        """Format a :class:`MySQLJSONSearchExpression` node."""
        from ..expression.json import MySQLJSONSearchExpression

        if not isinstance(expr, MySQLJSONSearchExpression):
            raise TypeError(
                f"format_json_search expects MySQLJSONSearchExpression, got {type(expr).__name__}"
            )

        one_or_all = "'all'" if expr.all else "'one'"
        if expr.path:
            sql = (
                f"JSON_SEARCH({expr.json_doc}, {one_or_all}, {self.get_parameter_placeholder()}, "
                f"NULL, {self.get_parameter_placeholder()})"
            )
            params = (expr.search_str, expr.path)
        else:
            sql = f"JSON_SEARCH({expr.json_doc}, {one_or_all}, {self.get_parameter_placeholder()})"
            params = (expr.search_str,)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_json_arrow_expression(self, expr: "JSONPathNode") -> Tuple[str, Tuple]:
        """Format JSON expression using arrow operators for MySQL.

        MySQL's -> and ->> operators require:
        1. The JSON path as a string literal, not a parameter placeholder
        2. No parentheses around the expression

        Takes either JSON path node -- :class:`JSONDocumentExpression` for
        ``->``, :class:`JSONTextExpression` for ``->>`` -- and tells them apart
        by ``expr.operation``, not by class, so which one the caller built does
        not change the SQL. Any other operation is emitted as an infix
        comparison with the path bound; see :class:`JSONPathNode` for why that
        branch has no class of its own.
        """
        if isinstance(expr.column, bases.BaseExpression):
            col_sql, col_params = expr.column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(expr.column)), ()

        if expr.operation in ("->", "->>"):
            escaped_path = self._escape_sql_string(expr.path)
            sql = f"{col_sql}{expr.operation}'{escaped_path}'"
            params = col_params
        else:
            sql = f"({col_sql} {expr.operation} {self.get_parameter_placeholder()})"
            params = col_params + (expr.path,)

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    def format_json_function_expression(self, expr: "JSONPathNode") -> Tuple[str, Tuple]:
        """Format JSON expression using function-based equivalents for MySQL.

        MySQL supports JSON_EXTRACT and JSON_UNQUOTE, and also supports
        the native arrow operators.  Both paths are available.
        This is the function-based path, usable via JSONPathMode.FUNCTION.

        Takes either JSON path node and tells them apart by ``expr.operation``:
        ``->`` is JSON_EXTRACT (a document), ``->>`` is
        JSON_UNQUOTE(JSON_EXTRACT(...)) (text), anything else is an infix
        operator with the path inlined.
        """
        if isinstance(expr.column, bases.BaseExpression):
            col_sql, col_params = expr.column.to_sql()
        else:
            col_sql, col_params = self.format_identifier(str(expr.column)), ()

        escaped_path = self._escape_sql_string(expr.path)

        if expr.operation == "->":
            sql = f"JSON_EXTRACT({col_sql}, '{escaped_path}')"
            params = col_params
        elif expr.operation == "->>":
            sql = f"JSON_UNQUOTE(JSON_EXTRACT({col_sql}, '{escaped_path}'))"
            params = col_params
        else:
            sql = f"{col_sql} {expr.operation} '{escaped_path}'"
            params = col_params

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, params

    def format_json_table_expression(self, expr) -> Tuple[str, tuple]:
        """Format JSON_TABLE expression with safe literal escaping."""
        from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol

        expr.validate(strict=self.strict_validation)

        parts = ["JSON_TABLE("]

        # Handle json_doc: if it's a string literal, escape and quote it;
        # if it's a ToSQLProtocol expression, use to_sql() for parameterized
        # queries; otherwise raise to prevent SQL injection.
        if isinstance(expr.json_doc, str):
            parts.append(f"'{self._escape_sql_string(expr.json_doc)}'")
        elif isinstance(expr.json_doc, ToSQLProtocol):
            json_sql, _ = expr.json_doc.to_sql()
            parts.append(json_sql)
        else:
            raise ValueError(
                f"json_doc must be a string or implement ToSQLProtocol, got {type(expr.json_doc).__name__}"
            )

        parts.append(",")
        escaped_path = self._escape_sql_string(expr.path)
        parts.append(f"'{escaped_path}'")
        parts.append(" COLUMNS (")

        column_parts = []
        for col in expr.columns:
            if col.ordinality:
                column_parts.append(f"{self.format_identifier(col.name)} FOR ORDINALITY")
            elif col.exists:
                escaped_col_path = self._escape_sql_string(col.path) if col.path else ""
                column_parts.append(f"{self.format_identifier(col.name)} {col.type} EXISTS PATH '{escaped_col_path}'")
            else:
                if not self._validate_data_type(col.type):
                    raise ValueError(f"Invalid data type: {col.type}")
                col_def = f"{self.format_identifier(col.name)} {col.type}"
                if col.path:
                    escaped_col_path = self._escape_sql_string(col.path)
                    col_def += f" PATH '{escaped_col_path}'"
                if col.error_handling:
                    valid_error_handling = {"NULL", "ERROR", "DEFAULT"}
                    error_handling_upper = col.error_handling.upper()
                    if error_handling_upper not in valid_error_handling:
                        raise ValueError(
                            f"Invalid error_handling: {col.error_handling}. Must be one of {valid_error_handling}"
                        )
                    if error_handling_upper == "DEFAULT":
                        escaped_default = self._escape_sql_string(str(col.default_value))
                        col_def += f" DEFAULT '{escaped_default}' ON ERROR"
                    else:
                        col_def += f" {error_handling_upper} ON ERROR"
                column_parts.append(col_def)

        for nested in expr.nested_paths:
            escaped_nested_path = self._escape_sql_string(nested.path)
            nested_def = f"NESTED PATH '{escaped_nested_path}' COLUMNS ("
            nested_cols = []
            for col in nested.columns:
                if col.ordinality:
                    nested_cols.append(f"{self.format_identifier(col.name)} FOR ORDINALITY")
                else:
                    escaped_nested_col_path = self._escape_sql_string(col.path) if col.path else ""
                    nested_cols.append(
                        f"{self.format_identifier(col.name)} {col.type} PATH '{escaped_nested_col_path}'"
                    )
            nested_def += ", ".join(nested_cols) + ")"
            if nested.alias:
                nested_def = f"{self.format_identifier(nested.alias)} AS " + nested_def
            column_parts.append(nested_def)

        parts.append(", ".join(column_parts))
        parts.append("))")

        if expr.alias:
            parts.append(f" AS {self.format_identifier(expr.alias)}")

        return "".join(parts), ()
