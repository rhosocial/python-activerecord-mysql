# docs/examples/ar-migration/02_partition_lifecycle.py
"""Partition lifecycle suggestions on MySQL (offline, no server).

After a table is partitioned, the same lifecycle intents are rendered by the
MySQL backend into its own DDL expression nodes: ADD PARTITION (append) and
REORGANIZE PARTITION (split / reorganize), DROP PARTITION, a retention chain,
REMOVE PARTITIONING / COALESCE PARTITION, and DROP TABLE. MySQL has no
MERGE PARTITION, so that suggestion is always declined.

Nothing here connects to a database: each suggestion's operations are printed
straight from ``expr.to_sql()``.

Run from the repository root with ``PYTHONPATH=src``:

    python docs/examples/ar-migration/02_partition_lifecycle.py
"""

from rhosocial.activerecord.backend.expression import Column, PartitionByRangeClause
from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.partition import MySQLPartitionValue

DIALECT = MySQLDialect(version=(8, 0, 0))
TABLE = "orders"


def _strategy(word: str) -> PartitionByRangeClause:
    """A strategy clause carrying the given MySQL word."""
    clause = PartitionByRangeClause(DIALECT, [Column(DIALECT, "id")])
    clause.method = word
    clause.word = word
    return clause


def _range(name: str, bound: int) -> PartitionDefinitionExpression:
    return PartitionDefinitionExpression(
        DIALECT, name=name, less_than=[MySQLPartitionValue(DIALECT, bound)]
    )


def _show(title: str, suggestion: object) -> None:
    """Print a suggestion's operations; SQL text comes only from to_sql()."""
    print(f"\n== {title} ==")
    operations = suggestion.operations  # type: ignore[attr-defined]
    if operations is False:
        print("   <declined: MySQL has no such mechanism for this plan/strategy>")
        return
    if operations is None:
        print("   <no-op: nothing needs doing>")
        return
    for expr in operations:
        print("  ", expr.to_sql()[0])


def main() -> None:
    d = DIALECT
    ranges = [_range("p0", 100), _range("p1", 200), _range("p2", 300)]

    # ADD: append a new partition above the maximum.
    _show(
        "add (append above the maximum)",
        d.suggest_partition_add(
            _strategy("RANGE"),
            {"table": TABLE, "definitions": [_range("p3", 400)]},
        ),
    )
    # ADD with an existing partition + `into` becomes REORGANIZE.
    _show(
        "add (reorganize inside a range)",
        d.suggest_partition_add(
            _strategy("RANGE"),
            {
                "table": TABLE,
                "partition": "p0",
                "into": [_range("p0", 50), _range("pX", 100)],
            },
        ),
    )

    # DROP: named partitions.
    _show(
        "drop (named partitions)",
        d.suggest_partition_drop(_strategy("RANGE"), {"table": TABLE, "names": ["p0", "p1"]}),
    )

    # RETENTION: drop everything at/below a cutoff, but never the last partition.
    _show(
        "retention (cutoff=250 keeps p2)",
        d.suggest_partition_retention(
            _strategy("RANGE"),
            {"table": TABLE, "definitions": ranges, "cutoff": 250},
        ),
    )
    _show(
        "retention (all old -> newest kept)",
        d.suggest_partition_retention(
            _strategy("RANGE"),
            {"table": TABLE, "definitions": ranges, "cutoff": 300},
        ),
    )
    _show(
        "retention (nothing old -> no-op)",
        d.suggest_partition_retention(
            _strategy("RANGE"),
            {"table": TABLE, "definitions": ranges, "cutoff": 50},
        ),
    )

    # SPLIT: REORGANIZE PARTITION ... INTO (...).
    _show(
        "split (reorganize p0)",
        d.suggest_partition_split(
            _strategy("RANGE"),
            {
                "table": TABLE,
                "partition": "p0",
                "into": [_range("p0", 50), _range("pX", 100)],
            },
        ),
    )

    # TABLE ALTER: remove partitioning, or COALESCE for HASH/KEY.
    _show(
        "table_alter (remove partitioning)",
        d.suggest_partition_table_alter(_strategy("RANGE"), {"table": TABLE}),
    )
    _show(
        "table_alter (coalesce HASH by 2)",
        d.suggest_partition_table_alter(
            _strategy("HASH"), {"table": TABLE, "mode": "coalesce", "count": 2}
        ),
    )

    # TABLE DROP: drop the whole partitioned table.
    _show(
        "table_drop",
        d.suggest_partition_table_drop(_strategy("RANGE"), {"table": TABLE}),
    )

    # MERGE: MySQL has no MERGE PARTITION -- always declined.
    _show("merge (always declined)", d.suggest_partition_merge(_strategy("RANGE"), {}))

    # A few declined/no-op paths for completeness.
    _show(
        "drop without names (no-op)",
        d.suggest_partition_drop(_strategy("RANGE"), {"table": TABLE}),
    )
    _show(
        "drop on HASH (declined)",
        d.suggest_partition_drop(_strategy("HASH"), {"table": TABLE, "names": ["p0"]}),
    )
    _show(
        "add on HASH (declined)",
        d.suggest_partition_add(
            _strategy("HASH"),
            {"table": TABLE, "definitions": [_range("p3", 400)]},
        ),
    )


if __name__ == "__main__":
    main()
