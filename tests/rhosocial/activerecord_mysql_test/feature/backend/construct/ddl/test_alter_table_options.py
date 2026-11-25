# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/ddl/test_alter_table_options.py
"""MySQL ``ALTER TABLE ... <table options>`` rendering.

MySQL's ``ALTER TABLE`` grammar accepts ``table_options`` as an alter
specification, so an existing table's engine, charset, collation, row format,
comment and auto-increment counter can change in place. Core models table
options for creation only, so the ALTER-time carrier is backend-proprietary.

Pure-construction tests: no database connection is required.
"""

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLAlterTableOptionsStatement,
)


@pytest.fixture
def dialect():
    return MySQLDialect((8, 0, 0))


class TestRendering:
    def test_all_options(self, dialect):
        sql, params = MySQLAlterTableOptionsStatement(
            dialect,
            "orders",
            engine="InnoDB",
            charset="utf8mb4",
            collate="utf8mb4_general_ci",
            row_format="DYNAMIC",
            comment="orders table",
            auto_increment=100,
            database="shop",
        ).to_sql()
        assert sql == (
            "ALTER TABLE `shop`.`orders` ENGINE=InnoDB, DEFAULT CHARSET=utf8mb4, "
            "COLLATE=utf8mb4_general_ci, ROW_FORMAT=DYNAMIC, AUTO_INCREMENT=100, "
            "COMMENT='orders table'"
        )
        assert params == ()

    def test_engine_only(self, dialect):
        sql, _ = MySQLAlterTableOptionsStatement(
            dialect, "orders", engine="InnoDB"
        ).to_sql()
        assert sql == "ALTER TABLE `orders` ENGINE=InnoDB"

    def test_empty_comment_clears(self, dialect):
        sql, _ = MySQLAlterTableOptionsStatement(
            dialect, "orders", comment=""
        ).to_sql()
        assert sql == "ALTER TABLE `orders` COMMENT=''"

    def test_row_format_accepts_lowercase(self, dialect):
        sql, _ = MySQLAlterTableOptionsStatement(
            dialect, "orders", row_format="dynamic"
        ).to_sql()
        assert sql == "ALTER TABLE `orders` ROW_FORMAT=DYNAMIC"

    def test_comment_quotes_are_escaped(self, dialect):
        sql, _ = MySQLAlterTableOptionsStatement(
            dialect, "orders", comment="O'Brien"
        ).to_sql()
        assert "COMMENT='O''Brien'" in sql


class TestRefusals:
    def test_no_options_is_refused(self, dialect):
        with pytest.raises(ValueError, match="at least one option"):
            MySQLAlterTableOptionsStatement(dialect, "orders").to_sql()

    def test_blank_table_is_refused(self, dialect):
        with pytest.raises(ValueError, match="non-empty table name"):
            MySQLAlterTableOptionsStatement(dialect, "  ", engine="InnoDB").to_sql()

    def test_unknown_engine_is_refused(self, dialect):
        with pytest.raises(ValueError):
            MySQLAlterTableOptionsStatement(
                dialect, "orders", engine="NotAStorageEngine"
            ).to_sql()

    def test_unknown_charset_is_refused(self, dialect):
        with pytest.raises(ValueError):
            MySQLAlterTableOptionsStatement(
                dialect, "orders", charset="not-a-charset"
            ).to_sql()

    def test_unknown_row_format_is_refused(self, dialect):
        with pytest.raises(ValueError, match="Unsupported MySQL ROW_FORMAT"):
            MySQLAlterTableOptionsStatement(
                dialect, "orders", row_format="TINY"
            ).to_sql()

    def test_zero_auto_increment_is_refused(self, dialect):
        with pytest.raises(ValueError, match="must be positive"):
            MySQLAlterTableOptionsStatement(
                dialect, "orders", auto_increment=0
            ).to_sql()

    def test_bool_auto_increment_is_refused(self, dialect):
        with pytest.raises(TypeError, match="auto_increment must be an int"):
            MySQLAlterTableOptionsStatement(
                dialect, "orders", auto_increment=True
            ).to_sql()

    def test_non_string_comment_is_refused(self, dialect):
        with pytest.raises(TypeError, match="comment must be a string"):
            MySQLAlterTableOptionsStatement(dialect, "orders", comment=1).to_sql()

    def test_wrong_node_kind_is_refused(self, dialect):
        from rhosocial.activerecord.backend.expression.objects import Table

        with pytest.raises(TypeError):
            dialect.format_mysql_alter_table_options_statement(Table(dialect, "orders"))
