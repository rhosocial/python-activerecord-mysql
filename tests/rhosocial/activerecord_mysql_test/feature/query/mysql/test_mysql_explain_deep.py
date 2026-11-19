# tests/rhosocial/activerecord_mysql_test/feature/query/mysql/test_mysql_explain_deep.py
"""Backend-local, deep EXPLAIN tests for MySQL.

The shared testsuite contracts only assert that EXPLAIN *can run*. This file
interprets what MySQL actually returns, which is deliberately NOT generalized
into the testsuite because dialects disagree on plan shape:

* ``EXPLAIN`` / ``EXPLAIN FORMAT=TRADITIONAL`` -> tabular rows such as
  ``{id, select_type, table, partitions, type, possible_keys, key, rows, Extra}``.
  ``type`` is the access method (``const`` / ``ref`` for an index lookup,
  ``ALL`` for a full scan) and ``key`` names the chosen index.
* ``EXPLAIN FORMAT=JSON`` -> a single ``EXPLAIN`` column holding a JSON document
  with a ``query_block`` node.
* ``EXPLAIN ANALYZE`` (MySQL >= 8.0.18) -> a single ``EXPLAIN`` column with a
  tree whose nodes carry ``actual time=`` statistics.
* Partitioned tables expose the ``partitions`` column, which is the concrete
  evidence of partition pruning.

Option support is version-gated and checked here through the dialect's
``supports_explain_analyze()`` / ``supports_explain_format()`` methods. The
renderer itself does not refuse unsupported options, so every option test first
asserts the corresponding capability gate. Construction-level tests render SQL
from a ``MySQLDialect`` with an explicit version and need no live server;
interpretation tests run against a real MySQL via ``order_fixtures``.
"""

import json
from typing import Any, Dict, List

