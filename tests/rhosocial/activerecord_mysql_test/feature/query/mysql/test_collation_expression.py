# tests/rhosocial/activerecord_mysql_test/feature/query/mysql/test_collation_expression.py
"""
Tests for expression-level COLLATE support on MySQL.
"""

import pytest

from rhosocial.activerecord.backend.expression import CollationName, Column, Literal
from rhosocial.activerecord.backend.impl.mysql import (
    MySQLCollation,
    MySQLCollationValidator,
    MySQLDialect,
)


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


@pytest.fixture
def collation_table(mysql_backend):
    mysql_backend.execute("DROP TABLE IF EXISTS test_collation_expression")
    mysql_backend.execute("""
        CREATE TABLE test_collation_expression (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    mysql_backend.execute("""
        INSERT INTO test_collation_expression (name)
        VALUES ('Alice'), ('alice'), ('Bob')
    """)
    yield "test_collation_expression"
    mysql_backend.execute("DROP TABLE IF EXISTS test_collation_expression")


class TestMySQLCollationValidator:
    def test_supports_known_legacy_collation(self):
        assert MySQLCollationValidator.is_supported("utf8mb4_unicode_ci", (5, 7, 0))

    def test_rejects_mysql_8_collation_on_older_version(self):
        assert not MySQLCollationValidator.is_supported("utf8mb4_0900_ai_ci", (5, 7, 0))
        assert MySQLCollationValidator.is_supported("utf8mb4_0900_ai_ci", (8, 0, 0))

    def test_validate_normalizes_case(self):
        assert MySQLCollationValidator.validate("UTF8MB4_BIN", (5, 7, 0)) == "utf8mb4_bin"

    def test_validate_rejects_unknown_collation(self):
        with pytest.raises(ValueError, match="Unsupported MySQL collation"):
            MySQLCollationValidator.validate("unknown_ci", (8, 0, 0))

    def test_enum_contains_representative_collations(self):
        values = {collation.value for collation in MySQLCollation}

        assert "binary" in values
        assert "latin1_swedish_ci" in values
        assert "utf8mb4_unicode_ci" in values
        assert "utf8mb4_0900_ai_ci" in values
        assert "utf8mb4_ja_0900_as_cs" in values


class TestMySQLCollationExpression:
    def test_column_collate_generates_sql(self, dialect):
        expr = Column(dialect, "name", table="users").collate(MySQLCollation.UTF8MB4_BIN)

        sql, params = expr.to_sql()

        assert sql == "`users`.`name` COLLATE utf8mb4_bin"
        assert params == ()

    def test_literal_collate_preserves_parameter_binding(self, dialect):
        expr = Literal(dialect, "Alice").collate(MySQLCollation.UTF8MB4_0900_AI_CI)

        sql, params = expr.to_sql()

        assert sql == "%s COLLATE utf8mb4_0900_ai_ci"
        assert params == ("Alice",)

    def test_rejects_schema_qualified_collation(self, dialect):
        expr = Column(dialect, "name").collate(CollationName("utf8mb4_bin", schema="public"))

        with pytest.raises(Exception, match="schema-qualified or keyword COLLATE"):
            expr.to_sql()

    def test_rejects_unsupported_collation(self, dialect):
        expr = Column(dialect, "name").collate("unknown_ci")

        with pytest.raises(ValueError, match="Unsupported MySQL collation"):
            expr.to_sql()

    def test_rejects_mysql_8_collation_on_older_version(self):
        dialect = MySQLDialect(version=(5, 7, 0))
        expr = Column(dialect, "name").collate(MySQLCollation.UTF8MB4_0900_AI_CI)

        with pytest.raises(ValueError, match="requires MySQL 8.0"):
            expr.to_sql()

    def test_collate_executes_case_sensitive_match(self, mysql_backend, collation_table):
        expr = Column(mysql_backend.dialect, "name", table=collation_table).collate(
            MySQLCollation.UTF8MB4_BIN
        )
        sql, params = expr.to_sql()

        rows = mysql_backend.fetch_all(
            f"SELECT name FROM `{collation_table}` WHERE {sql} = %s ORDER BY id",
            (*params, "Alice"),
        )

        assert [row["name"] for row in rows] == ["Alice"]

    def test_collate_executes_case_insensitive_match(self, mysql_backend, collation_table):
        expr = Column(mysql_backend.dialect, "name", table=collation_table).collate(
            MySQLCollation.UTF8MB4_UNICODE_CI
        )
        sql, params = expr.to_sql()

        rows = mysql_backend.fetch_all(
            f"SELECT name FROM `{collation_table}` WHERE {sql} = %s ORDER BY id",
            (*params, "Alice"),
        )

        assert [row["name"] for row in rows] == ["Alice", "alice"]
