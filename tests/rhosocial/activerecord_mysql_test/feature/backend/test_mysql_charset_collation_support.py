# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_charset_collation_support.py
"""MySQL charset / collation / storage-engine capability protocol tests.

The dialect exposes a version-aware whitelist and validation interface; table
options validate user input at construction time instead of storing arbitrary
strings.
"""

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import MySQLCreateTableOptions
from rhosocial.activerecord.backend.impl.mysql.mixins import (
    MySQLCharset,
    MySQLStorageEngine,
)
from rhosocial.activerecord.backend.impl.mysql.protocols import (
    MySQLCharsetCollationSupport,
)


def test_dialect_implements_protocol():
    assert isinstance(MySQLDialect(version=(8, 0, 0)), MySQLCharsetCollationSupport)


def test_validate_charset_accepts_enum_and_string():
    dialect = MySQLDialect(version=(8, 0, 0))
    assert dialect.validate_charset_name(MySQLCharset.UTF8MB4) == "utf8mb4"
    assert dialect.validate_charset_name("UTF8MB4") == "utf8mb4"
    with pytest.raises(ValueError):
        dialect.validate_charset_name("not_a_charset")


def test_validate_storage_engine_normalizes_case():
    dialect = MySQLDialect(version=(8, 0, 0))
    assert dialect.validate_storage_engine_name(MySQLStorageEngine.INNODB) == "InnoDB"
    assert dialect.validate_storage_engine_name("innodb") == "InnoDB"
    with pytest.raises(ValueError):
        dialect.validate_storage_engine_name("Evil")


def test_validate_collation_rejects_unknown():
    dialect = MySQLDialect(version=(8, 0, 0))
    assert dialect.validate_collation_by_name("UTF8MB4_UNICODE_CI") == "utf8mb4_unicode_ci"
    with pytest.raises(ValueError):
        dialect.validate_collation_by_name("not_a_collation")


def test_table_options_reject_unknown_values():
    dialect = MySQLDialect(version=(8, 0, 0))
    with pytest.raises(ValueError):
        MySQLCreateTableOptions(dialect, engine="Evil")
    with pytest.raises(ValueError):
        MySQLCreateTableOptions(dialect, charset="not_a_charset")
    with pytest.raises(ValueError):
        MySQLCreateTableOptions(dialect, collate="not_a_collation")


def test_charset_version_gating():
    assert MySQLDialect(version=(5, 5, 3)).supports_charset("utf8mb4") is True
    assert MySQLDialect(version=(5, 5, 2)).supports_charset("utf8mb4") is False


def test_auto_increment_and_row_format_rendered():
    from rhosocial.activerecord.backend.expression import CreateTableExpression
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
    from rhosocial.activerecord.backend.expression.types import IntegerType
    from rhosocial.activerecord.backend.impl.mysql.expression import MySQLRowFormat

    dialect = MySQLDialect(version=(8, 0, 0))
    options = MySQLCreateTableOptions(
        dialect, auto_increment=1000, row_format=MySQLRowFormat.DYNAMIC
    )
    expr = CreateTableExpression(
        dialect,
        "t",
        [ColumnDefinition(dialect, "id", IntegerType(dialect))],
        table_options=options,
    )
    sql, _ = expr.to_sql()
    assert "AUTO_INCREMENT=1000" in sql
    assert "ROW_FORMAT=DYNAMIC" in sql


def test_invalid_row_format_rejected():
    with pytest.raises(ValueError):
        MySQLCreateTableOptions(MySQLDialect(version=(8, 0, 0)), row_format="EVIL")


def test_invalid_auto_increment_rejected():
    with pytest.raises(ValueError):
        MySQLCreateTableOptions(MySQLDialect(version=(8, 0, 0)), auto_increment=0)
