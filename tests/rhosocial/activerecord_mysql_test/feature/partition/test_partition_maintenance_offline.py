# tests/rhosocial/activerecord_mysql_test/feature/partition/test_partition_maintenance_offline.py
"""Unit tests for MySQL partition maintenance helpers and subpartition limits.

These tests never connect to a server.  A tiny fake backend supplies the
snapshot rows and records the SQL that ``ensure`` / ``drop_before`` would
send, so the planning rules and the DDL they produce are both covered.

Live execution tests live under ``feature/backend`` and require a configured
MySQL scenario.
"""

from datetime import date, datetime

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLSubpartitionClause,
    MySQLSubpartitionDefinition,
    MySQLSubpartitionStrategy,
    MySQLPartitionValue,
)
from rhosocial.activerecord.backend.partition import (
    AsyncPartitionEnsurer,
    AsyncPartitionInventory,
    AsyncPartitionRetention,
    AsyncPartitionValidator,
    PartitionEnsurer,
    PartitionInventory,
    PartitionReport as CorePartitionReport,
    PartitionRetention,
    PartitionValidator,
)
from rhosocial.activerecord.backend.impl.mysql.partition_maintenance import (
    AsyncMySQLPartitionMaintenance,
    MySQLPartitionMaintenance,
    MySQLPartitionPlan,
    MySQLPartitionReport,
    build_report,
    plan_additions,
    plan_changes,
    select_drops,
)


@pytest.fixture
def dialect():
    return MySQLDialect(version=(8, 0, 0))


def _value(dialect, value):
    return MySQLPartitionValue(dialect, value)


def _definition(dialect, name, upper_bound):
    if upper_bound is None:
        return MySQLPartitionDefinition(
            name=name, less_than=[MySQLPartitionMaxValue(dialect)]
        )
    return MySQLPartitionDefinition(name=name, less_than=[_value(dialect, upper_bound)])


def _rows(*partitions):
    """Build information_schema.PARTITIONS-shaped rows.

    Each partition is ``(name, description, subnames)`` or
    ``(name, description, subnames, method)``; when subnames is empty a
    single top-level row is produced.
    """
    rows = []
    for partition in partitions:
        name, description, subnames = partition[:3]
        method = partition[3] if len(partition) > 3 else "RANGE"
        if not subnames:
            rows.append(
                {
                    "name": name,
                    "subname": None,
                    "method": method,
                    "submethod": None,
                    "description": description,
                    "table_rows": 1,
                    "data_length": 2,
                    "index_length": 3,
                }
            )
            continue
        for index, subname in enumerate(subnames):
            rows.append(
                {
                    "name": name,
                    "subname": subname,
                    "method": method,
                    "submethod": "HASH",
                    "description": description,
                    "table_rows": index + 1,
                    "data_length": 2,
                    "index_length": 3,
                }
            )
    return rows


class FakeBackend:
    """Minimal backend surface used by the maintenance class."""

    def __init__(self, rows):
        self.dialect = MySQLDialect(version=(8, 0, 0))
        self._rows = rows
        self.executed = []

    def fetch_all(self, sql, params=None):
        return list(self._rows)

    def execute(self, sql, params=None):
        self.executed.append((sql, params))


class FakeAsyncBackend(FakeBackend):
    """Async counterpart of :class:`FakeBackend`."""

    async def fetch_all(self, sql, params=None):
        return list(self._rows)

    async def execute(self, sql, params=None):
        self.executed.append((sql, params))


# --- subpartition capability limits ----------------------------------------


def test_subpartition_hash_and_key_are_accepted(dialect):
    for strategy in (
        MySQLSubpartitionStrategy.HASH,
        MySQLSubpartitionStrategy.KEY,
        MySQLSubpartitionStrategy.LINEAR_HASH,
        MySQLSubpartitionStrategy.LINEAR_KEY,
    ):
        clause = MySQLSubpartitionClause(
            dialect, strategy=strategy,
            expression=Column(dialect, "id"), count=2,
        )
        sql, params = clause.to_sql()
        assert f"SUBPARTITION BY {strategy.value}" in sql
        assert "`id`" in sql
        assert "SUBPARTITIONS 2" in sql
        assert params == ()


@pytest.mark.parametrize("strategy", ["RANGE", "RANGE COLUMNS", "LIST", "LIST COLUMNS"])
def test_subpartition_range_and_list_are_refused_by_name(dialect, strategy):
    with pytest.raises(UnsupportedFeatureError, match="SUBPARTITION BY"):
        MySQLSubpartitionClause(dialect, strategy=strategy)


