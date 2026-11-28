# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/expression/test_expression_registry.py
"""Construct-level tests for MySQL's published expression table and ``Parameter``.

No live database is involved: a ``MySQLDialect`` instance renders the nodes and
the registries are data assembled at import time.
"""

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Parameter
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSIONS,
    RegistryError,
    RegistryReason,
)
from rhosocial.activerecord.backend.impl.dummy.expression_registry import (
    DUMMY_EXPRESSIONS,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLOptimizerHintExpression,
)
from rhosocial.activerecord.backend.impl.mysql.expression_registry import (
    MYSQL_EXPRESSIONS,
    MYSQL_EXPRESSION_REGISTRY,
)
from rhosocial.activerecord.backend.impl.sqlite.expression_registry import (
    SQLITE_EXPRESSIONS,
)


def test_mysql_registry_is_frozen() -> None:
    assert MYSQL_EXPRESSION_REGISTRY.is_frozen
    with pytest.raises(RegistryError) as excinfo:
        MYSQL_EXPRESSION_REGISTRY.unregister_node("mysql_optimizer_hint_expression")
    assert excinfo.value.reason is RegistryReason.REGISTRY_FROZEN


def test_mysql_kinds_are_core_plus_mysql_only() -> None:
    kinds = set(MYSQL_EXPRESSION_REGISTRY.node_kinds())
    assert kinds == set(CORE_EXPRESSIONS) | set(MYSQL_EXPRESSIONS)

    # No sibling backend's own kinds leak into MySQL's table (sqlite/dummy
    # ship with core; neither takes a live database to collect).
    sibling_owned = set(SQLITE_EXPRESSIONS) | set(DUMMY_EXPRESSIONS)
    assert sibling_owned, "sibling registries must contribute kinds to compare"
    assert not (kinds & sibling_owned)


def test_resolve_node_returns_core_and_mysql_classes() -> None:
    assert MYSQL_EXPRESSION_REGISTRY.resolve_node("parameter") is Parameter
    assert (
        MYSQL_EXPRESSION_REGISTRY.resolve_node("mysql_optimizer_hint_expression")
        is MySQLOptimizerHintExpression
    )


def test_parameter_binds_by_default_and_inlines_on_request() -> None:
    dialect = MySQLDialect()
    value = "O'Reilly"
    assert Parameter(dialect, value).to_sql() == ("%s", (value,))

    sql, params = Parameter(dialect, value, inline=True).to_sql()
    assert sql == "'O''Reilly'"  # backend SQL text, escaped by MySQLDialect
    assert params == ()


def test_raw_value_at_value_position_is_bound_not_inlined() -> None:
    dialect = MySQLDialect()
    raw = "O'Reilly; DROP TABLE users--"
    predicate = ComparisonPredicate(dialect, "eq", Column(dialect, "name"), raw)

    assert isinstance(predicate.right, Parameter)
    sql, params = predicate.to_sql()
    assert sql == "`name` = %s"
    assert "DROP TABLE" not in sql
    assert params == (raw,)
