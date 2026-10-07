# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_clause_pair_guard.py
"""Guard: every clause pair the MySQL dialect consumes is four-state distinguishable.

Round rule: each spellable alternative has its own parameter, "unspecified" is
the state where none of a pair's parameters is set, and setting both raises
``ValueError`` at construction. For every pair the MySQL dialect consumes, the
four states must be pairwise distinguishable:

====================  ======================================================
neither parameter     neither spelling rendered
parameter A           A's spelling rendered, or a refusal naming A
parameter B           B's spelling rendered, or a refusal naming B
both parameters       ``ValueError`` at construction
====================  ======================================================

A dialect that cannot express one side must refuse it *by name*; silently
dropping the spelling would make that state indistinguishable from "neither"
and fails here. Refusals count as distinguishable only when their message names
the requested spelling (the two refusals of one pair must differ).

The dialect is pinned to MySQL 8.0.19: every capability this table exercises is
available at that version (``[NOT] ENFORCED`` on CHECK constraints arrived in
8.0.16). ``TestTableCheckEnforcedAcrossVersions`` separately pins 8.0.0 and
asserts the same four-state property through spelling-named refusals.
"""

from __future__ import annotations

import re

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_sources import CTEExpression
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    CreateTableAsExpression,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    DropViewExpression,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLExchangePartitionExpression,
)

#: The version the main table runs at: CHECK + [NOT] ENFORCED are available.
PAIR_GUARD_VERSION = (8, 0, 19)


def _dialect(version=PAIR_GUARD_VERSION):
    return MySQLDialect(version=version)


def _table(d, name="t"):
    return Table(d, name)


def _query(d):
    return QueryExpression(d, select=[Column(d, "id")], from_=_table(d))


def _fk(d, **kw):
    return TableConstraint(
        d,
        TableConstraintType.FOREIGN_KEY,
        name="fk",
        columns=["a"],
        foreign_key_table=_table(d, "t2"),
        foreign_key_columns=["b"],
        **kw,
    )


def _check(d, **kw):
    return TableConstraint(
        d,
        TableConstraintType.CHECK,
        name="ck",
        check_condition=ComparisonPredicate(d, "=", Column(d, "a"), Column(d, "b")),
        **kw,
    )


def _column_fk(d, **kw):
    return ColumnConstraint(
        d,
        ColumnConstraintType.FOREIGN_KEY,
        name="fk",
        foreign_key_reference=(_table(d, "t2"), ["b"]),
        **kw,
    )


class PairCase:
    """One clause pair and how the MySQL dialect answers each state.

    Exactly one of ``a_render`` / ``a_error`` is set per side: a side is either
    rendered (SQL must match the pattern) or refused by name (the error message
    must match the pattern).
    """

    def __init__(
        self,
        case_id,
        builder,
        a,
        b,
        a_render=None,
        b_render=None,
        a_error=None,
        b_error=None,
    ):
        self.case_id = case_id
        self.builder = builder
        self.a = a
        self.b = b
        assert (a_render is None) != (a_error is None), case_id
        assert (b_render is None) != (b_error is None), case_id
        self.a_pattern = re.compile(a_render or a_error)
        self.b_pattern = re.compile(b_render or b_error)
        self.a_renders = a_render is not None
        self.b_renders = b_render is not None

    def build(self, dialect, **kwargs):
        return self.builder(dialect, **kwargs)

    def outcome(self, dialect, **kwargs):
        """Render one state to a hashable, comparable outcome."""
        try:
            expr = self.build(dialect, **kwargs)
        except ValueError as exc:
            return ("ValueError", str(exc))
        try:
            sql, _params = expr.to_sql()
            return ("sql", sql)
        except UnsupportedFeatureError as exc:
            return ("UnsupportedFeatureError", str(exc))

    def sql(self, dialect, **kwargs):
        return self.outcome(dialect, **kwargs)[1]


