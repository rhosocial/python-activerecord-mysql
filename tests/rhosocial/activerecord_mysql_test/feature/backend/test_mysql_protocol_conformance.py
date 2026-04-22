# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_protocol_conformance.py
"""
Tests to verify MySQLDialect protocol conformance and protocol non-overlap.

This test ensures:
1. MySQLDialect implements all methods defined in the protocols it claims to support
2. All protocols have at least one member
3. No two protocols share the same method name (no overlap)
"""
import sys
from itertools import combinations
from typing import Protocol

if sys.version_info >= (3, 13):
    from typing import get_protocol_members
elif sys.version_info >= (3, 12):
    from typing import _get_protocol_attrs as get_protocol_members

import pytest
from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.impl.mysql import dialect as mysql_dialect
from rhosocial.activerecord.backend.impl.mysql import protocols as mysql_protocols


def get_all_protocol_methods(proto: type) -> set:
    """Extract all public method names from a protocol."""
    members = set()
    if sys.version_info >= (3, 13):
        members = get_protocol_members(proto)
    elif sys.version_info >= (3, 12):
        members = get_protocol_members(proto)
    else:
        for name in proto.__dict__:
            if name.startswith("_"):
                continue
            val = proto.__dict__[name]
            if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
                members.add(name)
        members.update(
            k for k in getattr(proto, "__annotations__", {})
            if not k.startswith("_")
        )
    return members


MYSQL_PROTOCOLS = [
    dialect_protocols.CTESupport,
    dialect_protocols.FilterClauseSupport,
    dialect_protocols.WindowFunctionSupport,
    dialect_protocols.JSONSupport,
    dialect_protocols.ReturningSupport,
    dialect_protocols.AdvancedGroupingSupport,
    dialect_protocols.ArraySupport,
    dialect_protocols.ExplainSupport,
    dialect_protocols.GraphSupport,
    dialect_protocols.LockingSupport,
    dialect_protocols.MergeSupport,
    dialect_protocols.OrderedSetAggregationSupport,
    dialect_protocols.QualifyClauseSupport,
    dialect_protocols.TemporalTableSupport,
    dialect_protocols.UpsertSupport,
    dialect_protocols.LateralJoinSupport,
    dialect_protocols.WildcardSupport,
    dialect_protocols.JoinSupport,
    dialect_protocols.ViewSupport,
    dialect_protocols.SchemaSupport,
    dialect_protocols.IndexSupport,
    dialect_protocols.SequenceSupport,
    dialect_protocols.TableSupport,
    dialect_protocols.ConstraintSupport,
    dialect_protocols.IntrospectionSupport,
    dialect_protocols.TransactionControlSupport,
    dialect_protocols.SQLFunctionSupport,
    # MySQL-specific protocols
    mysql_protocols.MySQLDMLOperationSupport,
    mysql_protocols.MySQLTriggerSupport,
    mysql_protocols.MySQLTableSupport,
    mysql_protocols.MySQLSetTypeSupport,
    mysql_protocols.MySQLJSONFunctionSupport,
    mysql_protocols.MySQLSpatialSupport,
    mysql_protocols.MySQLVectorSupport,
    mysql_protocols.MySQLFullTextSearchSupport,
    mysql_protocols.MySQLLockingSupport,
    mysql_protocols.MySQLModifyColumnSupport,
]


class TestMySQLDialectProtocolConformance:
    """Assert MySQLDialect implements all protocols it declares to support."""

    @pytest.fixture
    def dialect(self):
        """Create a MySQLDialect instance for testing."""
        return mysql_dialect.MySQLDialect()

    @pytest.mark.parametrize("protocol", MYSQL_PROTOCOLS)
    def test_implements_protocol(self, dialect, protocol):
        """MySQLDialect should implement each protocol in MYSQL_PROTOCOLS."""
        assert isinstance(dialect, protocol), (
            f"MySQLDialect does not implement protocol {protocol.__name__}, "
            f"missing methods: {get_all_protocol_methods(protocol) - set(dir(dialect))}"
        )


class TestProtocolNonOverlap:
    """Assert protocols do not have overlapping method names."""

    def test_no_interface_overlap_between_protocols(self):
        """No two protocols should share the same method name."""
        member_map = {
            proto.__name__: get_all_protocol_methods(proto)
            for proto in MYSQL_PROTOCOLS
        }

        for name, members in member_map.items():
            assert len(members) > 0, f"Protocol {name} has no members defined"

        excluded_overlaps = {
            ('JSONSupport', 'MySQLJSONFunctionSupport'),
            ('MySQLJSONFunctionSupport', 'JSONSupport'),
            ('JSONSupport', 'MySQLDMLOperationSupport'),
            ('MySQLDMLOperationSupport', 'JSONSupport'),
            ('LockingSupport', 'MySQLLockingSupport'),
            ('MySQLLockingSupport', 'LockingSupport'),
            ('TableSupport', 'MySQLTableSupport'),
            ('MySQLTableSupport', 'TableSupport'),
        }

        violations = []
        for (name_a, members_a), (name_b, members_b) in combinations(member_map.items(), 2):
            if (name_a, name_b) in excluded_overlaps:
                continue
            overlap = members_a & members_b
            if overlap:
                violations.append(f"{name_a} ∩ {name_b} = {overlap}")

        assert not violations, (
            "The following protocols have overlapping interfaces, need to merge or rename:\n"
            + "\n".join(f"  • {v}" for v in violations)
        )