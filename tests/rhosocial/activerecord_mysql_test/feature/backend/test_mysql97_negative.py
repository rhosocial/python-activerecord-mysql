# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql97_negative.py
"""
Negative tests for MySQL 9.7 features.

Ensures that older MySQL versions correctly report unsupported features
and do not silently generate invalid SQL.
"""
import pytest
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import (
    CreateJsonDualityViewExpression,
    DualityObjectSpec,
    DualityColumnMapping,
    DualityViewDMLTag,
    MySQLOptimizerHintExpression,
    SetVarHint,
)


@pytest.fixture
def dialect_84():
    return MySQLDialect(version=(8, 4, 0))


@pytest.fixture
def dialect_80():
    return MySQLDialect(version=(8, 0, 0))


@pytest.fixture
def dialect_56():
    return MySQLDialect(version=(5, 6, 0))


class TestJsonDualityViewNegative:
    """Verify old versions report JSON Duality Views as unsupported."""

    def test_not_supported_on_84(self, dialect_84):
        assert not dialect_84.supports_json_duality_view()
        assert not dialect_84.supports_json_duality_view_dml()

    def test_not_supported_on_80(self, dialect_80):
        assert not dialect_80.supports_json_duality_view()
        assert not dialect_80.supports_json_duality_view_dml()


class TestOptimizerHintNegative:
    """Verify old versions report optimizer features as unsupported."""

    def test_hypergraph_not_on_84(self, dialect_84):
        assert dialect_84.supports_optimizer_hint()
        assert not dialect_84.supports_hypergraph_optimizer()

    def test_hint_not_on_56(self, dialect_56):
        assert not dialect_56.supports_optimizer_hint()
        assert not dialect_56.supports_hypergraph_optimizer()

    def test_hint_still_generates_sql_on_80(self, dialect_80):
        """SET_VAR hint syntax works on 8.0+ even without hypergraph."""
        expr = MySQLOptimizerHintExpression(dialect_80, [
            SetVarHint("max_execution_time", "5000")
        ])
        sql, params = expr.to_sql()
        assert sql == "/*+ SET_VAR(max_execution_time='5000') */"
        assert "hypergraph" not in sql
