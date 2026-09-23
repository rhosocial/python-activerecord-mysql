# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_column_definition.py
"""Tests for the MySQL-specific column definition expressions."""

import pytest

from rhosocial.activerecord.backend.expression import ColumnDefinition
from rhosocial.activerecord.backend.expression import ColumnCommentClause
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLColumnDefinition,
    MySQLColumnFormat,
    MySQLColumnOptions,
    MySQLColumnStorage,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.mysql import MySQLDialect

    return MySQLDialect((8, 0, 0))


def _column(dialect, **kwargs):
    return MySQLColumnDefinition(dialect, "name", VarCharType(dialect, length=50), **kwargs)


def test_derives_generic_column_definition():
    col = MySQLColumnDefinition.__mro__
    assert ColumnDefinition in col
    assert issubclass(MySQLColumnDefinition, ColumnDefinition)


def test_character_set(dialect):
    sql, _ = _column(dialect, character_set="utf8mb4").to_sql()
    assert sql == "`name` VARCHAR(50) CHARACTER SET `utf8mb4`"


def test_column_format(dialect):
    sql, _ = _column(dialect, column_format=MySQLColumnFormat.FIXED).to_sql()
    assert sql == "`name` VARCHAR(50) COLUMN_FORMAT FIXED"


def test_storage(dialect):
    sql, _ = _column(dialect, storage=MySQLColumnStorage.DISK).to_sql()
    assert sql == "`name` VARCHAR(50) STORAGE DISK"


def test_invisible(dialect):
    sql, _ = _column(dialect, invisible=True).to_sql()
    assert sql == "`name` VARCHAR(50) INVISIBLE"


def test_combined_attributes(dialect):
    sql, _ = _column(
        dialect,
        character_set="utf8mb4",
        column_format=MySQLColumnFormat.DYNAMIC,
        storage=MySQLColumnStorage.MEMORY,
        invisible=True,
    ).to_sql()
    assert sql == (
        "`name` VARCHAR(50) CHARACTER SET `utf8mb4` "
        "COLUMN_FORMAT DYNAMIC STORAGE MEMORY INVISIBLE"
    )


def test_generic_column_still_renders_on_mysql(dialect):
    """MySQL format_column_definition accepts the generic ColumnDefinition too."""
    generic = ColumnDefinition(dialect, "name", VarCharType(dialect, length=50), comment=ColumnCommentClause(dialect, "c"))
    sql, _ = generic.to_sql()
    assert sql == "`name` VARCHAR(50) COMMENT 'c'"


def test_invalid_column_format_type(dialect):
    with pytest.raises(TypeError, match="MySQLColumnFormat"):
        _column(dialect, column_format="FIXED")


def test_options_select_mysql_column_class():
    options = MySQLColumnOptions(character_set="utf8mb4")
    assert options.column_definition_class() is MySQLColumnDefinition


def test_options_apply_to(dialect):
    options = MySQLColumnOptions(
        character_set="utf8mb4", invisible=True, storage=MySQLColumnStorage.DISK
    )
    col = MySQLColumnDefinition(dialect, "c", VarCharType(dialect, length=10))
    options.apply_to(col)
    assert col.character_set == "utf8mb4"
    assert col.invisible is True
    assert col.storage is MySQLColumnStorage.DISK


def test_options_apply_to_rejects_generic_column(dialect):
    options = MySQLColumnOptions(character_set="utf8mb4")
    generic = ColumnDefinition(dialect, "c", VarCharType(dialect, length=10))
    with pytest.raises(TypeError, match="MySQLColumnDefinition"):
        options.apply_to(generic)


def test_options_invalid_storage_type():
    with pytest.raises(TypeError, match="MySQLColumnStorage"):
        MySQLColumnOptions(storage="DISK")
