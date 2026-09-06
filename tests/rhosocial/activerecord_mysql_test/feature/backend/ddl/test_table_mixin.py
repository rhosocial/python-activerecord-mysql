# tests/rhosocial/activerecord_mysql_test/feature/backend/ddl/test_table_mixin.py
"""
Tests for the MySQLTableMixin.

These are pure expression-level (no live server needed) tests that pin the
MySQL-specific CREATE TABLE formatting rules implemented in
``src/rhosocial/activerecord/backend/impl/mysql/mixins/table.py``:

- capability flags (LIKE syntax, inline index, storage engine, charset)
- data type validation (single-quote support for ENUM)
- CREATE TABLE / CREATE TABLE ... LIKE formatting
- column definition, table constraint, inline index and storage option formatting

Note: MySQLDialect defines its own ``format_create_table_statement`` family of
methods that shadow part of the mixin. To exercise the mixin implementation
directly, the tests call the unbound mixin methods with the dialect instance as
``self`` (the dialect provides ``format_identifier``/``_escape_sql_string``).
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.mixins.table import MySQLTableMixin


@pytest.fixture
def dialect():
    """Return a MySQLDialect instance for formatting tests."""
    return MySQLDialect(version=(8, 0, 0))


def _column(name="id", data_type=None, constraints=None, comment=None):
    """Build a ColumnDefinition with a default IntegerType."""
    if data_type is None:
        data_type = IntegerType()
    return ColumnDefinition(name, data_type, constraints=constraints or [], comment=comment)


class TestTableMixinCapabilityFlags:
    """Verify MySQL table capability flags exposed by the mixin."""

    def test_supports_table_like_syntax(self, dialect):
        """CREATE TABLE ... LIKE should be reported as supported."""
        assert dialect.supports_table_like_syntax() is True, "MySQL supports CREATE TABLE ... LIKE"

    def test_supports_inline_index(self, dialect):
        """Inline INDEX definitions should be reported as supported."""
        assert dialect.supports_inline_index() is True, "MySQL supports inline index definitions"

    def test_supports_storage_engine_option(self, dialect):
        """ENGINE storage options should be reported as supported."""
        assert dialect.supports_storage_engine_option() is True, "MySQL supports ENGINE storage options"

    def test_supports_charset_option(self, dialect):
        """DEFAULT CHARSET options should be reported as supported."""
        assert dialect.supports_charset_option() is True, "MySQL supports DEFAULT CHARSET options"


class TestValidateDataType:
    """Verify _validate_data_type accepts and rejects data type strings."""

    def test_accepts_plain_type(self):
        """Plain alphanumeric types such as INT should validate."""
        assert MySQLTableMixin._validate_data_type("INT") is True, "plain INT type should validate"

    def test_accepts_parametrized_type(self):
        """Parametrized types such as VARCHAR(255) should validate."""
        assert MySQLTableMixin._validate_data_type("VARCHAR(255)") is True, "VARCHAR(255) should validate"

    def test_accepts_enum_with_quotes(self):
        """MySQL ENUM types with single-quoted values should validate."""
        valid = MySQLTableMixin._validate_data_type("ENUM('draft','published')")
        assert valid is True, "ENUM with quotes should validate"

    def test_accepts_spaces_and_commas(self):
        """Types containing spaces and commas should validate."""
        assert MySQLTableMixin._validate_data_type("DECIMAL(10, 2)") is True, "DECIMAL(10, 2) should validate"

    def test_rejects_semicolon_injection(self):
        """Types containing SQL statement separators should be rejected."""
        valid = MySQLTableMixin._validate_data_type("VARCHAR(255); DROP TABLE x")
        assert valid is False, "semicolon injection rejected"

    def test_rejects_double_quote_injection(self):
        """Types containing double quotes should be rejected."""
        assert MySQLTableMixin._validate_data_type('VARCHAR(255)" OR 1=1') is False, "double quote injection rejected"

    def test_rejects_hyphen_comment_injection(self):
        """Types containing SQL comment markers should be rejected."""
        assert MySQLTableMixin._validate_data_type("INT--comment") is False, "hyphen comment injection rejected"


class TestFormatCreateTableStatement:
    """Verify the mixin format_create_table_statement produces valid CREATE TABLE SQL."""

    def test_basic(self, dialect):
        """A plain CREATE TABLE should quote identifiers and list columns."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id", IntegerType(), [ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)])],
        )
        sql, params = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert sql == "CREATE TABLE `users` (`id` INT PRIMARY KEY)", f"unexpected SQL: {sql}"
        assert params == (), "basic CREATE TABLE has no bound parameters"

    def test_temporary(self, dialect):
        """TEMPORARY should be appended after CREATE TABLE by the mixin."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="tmp_users",
            columns=[_column("id")],
            temporary=True,
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert sql.startswith("CREATE TABLE TEMPORARY"), f"TEMPORARY keyword missing: {sql}"

    def test_if_not_exists(self, dialect):
        """IF NOT EXISTS should appear after CREATE TABLE."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id")],
            if_not_exists=True,
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert "CREATE TABLE IF NOT EXISTS" in sql, f"IF NOT EXISTS missing: {sql}"

    def test_comment(self, dialect):
        """A table comment should be emitted as a quoted COMMENT clause."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id")],
            dialect_options={"comment": "User accounts"},
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert "COMMENT 'User accounts'" in sql, f"table comment missing: {sql}"

    def test_comment_escaped_quote(self, dialect):
        """A table comment containing quotes should be escaped."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id")],
            dialect_options={"comment": "it's"},
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert "COMMENT 'it''s'" in sql, f"comment quote not escaped: {sql}"

    def test_storage_options(self, dialect):
        """ENGINE storage options should be appended after the column list."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id")],
            storage_options={"ENGINE": "InnoDB"},
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert sql.endswith("ENGINE='InnoDB'"), f"storage option missing: {sql}"

    def test_table_constraint_appended(self, dialect):
        """Table-level constraints should be listed after columns."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id")],
            table_constraints=[TableConstraint(TableConstraintType.PRIMARY_KEY, columns=["id"])],
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert "PRIMARY KEY (`id`)" in sql, f"table constraint missing: {sql}"

    def test_inline_index_appended(self, dialect):
        """Inline index definitions should be listed after columns."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[_column("id")],
            indexes=[IndexDefinition("idx_id", ["id"])],
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert "INDEX `idx_id` (`id`)" in sql, f"inline index missing: {sql}"

    def test_like_table_delegation(self, dialect):
        """A like_table dialect option should delegate to format_create_table_like."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users_copy",
            columns=[],
            dialect_options={"like_table": "users"},
        )
        sql, _ = MySQLTableMixin.format_create_table_statement(dialect, expr)
        assert sql == "CREATE TABLE `users_copy` LIKE `users`", f"unexpected SQL: {sql}"