import pytest
from rhosocial.activerecord.backend.expression import RawSQL
from rhosocial.activerecord.backend.expression.statements import (
    ExplainFormat,
    ExplainOptions,
    ExplainStatement,
    ExplainType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

#: The autouse ``schema`` fixture in this directory recreates only the families
#: a module declares. The order fixtures need users/orders/order_items.
TABLES = ("users", "orders", "order_items")

PARTITION_TABLE = "ar_mysql_explain_deep_events"
DDL = ExecutionOptions(stmt_type=StatementType.DDL)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _render(dialect: MySQLDialect, **options: Any) -> str:
    """Render an EXPLAIN statement with the given options, without a DB."""
    expr = ExplainStatement(dialect, RawSQL(dialect, "SELECT 1"), ExplainOptions(**options))
    return expr.to_sql()[0]


def _plan_rows(plan: Any) -> List[Dict[str, Any]]:
    """Extract MySQL's tabular EXPLAIN rows from an ActiveRecord plan."""
    return [row for row in plan if isinstance(row, dict) and "select_type" in row]


def _require_explain(dialect: MySQLDialect) -> None:
    if not dialect.supports_explain_plan():
        pytest.skip("this dialect does not support EXPLAIN")


def _seed_users(backend: Any) -> None:
    """Seed one user so a PK probe is a real const lookup, not 'no matching row'."""
    backend.execute("INSERT INTO users (age) VALUES (30)", ())


async def _async_seed_users(backend: Any) -> None:
    await backend.execute("INSERT INTO users (age) VALUES (30)", ())


def _create_partition_table(database: Any) -> None:
    """Create a RANGE-partitioned table used for pruning evidence."""
    sql = (
        f"CREATE TABLE {PARTITION_TABLE} ("
        "  id INT NOT NULL, created DATE NOT NULL, payload VARCHAR(40),"
        "  PRIMARY KEY (id, created)"
        ") ENGINE=InnoDB "
        "PARTITION BY RANGE (YEAR(created)) ("
        "  PARTITION p2020 VALUES LESS THAN (2021),"
        "  PARTITION p2021 VALUES LESS THAN (2022),"
        "  PARTITION pmax VALUES LESS THAN MAXVALUE"
        ")"
    )
    database.execute(f"DROP TABLE IF EXISTS {PARTITION_TABLE}", (), options=DDL)
    database.execute(sql, (), options=DDL)
    database.execute(
        f"INSERT INTO {PARTITION_TABLE} (id, created, payload) VALUES "
        "(1, '2020-05-01', 'a'), (2, '2021-06-01', 'b'), (3, '2022-07-01', 'c')",
        (),
    )


def _partitions_of(plan: List[Dict[str, Any]]) -> List[str]:
    """Collect the partition names reported by tabular EXPLAIN rows."""
    found: List[str] = []
    for row in _plan_rows(plan):
        value = row.get("partitions")
        if value:
            found.extend(part.strip() for part in str(value).split(",") if part.strip())
    return found


# ---------------------------------------------------------------------------
# construction / capability gates -- no live DB required
# ---------------------------------------------------------------------------


class TestMySQLExplainConstruction:
    """Option support and SQL rendering, driven by explicit server versions."""

    def test_analyze_capability_is_version_gated(self):
        """ANALYZE needs MySQL >= 8.0.18."""
        assert MySQLDialect(version=(5, 7, 0)).supports_explain_analyze() is False
        assert MySQLDialect(version=(8, 0, 17)).supports_explain_analyze() is False
        assert MySQLDialect(version=(8, 0, 18)).supports_explain_analyze() is True
        assert MySQLDialect(version=(9, 0, 0)).supports_explain_analyze() is True

    def test_format_capability_is_version_gated(self):
        """TEXT is universal, JSON needs 5.6.5+, TREE needs 8.0.16+."""
        d56 = MySQLDialect(version=(5, 6, 4))
        d565 = MySQLDialect(version=(5, 6, 5))
        d8015 = MySQLDialect(version=(8, 0, 15))
        d8016 = MySQLDialect(version=(8, 0, 16))
        assert d56.supports_explain_format("TEXT") is True
        assert d565.supports_explain_format("TEXT") is True
        assert d56.supports_explain_format("JSON") is False
        assert d565.supports_explain_format("JSON") is True
        assert d8015.supports_explain_format("TREE") is False
        assert d8016.supports_explain_format("TREE") is True
        assert d8016.supports_explain_format("XML") is False
        assert d8016.supports_explain_format("YAML") is False
        assert d8016.supports_explain_format("DOT") is False

    def test_basic_explain_renders_plain_prefix(self):
        dialect = MySQLDialect(version=(8, 0, 0))
        assert _render(dialect) == "EXPLAIN SELECT 1"

    def test_analyze_renders_when_supported(self):
        dialect = MySQLDialect(version=(8, 0, 18))
        assert dialect.supports_explain_analyze() is True
        assert _render(dialect, analyze=True) == "EXPLAIN ANALYZE SELECT 1"

    def test_json_format_renders_when_supported(self):
        dialect = MySQLDialect(version=(5, 7, 0))
        assert dialect.supports_explain_format("JSON") is True
        assert _render(dialect, format=ExplainFormat.JSON) == "EXPLAIN FORMAT=JSON SELECT 1"

    def test_tree_format_renders_when_supported(self):
        dialect = MySQLDialect(version=(8, 0, 18))
        assert dialect.supports_explain_format("TREE") is True
        assert _render(dialect, format=ExplainFormat.TREE) == "EXPLAIN FORMAT=TREE SELECT 1"

    def test_query_plan_type_renders_without_extra_clause(self):
        """QUERY_PLAN is a generic type; MySQL maps it to a plain EXPLAIN."""
        dialect = MySQLDialect(version=(8, 0, 0))
        assert _render(dialect, type=ExplainType.QUERY_PLAN) == "EXPLAIN SELECT 1"

    def test_mysql9_defaults_to_traditional_format(self):
        """MySQL 9 defaults to FORMAT=TRADITIONAL for a bare EXPLAIN."""
        dialect = MySQLDialect(version=(9, 0, 0))
        assert _render(dialect) == "EXPLAIN FORMAT=TRADITIONAL SELECT 1"
        # An explicit generic type suppresses the traditional clause again.
        assert _render(dialect, type=ExplainType.QUERY_PLAN) == "EXPLAIN SELECT 1"
        assert _render(dialect, format=ExplainFormat.JSON) == "EXPLAIN FORMAT=JSON SELECT 1"


# ---------------------------------------------------------------------------
# result interpretation -- synchronous, needs a real MySQL
# ---------------------------------------------------------------------------


class TestMySQLExplainDeep:
    """Interpret MySQL's EXPLAIN output through ActiveRecord."""

    def test_plan_rows_have_mysql_shape(self, order_fixtures):
        User, _, _ = order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        plan = User.query().explain().aggregate()
        rows = _plan_rows(plan)
        assert rows, "EXPLAIN must return tabular rows with a select_type column"
        assert {"select_type", "table", "type", "key", "partitions", "Extra"} <= set(rows[0])

    def test_full_scan_on_unindexed_column(self, order_fixtures):
        """A filter on a non-indexed column plans as an ALL-table scan."""
        User, _, _ = order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        plan = User.query().where(User.c.age > 30).explain().aggregate()
        rows = [row for row in _plan_rows(plan) if row.get("table") == "users"]
        assert rows, "expected a plan row for the users table"
        assert any(row.get("type") == "ALL" for row in rows), "expected a full table scan"
        assert all(row.get("key") in (None, "") for row in rows), "no index should be chosen"

    def test_primary_key_lookup_uses_index(self, order_fixtures):
        """A primary-key predicate plans as an index access, not a scan."""
        User, _, _ = order_fixtures
        backend = User.backend()
        dialect = backend.dialect
        _require_explain(dialect)
        _seed_users(backend)
        plan = User.query().where(User.c.id == 1).explain().aggregate()
        rows = [row for row in _plan_rows(plan) if row.get("table") == "users"]
        assert rows, "expected a plan row for the users table"
        assert any(row.get("key") == "PRIMARY" for row in rows), "expected the PRIMARY index"
        assert any(row.get("type") != "ALL" for row in rows), "expected an indexed access method"

    def test_join_plan_lists_both_tables(self, order_fixtures):
        """A two-table JOIN produces plan rows for both relations."""
        User, Order, _ = order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        plan = User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain().aggregate()
        tables = {row.get("table") for row in _plan_rows(plan)}
        assert {"users", "orders"} <= tables, "JOIN plan must mention both tables"

    def test_json_format_returns_parseable_document(self, order_fixtures):
        """FORMAT=JSON yields a single EXPLAIN column with a query_block."""
        User, _, _ = order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        if not dialect.supports_explain_format("JSON"):
            pytest.skip("server does not support EXPLAIN FORMAT=JSON")
        plan = User.query().explain(format=ExplainFormat.JSON).aggregate()
        assert plan and isinstance(plan[0], dict) and "EXPLAIN" in plan[0]
        document = json.loads(plan[0]["EXPLAIN"])
        assert "query_block" in document

    def test_analyze_returns_plan_when_supported(self, order_fixtures):
        """EXPLAIN ANALYZE is accepted and returns a plan on modern servers."""
        User, _, _ = order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        if not dialect.supports_explain_analyze():
            pytest.skip("server does not support EXPLAIN ANALYZE")
        plan = User.query().explain(analyze=True).aggregate()
        assert isinstance(plan, list) and plan, "ANALYZE must return a non-empty plan"
        assert all(isinstance(row, dict) for row in plan)


# ---------------------------------------------------------------------------
# result interpretation -- asynchronous (mirrors the sync cases)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAsyncMySQLExplainDeep:
    """Interpret MySQL's EXPLAIN output through the async ActiveRecord."""

    async def test_full_scan_on_unindexed_column(self, async_order_fixtures):
        User, _, _ = async_order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        plan = await User.query().where(User.c.age > 30).explain().aggregate()
        rows = [row for row in _plan_rows(plan) if row.get("table") == "users"]
        assert rows and any(row.get("type") == "ALL" for row in rows)

    async def test_primary_key_lookup_uses_index(self, async_order_fixtures):
        User, _, _ = async_order_fixtures
        backend = User.backend()
        dialect = backend.dialect
        _require_explain(dialect)
        await _async_seed_users(backend)
        plan = await User.query().where(User.c.id == 1).explain().aggregate()
        rows = [row for row in _plan_rows(plan) if row.get("table") == "users"]
        assert rows and any(row.get("key") == "PRIMARY" for row in rows)

    async def test_join_plan_lists_both_tables(self, async_order_fixtures):
        User, Order, _ = async_order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        plan = (
            await User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain().aggregate()
        )
        tables = {row.get("table") for row in _plan_rows(plan)}
        assert {"users", "orders"} <= tables

    async def test_json_format_returns_parseable_document(self, async_order_fixtures):
        User, _, _ = async_order_fixtures
        dialect = User.backend().dialect
        _require_explain(dialect)
        if not dialect.supports_explain_format("JSON"):
            pytest.skip("server does not support EXPLAIN FORMAT=JSON")
        plan = await User.query().explain(format=ExplainFormat.JSON).aggregate()
        assert plan and isinstance(plan[0], dict) and "EXPLAIN" in plan[0]
        assert "query_block" in json.loads(plan[0]["EXPLAIN"])


# ---------------------------------------------------------------------------
# partition pruning -- declarative partitioning is a real MySQL capability
# ---------------------------------------------------------------------------


@pytest.fixture
def partition_database(database):
    """A live backend with a RANGE-partitioned table seeded for pruning."""
    _create_partition_table(database)
    try:
        yield database
    finally:
        database.execute(f"DROP TABLE IF EXISTS {PARTITION_TABLE}", (), options=DDL)


class TestMySQLPartitionPruningDeep:
    """Assert partition-pruning evidence in the native MySQL plan."""

    def test_partition_pruning_narrows_to_target_partition(self, partition_database):
        """A predicate on the partition key reports only the matching partition."""
        sql = (
            f"EXPLAIN SELECT * FROM {PARTITION_TABLE} "
            "WHERE created >= '2021-01-01' AND created < '2022-01-01'"
        )
        plan = partition_database.fetch_all(sql, ())
        partitions = _partitions_of([dict(row) for row in plan])
        assert "p2021" in partitions, "expected the target partition in the plan"
        assert "p2020" not in partitions, "non-matching partitions should be pruned"

    def test_full_scan_exposes_all_partitions(self, partition_database):
        """An unfiltered query lists every partition instead of pruning."""
        plan = partition_database.fetch_all(f"EXPLAIN SELECT * FROM {PARTITION_TABLE}", ())
        partitions = set(_partitions_of([dict(row) for row in plan]))
        assert {"p2020", "p2021", "pmax"} <= partitions
