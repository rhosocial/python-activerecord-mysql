# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_dialect_security.py
"""
Tests for MySQL dialect SQL injection security fixes.

This test module verifies that string escaping and validation
methods properly sanitize user input to prevent SQL injection.
Tests are run against the actual MySQL dialect.
"""
import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.impl.mysql.expression.json_table import (
    MySQLJSONTableExpression,
    JSONTableColumn,
)


@pytest.fixture
def dialect():
    """Create a MySQL test dialect."""
    return MySQLDialect()


def test_mysql_format_column_definition_default_string_escaping(dialect):
    """Test DEFAULT constraint string is escaped in MySQL."""
    constraint = ColumnConstraint(
        constraint_type=ColumnConstraintType.DEFAULT,
        default_value="test's value",
    )

    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
        constraints=[constraint],
    )

    sql, params = dialect._format_column_definition_mysql(col_def, ColumnConstraintType)
    assert "test''s value" in sql


def test_mysql_format_column_definition_comment_string_escaping(dialect):
    """Test COMMENT string is escaped in MySQL column definition."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
        comment="Comment with 'single quote'",
    )

    sql, params = dialect._format_column_definition_mysql(col_def, ColumnConstraintType)
    assert "Comment with ''single quote''" in sql


def test_mysql_escape_sql_string(dialect):
    """Test MySQL inherits _escape_sql_string."""
    result = dialect._escape_sql_string("Table's comment")
    assert result == "Table''s comment"


def test_mysql_validate_data_type(dialect):
    """Test MySQL inherits _validate_data_type."""
    assert dialect._validate_data_type("VARCHAR(255)")
    assert dialect._validate_data_type("INT")
    assert dialect._validate_data_type("BIGINT")
    assert not dialect._validate_data_type("INT; DROP TABLE users--")


def test_mysql_format_column_definition_data_type_validation(dialect):
    """Test column definition validates data_type."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "VARCHAR(255)" in sql


def test_mysql_format_column_definition_data_type_rejects_injection(dialect):
    """Test that malicious data_type is rejected."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255); DROP TABLE users--",
    )

    with pytest.raises(ValueError, match="Invalid data type"):
        dialect.format_column_definition(col_def)


def test_mysql_json_table_path_escaping(dialect):
    """Test JSON_TABLE path is escaped."""
    expr = MySQLJSONTableExpression(
        dialect=dialect,
        json_doc='{"key": "value"}',
        path="$.key's",
        columns=[
            JSONTableColumn(
                name="col1",
                type="VARCHAR(255)",
                path="$.name",
            ),
        ],
    )

    sql, params = dialect.format_json_table_expression(expr)

    assert "key''s" in sql
    assert "'; DROP" not in sql


def test_mysql_json_table_column_path_escaping(dialect):
    """Test JSON_TABLE column path is escaped."""
    expr = MySQLJSONTableExpression(
        dialect=dialect,
        json_doc='{"data": "test"}',
        path="$.data",
        columns=[
            JSONTableColumn(
                name="col1",
                type="VARCHAR(255)",
                path="$.field's",
            ),
        ],
    )

    sql, params = dialect.format_json_table_expression(expr)

    assert "field''s" in sql


def test_mysql_json_table_alias_quoted(dialect):
    """Test JSON_TABLE alias uses format_identifier (backticks for MySQL)."""
    expr = MySQLJSONTableExpression(
        dialect=dialect,
        json_doc='{"data": "test"}',
        path="$.data",
        columns=[
            JSONTableColumn(
                name="col1",
                type="VARCHAR(255)",
                path="$.col1",
            ),
        ],
        alias="test_alias",
    )

    sql, params = dialect.format_json_table_expression(expr)

    # MySQL uses backticks for identifier quotes
    assert "`test_alias`" in sql


def test_mysql_format_cast_expression_valid(dialect):
    """Test that CAST expression validates target_type."""
    sql, params = dialect.format_cast_expression("column", "INTEGER", (), None)
    assert "INTEGER" in sql


def test_mysql_format_cast_expression_rejects_injection(dialect):
    """Test that malicious target_type is rejected."""
    with pytest.raises(ValueError, match="Invalid target type"):
        dialect.format_cast_expression("column", "INTEGER; DROP TABLE users--", (), None)