#: Every pair the MySQL backend consumes through its own formatters (or, for
#: the exchange-partition node, through its own expression). Pairs handled by
#: inherited core formatters whose rendering MySQL accepts unchanged
#: (DROP TABLE CASCADE/RESTRICT, UNION ALL/DISTINCT) are not backend-owned and
#: stay covered by core's guard.
PAIR_CASES = (
    PairCase(
        "MySQLExchangePartitionExpression.with_validation",
        lambda d, **kw: MySQLExchangePartitionExpression(
            d, _table(d, "events"), "p0", _table(d, "events_archive"), **kw
        ),
        "with_validation",
        "without_validation",
        a_render=r"WITH VALIDATION\b",
        b_render=r"WITHOUT VALIDATION\b",
    ),
    PairCase(
        "TruncateExpression.cascade",
        lambda d, **kw: TruncateExpression(d, _table(d), **kw),
        "cascade",
        "restrict",
        a_error=r"CASCADE\b",
        b_error=r"RESTRICT\b",
    ),
    PairCase(
        "TruncateExpression.restart_identity",
        lambda d, **kw: TruncateExpression(d, _table(d), **kw),
        "restart_identity",
        "continue_identity",
        a_error=r"RESTART IDENTITY\b",
        b_error=r"CONTINUE IDENTITY\b",
    ),
    PairCase(
        "DropViewExpression.cascade",
        lambda d, **kw: DropViewExpression(d, View(d, "v"), **kw),
        "cascade",
        "restrict",
        a_error=r"CASCADE\b",
        b_error=r"RESTRICT\b",
    ),
    PairCase(
        "BeginTransactionExpression.deferrable",
        lambda d, **kw: BeginTransactionExpression(d, **kw),
        "deferrable",
        "not_deferrable",
        a_error=r"(?<!NOT )DEFERRABLE\b",
        b_error=r"NOT DEFERRABLE\b",
    ),
    PairCase(
        "SetTransactionExpression.deferrable",
        lambda d, **kw: SetTransactionExpression(d, **kw),
        "deferrable",
        "not_deferrable",
        a_error=r"(?<!NOT )DEFERRABLE\b",
        b_error=r"NOT DEFERRABLE\b",
    ),
    PairCase(
        "BeginTransactionExpression.wait",
        lambda d, **kw: BeginTransactionExpression(d, **kw),
        "wait",
        "no_wait",
        a_error=r"(?<!NO )WAIT\b",
        b_error=r"NO WAIT\b",
    ),
    PairCase(
        "SetTransactionExpression.wait",
        lambda d, **kw: SetTransactionExpression(d, **kw),
        "wait",
        "no_wait",
        a_error=r"(?<!NO )WAIT\b",
        b_error=r"NO WAIT\b",
    ),
    PairCase(
        "TableConstraint.enforced",
        _check,
        "enforced",
        "not_enforced",
        a_render=r"(?<!NOT )ENFORCED\b",
        b_render=r"NOT ENFORCED\b",
    ),
    PairCase(
        "TableConstraint.deferrable",
        _fk,
        "deferrable",
        "not_deferrable",
        a_error=r"(?<!NOT )DEFERRABLE\b",
        b_error=r"NOT DEFERRABLE\b",
    ),
    PairCase(
        "TableConstraint.initially_deferred",
        _fk,
        "initially_deferred",
        "initially_immediate",
        a_error=r"INITIALLY DEFERRED\b",
        b_error=r"INITIALLY IMMEDIATE\b",
    ),
    PairCase(
        "ColumnConstraint.deferrable",
        _column_fk,
        "deferrable",
        "not_deferrable",
        a_error=r"(?<!NOT )DEFERRABLE\b",
        b_error=r"NOT DEFERRABLE\b",
    ),
    PairCase(
        "ColumnConstraint.initially_deferred",
        _column_fk,
        "initially_deferred",
        "initially_immediate",
        a_error=r"INITIALLY DEFERRED\b",
        b_error=r"INITIALLY IMMEDIATE\b",
    ),
)

PAIR_IDS = [case.case_id for case in PAIR_CASES]


