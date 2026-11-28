# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/types/test_type_domain_negative.py
"""Explicit negative contracts for MySQL TYPE and DOMAIN DDL."""

from __future__ import annotations

from typing import Tuple

import pytest

from rhosocial.activerecord.backend.dialect import (
    DataTypeMixin,
    DataTypeSupport,
    DomainMixin,
    UserDefinedTypeMixin,
)
from rhosocial.activerecord.backend.dialect.protocols import (
    AlterDomainSupport,
    AlterTypeSupport,
    CreateDomainSupport,
    CreateTypeSupport,
    DropDomainSupport,
    DropTypeSupport,
    TypeObjectSupport,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import BaseExpression, Parameter
from rhosocial.activerecord.backend.expression.statements import (
    AlterDomainStatement,
    AlterTypeStatement,
    CreateDomainStatement,
    CreateTypeStatement,
    DomainCheckConstraint,
    DomainValueExpression,
    DropDomainDefaultAction,
    DropDomainStatement,
    DropTypeStatement,
    TypeAlterAction,
    TypeDefinition,
)
from rhosocial.activerecord.backend.expression.types import DataType, IntegerType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLEnumType, MySQLSetType
from rhosocial.activerecord.backend.impl.mysql.mixins import MySQLTypeSupportMixin
from rhosocial.activerecord.backend.expression.objects import Domain, Type


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
        CreateTypeStatement(dialect, Type(dialect, "status"), definition),
        AlterTypeStatement(dialect, Type(dialect, "status"), action),
        DropTypeStatement(dialect, Type(dialect, "status")),
        definition,
        action,
    )


def _domain_nodes(dialect: MySQLDialect) -> Tuple[BaseExpression, ...]:
    # A CHECK expression accepts no bind parameter either, so every literal
    # in the tree says ``inline=True`` itself; a binding literal here would
    # be refused at render time rather than silently inlined.
    condition = DomainValueExpression(dialect) > Parameter(dialect, 0, inline=True)
    check = DomainCheckConstraint(dialect, condition)
    return (
        CreateDomainStatement(dialect, Domain(dialect, "positive"), IntegerType(dialect)),
        AlterDomainStatement(dialect, Domain(dialect, "positive"), DropDomainDefaultAction(dialect)),
        DropDomainStatement(dialect, Domain(dialect, "positive")),
        DomainValueExpression(dialect),
        check,
        DropDomainDefaultAction(dialect),
    )


def test_type_and_domain_protocols_are_composed(dialect: MySQLDialect) -> None:
    # The umbrella TYPE and DOMAIN protocols were split into one per statement,
    # plus the naming side, so each is asked about on its own here.
    for protocol in (
        CreateTypeSupport,
        AlterTypeSupport,
        DropTypeSupport,
        CreateDomainSupport,
        AlterDomainSupport,
        DropDomainSupport,
        TypeObjectSupport,
    ):
        assert isinstance(dialect, protocol), protocol.__name__
    assert isinstance(dialect, UserDefinedTypeMixin)
    assert isinstance(dialect, DomainMixin)
    assert isinstance(dialect, DataTypeSupport)


def test_type_and_domain_protocols_are_structural_not_inherited() -> None:
    """The TYPE/DOMAIN protocols are answered structurally, never as bases.

    Each protocol is ``runtime_checkable``, so a structural match already makes
    ``isinstance`` answer True; naming one as a base would only add ellipsis
    stubs to the dialect's MRO. The generic type and domain mixins still
    precede the one protocol that reaches the MRO through a mixin
    (``MySQLTypeSupportMixin``'s ``DataTypeSupport``).
    """
    mro = MySQLDialect.__mro__
    for protocol in (
        CreateTypeSupport,
        AlterTypeSupport,
        DropTypeSupport,
        CreateDomainSupport,
        AlterDomainSupport,
        DropDomainSupport,
        TypeObjectSupport,
    ):
        assert protocol not in mro, (
            f"{protocol.__name__} must be satisfied structurally, not inherited"
        )
    assert DataTypeMixin in mro
    assert DataTypeSupport not in mro
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
    # A kind-based "can you render this class" question is not a capability
    # flag: the formatters fail on the node itself (see the two tests below),
    # and ``supported_type_definitions()`` is empty.
    assert not hasattr(dialect, "supports_type_definition")
    assert not hasattr(dialect, "supports_type_alter_action")
    assert dialect.supports_domain_nullable() is False
    assert dialect.supports_domain_not_null() is False
    assert not hasattr(dialect, "supports_alter_domain_action")
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