class TestFormatCreateTableLike:
    """Verify mixin format_create_table_like produces CREATE TABLE ... LIKE SQL."""

    def test_single_table(self, dialect):
        """A plain LIKE target should be quoted as an identifier."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users_copy",
            columns=[],
            dialect_options={"like_table": "users"},
        )
        sql, params = MySQLTableMixin.format_create_table_like(dialect, expr)
        assert sql == "CREATE TABLE `users_copy` LIKE `users`", f"unexpected SQL: {sql}"
        assert params == (), "CREATE TABLE ... LIKE takes no bound parameters"

    def test_schema_table_tuple(self, dialect):
        """A (schema, table) LIKE target should be quoted as schema.table."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="users_copy",
            columns=[],
            dialect_options={"like_table": ("app", "users")},
        )
        sql, _ = MySQLTableMixin.format_create_table_like(dialect, expr)
        assert "LIKE `app`.`users`" in sql, f"schema-qualified LIKE target missing: {sql}"

    def test_temporary_and_if_not_exists(self, dialect):
        """TEMPORARY and IF NOT EXISTS should be honored for LIKE tables."""
        expr = CreateTableExpression(
            dialect=dialect,
            table="tmp_users",
            columns=[],
            temporary=True,
            if_not_exists=True,
            dialect_options={"like_table": "users"},
        )
        sql, _ = MySQLTableMixin.format_create_table_like(dialect, expr)
        assert sql.startswith("CREATE TABLE TEMPORARY IF NOT EXISTS"), f"unexpected SQL: {sql}"
        assert sql.endswith("LIKE `users`"), f"LIKE clause missing: {sql}"


class TestFormatColumnDefinition:
    """Verify format_column_definition handles MySQL column syntax."""

    def test_basic_column(self, dialect):
        """A plain column should render name and type."""
        sql, params = dialect.format_column_definition(_column("id", IntegerType()))
        assert sql == "`id` INT", f"unexpected SQL: {sql}"
        assert params == [], "no parameters expected for plain column"

    def test_not_null_constraint(self, dialect):
        """NOT NULL constraints should be appended."""
        col = _column(
            "name",
            VarCharType(dialect=dialect, length=100),
            [ColumnConstraint(ColumnConstraintType.NOT_NULL)],
        )
        sql, _ = dialect.format_column_definition(col)
        assert sql == "`name` VARCHAR(100) NOT NULL", f"unexpected SQL: {sql}"

    def test_auto_increment(self, dialect):
        """AUTO_INCREMENT should be appended for auto-increment columns."""
        col = _column(
            "id",
            IntegerType(),
            [ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)],
        )
        sql, _ = dialect.format_column_definition(col)
        assert sql == "`id` INT PRIMARY KEY AUTO_INCREMENT", f"unexpected SQL: {sql}"

    def test_column_comment(self, dialect):
        """Column comments should be emitted as quoted COMMENT clauses."""
        col = _column("id", IntegerType(), comment="primary key")
        sql, _ = dialect.format_column_definition(col)
        assert sql == "`id` INT COMMENT 'primary key'", f"unexpected SQL: {sql}"