class TestFourStatesArePairwiseDistinguishable:
    """The four states of every consumed pair are pairwise distinguishable."""

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_four_outcomes_are_distinct(self, case):
        dialect = _dialect()
        outcomes = [
            case.outcome(dialect),
            case.outcome(dialect, **{case.a: True}),
            case.outcome(dialect, **{case.b: True}),
            case.outcome(dialect, **{case.a: True, case.b: True}),
        ]
        assert len(set(outcomes)) == 4, (
            f"{case.case_id}: states are not pairwise distinguishable: {outcomes}"
        )
        assert outcomes[3] == (
            "ValueError",
            f"{case.a} and {case.b} are mutually exclusive options",
        ), f"{case.case_id}: both-set must be refused at construction: {outcomes[3]}"

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_neither_set_renders_neither_spelling(self, case):
        dialect = _dialect()
        outcome = case.outcome(dialect)
        assert outcome[0] == "sql", f"{case.case_id}: neither state refused: {outcome}"
        assert not case.a_pattern.search(outcome[1]), (
            f"{case.case_id}: with neither parameter set the SQL still spells "
            f"{case.a!r}: {outcome[1]!r}"
        )
        assert not case.b_pattern.search(outcome[1]), (
            f"{case.case_id}: with neither parameter set the SQL still spells "
            f"{case.b!r}: {outcome[1]!r}"
        )

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_a_set_renders_a_or_refuses_a_by_name(self, case):
        outcome = case.outcome(_dialect(), **{case.a: True})
        if case.a_renders:
            assert outcome[0] == "sql", f"{case.case_id}: {case.a!r} was refused: {outcome}"
            assert case.a_pattern.search(outcome[1]), (
                f"{case.case_id}: {case.a!r} was not rendered: {outcome[1]!r}"
            )
            assert not case.b_pattern.search(outcome[1]), (
                f"{case.case_id}: setting {case.a!r} also rendered {case.b!r}: "
                f"{outcome[1]!r}"
            )
        else:
            assert outcome[0] == "UnsupportedFeatureError", (
                f"{case.case_id}: {case.a!r} was not refused by name: {outcome}"
            )
            assert case.a_pattern.search(outcome[1]), (
                f"{case.case_id}: refusal does not name {case.a!r}: {outcome[1]!r}"
            )

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_b_set_renders_b_or_refuses_b_by_name(self, case):
        outcome = case.outcome(_dialect(), **{case.b: True})
        if case.b_renders:
            assert outcome[0] == "sql", f"{case.case_id}: {case.b!r} was refused: {outcome}"
            assert case.b_pattern.search(outcome[1]), (
                f"{case.case_id}: {case.b!r} was not rendered: {outcome[1]!r}"
            )
            assert not case.a_pattern.search(outcome[1]), (
                f"{case.case_id}: setting {case.b!r} also rendered {case.a!r}: "
                f"{outcome[1]!r}"
            )
        else:
            assert outcome[0] == "UnsupportedFeatureError", (
                f"{case.case_id}: {case.b!r} was not refused by name: {outcome}"
            )
            assert case.b_pattern.search(outcome[1]), (
                f"{case.case_id}: refusal does not name {case.b!r}: {outcome[1]!r}"
            )


class TestTableCheckEnforcedAcrossVersions:
    """``[NOT] ENFORCED`` on CHECK constraints: rendered or refused by name.

    ``supports_constraint_enforced()`` is version-gated (8.0.16+). Below that
    version the spelling must still be refused *by name*, or the two refusals
    would be indistinguishable from each other.
    """

    def _outcome(self, version, **kw):
        return _check(_dialect(version), **kw)

    def test_rendered_at_8_0_19(self):
        dialect = _dialect((8, 0, 19))
        enforced = _check(dialect, enforced=True).to_sql()[0]
        not_enforced = _check(dialect, not_enforced=True).to_sql()[0]
        assert re.search(r"(?<!NOT )ENFORCED\b", enforced), enforced
        assert re.search(r"NOT ENFORCED\b", not_enforced), not_enforced

    @pytest.mark.parametrize(
        "kwargs, spelling",
        [
            ({"enforced": True}, r"(?<!NOT )ENFORCED\b"),
            ({"not_enforced": True}, r"NOT ENFORCED\b"),
        ],
        ids=["enforced", "not_enforced"],
    )
    def test_refused_by_name_at_8_0_0(self, kwargs, spelling):
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            _check(_dialect((8, 0, 0)), **kwargs).to_sql()
        assert re.search(spelling, str(exc_info.value)), str(exc_info.value)

    def test_four_states_distinct_at_8_0_0(self):
        dialect = _dialect((8, 0, 0))

        def outcome(**kw):
            try:
                expr = _check(dialect, **kw)
            except ValueError as exc:
                return ("ValueError", str(exc))
            try:
                return ("sql", expr.to_sql()[0])
            except UnsupportedFeatureError as exc:
                return ("UnsupportedFeatureError", str(exc))

        outcomes = [
            outcome(),
            outcome(enforced=True),
            outcome(not_enforced=True),
            outcome(enforced=True, not_enforced=True),
        ]
        assert len(set(outcomes)) == 4, outcomes