def test_subpartition_range_is_not_silently_downgraded(dialect):
    with pytest.raises(UnsupportedFeatureError) as caught:
        MySQLSubpartitionClause(dialect, strategy="RANGE")
    assert "RANGE" in caught.value.feature_name
    assert "HASH" in (caught.value.suggestion or "")


def test_explicit_per_partition_subpartition_definitions(dialect):
    expression = MySQLPartitionByRange(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            MySQLPartitionDefinition(
                "p2026",
                less_than=[_value(dialect, "2027-01-01")],
                subpartition_definitions=[
                    MySQLSubpartitionDefinition("p2026_s0"),
                    MySQLSubpartitionDefinition("p2026_s1"),
                ],
            ),
            MySQLPartitionDefinition(
                "p2027",
                less_than=[_value(dialect, "2028-01-01")],
                subpartition_definitions=[
                    MySQLSubpartitionDefinition("p2027_s0"),
                ],
            ),
        ],
        subpartition_by=MySQLSubpartitionClause(
            dialect,
            strategy=MySQLSubpartitionStrategy.HASH,
            expression=Column(dialect, "tenant_id"),
            count=2,
        ),
    )

    sql, params = expression.to_sql()

    assert sql.index("SUBPARTITION BY HASH") < sql.index("PARTITION `p2026`")
    assert "`p2026_s0`" in sql and "`p2026_s1`" in sql
    assert "`p2027_s0`" in sql
    assert params == ()


def test_subpartition_definition_options_still_render_after_rejection(dialect):
    expression = MySQLPartitionByRangeColumns(
        dialect,
        [Column(dialect, "created_at")],
        partitions=[
            MySQLPartitionDefinition(
                "p0",
                less_than=[_value(dialect, "2026-01-01")],
                subpartition_definitions=[MySQLSubpartitionDefinition("s0")],
            )
        ],
        subpartition_by=MySQLSubpartitionClause(
            dialect,
            strategy=MySQLSubpartitionStrategy.KEY,
            expression=Column(dialect, "id"),
            count=1,
        ),
    )
    sql, _ = expression.to_sql()
    assert "SUBPARTITION BY KEY" in sql
    assert "`id`" in sql
    assert "`s0`" in sql


# --- plan validation -------------------------------------------------------


def test_plan_requires_unique_names_and_ascending_bounds(dialect):
    with pytest.raises(ValueError, match="must be unique"):
        MySQLPartitionPlan(
            "events",
            (
                _definition(dialect, "p1", 10),
                _definition(dialect, "p1", 20),
            ),
        )
    with pytest.raises(ValueError, match="ascending order"):
        MySQLPartitionPlan(
            "events",
            (
                _definition(dialect, "p1", 20),
                _definition(dialect, "p2", 10),
            ),
        )


def test_plan_requires_maxvalue_last(dialect):
    with pytest.raises(ValueError, match="MAXVALUE partition must be the last"):
        MySQLPartitionPlan(
            "events",
            (
                _definition(dialect, "pmax", None),
                _definition(dialect, "p1", 10),
            ),
        )


