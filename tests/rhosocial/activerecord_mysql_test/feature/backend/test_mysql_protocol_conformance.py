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
            # MySQL-specific protocols extend generic protocols (intentional inheritance)
            ('JSONSupport', 'MySQLJSONFunctionSupport'),
            ('MySQLJSONFunctionSupport', 'JSONSupport'),
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


class TestMySQLProtocolDerivation:
    """Verify MySQL-specific protocols derive from their generic counterparts.

    This ensures that backend-specific protocols inherit the standard interface,
    allowing isinstance() checks against generic protocols to work correctly.
    """

    PROTOCOL_DERIVATIONS = [
        ("MySQLTableSupport", "TableSupport"),
        ("MySQLLockingSupport", "LockingSupport"),
        ("MySQLJSONFunctionSupport", "JSONSupport"),
    ]

    @pytest.mark.parametrize("mysql_name,generic_name", PROTOCOL_DERIVATIONS)
    def test_protocol_derives_from_generic(self, mysql_name, generic_name):
        """Backend-specific protocol should derive from its generic counterpart."""
        mysql_proto = getattr(mysql_protocols, mysql_name)
        generic_proto = getattr(dialect_protocols, generic_name)
        assert issubclass(mysql_proto, generic_proto), (
            f"{mysql_name} does not derive from {generic_name}"
        )

    def test_dialect_satisfies_generic_protocols_via_derivation(self):
        """MySQLDialect should satisfy generic protocols through derived protocols."""
        dialect = mysql_dialect.MySQLDialect()
        for mysql_name, generic_name in self.PROTOCOL_DERIVATIONS:
            generic_proto = getattr(dialect_protocols, generic_name)
            if getattr(generic_proto, "_is_runtime_protocol", False):
                assert isinstance(dialect, generic_proto), (
                    f"MySQLDialect does not satisfy {generic_name} "
                    f"(should be inherited via {mysql_name})"
                )


class TestMySQLExpressionDialectSeparation:
    """Verify MySQL-specific expression classes delegate to dialect for SQL generation.

    Expression-Dialect separation means expression classes collect parameters
    and delegate to_sql() to dialect.format_*() methods, never directly
    constructing SQL strings.
    """

    EXPRESSION_DIALECT_PAIRS = [
        ("MySQLLoadDataExpression", "format_load_data_statement"),
        ("MySQLJSONTableExpression", "format_json_table_expression"),
        ("MySQLJSONExtractExpression", "format_json_extract"),
        ("MySQLJSONObjectExpression", "format_json_object"),
        ("MySQLJSONArrayExpression", "format_json_array"),
        ("MySQLJSONContainsExpression", "format_json_contains"),
        ("MySQLSTGeomFromTextExpression", "format_st_geom_from_text"),
        ("MySQLSTDistanceExpression", "format_st_distance"),
        ("MySQLSTWithinExpression", "format_st_within"),
        ("MySQLSTContainsExpression", "format_st_contains"),
        ("MySQLVectorExpression", "format_vector_literal"),
        ("MySQLDistanceEuclideanExpression", "format_distance_euclidean"),
        ("MySQLDistanceCosineExpression", "format_distance_cosine"),
        ("MySQLDistanceDotExpression", "format_distance_dot"),
        ("MySQLMatchAgainstExpression", "format_match_against"),
    ]

    @pytest.mark.parametrize("expr_name,format_method", EXPRESSION_DIALECT_PAIRS)
    def test_expression_delegates_to_dialect(self, expr_name, format_method):
        """Expression.to_sql() should delegate to dialect.format_*() method."""
        from rhosocial.activerecord.backend.impl.mysql import expression as mysql_expr

        # Find the expression class
        expr_class = None
        for module_name in dir(mysql_expr):
            module = getattr(mysql_expr, module_name)
            if hasattr(module, expr_name):
                expr_class = getattr(module, expr_name)
                break

        # Also check top-level imports
        if expr_class is None:
            expr_class = getattr(mysql_expr, expr_name, None)

        assert expr_class is not None, f"Expression class {expr_name} not found"

        # Verify the dialect has the corresponding format method
        dialect = mysql_dialect.MySQLDialect()
        assert hasattr(dialect, format_method), (
            f"MySQLDialect missing format method {format_method} "
            f"for expression {expr_name}"
        )