# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_type_protocol.py
"""
MySQL type protocol conformance tests.

Verifies the two-level data-type contract between the core ``DataType``
system and the MySQL backend:

- ``supports_data_type_<name>`` / ``format_data_type_<name>`` 1:1
  correspondence on ``MySQLDialect``;
- ``supports_data_types()`` merges the ``mysql_*`` namespaced family with
  the core family;
- ``suggested_data_types()`` values are real ``DataType`` classes and its
  keys are disjoint from the supported keys;
- ``MySQLEnumType`` renders ``ENUM('a','b')`` (with charset/collation
  extensions);
- dialect-specific range checks live in the formatters (DECIMAL/FLOAT
  precision, fractional-seconds precision);
- ``dialect_options`` forwards through construction and participates in
  equality.
"""

import pytest

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.expression.types import (
    DataType,
    DecimalType,
    FloatType,
    IntegerType,
    TimestampType,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLEnumType,
    MySQLIntType,
    MySQLSetType,
)


@pytest.fixture
def dialect():
    return MySQLDialect()


class TestSupportFormatCorrespondence:
    """Every format_data_type_<name> has supports_data_type_<name>, 1:1."""

    def test_format_family_equals_supports_family(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MySQLDialect)
            if member.startswith("format_data_type_")
        }
        support_names = {
            member[len("supports_data_type_"):]
            for member in dir(MySQLDialect)
            if member.startswith("supports_data_type_")
        }
        assert format_names, "MySQLDialect must implement format_data_type_* members"
        assert format_names == support_names

    def test_supports_data_types_covers_every_formatter(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MySQLDialect)
            if member.startswith("format_data_type_")
        }
        supported = dialect.supports_data_types()
        assert set(supported) == format_names

    def test_supports_data_types_returns_classes(self, dialect):
        for name, klass in dialect.supports_data_types().items():
            assert isinstance(klass, type), name
            assert issubclass(klass, DataType), name

    def test_inherits_mixin_scan_implementation(self, dialect):
        # The merge comes from DDLTypeMixin's scan-based
        # supports_data_types(); MySQL only declares the per-type pairs.
        assert MySQLDialect.supports_data_types is DDLTypeMixin.supports_data_types


class TestSupportsDataTypesMapping:
    """supports_data_types() merges mysql_* namespaced and core entries."""

    def test_includes_mysql_namespaced_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "mysql_int" in supported
        assert supported["mysql_int"] is MySQLIntType
        assert "mysql_enum" in supported
        assert "mysql_set" in supported
        assert "mysql_vector" in supported

    def test_includes_core_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "integer" in supported
        assert supported["integer"] is IntegerType
        assert "varchar" in supported
        assert "decimal" in supported
        assert "json" in supported

    def test_per_type_support_methods_are_truthful(self, dialect):
        supported = dialect.supports_data_types()
        for name in supported:
            checker = getattr(dialect, f"supports_data_type_{name}")
            assert checker() is True, name


class TestSuggestedDataTypes:
    """suggested_data_types(): real classes, disjoint from supported keys."""

    def test_values_are_data_type_classes(self, dialect):
        suggestions = dialect.suggested_data_types()
        for key, klass in suggestions.items():
            assert isinstance(klass, type), key
            assert issubclass(klass, DataType), key

    def test_keys_disjoint_from_supported(self, dialect):
        suggestions = dialect.suggested_data_types()
        supported = dialect.supports_data_types()
        assert not (set(suggestions) & set(supported))

    def test_uuid_suggested_as_fixed_length_binary(self, dialect):
        suggestions = dialect.suggested_data_types()
        # MySQL has no native UUID type; the convention is BINARY(16).
        assert "uuid" in suggestions
        klass = suggestions["uuid"]
        sql, _ = klass(dialect, 16).to_sql()
        assert sql == "BINARY(16)"

    def test_enum_suggested_as_mysql_enum(self, dialect):
        suggestions = dialect.suggested_data_types()
        assert suggestions.get("enum") is MySQLEnumType


