# tests/rhosocial/activerecord_mysql_test/feature/backend/protocol/test_protocol_members.py
"""
Tests for the MySQL-specific protocol declarations.

These tests exercise ``src/rhosocial/activerecord/backend/impl/mysql/protocols.py``
without a live server:

- every exported class is a runtime-checkable Protocol
- every declared method is callable on a protocol instance (their ``...`` bodies
  execute and return ``None``), proving the declaration surface is sound
- the MySQLDialect satisfies every declared protocol
- the declared protocol method set matches the concrete dialect surface
"""

import inspect

import pytest

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql import protocols as mysql_protocols


def _iter_protocols():
    """Yield every Protocol class declared in the mysql protocols module.

    Only classes defined in this module are included; generic protocols that
    are merely re-exported (IndexSupport, JSONSupport, ...) are excluded.
    """
    module_name = mysql_protocols.__name__
    for name in dir(mysql_protocols):
        cls = getattr(mysql_protocols, name)
        if isinstance(cls, type) and getattr(cls, "_is_protocol", False) and cls.__module__ == module_name:
            yield cls


def _iter_protocol_methods(protocol):
    """Yield (name, method) for every method declared directly on the protocol."""
    for name in protocol.__dict__:
        if name.startswith("_"):
            continue
        method = getattr(protocol, name)
        if callable(method):
            yield name, method


def _call_with_dummy_args(protocol, method):
    """Call a protocol method on a bare instance, binding None to every parameter."""
    instance = object.__new__(protocol)
    signature = inspect.signature(method)
    args = []
    kwargs = {}
    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            kwargs[param_name] = None
        else:
            args.append(None)
    return getattr(instance, method.__name__)(*args, **kwargs)


PROTOCOLS = list(_iter_protocols())


class TestProtocolDeclarations:
    """Verify the exported protocol classes are well-formed Protocols."""

    def test_protocols_are_runtime_checkable(self):
        """Every exported protocol should be a runtime-checkable Protocol."""
        assert len(PROTOCOLS) > 0, "at least one MySQL protocol should be declared"
        for protocol in PROTOCOLS:
            assert getattr(protocol, "_is_runtime_protocol", False) is True, (
                f"{protocol.__name__} should be runtime-checkable"
            )

    def test_protocol_has_members(self):
        """Every protocol should declare at least one method."""
        for protocol in PROTOCOLS:
            methods = list(_iter_protocol_methods(protocol))
            assert methods, f"protocol {protocol.__name__} declares no methods"

    def test_method_bodies_execute(self):
        """Every declared method should be callable and return None (``...`` body)."""
        for protocol in PROTOCOLS:
            for name, method in _iter_protocol_methods(protocol):
                result = _call_with_dummy_args(protocol, method)
                assert result is None, f"{protocol.__name__}.{name} should return None from its ... body"


class TestDialectProtocolSatisfaction:
    """Verify the concrete MySQLDialect satisfies every declared protocol."""

    @pytest.fixture
    def dialect(self):
        """Create a MySQLDialect instance for protocol checks."""
        return MySQLDialect(version=(8, 0, 0))

    def test_dialect_satisfies_all_protocols(self, dialect):
        """isinstance(dialect, protocol) should hold for every MySQL protocol."""
        for protocol in PROTOCOLS:
            assert isinstance(dialect, protocol), (
                f"MySQLDialect does not implement protocol {protocol.__name__}"
            )

    def test_dialect_implements_declared_methods(self, dialect):
        """The dialect should expose every method declared by the protocols."""
        for protocol in PROTOCOLS:
            for name, _method in _iter_protocol_methods(protocol):
                assert hasattr(dialect, name), (
                    f"MySQLDialect is missing {protocol.__name__}.{name}"
                )

    def test_support_checks_return_bool(self, dialect):
        """Every zero-argument supports_* declared method should return a bool."""
        for protocol in PROTOCOLS:
            for name, method in _iter_protocol_methods(protocol):
                if not name.startswith("supports_"):
                    continue
                signature = inspect.signature(method)
                required = [
                    p
                    for p in signature.parameters.values()
                    if p.name != "self"
                    and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                    and p.default is inspect.Parameter.empty
                ]
                if required:
                    continue
                value = getattr(dialect, name)()
                assert isinstance(value, bool), (
                    f"{protocol.__name__}.{name} should return a bool, got {type(value).__name__}"
                )


class TestProtocolMethodSurface:
    """Verify the protocol declaration surface matches the mixin implementations."""

    def test_protocol_names_stable(self):
        """The exported protocol class names should match the documented set."""
        names = {protocol.__name__ for protocol in PROTOCOLS}
        expected = {
            "MySQLDMLOperationSupport",
            "MySQLTriggerSupport",
            "MySQLTableSupport",
            "MySQLPartitionSupport",
            "MySQLSetTypeSupport",
            "MySQLJSONFunctionSupport",
            "MySQLSpatialSupport",
            "MySQLVectorSupport",
            "MySQLFullTextSearchSupport",
            "MySQLLockingSupport",
            "MySQLModifyColumnSupport",
            "MySQLJsonDualityViewSupport",
            "MySQLOptimizerHintSupport",
            "MySQLRenameTableSupport",
            "MySQLTableStatementSupport",
            "MySQLMaintenanceSupport",
            "MySQLRoutineSupport",
            "MySQLLoadXMLSupport",
            "MySQLAdminCommandSupport",
        }
        assert names == expected, f"unexpected protocol surface: {names - expected}"

    def test_all_declared_in_module_all(self):
        """Every protocol should be re-exported through the module surface."""
        for protocol in PROTOCOLS:
            assert hasattr(mysql_protocols, protocol.__name__), (
                f"{protocol.__name__} should be reachable from the module"
            )


class TestProtocolExports:
    """Verify the mysql package exposes the protocol module for consumers."""

    def test_backend_imports_protocols(self):
        """The mysql backend package should importable and expose protocols."""
        from rhosocial.activerecord.backend.impl import mysql as mysql_pkg

        assert hasattr(mysql_pkg, "protocols"), "mysql package should expose protocols"