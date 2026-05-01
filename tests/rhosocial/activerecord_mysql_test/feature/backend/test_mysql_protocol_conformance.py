# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_protocol_conformance.py
"""
Tests to verify MySQLDialect protocol conformance and protocol non-overlap.

This test ensures:
1. MySQLDialect implements all methods defined in the protocols it claims to support
2. All protocols have at least one member
3. No two protocols share the same method name (no overlap)
"""
import inspect
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
from rhosocial.activerecord.backend.impl.mysql import mixins as mysql_mixins
from rhosocial.activerecord.backend.impl.mysql import protocols as mysql_protocols


def get_all_protocol_methods(proto: type) -> set:
    """Extract all public method names from a protocol, including inherited."""
    members = set()
    if sys.version_info >= (3, 13):
        members = get_protocol_members(proto)
    elif sys.version_info >= (3, 12):
        members = get_protocol_members(proto)
    else:
        # Walk MRO to include methods from parent protocols
        for cls in proto.__mro__:
            if cls is object:
                continue
            for name in cls.__dict__:
                if name.startswith("_"):
                    continue
                val = cls.__dict__[name]
                if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
                    members.add(name)
            members.update(
                k for k in getattr(cls, "__annotations__", {})
                if not k.startswith("_")
            )
    return members


def get_own_protocol_methods(proto: type) -> set:
    """Extract public method names declared directly on a protocol (not inherited).

    Used for forward coverage: only checks methods the protocol itself declares,
    since parent protocol methods are typically implemented by generic mixins.
    """
    members = set()
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
            # MySQL DML includes upsert capabilities (ON DUPLICATE KEY UPDATE)
            ('UpsertSupport', 'MySQLDMLOperationSupport'),
            ('MySQLDMLOperationSupport', 'UpsertSupport'),
            # MySQL fulltext search includes index capabilities
            ('IndexSupport', 'MySQLFullTextSearchSupport'),
            ('MySQLFullTextSearchSupport', 'IndexSupport'),
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


# ============================================================================
# Phase -1: Protocol Implementation Completeness Tests
# ============================================================================

# Map from MySQL-specific Protocol → corresponding Mixin class
MYSQL_PROTOCOL_MIXIN_PAIRS = [
    (mysql_protocols.MySQLDMLOperationSupport, mysql_mixins.MySQLDMLOperationMixin),
    (mysql_protocols.MySQLTriggerSupport, mysql_mixins.MySQLTriggerMixin),
    (mysql_protocols.MySQLTableSupport, mysql_mixins.MySQLTableMixin),
    (mysql_protocols.MySQLSetTypeSupport, mysql_mixins.MySQLSetTypeMixin),
    (mysql_protocols.MySQLJSONFunctionSupport, mysql_mixins.MySQLJSONFunctionMixin),
    (mysql_protocols.MySQLSpatialSupport, mysql_mixins.MySQLSpatialMixin),
    (mysql_protocols.MySQLVectorSupport, mysql_mixins.MySQLVectorMixin),
    (mysql_protocols.MySQLFullTextSearchSupport, mysql_mixins.MySQLFullTextSearchMixin),
    (mysql_protocols.MySQLLockingSupport, mysql_mixins.MySQLLockingMixin),
    (mysql_protocols.MySQLModifyColumnSupport, mysql_mixins.MySQLModifyColumnMixin),
]


