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

Every statement handed to a backend API is built with the expression system:
``QueryStatement`` / ``InsertStatement`` / ``CreateTableStatement`` /
``DropTableStatement``. No raw SQL string is ever passed to execute/fetch/explain.
Option support is version-gated through the dialect's
``supports_explain_analyze()`` / ``supports_explain_format()`` methods; the
renderer itself does not refuse unsupported options, so every option test first
asserts the corresponding capability gate.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import pytest
from rhosocial.activerecord.backend.expression import (
    AllColumnsWildcard,
    Column,
    ColumnConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ComparisonPredicate,
    CreateTableStatement,
    DropTableStatement,
    ExplainStatement,
    IndexDefinition,
    InsertStatement,
    Literal,
    QueryStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.statements import (
    ExplainFormat,
    ExplainOptions,
    ExplainType,
)
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    DateTimeType,
    VarCharType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.explain import (
    MySQLExplainResult,
    MySQLExplainRow,
)
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLPartitionByRangeColumns,
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
)

#: The autouse ``schema`` fixture in this directory recreates only the families
#: a module declares. The order fixtures need users/orders/order_items.
TABLES = ("users", "orders", "order_items")

PARTITION_TABLE = "ar_mysql_explain_deep_events"
DDL = ExecutionOptions(stmt_type=StatementType.DDL)

#: Expected rendered SELECT used by the construction-level SQL assertions.
#: It is an assertion value only -- never passed to a backend API.
_BASE_SQL = "SELECT `id` FROM `users`"


# ---------------------------------------------------------------------------
# expression builders
# ---------------------------------------------------------------------------


def _base_query(dialect: MySQLDialect, **kwargs: Any) -> QueryStatement:
    """The QueryStatement used as the explain target in construction tests."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
        **kwargs,
    )


def _render(dialect: MySQLDialect, options: Optional[ExplainOptions] = None) -> Tuple[str, tuple]:
    """Render an EXPLAIN statement from a QueryStatement, without a DB."""
    expr = ExplainStatement(dialect, statement=_base_query(dialect), options=options)
    return expr.to_sql()


def _plan_rows(plan: Any) -> List[Dict[str, Any]]:
    """Extract MySQL's tabular EXPLAIN rows from an ActiveRecord plan."""
    return [row for row in plan if isinstance(row, dict) and "select_type" in row]


def _require_explain(dialect: MySQLDialect) -> None:
    if not dialect.supports_explain_plan():
        pytest.skip("this dialect does not support EXPLAIN")


def _seed_users_stmt(dialect: MySQLDialect) -> InsertStatement:
    """An InsertStatement that makes a PK probe a real const lookup."""
    return InsertStatement(
        dialect,
        into=Table(dialect, "users"),
        columns=["age"],
        source=ValuesSource(dialect, [[Literal(dialect, 30)]]),
    )


def _seed_users(backend: Any) -> None:
    backend.execute(*_seed_users_stmt(backend.dialect).to_sql())


async def _async_seed_users(backend: Any) -> None:
    await backend.execute(*_seed_users_stmt(backend.dialect).to_sql())


def _create_partition_table_stmt(dialect: MySQLDialect) -> CreateTableStatement:
    """A RANGE COLUMNS partitioned table, built entirely from expressions."""
    not_null = [ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, PARTITION_TABLE),
        columns=[
            ColumnDefinition(dialect, "id", BigIntType(dialect), constraints=not_null),
            ColumnDefinition(dialect, "created_at", DateTimeType(dialect), constraints=not_null),
            ColumnDefinition(dialect, "payload", VarCharType(dialect, 40)),
        ],
        indexes=[IndexDefinition(dialect, name="idx_created_at", columns=["created_at"])],
        partition=MySQLPartitionByRangeColumns(
            dialect=dialect,
            keys=[Column(dialect, "created_at")],
            partitions=[
                MySQLPartitionDefinition(
                    name="p2020", less_than=[MySQLPartitionValue(dialect, "2021-01-01")]
                ),
                MySQLPartitionDefinition(
                    name="p2021", less_than=[MySQLPartitionValue(dialect, "2022-01-01")]
                ),
                MySQLPartitionDefinition(name="pmax", less_than=[MySQLPartitionMaxValue(dialect)]),
            ],
        ),
    )


def _seed_partition_rows_stmt(dialect: MySQLDialect) -> InsertStatement:
    return InsertStatement(
        dialect,
        into=Table(dialect, PARTITION_TABLE),
        columns=["id", "created_at", "payload"],
        source=ValuesSource(
            dialect,
            [
                [
                    Literal(dialect, 1),
                    Literal(dialect, "2020-05-01"),
                    Literal(dialect, "a"),
                ],
                [
                    Literal(dialect, 2),
                    Literal(dialect, "2021-06-01"),
                    Literal(dialect, "b"),
                ],
            ],
        ),
    )


def _drop_partition_table_stmt(dialect: MySQLDialect) -> DropTableStatement:
    return DropTableStatement(dialect, table=Table(dialect, PARTITION_TABLE), if_exists=True)


def _create_partition_table(database: Any) -> None:
    dialect = database.dialect
    database.execute(*_drop_partition_table_stmt(dialect).to_sql())
    database.execute(*_create_partition_table_stmt(dialect).to_sql())
    database.execute(*_seed_partition_rows_stmt(dialect).to_sql())


