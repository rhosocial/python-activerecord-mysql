# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_type_domain_negative.py
"""Explicit negative contracts for MySQL TYPE and DOMAIN DDL."""

from __future__ import annotations

from typing import Tuple

import pytest

from rhosocial.activerecord.backend.dialect import (
    DataTypeMixin,
    DataTypeSupport,
    DomainMixin,
    DomainSupport,
    UserDefinedTypeMixin,
    UserDefinedTypeSupport,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import BaseExpression, Literal
from rhosocial.activerecord.backend.expression.statements import (
    AlterDomainExpression,
    AlterTypeExpression,
    CreateDomainExpression,
    CreateTypeExpression,
    DomainCheckConstraint,
    DomainNullability,
    DomainValueExpression,
    DropDomainDefaultAction,
    DropDomainExpression,
    DropTypeExpression,
    TypeAlterAction,
    TypeDefinition,
)
from rhosocial.activerecord.backend.expression.types import DataType, IntegerType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLEnumType, MySQLSetType
from rhosocial.activerecord.backend.impl.mysql.mixins import MySQLTypeSupportMixin


class _TestTypeDefinition(TypeDefinition):
    @property
    def definition_kind(self) -> str:
        return "negative"


class _TestTypeAlterAction(TypeAlterAction):
    @property
    def action_kind(self) -> str:
        return "negative"


TYPE_SUPPORT_FLAGS = (
    "supports_type_objects",
    "supports_create_type",
    "supports_alter_type",
    "supports_drop_type",
    "supports_create_type_if_not_exists",
    "supports_create_type_or_replace",
    "supports_alter_type_if_exists",
    "supports_drop_type_if_exists",
    "supports_multiple_type_alter_actions",
)

DOMAIN_SUPPORT_FLAGS = (
    "supports_domains",
    "supports_create_domain",
    "supports_alter_domain",
    "supports_drop_domain",
    "supports_domain_default",
    "supports_domain_checks",
    "supports_named_domain_checks",
    "supports_multiple_domain_checks",
    "supports_domain_collation",
    "supports_multiple_domain_alter_actions",
    "supports_drop_domain_if_exists",
    "supports_drop_domain_cascade",
    "supports_drop_domain_restrict",
    "supports_unnamed_domain_check_drop",
)

TYPE_FORMATTERS = (
    "format_create_type_statement",
    "format_alter_type_statement",
    "format_drop_type_statement",
    "format_type_definition",
    "format_type_alter_action",
)

DOMAIN_FORMATTERS = (
    "format_create_domain_statement",
    "format_alter_domain_statement",
    "format_drop_domain_statement",
    "format_domain_value_expression",
    "format_domain_check_constraint",
    "format_domain_alter_action",
)


@pytest.fixture
def dialect() -> MySQLDialect:
    return MySQLDialect(version=(8, 0, 0))


def _type_nodes(dialect: MySQLDialect) -> Tuple[BaseExpression, ...]:
    definition = _TestTypeDefinition(dialect)
    action = _TestTypeAlterAction(dialect)
    return (
        CreateTypeExpression(dialect, "status", definition),
        AlterTypeExpression(dialect, "status", [action]),
        DropTypeExpression(dialect, "status"),
        definition,
        action,
    )


def _domain_nodes(dialect: MySQLDialect) -> Tuple[BaseExpression, ...]:
    condition = DomainValueExpression(dialect) > Literal(dialect, 0, inline_literals=True)
    check = DomainCheckConstraint(dialect, condition)
    return (
        CreateDomainExpression(dialect, "positive", IntegerType(dialect)),
        AlterDomainExpression(dialect, "positive", [DropDomainDefaultAction(dialect)]),
        DropDomainExpression(dialect, "positive"),
        DomainValueExpression(dialect),
        check,
        DropDomainDefaultAction(dialect),
    )


def test_type_and_domain_protocols_are_composed(dialect: MySQLDialect) -> None:
    assert isinstance(dialect, UserDefinedTypeSupport)
    assert isinstance(dialect, DomainSupport)
    assert isinstance(dialect, UserDefinedTypeMixin)
    assert isinstance(dialect, DomainMixin)
    assert isinstance(dialect, DataTypeSupport)


def test_type_and_domain_mixins_precede_protocols() -> None:
    mro = MySQLDialect.__mro__
    assert mro.index(UserDefinedTypeMixin) < mro.index(UserDefinedTypeSupport)
    assert mro.index(DomainMixin) < mro.index(DomainSupport)
    assert mro.index(DataTypeMixin) < mro.index(DataTypeSupport)
    assert mro.index(MySQLTypeSupportMixin) < mro.index(DataTypeSupport)
    assert issubclass(MySQLTypeSupportMixin, DataTypeMixin)
    assert issubclass(MySQLTypeSupportMixin, DataTypeSupport)
    assert not issubclass(MySQLTypeSupportMixin, UserDefinedTypeMixin)
    assert not issubclass(MySQLTypeSupportMixin, DomainMixin)


def test_core_type_and_domain_formatters_own_the_mro() -> None:
    for method_name in TYPE_FORMATTERS:
        assert getattr(MySQLDialect, method_name) is getattr(
            UserDefinedTypeMixin,
            method_name,
        )
    for method_name in DOMAIN_FORMATTERS:
        assert getattr(MySQLDialect, method_name) is getattr(
            DomainMixin,
            method_name,
        )


def test_schema_level_type_and_domain_support_is_false(dialect: MySQLDialect) -> None:
    for name in TYPE_SUPPORT_FLAGS + DOMAIN_SUPPORT_FLAGS:
        assert getattr(dialect, name)() is False, name
    assert dialect.supports_type_definition(_TestTypeDefinition) is False
    assert dialect.supports_type_alter_action(_TestTypeAlterAction) is False
    for nullability in DomainNullability:
        assert dialect.supports_domain_nullability(nullability) is False
    assert dialect.supports_alter_domain_action(DropDomainDefaultAction) is False
    assert dialect.supported_type_definitions() == ()


def test_type_formatters_and_expressions_fail_fast(dialect: MySQLDialect) -> None:
    nodes = _type_nodes(dialect)
    for formatter_name, node in zip(TYPE_FORMATTERS, nodes):
        with pytest.raises(UnsupportedFeatureError):
            getattr(dialect, formatter_name)(node)
        with pytest.raises(UnsupportedFeatureError):
            node.to_sql()


def test_domain_formatters_and_expressions_fail_fast(dialect: MySQLDialect) -> None:
    nodes = _domain_nodes(dialect)
    for formatter_name, node in zip(DOMAIN_FORMATTERS, nodes):
        with pytest.raises(UnsupportedFeatureError):
            getattr(dialect, formatter_name)(node)
        with pytest.raises(UnsupportedFeatureError):
            node.to_sql()


def test_enum_and_set_remain_data_types(dialect: MySQLDialect) -> None:
    enum_type = MySQLEnumType(dialect, ["a", "b"])
    set_type = MySQLSetType(dialect, ["a", "b"])

    assert isinstance(enum_type, DataType)
    assert isinstance(set_type, DataType)
    assert not isinstance(enum_type, TypeDefinition)
    assert not isinstance(set_type, TypeDefinition)
    assert dialect.supports_data_type_mysql_enum() is True
    assert dialect.supports_data_type_mysql_set() is True
    assert enum_type.to_sql()[0] == "ENUM('a','b')"
    assert set_type.to_sql()[0] == "SET('a','b')"
