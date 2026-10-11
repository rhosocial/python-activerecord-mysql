# tests/rhosocial/activerecord_mysql_test/feature/backend/test_json_arrow_expression.py
"""Tests for MySQL JSON arrow (-> / ->>) and function-based expressions.

These are pure SQL-rendering tests (no live MySQL server) exercising the
``MySQLJSONFunctionMixin.format_json_arrow_expression`` and
``format_json_function_expression`` branches added in the connection
serialization PR.

Core used to have a single ``JSONExpression`` covering both access operators
and has since split it in two, one per operator: ``->`` yields a document and
is a ``JSONDocumentExpression``, ``->>`` yields text and is a
``JSONTextExpression``. Both render through the same ``format_json_expression``
dispatch and both formatters here still branch on ``expr.operation``, so the
class names below record which operator each test means and nothing about the
SQL changed.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.advanced_functions import (
    JSONDocumentExpression,
    JSONPathMode,
    JSONTextExpression,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLSignedType, MySQLUnsignedType


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


class TestArrowExpression:
    def test_arrow_column_identifier(self, dialect):
        """``->`` yields a document, so it is a JSONDocumentExpression."""
        expr = JSONDocumentExpression(dialect, "data", "$.name", "->")
        sql, params = expr.to_sql()
        assert sql == "`data`->'$.name'"
        assert params == ()

    def test_arrow_operator_identifier(self, dialect):
        """``->>`` yields text, so it is a JSONTextExpression."""
        expr = JSONTextExpression(dialect, "data", "$.name", "->>")
        sql, params = expr.to_sql()
        assert sql == "`data`->>'$.name'"
        assert params == ()

    def test_arrow_with_nested_column_expression(self, dialect):
        col = Column(dialect, "payload")
        expr = JSONDocumentExpression(dialect, col, "$.a.b", "->")
        sql, params = expr.to_sql()
        assert sql == "`payload`->'$.a.b'"
        assert params == ()

    def test_arrow_with_cast_types(self, dialect):
        expr = JSONTextExpression(
            dialect, "data", "$.age", "->>", mode=JSONPathMode.ARROW
        ).cast(MySQLUnsignedType(dialect))
        sql, params = expr.to_sql()
        assert sql == "CAST(`data`->>'$.age' AS UNSIGNED)"
        assert params == ()

    def test_arrow_with_alias(self, dialect):
        expr = JSONDocumentExpression(dialect, "data", "$.name", "->", alias="nm")
        sql, params = expr.to_sql()
        assert sql == "`data`->'$.name' AS `nm`"
        assert params == ()

    def test_arrow_forced_mode_renders_arrow(self):
        old = MySQLDialect(version=(5, 7, 0))
        expr = JSONDocumentExpression(old, "data", "$.name", "->", mode=JSONPathMode.ARROW)
        sql, params = expr.to_sql()
        assert sql == "`data`->'$.name'"
        assert params == ()

    def test_arrow_other_operator_uses_placeholder(self, dialect):
        """An operator that is neither ``->`` nor ``->>``.

        ``=`` is not one of the two operators core split, and it says nothing
        about the result type -- it is a comparison, so it yields a boolean and
        neither JSONDocumentExpression nor JSONTextExpression means it. The
        base class is used as a plain carrier for the node; the branch is
        chosen by ``operation`` alone, so either class renders this identically.
        """
        expr = JSONDocumentExpression(dialect, "data", "$.name", "=")
        sql, params = expr.to_sql()
        assert sql == "(`data` = %s)"
        assert params == ("$.name",)

    def test_arrow_other_operator_with_column_expression(self, dialect):
        """As above: ``@>`` is not an arrow, so no JSON path class denotes it."""
        col = Column(dialect, "payload")
        expr = JSONDocumentExpression(dialect, col, "someval", "@>")
        sql, params = expr.to_sql()
        assert sql == "(`payload` @> %s)"
        assert params == ("someval",)


class TestFunctionExpression:
    def test_function_extract(self, dialect):
        """``->`` is JSON_EXTRACT and yields a document."""
        expr = JSONDocumentExpression(dialect, "data", "$.name", "->", mode=JSONPathMode.FUNCTION)
        sql, params = expr.to_sql()
        assert sql == "JSON_EXTRACT(`data`, '$.name')"
        assert params == ()

    def test_function_unquote(self, dialect):
        """``->>`` unquotes and yields text."""
        expr = JSONTextExpression(dialect, "data", "$.name", "->>", mode=JSONPathMode.FUNCTION)
        sql, params = expr.to_sql()
        assert sql == "JSON_UNQUOTE(JSON_EXTRACT(`data`, '$.name'))"
        assert params == ()

    def test_function_other_operator(self, dialect):
        """``@>`` is not an arrow, so no JSON path class denotes it.

        Same as the arrow-mode case: the base class is a carrier and
        ``operation`` alone picks the branch.
        """
        expr = JSONDocumentExpression(dialect, "data", "$.name", "@>", mode=JSONPathMode.FUNCTION)
        sql, params = expr.to_sql()
        assert sql == "`data` @> '$.name'"
        assert params == ()

    def test_function_with_column_expression(self, dialect):
        col = Column(dialect, "payload")
        expr = JSONDocumentExpression(dialect, col, "$.a", "->", mode=JSONPathMode.FUNCTION)
        sql, params = expr.to_sql()
        assert sql == "JSON_EXTRACT(`payload`, '$.a')"
        assert params == ()

    def test_function_with_cast_types(self, dialect):
        expr = JSONTextExpression(
            dialect, "data", "$.age", "->>", mode=JSONPathMode.FUNCTION
        ).cast(MySQLSignedType(dialect))
        sql, params = expr.to_sql()
        assert sql == "CAST(JSON_UNQUOTE(JSON_EXTRACT(`data`, '$.age')) AS SIGNED)"
        assert params == ()

    def test_function_with_alias(self, dialect):
        expr = JSONDocumentExpression(dialect, "data", "$.name", "->", mode=JSONPathMode.FUNCTION, alias="nm")
        sql, params = expr.to_sql()
        assert sql == "JSON_EXTRACT(`data`, '$.name') AS `nm`"
        assert params == ()


class TestModeDispatch:
    def test_auto_uses_arrow_when_supported(self, dialect):
        expr = JSONDocumentExpression(dialect, "data", "$.name", "->")
        sql, _ = expr.to_sql()
        assert "JSON_EXTRACT" not in sql
        assert "->" in sql

    def test_auto_falls_back_to_function_when_unsupported(self):
        old = MySQLDialect(version=(5, 7, 0))
        expr = JSONDocumentExpression(old, "data", "$.name", "->")
        sql, params = expr.to_sql()
        assert sql == "JSON_EXTRACT(`data`, '$.name')"
        assert params == ()

    def test_string_mode_coercion(self, dialect):
        expr = JSONDocumentExpression(dialect, "data", "$.name", "->", mode="function")
        sql, _ = expr.to_sql()
        assert sql == "JSON_EXTRACT(`data`, '$.name')"

    def test_escaped_path_backslash(self, dialect):
        expr = JSONDocumentExpression(dialect, "data", "$.a\\b", "->")
        sql, _ = expr.to_sql()
        assert sql == r"`data`->'$.a\\b'"

    def test_escaped_path_single_quote(self, dialect):
        expr = JSONDocumentExpression(dialect, "data", "$.a'b", "->")
        sql, _ = expr.to_sql()
        assert sql == "`data`->'$.a''b'"


class TestJSONCapabilityVersions:
    def test_supports_json_type_version_boundary(self):
        assert MySQLDialect(version=(5, 6, 0)).supports_json_type() is False
        assert MySQLDialect(version=(5, 7, 8)).supports_json_type() is True

    def test_supports_json_merge_patch_version_boundary(self):
        assert MySQLDialect(version=(8, 0, 2)).supports_json_merge_patch() is False
        assert MySQLDialect(version=(8, 0, 3)).supports_json_merge_patch() is True

    def test_supports_json_table_version_boundary(self):
        assert MySQLDialect(version=(8, 0, 3)).supports_json_table() is False
        assert MySQLDialect(version=(8, 0, 4)).supports_json_table() is True

    def test_supports_json_function_known_and_unknown(self):
        assert MySQLDialect(version=(8, 0, 2)).supports_json_function("JSON_MERGE_PATCH") is False
        assert MySQLDialect(version=(8, 0, 4)).supports_json_function("JSON_TABLE") is True
        assert MySQLDialect(version=(5, 7, 0)).supports_json_function("CUSTOM_FN") is False
        assert MySQLDialect(version=(5, 7, 8)).supports_json_function("CUSTOM_FN") is True

    def test_supports_json_arrow_operators(self):
        assert MySQLDialect(version=(5, 7, 8)).supports_json_arrow_operators() is False
        assert MySQLDialect(version=(5, 7, 9)).supports_json_arrow_operators() is True
        assert MySQLDialect(version=(8, 0, 0)).get_json_access_operator() == "->"
