# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/mixins/test_mysql_charset_collation_support.py
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
from rhosocial.activerecord.backend.expression.objects import Table


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
    legacy = MySQLDialect(version=(5, 5, 2))
    modern = MySQLDialect(version=(5, 5, 3))
    assert "utf8mb4" not in legacy.supported_charsets()
    with pytest.raises(ValueError):
        legacy.validate_charset_name("utf8mb4")
    assert "utf8mb4" in modern.supported_charsets()
    assert modern.validate_charset_name("utf8mb4") == "utf8mb4"


def test_every_builtin_engine_has_a_parameterless_switch():
    """Storage-engine support is asked one engine at a time, never by name."""
    dialect = MySQLDialect(version=(8, 0, 0))
    for switch in (
        "supports_storage_engine_innodb",
        "supports_storage_engine_myisam",
        "supports_storage_engine_memory",
        "supports_storage_engine_csv",
        "supports_storage_engine_archive",
        "supports_storage_engine_blackhole",
        "supports_storage_engine_mrg_myisam",
        "supports_storage_engine_federated",
        "supports_storage_engine_ndb",
        "supports_storage_engine_ndbcluster",
        "supports_storage_engine_example",
        "supports_storage_engine_performance_schema",
        "supports_storage_engine_temporary",
    ):
        assert getattr(dialect, switch)() is True
    assert getattr(dialect, "supports_storage_engine", None) is None


def test_engine_switches_mirror_the_available_set():
    """A switch is True exactly when its engine is in the available set."""
    dialect = MySQLDialect(version=(8, 0, 0))
    available = dialect.supported_storage_engines()
    assert dialect.supports_storage_engine_innodb() is ("InnoDB" in available)
    assert dialect.supports_storage_engine_mrg_myisam() is ("MRG_MyISAM" in available)


def test_text_encoding_suggestion_uses_the_version_default_collation():
    from rhosocial.activerecord.backend.suggestion.definitions import (
        TextEncodingSuggestion,
    )

    modern = MySQLDialect(version=(8, 0, 0)).suggest_text_encoding()
    assert isinstance(modern, TextEncodingSuggestion)
    assert modern.charset == "utf8mb4"
    assert modern.collation == "utf8mb4_0900_ai_ci"

    legacy = MySQLDialect(version=(5, 7, 0)).suggest_text_encoding()
    assert legacy.charset == "utf8mb4"
    assert legacy.collation == "utf8mb4_general_ci"


def test_storage_engine_suggestion_is_transactional_innodb():
    from rhosocial.activerecord.backend.suggestion.definitions import (
        StorageEngineSuggestion,
    )

    suggestion = MySQLDialect(version=(8, 0, 0)).suggest_storage_engine()
    assert isinstance(suggestion, StorageEngineSuggestion)
    assert suggestion.engine == "InnoDB"
    assert suggestion.transactional is True


def test_suggestion_protocols_are_answered():
    from rhosocial.activerecord.backend.suggestion.protocols import (
        StorageEngineSuggestionSupport,
        TextEncodingSuggestionSupport,
    )

    dialect = MySQLDialect(version=(8, 0, 0))
    assert isinstance(dialect, TextEncodingSuggestionSupport)
    assert isinstance(dialect, StorageEngineSuggestionSupport)


def test_auto_increment_and_row_format_rendered():
    from rhosocial.activerecord.backend.expression import CreateTableStatement
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
    from rhosocial.activerecord.backend.expression.types import IntegerType
    from rhosocial.activerecord.backend.impl.mysql.expression import MySQLRowFormat

    dialect = MySQLDialect(version=(8, 0, 0))
    options = MySQLCreateTableOptions(
        dialect, auto_increment=1000, row_format=MySQLRowFormat.DYNAMIC
    )
    expr = CreateTableStatement(
        dialect,
        Table(dialect, "t"),
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
