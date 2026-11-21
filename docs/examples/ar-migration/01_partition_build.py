# docs/examples/ar-migration/01_partition_build.py
"""Build-partition suggestions on MySQL (offline, no server).

The same migration intent -- "create a partitioned table" -- is rendered by the
MySQL backend for every one of its eight partition strategies. Nothing here
connects to a database: a dialect is constructed with a version, a plan is
assembled from real expression nodes, and each suggestion's operations are
printed straight from ``expr.to_sql()``.

Run from the repository root with ``PYTHONPATH=src``:

    python docs/examples/ar-migration/01_partition_build.py
"""

from rhosocial.activerecord.backend.expression import Column, PartitionByRangeClause
from rhosocial.activerecord.backend.expression.statements import PartitionDefinitionExpression
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.partition import MySQLPartitionValue

DIALECT = MySQLDialect(version=(8, 0, 0))


def _strategy(word: str, key: str = "id") -> PartitionByRangeClause:
    """A strategy clause carrying the given MySQL word.

    Core offers the three base RANGE/LIST/HASH clause classes; MySQL's COLUMNS
    and LINEAR variants share the clause shape, so the word is overridden here.
    The suggestion methods read the word off the clause.
    """
    clause = PartitionByRangeClause(DIALECT, [Column(DIALECT, key)])
    clause.method = word
    clause.word = word
    return clause


def _range(name: str, bound: int) -> PartitionDefinitionExpression:
    return PartitionDefinitionExpression(
        DIALECT, name=name, less_than=[MySQLPartitionValue(DIALECT, bound)]
    )


def _list(name: str, value: str) -> PartitionDefinitionExpression:
    return PartitionDefinitionExpression(
        DIALECT, name=name, in_values=[MySQLPartitionValue(DIALECT, value)]
    )


def _show(title: str, suggestion: object) -> None:
    """Print a suggestion's operations; SQL text comes only from to_sql()."""
    print(f"\n== {title} ==")
    operations = suggestion.operations  # type: ignore[attr-defined]
    if operations is False:
        print("   <declined: no such MySQL form for this plan/strategy>")
        return
    if operations is None:
        print("   <no-op>")
        return
    for expr in operations:
        print("  ", expr.to_sql()[0])


def main() -> None:
    d = DIALECT
    ranges = [_range("p0", 100), _range("p1", 200)]
    lists = [_list("p0", "a"), _list("p1", "b")]

    # Value-based partitioning: keys + explicit partition definitions.
    _show(
        "RANGE",
        d.suggest_partition_build(
            _strategy("RANGE"), {"keys": [Column(d, "id")], "definitions": ranges}
        ),
    )
    _show(
        "RANGE COLUMNS",
        d.suggest_partition_build(
            _strategy("RANGE COLUMNS", "created_at"),
            {"keys": [Column(d, "created_at")], "definitions": ranges},
        ),
    )
    _show(
        "LIST",
        d.suggest_partition_build(
            _strategy("LIST", "region"), {"keys": [Column(d, "region")], "definitions": lists}
        ),
    )
    _show(
        "LIST COLUMNS",
        d.suggest_partition_build(
            _strategy("LIST COLUMNS", "region"),
            {"keys": [Column(d, "region")], "definitions": lists},
        ),
    )

    # Algorithmic partitioning: a key expression plus a partition count.
    _show(
        "HASH",
        d.suggest_partition_build(
            _strategy("HASH"), {"keys": [Column(d, "id")], "partitions_count": 4}
        ),
    )
    _show(
        "LINEAR HASH",
        d.suggest_partition_build(
            _strategy("LINEAR HASH"), {"keys": [Column(d, "id")], "partitions_count": 4}
        ),
    )
    _show(
        "KEY",
        d.suggest_partition_build(
            _strategy("KEY"), {"keys": [Column(d, "id")], "partitions_count": 4}
        ),
    )
    _show(
        "LINEAR KEY",
        d.suggest_partition_build(
            _strategy("LINEAR KEY"), {"keys": [Column(d, "id")], "partitions_count": 4}
        ),
    )

    # Tri-state: an unknown strategy and a RANGE plan without definitions decline.
    _show(
        "declined (unknown strategy)",
        d.suggest_partition_build("SPATIAL", {"keys": [Column(d, "id")]}),
    )
    _show(
        "declined (RANGE without definitions)",
        d.suggest_partition_build(_strategy("RANGE"), {"keys": [Column(d, "id")]}),
    )


if __name__ == "__main__":
    main()
