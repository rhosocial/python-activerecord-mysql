# tests/rhosocial/activerecord_mysql_test/feature/backend/mysql/test_partition_syntax_matrix.py
"""Offline MySQL partition syntax matrix.

The matrix itself lives in ``partition_syntax_fixtures``.  This module only
asserts each case's contract: the rendered SQL fragments, the plan rules,
the named refusal for unsupported subpartitioning, and the plan-driven
maintenance operations.  No server connection is required.
"""

from typing import Any, Mapping, Sequence, Tuple

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.partition_maintenance import (
    MySQLPartitionMaintenance,
    MySQLPartitionPlan,
)

# Imported for pytest fixture discovery; the name is injected into test signatures.
from partition_syntax_fixtures import CASES, partition_syntax_case  # noqa: F401

#: Every family the matrix promises to cover, one case each.
EXPECTED_FAMILIES = {
    "range",
    "range_columns",
    "list",
    "list_columns",
    "hash",
    "key",
    "linear_hash",
    "linear_key",
    "range_maxvalue",
    "hash_subpartition",
    "key_subpartition",
    "range_subpartition_refused",
    "list_subpartition_refused",
    "partition_options",
    "lifecycle_add_drop",
    "lifecycle_reorganize",
    "lifecycle_exchange",
    "lifecycle_coalesce",
    "lifecycle_truncate",
    "lifecycle_remove",
    "maintenance_analyze_check_optimize_rebuild_repair",
    "maintenance_ensure_list_drop_before",
}


class _FakeBackend:
    """Minimal backend surface used by ``MySQLPartitionMaintenance``."""

    def __init__(self, rows: Sequence[Mapping[str, Any]]):
        self.dialect = MySQLDialect(version=(8, 0, 0))
        self._rows = rows
        self.executed: Tuple[Tuple[str, Any], ...] = ()

    def fetch_all(self, sql: str, params: Any = None) -> Sequence[Mapping[str, Any]]:
        return list(self._rows)

    def execute(self, sql: str, params: Any = None) -> None:
        self.executed = self.executed + ((sql, params),)


def _new_dialect() -> MySQLDialect:
    """Return an adapted-enough dialect for MySQL 8.0 syntax."""
    return MySQLDialect(version=(8, 0, 0))


def _render(builder: Any, dialect: MySQLDialect) -> Tuple[str, Tuple[Any, ...]]:
    """Render one expression or a sequence of expressions."""
    result = builder(dialect)
    expressions = result if isinstance(result, (list, tuple)) else [result]
    rendered = [expression.to_sql() for expression in expressions]
    sql = "\n".join(statement[0] for statement in rendered)
    params = tuple(param for statement in rendered for param in statement[1])
    return sql, params


def test_partition_syntax_matrix_covers_every_family():
    """The matrix declares exactly one case for every promised family."""
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))
    assert set(names) == EXPECTED_FAMILIES
    for case in CASES:
        assert case.description
        assert case.builder is not None or case.maintenance is not None


def test_partition_syntax_sql_contract(partition_syntax_case):  # noqa: F811
    """Rendered SQL carries required fragments and omits forbidden ones."""
    case = partition_syntax_case
    dialect = _new_dialect()

    if case.builder is None:
        pytest.skip("case exercises maintenance planning only")

    if case.refusal_feature is not None:
        with pytest.raises(UnsupportedFeatureError) as caught:
            case.builder(dialect)
        assert case.refusal_feature in caught.value.feature_name
        assert "HASH" in (caught.value.suggestion or "")
        return

    sql, params = _render(case.builder, dialect)
    assert params == ()

    for fragment in case.expected_fragments:
        assert fragment in sql, f"missing fragment {fragment!r} in {sql!r}"
    for fragment in case.forbidden_fragments:
        assert fragment not in sql, f"forbidden fragment {fragment!r} in {sql!r}"

    offsets = [sql.index(fragment) for fragment in case.ordered_fragments]
    assert offsets == sorted(offsets), "fragments are out of order"


def test_partition_syntax_plan_contract(partition_syntax_case):  # noqa: F811
    """Valid plans build; invalid plans raise the documented ValueError."""
    case = partition_syntax_case
    dialect = _new_dialect()

    if case.plan is None:
        pytest.skip("case has no plan contract")

    plan = case.plan(dialect)
    assert isinstance(plan, MySQLPartitionPlan)
    assert plan.table == "events"
    assert plan.definitions

    if case.invalid_plan is not None:
        with pytest.raises(ValueError, match=case.invalid_plan_match):
            case.invalid_plan(dialect)


def test_partition_syntax_maintenance_contract(partition_syntax_case):  # noqa: F811
    """ensure, list and drop_before follow the plan against a fake backend."""
    case = partition_syntax_case
    if case.maintenance is None:
        pytest.skip("case has no maintenance contract")

    scenario = case.maintenance
    backend = _FakeBackend(scenario.rows())
    maintenance = MySQLPartitionMaintenance(backend)
    plan = scenario.plan(backend.dialect)

    listed = maintenance.list(plan.table, plan=plan)
    assert listed.partition_names == scenario.expected_existing
    assert listed.orphans == ()

    ensured = maintenance.ensure(plan)
    assert ensured.missing == scenario.expected_missing
    assert ensured.added == scenario.expected_added
    assert tuple(name for name, _reason in ensured.skipped) == scenario.expected_skipped
    assert ensured.orphans == ()
    assert len(backend.executed) == 1
    ensure_sql, ensure_params = backend.executed[0]
    assert ensure_params == ()
    for fragment in scenario.expected_ensure_fragments:
        assert fragment in ensure_sql

    dry = maintenance.drop_before(plan, scenario.cutoff)
    assert dry.dropped == scenario.expected_dropped
    assert dry.skipped == ()
    assert dry.dry_run is True
    assert len(backend.executed) == 1

    executed = maintenance.drop_before(plan, scenario.cutoff, dry_run=False)
    assert executed.dropped == scenario.expected_dropped
    assert executed.dry_run is False
    assert len(backend.executed) == 2
    drop_sql, drop_params = backend.executed[1]
    assert drop_params == ()
    for fragment in scenario.expected_drop_fragments:
        assert fragment in drop_sql
