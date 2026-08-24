# tests/rhosocial/activerecord_mysql_test/feature/backend/test_expression_roundtrip_all.py
"""
Functional serialization coverage for MySQL expression classes.

Every expression class defined in ``rhosocial.activerecord.backend.impl.mysql
.expression`` must round-trip losslessly through dict / JSON / XML encodings,
and produce identical ``to_sql()`` where the MySQL dialect supports it.
"""

import pytest

from rhosocial.activerecord.testsuite.utils.expression import (
    collect_expression_classes,
    make_instance,
    register_all,
    register_special_constructor,
    roundtrip_expression,
    sql_consistent,
)

MYSQL_EXPR_PKG = "rhosocial.activerecord.backend.impl.mysql.expression"

CLASSES = collect_expression_classes(MYSQL_EXPR_PKG)
register_all(CLASSES)


def _table(d, name="t"):
    from rhosocial.activerecord.backend.expression.core import TableExpression
    return TableExpression(d, name)


def _register_mysql_specials():
    from rhosocial.activerecord.backend.expression.core import Column, Literal
    from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

    def match_against(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.match_against import (
            MySQLMatchAgainstExpression,
        )
        return MySQLMatchAgainstExpression(d, columns=["title"], search_string="x")

    def json_object(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.json import (
            MySQLJSONObjectExpression,
        )
        return MySQLJSONObjectExpression(d, {"a": 1})

    def json_array(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.json import (
            MySQLJSONArrayExpression,
        )
        return MySQLJSONArrayExpression(d, 1, 2, alias="arr")

    def json_extract(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.json import (
            MySQLJSONExtractExpression,
        )
        return MySQLJSONExtractExpression(d, "data", "$.a", alias="n")

    def json_contains(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.json import (
            MySQLJSONContainsExpression,
        )
        return MySQLJSONContainsExpression(d, "data", "x", "$.a")

    def st_distance(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.spatial import (
            MySQLSTDistanceExpression,
        )
        return MySQLSTDistanceExpression(d, "g1", "g2")

    def partition_clause(d):
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLPartitionClause,
        )
        return MySQLPartitionClause(d, "RANGE", [Column(d, "id")])

    def partition_by_range(d):
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLPartitionByRange,
        )
        return MySQLPartitionByRange(d, [Column(d, "id")])

    def partition_by_range_columns(d):
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLPartitionByRangeColumns,
        )
        return MySQLPartitionByRangeColumns(d, [Column(d, "a"), Column(d, "b")])

    def partition_by_list(d):
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLPartitionByList,
        )
        return MySQLPartitionByList(d, [Column(d, "id")])

    def partition_by_list_columns(d):
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLPartitionByListColumns,
        )
        return MySQLPartitionByListColumns(d, [Column(d, "a"), Column(d, "b")])

    def partition_by_hash(d):
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLPartitionByHash,
        )
        return MySQLPartitionByHash(d, [Column(d, "id")], partitions_count=4)

    def subpartition_clause(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLSubpartitionClause,
            MySQLSubpartitionStrategy,
        )
        return MySQLSubpartitionClause(
            d, MySQLSubpartitionStrategy.HASH, count=4
        )

    def coalesce_partition(d):
        from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
            MySQLCoalescePartitionExpression,
        )
        return MySQLCoalescePartitionExpression(d, table="t", count=2)

    register_special_constructor(
        "match_against.MySQLMatchAgainstExpression", match_against
    )
    register_special_constructor("json.MySQLJSONObjectExpression", json_object)
    register_special_constructor("json.MySQLJSONArrayExpression", json_array)
    register_special_constructor("json.MySQLJSONExtractExpression", json_extract)
    register_special_constructor("json.MySQLJSONContainsExpression", json_contains)
    register_special_constructor("spatial.MySQLSTDistanceExpression", st_distance)
    register_special_constructor("partition.MySQLPartitionClause", partition_clause)
    register_special_constructor("partition.MySQLPartitionByRange", partition_by_range)
    register_special_constructor(
        "partition.MySQLPartitionByRangeColumns", partition_by_range_columns
    )
    register_special_constructor("partition.MySQLPartitionByList", partition_by_list)
    register_special_constructor(
        "partition.MySQLPartitionByListColumns", partition_by_list_columns
    )
    register_special_constructor("partition.MySQLPartitionByHash", partition_by_hash)
    register_special_constructor(
        "partition.MySQLSubpartitionClause", subpartition_clause
    )
    register_special_constructor(
        "partition.MySQLCoalescePartitionExpression", coalesce_partition
    )


_register_mysql_specials()


@pytest.fixture(params=[fqn for fqn in sorted(CLASSES)], ids=sorted(CLASSES))
def mysql_expr_case(request, mysql_dialect):
    fqn = request.param
    cls = CLASSES[fqn]
    instance, source = make_instance(cls, mysql_dialect)
    if instance is None:
        pytest.skip(f"{fqn}: {source}")
    return fqn, instance


class TestMySQLExpressionRoundtrip:
    """All constructible MySQL expression classes round-trip losslessly."""

    def test_get_params_roundtrip(self, mysql_expr_case, mysql_dialect):
        fqn, instance = mysql_expr_case
        roundtrip_expression(fqn, instance, mysql_dialect)

    def test_to_sql_consistent(self, mysql_expr_case, mysql_dialect):
        fqn, instance = mysql_expr_case
        sql_consistent(fqn, instance, mysql_dialect)


def test_core_expressions_also_roundtrip(mysql_dialect):
    """Core expression classes usable with MySQL dialect also round-trip."""
    from rhosocial.activerecord.backend.expression.core import Column, Literal  # noqa: F401
    from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

    expr = ComparisonPredicate(
        mysql_dialect, "=", Column(mysql_dialect, "a"), Literal(mysql_dialect, 1)
    )
    roundtrip_expression("core", expr, mysql_dialect)
    sql_consistent("core", expr, mysql_dialect)