class TestMySQLEnumRendering:
    """MySQLEnumType inherits core EnumType; rendering keeps extensions."""

    def test_simple_enum(self, dialect):
        enum_type = MySQLEnumType(dialect, values=["a", "b"])
        assert enum_type.name == "mysql_enum"
        sql, params = enum_type.to_sql()
        assert sql == "ENUM('a','b')"
        assert params == ()

    def test_enum_with_charset_and_collation(self, dialect):
        enum_type = MySQLEnumType(
            dialect, values=["a", "b"],
            charset="utf8mb4", collation="utf8mb4_bin",
        )
        sql, _ = enum_type.to_sql()
        assert "ENUM('a','b')" in sql
        assert "CHARACTER SET utf8mb4" in sql
        assert "COLLATE utf8mb4_bin" in sql

    def test_enum_requires_non_empty_values(self, dialect):
        with pytest.raises(ValueError):
            MySQLEnumType(dialect, values=[])
        with pytest.raises(ValueError):
            MySQLEnumType(dialect, values=None)

    def test_set_type_still_renders_set(self, dialect):
        set_type = MySQLSetType(dialect, values=["read", "write"])
        sql, _ = set_type.to_sql()
        assert sql == "SET('read','write')"


class TestDialectRangeValidation:
    """Dialect-specific range checks live inside the formatters."""

    def test_decimal_precision_over_65_raises(self, dialect):
        data_type = DecimalType(dialect, 66, 2)
        with pytest.raises(ValueError, match="between 1 and 65"):
            dialect.format_data_type(data_type)

    def test_decimal_scale_over_30_raises(self, dialect):
        data_type = DecimalType(dialect, 65, 31)
        with pytest.raises(ValueError, match="between 0 and 30"):
            dialect.format_data_type(data_type)

    def test_decimal_scale_over_precision_raises(self, dialect):
        data_type = DecimalType(dialect, 10, 11)
        with pytest.raises(ValueError, match="cannot exceed"):
            dialect.format_data_type(data_type)

    def test_decimal_valid_range_renders(self, dialect):
        sql, _ = dialect.format_data_type(DecimalType(dialect, 65, 30))
        assert sql == "DECIMAL(65, 30)"

    def test_float_precision_over_53_raises(self, dialect):
        with pytest.raises(ValueError, match="between 1 and 53"):
            dialect.format_data_type(FloatType(dialect, 54))

    def test_timestamp_precision_over_6_raises(self, dialect):
        with pytest.raises(ValueError, match="between 0 and 6"):
            dialect.format_data_type(TimestampType(dialect, 7))

    def test_timestamp_valid_precision_renders(self, dialect):
        sql, _ = dialect.format_data_type(TimestampType(dialect, 6))
        assert sql == "TIMESTAMP(6)"


class TestDialectOptions:
    """dialect_options forwards through construction and affects equality."""

    def test_construction_forwards_dialect_options(self, dialect):
        data_type = MySQLIntType(dialect, unsigned=True,
                                 dialect_options={"display_width": 10})
        assert data_type.dialect_options == {"display_width": 10}

    def test_dialect_options_participate_in_equality(self, dialect):
        a = MySQLIntType(dialect, unsigned=True,
                         dialect_options={"display_width": 10})
        b = MySQLIntType(dialect, unsigned=True,
                         dialect_options={"display_width": 10})
        c = MySQLIntType(dialect, unsigned=True,
                         dialect_options={"display_width": 11})
        assert a == b
        assert a != c

    def test_equality_ignores_dialect(self, dialect):
        other = MySQLDialect()
        assert MySQLIntType(dialect, unsigned=True) == MySQLIntType(other, unsigned=True)

    def test_semantic_params_drive_equality(self, dialect):
        assert MySQLIntType(dialect, unsigned=True) != MySQLIntType(dialect)
        assert MySQLEnumType(dialect, values=["a"]) != MySQLEnumType(dialect, values=["b"])
        assert MySQLEnumType(dialect, values=["a"]) == MySQLEnumType(dialect, values=["a"])