def test_plan_accepts_iso_string_bounds_and_maxvalue(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    assert plan.table == "events"


# --- ensure planning -------------------------------------------------------


def test_plan_additions_adds_only_missing_ascending(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    additions, skipped = plan_additions(plan, ["p2026_01"])
    assert [definition.name for definition in additions] == ["p2026_02", "p2026_03"]
    assert skipped == []


def test_plan_additions_skips_missing_partition_below_maximum(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    additions, skipped = plan_additions(
        plan, ["p2026_01", "p2026_03"]
    )
    assert additions == []
    assert [name for name, _ in skipped] == ["p2026_02"]
    assert "REORGANIZE" in skipped[0][1]


def test_plan_additions_skips_after_maxvalue(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    additions, skipped = plan_additions(plan, ["p2026", "pmax"])
    assert additions == []

    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    additions, skipped = plan_additions(plan, ["p2026", "pmax"])
    assert additions == []
    assert [name for name, _ in skipped] == ["p2027"]
    assert "MAXVALUE" in skipped[0][1]


def test_plan_additions_reports_unknown_existing_partition(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
        ),
    )
    additions, skipped = plan_additions(plan, ["p_legacy", "p2026"])
    assert additions == []
    assert [name for name, _ in skipped] == ["p2027"]
    assert "not named by the plan" in skipped[0][1]


def test_plan_additions_list_definitions_need_no_ordering(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            MySQLPartitionDefinition("p_a", in_values=[_value(dialect, "a")]),
            MySQLPartitionDefinition("p_b", in_values=[_value(dialect, "b")]),
        ),
    )
    additions, skipped = plan_additions(plan, ["p_b"])
    assert [definition.name for definition in additions] == ["p_a"]
    assert skipped == []


# --- drop planning ---------------------------------------------------------


def test_select_drops_uses_whole_range_before_cutoff(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    dropped, skipped = select_drops(
        plan,
        ["p2026_01", "p2026_02", "p2026_03"],
        date(2026, 2, 1),
    )
    assert dropped == ["p2026_01"]
    assert skipped == []


def test_select_drops_includes_partition_ending_at_cutoff(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    dropped, skipped = select_drops(
        plan,
        ["p2026_01", "p2026_02", "p2026_03"],
        date(2026, 3, 1),
    )
    assert dropped == ["p2026_01", "p2026_02"]
    assert skipped == []


def test_select_drops_keeps_last_partition(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    dropped, skipped = select_drops(
        plan,
        ["p2026_01", "p2026_02"],
        datetime(2026, 4, 1),
    )
    assert dropped == ["p2026_01"]
    assert [name for name, _ in skipped] == ["p2026_02"]
    assert "last partition" in skipped[0][1]


def test_select_drops_ignores_missing_and_maxvalue(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    dropped, skipped = select_drops(plan, ["p2026", "pmax"], date(2026, 12, 31))
    assert dropped == []
    assert skipped == []


def test_select_drops_rejects_list_plan(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (MySQLPartitionDefinition("p_a", in_values=[_value(dialect, "a")]),),
    )
    with pytest.raises(ValueError, match="RANGE plans"):
        select_drops(plan, ["p_a"], 100)


# --- report building and the operations class ------------------------------


def test_build_report_flat_tree_with_subpartitions():
    report = build_report(
        "events",
        _rows(
            ("p2026", "2027-01-01", ("p2026_s0", "p2026_s1")),
            ("p2027", "2028-01-01", ()),
        ),
    )
    assert isinstance(report, MySQLPartitionReport)
    assert report.partition_names == ("p2026", "p2027")
    parent = report.partitions[0]
    assert parent.parent is None
    assert parent.extras["children"] == ("p2026_s0", "p2026_s1")
    assert parent.row_count == 3
    assert parent.size_bytes == 10
    child = report.partitions[1]
    assert child.parent == "p2026"
    assert child.method == "HASH"
    assert child.bound is None


def test_ensure_executes_one_add_statement_and_reports_skips(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = MySQLPartitionMaintenance(backend)

    report = maintenance.ensure(plan)

    assert report.missing == ("p2026_02", "p2026_03")
    assert report.added == ("p2026_02", "p2026_03")
    assert report.skipped == ()
    assert len(backend.executed) == 1
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` ADD PARTITION")
    assert "p2026_02" in sql and "p2026_03" in sql
    assert params == ()


def test_ensure_dry_run_sends_no_sql(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = MySQLPartitionMaintenance(backend)

    report = maintenance.ensure(plan, dry_run=True)

    assert report.added == ("p2026_02",)
    assert report.dry_run is True
    assert backend.executed == []


def test_drop_before_dry_run_and_execution(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_02", "2026-03-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )
    maintenance = MySQLPartitionMaintenance(backend)

    dry = maintenance.drop_before(plan, date(2026, 2, 1))
    assert dry.dropped == ("p2026_01",)
    assert dry.dry_run is True
    assert backend.executed == []

    executed = maintenance.drop_before(plan, date(2026, 2, 1), dry_run=False)
    assert executed.dropped == ("p2026_01",)
    assert executed.dry_run is False
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` DROP PARTITION")
    assert "p2026_01" in sql
    assert params == ()


# --- MAXVALUE folds, gap fills and refusals --------------------------------


def test_plan_changes_folds_new_partitions_into_maxvalue(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )
    report = MySQLPartitionMaintenance(backend).list("events", plan=plan)

    changes, skipped = plan_changes(plan, report, dialect)

    assert skipped == []
    assert [change.action for change in changes] == ["reorganize"]
    assert changes[0].partition == "pmax"
    assert [definition.name for definition in changes[0].definitions] == [
        "p2027",
        "pmax",
    ]


def test_ensure_reorganizes_maxvalue_into_new_partitions(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.missing == ("p2027",)
    assert report.added == ("p2027",)
    assert report.skipped == ()
    assert len(backend.executed) == 1
    sql, params = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` REORGANIZE PARTITION `pmax` INTO (")
    assert "PARTITION `p2027` VALUES LESS THAN ('2028-01-01')" in sql
    assert "PARTITION `pmax` VALUES LESS THAN (MAXVALUE)" in sql
    assert params == ()


def test_ensure_keeps_an_orphan_maxvalue_partition_while_folding(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "p2027", "2028-01-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.orphans == ("pmax",)
    assert report.added == ("p2027",)
    assert report.skipped == ()
    sql, _ = backend.executed[0]
    assert sql.startswith("ALTER TABLE `events` REORGANIZE PARTITION `pmax` INTO (")
    assert "PARTITION `pmax` VALUES LESS THAN (MAXVALUE)" in sql


def test_plan_changes_splits_the_partition_that_contains_a_gap(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )
    report = MySQLPartitionMaintenance(backend).list("events", plan=plan)

    changes, skipped = plan_changes(plan, report, dialect)

    assert skipped == []
    assert changes[0].action == "reorganize"
    assert changes[0].partition == "p2026_03"
    assert [definition.name for definition in changes[0].definitions] == [
        "p2026_02",
        "p2026_03",
    ]


def test_ensure_reorganizes_the_successor_for_an_intermediate_gap(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.missing == ("p2026_02",)
    assert report.added == ("p2026_02",)
    assert len(backend.executed) == 1
    sql, _ = backend.executed[0]
    assert sql.startswith(
        "ALTER TABLE `events` REORGANIZE PARTITION `p2026_03` INTO ("
    )
    assert "PARTITION `p2026_02` VALUES LESS THAN ('2026-03-01')" in sql
    assert "PARTITION `p2026_03` VALUES LESS THAN ('2026-04-01')" in sql


def test_ensure_splits_the_first_partition_for_a_leading_gap(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeBackend(_rows(("p2026_02", "2026-03-01", ())))

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.added == ("p2026_01",)
    sql, _ = backend.executed[0]
    assert sql.startswith(
        "ALTER TABLE `events` REORGANIZE PARTITION `p2026_02` INTO ("
    )
    assert "PARTITION `p2026_01` VALUES LESS THAN ('2026-02-01')" in sql


def test_ensure_refuses_a_range_already_covered_by_another_partition(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p_legacy", "2026-03-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.added == ()
    assert [name for name, _ in report.skipped] == ["p2026_02"]
    assert "already covered" in report.skipped[0][1]
    assert "p_legacy" in report.skipped[0][1]
    assert backend.executed == []


def test_ensure_refuses_when_a_catalogue_boundary_drifts(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-03-01"),
            _definition(dialect, "p2026_02", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.added == ()
    assert [name for name, _ in report.skipped] == ["p2026_02"]
    assert "ends at 2026-02-01" in report.skipped[0][1]
    assert "declares 2026-03-01" in report.skipped[0][1]
    assert backend.executed == []


def test_ensure_refuses_a_non_partitioned_table(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (_definition(dialect, "p2026", "2027-01-01"),),
    )
    backend = FakeBackend([])

    report = MySQLPartitionMaintenance(backend).ensure(plan)

    assert report.added == ()
    assert [name for name, _ in report.skipped] == ["p2026"]
    assert "not partitioned" in report.skipped[0][1] or "no partitions" in report.skipped[0][1]
    assert backend.executed == []


# --- validate and missing --------------------------------------------------


def test_list_fills_missing_from_the_plan_and_keeps_orphans(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_02", "2026-03-01", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).list("events", plan=plan)

    assert report.missing == ("p2026_03",)
    assert report.orphans == ("p2026_01",)


def test_validate_reports_missing_orphans_and_drift_without_repair(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-05"),
            _definition(dialect, "p2026_03", "2026-05-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_02", "2026-03-01", (), "LIST"),
            ("p_legacy", "2026-04-01", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).validate(plan)

    assert report.missing == ("p2026_03",)
    assert report.orphans == ("p_legacy",)
    assert report.dropped == ()
    assert report.added == ()
    assert report.skipped == ()
    assert report.dry_run is True
    assert len(report.issues) == 2
    assert any("method is LIST" in issue for issue in report.issues)
    assert any("boundary is 2026-03-01" in issue for issue in report.issues)
    assert backend.executed == []


def test_validate_accepts_a_plan_that_matches_the_catalogue(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026", "2027-01-01"),
            _definition(dialect, "pmax", None),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026", "2027-01-01", ()),
            ("pmax", "MAXVALUE", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).validate(plan)

    assert report.missing == ()
    assert report.orphans == ()
    assert report.issues == ()
    assert backend.executed == []


def test_drop_before_includes_a_partition_ending_at_the_cutoff(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
            _definition(dialect, "p2026_03", "2026-04-01"),
        ),
    )
    backend = FakeBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_02", "2026-03-01", ()),
            ("p2026_03", "2026-04-01", ()),
        )
    )

    report = MySQLPartitionMaintenance(backend).drop_before(
        plan, date(2026, 3, 1)
    )

    assert report.dropped == ("p2026_01", "p2026_02")
    assert report.dry_run is True
    assert backend.executed == []


# --- async parity ----------------------------------------------------------


@pytest.mark.asyncio
async def test_async_ensure_and_drop_before_match_sync_behaviour(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-01"),
        ),
    )
    backend = FakeAsyncBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = AsyncMySQLPartitionMaintenance(backend)

    ensured = await maintenance.ensure(plan)
    assert ensured.missing == ("p2026_02",)
    assert ensured.added == ("p2026_02",)
    assert backend.executed[-1][0].startswith("ALTER TABLE `events` ADD PARTITION")

    backend._rows = _rows(
        ("p2026_01", "2026-02-01", ()),
        ("p2026_02", "2026-03-01", ()),
    )
    dropped = await maintenance.drop_before(plan, date(2026, 3, 1), dry_run=False)
    assert dropped.dropped == ("p2026_01",)
    assert backend.executed[-1][0].startswith("ALTER TABLE `events` DROP PARTITION")


@pytest.mark.asyncio
async def test_async_validate_reports_the_same_findings_as_sync(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (
            _definition(dialect, "p2026_01", "2026-02-01"),
            _definition(dialect, "p2026_02", "2026-03-05"),
        ),
    )
    backend = FakeAsyncBackend(
        _rows(
            ("p2026_01", "2026-02-01", ()),
            ("p2026_02", "2026-03-01", (), "LIST"),
        )
    )
    maintenance = AsyncMySQLPartitionMaintenance(backend)

    report = await maintenance.validate(plan)

    assert report.issues == (
        "partition p2026_02 method is LIST but the plan declares RANGE",
        "partition p2026_02 boundary is 2026-03-01 but the plan declares "
        "2026-03-05",
    )
    assert report.dry_run is True
    assert backend.executed == []


def test_ensure_reports_orphans_without_dropping_them(dialect):
    plan = MySQLPartitionPlan(
        "events",
        (_definition(dialect, "p2026_02", "2026-03-01"),),
    )
    backend = FakeBackend(
        _rows(
            ("p_legacy", "2026-01-01", ()),
            ("p2026_01", "2026-02-01", ()),
        )
    )
    maintenance = MySQLPartitionMaintenance(backend)

    report = maintenance.ensure(plan, dry_run=True)

    assert report.orphans == ("p_legacy", "p2026_01")
    assert report.added == ("p2026_02",)
    assert report.skipped == ()
    assert backend.executed == []


def test_list_marks_orphans_only_when_plan_given(dialect):
    backend = FakeBackend(_rows(("p2026_01", "2026-02-01", ()),))
    maintenance = MySQLPartitionMaintenance(backend)

    assert maintenance.list("events").orphans == ()

    plan = MySQLPartitionPlan(
        "events",
        (_definition(dialect, "p2026_02", "2026-03-01"),),
    )
    assert maintenance.list("events", plan=plan).orphans == ("p2026_01",)


def test_report_is_the_core_contract_type():
    assert MySQLPartitionReport is CorePartitionReport


def test_the_sync_executor_offers_inventory_ensure_retention_and_validate():
    executor = MySQLPartitionMaintenance(FakeBackend([]))

    assert isinstance(executor, PartitionInventory)
    assert isinstance(executor, PartitionEnsurer)
    assert isinstance(executor, PartitionRetention)
    assert isinstance(executor, PartitionValidator)


def test_the_async_executor_offers_inventory_ensure_retention_and_validate():
    executor = AsyncMySQLPartitionMaintenance(FakeAsyncBackend([]))

    assert isinstance(executor, AsyncPartitionInventory)
    assert isinstance(executor, AsyncPartitionEnsurer)
    assert isinstance(executor, AsyncPartitionRetention)
    assert isinstance(executor, AsyncPartitionValidator)