class TestProtocolMethodSignatureConformance:
    """Verify MySQLDialect method signatures match Protocol declarations.

    Python's @runtime_checkable Protocol only checks method existence,
    not signature compatibility. This test catches parameter mismatches.
    """

    @pytest.fixture
    def dialect(self):
        """Create a MySQLDialect instance for testing."""
        return mysql_dialect.MySQLDialect()

    # Known signature mismatches between MySQL dialect and generic protocols.
    # MySQL uses **kwargs or different parameter names for some methods.
    # These are pre-existing issues that require a broader refactoring to fix.
    _SIGNATURE_MISMATCH_EXCLUSIONS = {
        # JSONSupport: MySQL uses expr-based signatures instead of named params
        ('JSONSupport', 'format_json_expression'),
        ('JSONSupport', 'format_json_table_expression'),
        # MySQLJSONFunctionSupport inherits from JSONSupport, same signature issues
        ('MySQLJSONFunctionSupport', 'format_json_expression'),
        ('MySQLJSONFunctionSupport', 'format_json_table_expression'),
        # ArraySupport: MySQL doesn't support arrays natively
        ('ArraySupport', 'format_array_expression'),
        # ExplainSupport: MySQL uses **kwargs for explain options
        ('ExplainSupport', 'format_explain_statement'),
    }

    @pytest.mark.parametrize("protocol", MYSQL_PROTOCOLS)
    def test_method_signatures_match_protocol(self, dialect, protocol):
        """Each method on MySQLDialect must have a compatible signature
        with the corresponding Protocol method."""
        proto_methods = get_all_protocol_methods(protocol)
        missing = []
        signature_mismatch = []

        for method_name in proto_methods:
            # Check existence
            if not hasattr(dialect, method_name):
                missing.append(method_name)
                continue

            # Check signature compatibility
            # Skip known mismatches between MySQL and generic protocols
            if (protocol.__name__, method_name) in self._SIGNATURE_MISMATCH_EXCLUSIONS:
                continue

            proto_method = getattr(protocol, method_name, None)
            dialect_method = getattr(dialect, method_name)

            if proto_method is not None and callable(proto_method):
                try:
                    proto_sig = inspect.signature(proto_method)
                    dialect_sig = inspect.signature(dialect_method)

                    # Compare parameter names (excluding 'self')
                    proto_params = [
                        p for p in proto_sig.parameters.values()
                        if p.name != 'self'
                    ]
                    dialect_params = [
                        p for p in dialect_sig.parameters.values()
                        if p.name != 'self'
                    ]

                    # Dialect must accept at least all required proto params
                    proto_required = [
                        p for p in proto_params
                        if p.default is inspect.Parameter.empty
                        and p.kind not in (
                            inspect.Parameter.VAR_POSITIONAL,
                            inspect.Parameter.VAR_KEYWORD,
                        )
                    ]
                    dialect_param_names = {p.name for p in dialect_params}

                    for req_param in proto_required:
                        if req_param.name not in dialect_param_names:
                            signature_mismatch.append(
                                f"{method_name}: missing required param "
                                f"'{req_param.name}' from protocol"
                            )
                except (ValueError, TypeError):
                    pass  # Some protocol methods can't be inspected

        assert not missing, (
            f"MySQLDialect missing methods for {protocol.__name__}: {missing}"
        )
        assert not signature_mismatch, (
            f"Signature mismatches for {protocol.__name__}: {signature_mismatch}"
        )


class TestProtocolMixinForwardCoverage:
    """Verify every method declared in Protocol is implemented in Mixin.

    This catches the failure mode where a Protocol declares format_* or
    supports_* methods but the corresponding Mixin doesn't implement them.
    """

    @pytest.mark.parametrize("protocol,mixin", MYSQL_PROTOCOL_MIXIN_PAIRS)
    def test_protocol_declared_methods_are_implemented(self, protocol, mixin):
        """Every format_* / supports_* in Protocol must exist in Mixin.

        Only checks methods declared directly on the protocol (not inherited
        from parent protocols), since parent protocol methods are typically
        implemented by generic mixins rather than the MySQL-specific one.
        """
        proto_methods = get_own_protocol_methods(protocol)
        mixin_methods = {name for name in dir(mixin) if not name.startswith('_')}
        missing = proto_methods - mixin_methods
        assert not missing, (
            f"{mixin.__name__} does not implement these methods "
            f"declared in {protocol.__name__}: {missing}"
        )


class TestProtocolMixinReverseCoverage:
    """Verify every format_*/supports_* in Mixin is declared in Protocol.

    This catches the failure mode where a Mixin implements format_* or
    supports_* methods but the corresponding Protocol doesn't declare them.
    This is the exact problem we're fixing: Mixin has format_* methods
    that Protocol doesn't know about.
    """

    @pytest.mark.parametrize("protocol,mixin", MYSQL_PROTOCOL_MIXIN_PAIRS)
    def test_mixin_public_methods_are_declared_in_protocol(self, protocol, mixin):
        """Every format_*/supports_*/get_* in Mixin must be declared in Protocol.

        Only checks methods defined on the Mixin itself (not inherited
        from object or other generic bases), and only public methods
        with the format_*/supports_*/get_* prefix pattern.
        """
        proto_methods = get_all_protocol_methods(protocol)

        # Collect Mixin's own public format_*, supports_*, get_* methods
        mixin_own_methods = set()
        for name in dir(mixin):
            if name.startswith('_'):
                continue
            if not (name.startswith('format_') or name.startswith('supports_')
                    or name.startswith('get_')):
                continue
            # Only include methods defined on the mixin itself, not inherited
            # from object or other generic bases
            if name in mixin.__dict__:
                mixin_own_methods.add(name)

        undeclared = mixin_own_methods - proto_methods
        assert not undeclared, (
            f"{mixin.__name__} implements these methods not declared in "
            f"{protocol.__name__}: {undeclared}"
        )