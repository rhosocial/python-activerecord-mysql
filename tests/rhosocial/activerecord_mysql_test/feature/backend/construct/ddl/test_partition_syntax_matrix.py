# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/ddl/test_partition_syntax_matrix.py
"""Offline MySQL partition syntax matrix.

The matrix itself lives in ``partition_syntax_fixtures``.  This module only
asserts each case's contract: the rendered SQL fragments, and the named refusal
for unsupported subpartitioning.  No server connection is required.
"""

from typing import Any, Tuple

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

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
}


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
        assert case.builder is not None


def test_partition_syntax_sql_contract(partition_syntax_case):  # noqa: F811
    """Rendered SQL carries required fragments and omits forbidden ones."""
    case = partition_syntax_case
    dialect = _new_dialect()

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
