# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/expression/test_expression_registry.py
"""Construct-level tests for MySQL's ``Parameter`` binding and raw-value coercion.

No live database is involved: a ``MySQLDialect`` instance renders the nodes.
The registry-shape rules live in the shared backend contract; only the
backend-specific rendering behaviour is kept here.
"""

from rhosocial.activerecord.backend.expression.core import Column, Parameter
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect


def test_parameter_binds_by_default_and_inlines_on_request() -> None:
    dialect = MySQLDialect()
    value = "O'Reilly"
    assert Parameter(dialect, value).to_sql() == ("%s", (value,))

    sql, params = Parameter(dialect, value, inline=True).to_sql()
    assert sql == "'O''Reilly'"  # backend SQL text, escaped by MySQLDialect
    assert params == ()


def test_raw_value_at_value_position_is_bound_not_inlined() -> None:
    dialect = MySQLDialect()
    raw = "O'Reilly; DROP TABLE users--"
    predicate = ComparisonPredicate(dialect, "eq", Column(dialect, "name"), raw)

    assert isinstance(predicate.right, Parameter)
    sql, params = predicate.to_sql()
    assert sql == "`name` = %s"
    assert "DROP TABLE" not in sql
    assert params == (raw,)
