# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/expression/test_artifact_registry.py
"""MySQL publishes its own artifact registry, composed with core's.

Core no longer keeps a process-global table holding every bundled backend's
kinds. Each owner publishes one frozen table:

* core's is :func:`core_registry`;
* MySQL's is :func:`backend_registry`, assembled with
  ``registry_for_packages(<this backend's expression package>, base=core_registry())``;
* the dialect answers with it, so ``deserialize(..., dialect)`` resolves the
  kind through the backend the caller supplied.

These tests state the ownership boundary directly: a MySQL kind resolves
through ``MySQLDialect.artifact_registry()``, another backend's kind is
refused by name, and the published table refuses mutation.
"""

import pytest

from rhosocial.activerecord.backend.expression.registry import (
    RegistryError,
    RegistryReason,
)
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionDeserializationError,
    core_registry,
    deserialize,
    serialize,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.admin import (
    MySQLFlushStatement,
)
from rhosocial.activerecord.backend.impl.mysql.registry import backend_registry
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.vacuum import (
    SQLiteVacuumStatement,
)


def test_the_dialect_answers_with_the_mysql_registry():
    """The dialect exposes MySQL's composed table, not core's and not a copy."""
    dialect = MySQLDialect((8, 0, 0))
    registry = dialect.artifact_registry()

    assert registry is backend_registry()
    assert registry.is_frozen
    assert registry.node_kinds() != core_registry().node_kinds()


def test_mysql_proprietary_kind_resolves_through_the_dialect():
    """A MySQL-only kind is read back through the dialect's own table."""
    dialect = MySQLDialect((8, 0, 0))
    registry = dialect.artifact_registry()

    kind = MySQLFlushStatement.kind()
    assert "mysql_flush" in kind
    assert registry.resolve_node(kind) is MySQLFlushStatement
    # The overlap with core is exactly the composition's base.
    assert "column" in registry.node_kinds()

    original = MySQLFlushStatement(dialect, ["TABLES"])
    restored = deserialize(serialize(original), dialect)
    assert isinstance(restored, MySQLFlushStatement)
    assert restored.options == original.options

    # Without a dialect the selection falls back to core, which refuses the
    # backend kind by name instead of guessing.
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(serialize(original))
    assert kind in str(caught.value)


def test_another_backends_kind_is_refused():
    """MySQL's table is core plus MySQL: SQLite's kinds are not included."""
    dialect = MySQLDialect((8, 0, 0))
    registry = dialect.artifact_registry()

    sqlite_kind = SQLiteVacuumStatement.kind()
    assert sqlite_kind not in registry.node_kinds()
    with pytest.raises(RegistryError) as caught:
        registry.resolve_node(sqlite_kind)
    assert caught.value.reason is RegistryReason.KIND_NOT_REGISTERED
    assert sqlite_kind in str(caught.value)

    artifact = serialize(SQLiteVacuumStatement(SQLiteDialect((3, 38, 0))))
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact, dialect)
    assert sqlite_kind in str(caught.value)


def test_the_published_registry_is_frozen():
    """A published table is a value; widening it means building a new one."""
    registry = backend_registry()
    assert registry.is_frozen

    with pytest.raises(RegistryError) as caught:
        registry.register_node(MySQLFlushStatement)
    assert caught.value.reason is RegistryReason.REGISTRY_FROZEN
    assert MySQLFlushStatement.kind() in str(caught.value)

    # A twin is the mutable workspace, and it cannot change the source.
    twin = registry.twin()
    assert not twin.is_frozen
    twin.register_node(SQLiteVacuumStatement)
    assert SQLiteVacuumStatement.kind() in twin.node_kinds()
    assert SQLiteVacuumStatement.kind() not in registry.node_kinds()


def test_the_expression_roundtrip_matrix_still_round_trips(mysql_dialect):
    """Core and MySQL kinds both read back through the dialect's table."""
    from expression_roundtrip_harness import assert_params_equal
    from rhosocial.activerecord.backend.expression.core import Column, Literal
    from rhosocial.activerecord.backend.expression.predicates import (
        ComparisonPredicate,
    )

    registry = mysql_dialect.artifact_registry()
    cases = (
        Column(mysql_dialect, "id"),
        Literal(mysql_dialect, 1),
        ComparisonPredicate(
            mysql_dialect, "=", Column(mysql_dialect, "a"), Literal(mysql_dialect, 1)
        ),
        MySQLFlushStatement(mysql_dialect, ["TABLES"]),
    )
    for instance in cases:
        restored = deserialize(serialize(instance), mysql_dialect, registry=registry)
        assert_params_equal(restored.get_params(), instance.get_params(), instance.kind())