def _partition_range_query(dialect: MySQLDialect) -> QueryStatement:
    where = ComparisonPredicate(
        dialect, ">=", Column(dialect, "created_at"), Literal(dialect, "2021-01-01")
    ) & ComparisonPredicate(
        dialect, "<", Column(dialect, "created_at"), Literal(dialect, "2022-01-01")
    )
    return QueryStatement(
        dialect,
        select=[AllColumnsWildcard(dialect)],
        from_=NamedRelationRef(dialect, Table(dialect, PARTITION_TABLE)),
        where=where,
    )


def _partition_full_query(dialect: MySQLDialect) -> QueryStatement:
    return QueryStatement(
        dialect,
        select=[AllColumnsWildcard(dialect)],
        from_=NamedRelationRef(dialect, Table(dialect, PARTITION_TABLE)),
    )


def _split_partitions(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _collect_explain_partitions(result: MySQLExplainResult) -> List[str]:
    found: List[str] = []
    for row in result.rows:
        found.extend(_split_partitions(row.partitions))
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
        sql, params = _render(dialect)
        assert sql == f"EXPLAIN {_BASE_SQL}"
        assert params == ()

    def test_analyze_renders_when_supported(self):
        dialect = MySQLDialect(version=(8, 0, 18))
        assert dialect.supports_explain_analyze() is True
        sql, params = _render(dialect, ExplainOptions(analyze=True))
        assert sql == f"EXPLAIN ANALYZE {_BASE_SQL}"
        assert params == ()

    def test_json_format_renders_when_supported(self):
        dialect = MySQLDialect(version=(5, 7, 0))
        assert dialect.supports_explain_format("JSON") is True
        sql, params = _render(dialect, ExplainOptions(format=ExplainFormat.JSON))
        assert sql == f"EXPLAIN FORMAT=JSON {_BASE_SQL}"
        assert params == ()

    def test_tree_format_renders_when_supported(self):
        dialect = MySQLDialect(version=(8, 0, 18))
        assert dialect.supports_explain_format("TREE") is True
        sql, params = _render(dialect, ExplainOptions(format=ExplainFormat.TREE))
        assert sql == f"EXPLAIN FORMAT=TREE {_BASE_SQL}"
        assert params == ()

    def test_query_plan_type_renders_without_extra_clause(self):
        """QUERY_PLAN is a generic type; MySQL maps it to a plain EXPLAIN."""
        dialect = MySQLDialect(version=(8, 0, 0))
        sql, _ = _render(dialect, ExplainOptions(type=ExplainType.QUERY_PLAN))
        assert sql == f"EXPLAIN {_BASE_SQL}"

    def test_where_clause_parameters_flow_through_explain(self):
        """A QueryStatement WHERE predicate keeps its bound parameter."""
        dialect = MySQLDialect(version=(8, 0, 0))
        query = _base_query(
            dialect,
            where=WhereClause(
                dialect,
                condition=ComparisonPredicate(
                    dialect, ">", Column(dialect, "age"), Literal(dialect, 30)
                ),
            ),
        )
        expr = ExplainStatement(dialect, statement=query)
        sql, params = expr.to_sql()
        assert sql == f"EXPLAIN {_BASE_SQL} WHERE `age` > %s"
        assert params == (30,)

    def test_mysql9_defaults_to_traditional_format(self):
        """MySQL 9 defaults to FORMAT=TRADITIONAL for a bare EXPLAIN."""
        dialect = MySQLDialect(version=(9, 0, 0))
        assert _render(dialect)[0] == f"EXPLAIN FORMAT=TRADITIONAL {_BASE_SQL}"
        # An explicit generic type suppresses the traditional clause again.
        assert (
            _render(dialect, ExplainOptions(type=ExplainType.QUERY_PLAN))[0]
            == f"EXPLAIN {_BASE_SQL}"
        )
        assert (
            _render(dialect, ExplainOptions(format=ExplainFormat.JSON))[0]
            == f"EXPLAIN FORMAT=JSON {_BASE_SQL}"
        )


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
        # MySQL <= 8 uses ``query_block``; MySQL 9 uses the v2 JSON plan schema
        # with a top-level ``query`` / ``query_type`` instead.
        assert isinstance(document, dict)
        assert "query_block" in document or "query" in document

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
        document = json.loads(plan[0]["EXPLAIN"])
        assert "query_block" in document or "query" in document


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
        database.execute(*_drop_partition_table_stmt(database.dialect).to_sql())


class TestMySQLPartitionPruningDeep:
    """Assert partition-pruning evidence in the native MySQL explain result."""

    def test_partition_pruning_narrows_to_target_partition(self, partition_database):
        """A predicate on the partition key reports only the matching partition."""
        dialect = partition_database.dialect
        if dialect.version < (5, 7, 0):
            pytest.skip("MySQL < 5.7 does not expose pruned partitions in EXPLAIN")
        expr = _partition_range_query(dialect)

        result = partition_database.explain(expr)

        assert isinstance(result, MySQLExplainResult)
        assert result.rows and all(isinstance(row, MySQLExplainRow) for row in result.rows)
        partitions = _collect_explain_partitions(result)
        assert "p2021" in partitions, "expected the target partition in the plan"
        assert "p2020" not in partitions, "non-matching partitions should be pruned"

    def test_full_scan_exposes_all_partitions(self, partition_database):
        """An unfiltered query lists every partition instead of pruning."""
        dialect = partition_database.dialect
        if dialect.version < (5, 7, 0):
            pytest.skip("MySQL < 5.7 does not expose pruned partitions in EXPLAIN")
        expr = _partition_full_query(dialect)

        result = partition_database.explain(expr)

        assert isinstance(result, MySQLExplainResult)
        partitions = set(_collect_explain_partitions(result))
        if partitions:
            assert {"p2020", "p2021", "pmax"} <= partitions