class TestFormatTableConstraint:
    """Verify mixin format_table_constraint handles table-level constraints."""

    def test_primary_key(self, dialect):
        """PRIMARY KEY constraints should list the referenced columns."""
        tc = TableConstraint(TableConstraintType.PRIMARY_KEY, columns=["id"])
        sql, params = MySQLTableMixin.format_table_constraint(dialect, tc)
        assert sql == "PRIMARY KEY (`id`)", f"unexpected SQL: {sql}"
        assert params == [], "PK constraint has no parameters"

    def test_primary_key_multiple_columns(self, dialect):
        """Composite PRIMARY KEY constraints should list all columns."""
        tc = TableConstraint(TableConstraintType.PRIMARY_KEY, columns=["a", "b"])
        sql, _ = MySQLTableMixin.format_table_constraint(dialect, tc)
        assert sql == "PRIMARY KEY (`a`, `b`)", f"unexpected SQL: {sql}"

    def test_unique(self, dialect):
        """UNIQUE constraints should list the referenced columns."""
        tc = TableConstraint(TableConstraintType.UNIQUE, columns=["email"])
        sql, _ = MySQLTableMixin.format_table_constraint(dialect, tc)
        assert sql == "UNIQUE (`email`)", f"unexpected SQL: {sql}"

    def test_named_constraint(self, dialect):
        """Named constraints should be prefixed with CONSTRAINT."""
        tc = TableConstraint(TableConstraintType.UNIQUE, name="uq_email", columns=["email"])
        sql, _ = MySQLTableMixin.format_table_constraint(dialect, tc)
        assert sql == "CONSTRAINT `uq_email` UNIQUE (`email`)", f"unexpected SQL: {sql}"

    def test_foreign_key(self, dialect):
        """FOREIGN KEY constraints should reference the target table and columns."""
        tc = TableConstraint(
            TableConstraintType.FOREIGN_KEY,
            columns=["user_id"],
            foreign_key_table="users",
            foreign_key_columns=["id"],
        )
        sql, _ = MySQLTableMixin.format_table_constraint(dialect, tc)
        assert sql == "FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)", f"unexpected SQL: {sql}"

    def test_empty_constraint(self, dialect):
        """A constraint with no resolvable branch should produce an empty string."""
        tc = TableConstraint(TableConstraintType.CHECK, columns=None)
        sql, _ = MySQLTableMixin.format_table_constraint(dialect, tc)
        assert sql == "", "unhandled constraint type should render as empty"


class TestFormatInlineIndex:
    """Verify mixin format_inline_index renders MySQL inline INDEX definitions."""

    def test_basic(self, dialect):
        """A plain index should render INDEX with its columns."""
        idx = IndexDefinition("idx_id", ["id"])
        sql = MySQLTableMixin.format_inline_index(dialect, idx)
        assert sql == "INDEX `idx_id` (`id`)", f"unexpected SQL: {sql}"

    def test_unique(self, dialect):
        """UNIQUE indexes should be prefixed with UNIQUE."""
        idx = IndexDefinition("uq_email", ["email"], unique=True)
        sql = MySQLTableMixin.format_inline_index(dialect, idx)
        assert sql == "UNIQUE INDEX `uq_email` (`email`)", f"unexpected SQL: {sql}"

    def test_multiple_columns(self, dialect):
        """Composite indexes should list all indexed columns."""
        idx = IndexDefinition("idx_name_age", ["name", "age"])
        sql = MySQLTableMixin.format_inline_index(dialect, idx)
        assert sql == "INDEX `idx_name_age` (`name`, `age`)", f"unexpected SQL: {sql}"

    def test_with_type(self, dialect):
        """Index types should be emitted with a USING clause."""
        idx = IndexDefinition("idx_name", ["name"], type="BTREE")
        sql = MySQLTableMixin.format_inline_index(dialect, idx)
        assert sql == "INDEX `idx_name` (`name`) USING BTREE", f"unexpected SQL: {sql}"


class TestFormatStorageOptions:
    """Verify format_storage_options handles string and non-string values."""

    def test_string_value(self, dialect):
        """String storage option values should be single-quoted."""
        sql = dialect.format_storage_options({"ENGINE": "InnoDB"})
        assert sql == "ENGINE='InnoDB'", f"unexpected SQL: {sql}"

    def test_non_string_value(self, dialect):
        """Numeric storage option values should not be quoted."""
        sql = dialect.format_storage_options({"AUTO_INCREMENT": 100})
        assert sql == "AUTO_INCREMENT=100", f"unexpected SQL: {sql}"

    def test_multiple_options(self, dialect):
        """Multiple storage options should be joined by spaces."""
        sql = dialect.format_storage_options({"ENGINE": "InnoDB", "AUTO_INCREMENT": 5})
        assert sql == "ENGINE='InnoDB' AUTO_INCREMENT=5", f"unexpected SQL: {sql}"

    def test_string_value_escaped(self, dialect):
        """String storage option values with quotes should be escaped."""
        sql = dialect.format_storage_options({"COMMENT": "it's"})
        assert sql == "COMMENT='it''s'", f"unexpected SQL: {sql}"