class TestDeclaredCapabilities:
    """The probes behind the consumed pairs answer what the formatter assumes."""

    def test_view_behavior_keywords_are_declined(self):
        dialect = _dialect()
        assert dialect.supports_cascade_view() is False
        assert dialect.supports_restrict_view() is False

    def test_truncate_options_are_declined(self):
        dialect = _dialect()
        assert dialect.supports_truncate_restart_identity() is False
        assert dialect.supports_truncate_cascade() is False
        assert dialect.supports_truncate_restrict() is False

    def test_transaction_deferrable_is_declined(self):
        dialect = _dialect()
        assert dialect.supports_deferrable_transaction() is False
        assert dialect.supports_deferrable_constraint() is False

    def test_check_enforcement_is_version_gated(self):
        assert _dialect((8, 0, 15)).supports_constraint_enforced() is False
        assert _dialect((8, 0, 16)).supports_constraint_enforced() is True

    def test_exchange_partition_validation_probes(self):
        assert _dialect((5, 6, 0)).supports_exchange_partition_with_validation() is False
        assert _dialect((5, 7, 0)).supports_exchange_partition_with_validation() is True
        assert _dialect((5, 6, 0)).supports_exchange_partition_without_validation() is True


class TestNewlyGatedMasterProbes:
    """The master probes core now consults are declared from MySQL measurement.

    Core gave four probes call sites: ``supports_materialized_cte`` (the CTE
    ``MATERIALIZED`` hint), ``supports_truncate`` (the TRUNCATE statement
    itself), the new ``supports_with_data_clause`` (``WITH [NO] DATA`` on CTAS
    and materialized-view statements) and the new ``supports_transaction_wait``
    (``WAIT`` / ``NO WAIT`` on transactions). The MySQL answers were measured
    directly against servers 5.6.51, 5.7.44, 8.0.46, 8.4.11, 9.2.0, 9.4.0 and
    26.7.0: TRUNCATE TABLE is real, and the other three spellings are rejected
    by every server (plain CTE itself only exists from 8.0.1). The verdicts are
    declared by this backend's own mixins -- inheriting a default would let a
    core default change flip MySQL silently -- and every declined spelling is
    refused by name rather than dropped.
    """

    #: The exact server versions the verdicts were measured on.
    MEASURED_VERSIONS = (
        (5, 6, 51),
        (5, 7, 44),
        (8, 0, 46),
        (8, 4, 11),
        (9, 2, 0),
        (9, 4, 0),
        (26, 7, 0),
    )

    @pytest.mark.parametrize(
        "version",
        MEASURED_VERSIONS,
        ids=[".".join(str(part) for part in v) for v in MEASURED_VERSIONS],
    )
    def test_measured_probe_verdicts(self, version):
        dialect = _dialect(version)
        assert dialect.supports_truncate() is True
        assert dialect.supports_materialized_cte() is False
        assert dialect.supports_with_data_clause() is False
        assert dialect.supports_transaction_wait() is False

    def test_mysql_mixins_own_the_resolved_probe_declarations(self):
        """The declaration that wins MRO lookup must be MySQL's own.

        Membership in ``__dict__`` is not enough: a declaration placed after a
        core mixin that defines the same method is shadowed, and the backend
        silently answers with core's default again.
        """
        from rhosocial.activerecord.backend.impl.mysql.mixins import (
            MySQLCTEMixin,
            MySQLTransactionMixin,
            MySQLTruncateMixin,
            MySQLViewMixin,
        )

        dialect = _dialect()
        expected_owner = {
            "supports_materialized_cte": MySQLCTEMixin,
            "supports_with_data_clause": MySQLViewMixin,
            "supports_transaction_wait": MySQLTransactionMixin,
            "supports_truncate": MySQLTruncateMixin,
        }
        for probe, mixin in expected_owner.items():
            owner = next(
                klass for klass in type(dialect).__mro__ if probe in vars(klass)
            )
            assert owner is mixin, (
                f"{probe} resolves to {owner.__module__}.{owner.__qualname__}, "
                f"not {mixin.__module__}.{mixin.__qualname__}"
            )

    def test_materialized_cte_is_refused_by_name(self):
        dialect = _dialect()
        with pytest.raises(UnsupportedFeatureError, match=r"(?<!NOT )MATERIALIZED"):
            CTEExpression(dialect, "c", _query(dialect), materialized=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match=r"NOT MATERIALIZED"):
            CTEExpression(dialect, "c", _query(dialect), not_materialized=True).to_sql()
        sql, _params = CTEExpression(dialect, "c", _query(dialect)).to_sql()
        assert "MATERIALIZED" not in sql

    def test_ctas_with_data_is_refused_by_name(self):
        dialect = _dialect()
        with pytest.raises(UnsupportedFeatureError, match=r"WITH DATA\b"):
            CreateTableAsExpression(
                dialect, _table(dialect), _query(dialect), with_data=True
            ).to_sql()
        with pytest.raises(UnsupportedFeatureError, match=r"WITH NO DATA\b"):
            CreateTableAsExpression(
                dialect, _table(dialect), _query(dialect), no_data=True
            ).to_sql()

    def test_transaction_wait_is_refused_by_name(self):
        dialect = _dialect()
        with pytest.raises(UnsupportedFeatureError, match=r"(?<!NO )WAIT\b"):
            BeginTransactionExpression(dialect, wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match=r"NO WAIT\b"):
            BeginTransactionExpression(dialect, no_wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match=r"(?<!NO )WAIT\b"):
            SetTransactionExpression(dialect, wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match=r"NO WAIT\b"):
            SetTransactionExpression(dialect, no_wait=True).to_sql()

    def test_truncate_gate_renders_mysqls_own_form(self):
        """``supports_truncate()`` is True, and the formatter is MySQL's own."""
        dialect = _dialect()
        assert dialect.supports_truncate() is True
        sql, params = TruncateExpression(dialect, _table(dialect)).to_sql()
        assert sql == "TRUNCATE TABLE `t`"
        assert params == ()


class TestGuardIsNotVacuous:
    """Guards so the checks above cannot pass by accident."""

    def test_every_case_has_two_distinct_parameters(self):
        for case in PAIR_CASES:
            assert case.a != case.b, case.case_id

    def test_every_consumed_pair_is_covered(self):
        expected = {
            "MySQLExchangePartitionExpression.with_validation",
            "TruncateExpression.cascade",
            "TruncateExpression.restart_identity",
            "DropViewExpression.cascade",
            "BeginTransactionExpression.deferrable",
            "BeginTransactionExpression.wait",
            "SetTransactionExpression.deferrable",
            "SetTransactionExpression.wait",
            "TableConstraint.enforced",
            "TableConstraint.deferrable",
            "TableConstraint.initially_deferred",
            "ColumnConstraint.deferrable",
            "ColumnConstraint.initially_deferred",
        }
        covered = {case.case_id for case in PAIR_CASES}
        assert covered == expected, (
            f"pairs consumed but not guarded: {sorted(expected - covered)}; "
            f"guarded but not consumed: {sorted(covered - expected)}"
        )
