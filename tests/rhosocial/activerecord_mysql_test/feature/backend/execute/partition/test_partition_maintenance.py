# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/partition/test_partition_maintenance.py
"""Live partition-maintenance round trip against a configured MySQL server.

The offline matrix proves the SQL and the planning rules.  This module proves
the same plan against ``information_schema.PARTITIONS`` on a real server: a
table with a MAXVALUE partition gains a partition through REORGANIZE, validate
agrees, and drop_before removes a partition that ends exactly at the cutoff.

No server is started here.  When none of the configured scenarios is reachable
the module is skipped at collection time; CI supplies the server.
"""

from uuid import uuid4

import pytest

from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
)
from rhosocial.activerecord.backend.impl.mysql.partition_maintenance import (
    AsyncMySQLPartitionMaintenance,
    MySQLPartitionMaintenance,
    MySQLPartitionPlan,
)

from mysql_live_server import mysql_server_available

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)


def _plan(table: str, backend) -> MySQLPartitionPlan:
    """Build the plan used by both the sync and async round trips."""
    dialect = backend.dialect
    return MySQLPartitionPlan(
        table,
        (
            MySQLPartitionDefinition(
                "p2026", less_than=[MySQLPartitionValue(dialect, 2027)]
            ),
            MySQLPartitionDefinition(
                "p2027", less_than=[MySQLPartitionValue(dialect, 2028)]
            ),
            MySQLPartitionDefinition(
                "pmax", less_than=[MySQLPartitionMaxValue(dialect)]
            ),
        ),
    )


def _create_table_sql(table: str) -> str:
    """The RANGE-partitioned table SQL used by both round trips."""
    return (
        f"CREATE TABLE `{table}` ("
        "`id` INT NOT NULL, "
        "PRIMARY KEY (`id`)"
        ") ENGINE=InnoDB "
        "PARTITION BY RANGE (`id`) ("
        "PARTITION `p2026` VALUES LESS THAN (2027), "
        "PARTITION `pmax` VALUES LESS THAN MAXVALUE"
        ")"
    )


def _create_table(backend, table: str) -> None:
    """Create a RANGE-partitioned table with a trailing MAXVALUE partition."""
    backend.execute(_create_table_sql(table))


class TestPartitionMaintenance:
    """Synchronous partition maintenance against a live server."""

    def test_ensure_list_validate_drop_before_round_trip(self, mysql_backend_single):
        backend = mysql_backend_single
        table = f"partition_maint_{uuid4().hex[:8]}"
        try:
            _create_table(backend, table)
            maintenance = MySQLPartitionMaintenance(backend)
            plan = _plan(table, backend)

            before = maintenance.list(table, plan=plan)
            assert before.partition_names == ("p2026", "pmax")
            assert before.missing == ("p2027",)
            assert before.orphans == ()

            ensured = maintenance.ensure(plan)
            assert ensured.added == ("p2027",)
            assert ensured.skipped == ()

            after = maintenance.list(table, plan=plan)
            assert after.partition_names == ("p2026", "p2027", "pmax")
            assert after.missing == ()
            assert after.orphans == ()

            validated = maintenance.validate(plan)
            assert validated.issues == ()
            assert validated.missing == ()

            dry = maintenance.drop_before(plan, 2027)
            assert dry.dropped == ("p2026",)
            assert dry.dry_run is True

            dropped = maintenance.drop_before(plan, 2027, dry_run=False)
            assert dropped.dropped == ("p2026",)

            final = maintenance.list(table, plan=plan)
            assert final.partition_names == ("p2027", "pmax")
            # The plan still names the partition retention just removed.
            assert final.missing == ("p2026",)
        finally:
            backend.execute(f"DROP TABLE IF EXISTS `{table}`")


class TestAsyncPartitionMaintenance:
    """Async round trip with the same method names as the sync class."""

    @pytest.mark.asyncio
    async def test_ensure_list_validate_drop_before_round_trip(
        self, async_mysql_backend_single
    ):
        backend = async_mysql_backend_single
        table = f"partition_maint_{uuid4().hex[:8]}"
        try:
            await backend.execute(_create_table_sql(table))
            maintenance = AsyncMySQLPartitionMaintenance(backend)
            plan = _plan(table, backend)

            before = await maintenance.list(table, plan=plan)
            assert before.partition_names == ("p2026", "pmax")
            assert before.missing == ("p2027",)

            ensured = await maintenance.ensure(plan)
            assert ensured.added == ("p2027",)
            assert ensured.skipped == ()

            after = await maintenance.list(table, plan=plan)
            assert after.partition_names == ("p2026", "p2027", "pmax")
            assert after.missing == ()

            validated = await maintenance.validate(plan)
            assert validated.issues == ()

            dropped = await maintenance.drop_before(plan, 2027, dry_run=False)
            assert dropped.dropped == ("p2026",)

            final = await maintenance.list(table, plan=plan)
            assert final.partition_names == ("p2027", "pmax")
        finally:
            await backend.execute(f"DROP TABLE IF EXISTS `{table}`")
