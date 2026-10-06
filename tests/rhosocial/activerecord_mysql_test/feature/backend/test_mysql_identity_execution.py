# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_identity_execution.py
"""Execution confirmation for MySQL's two auto-increment mechanisms.

MySQL numbers rows with the parameterless ``AUTO_INCREMENT`` column marker and
has no ``GENERATED ... AS IDENTITY`` grammar. Both halves are confirmed against
the live servers through core's ``execution_testing`` helper, never by
comparing rendered strings:

* the marker renders, the ``CREATE TABLE`` carrying it executes, and the
  rendered SQL really contains the marker -- an accepted statement without it
  would make the confirmation vacuous;
* an identity request -- bare, ``ALWAYS``, or with ``start``/``increment`` --
  is refused by the dialect, naming the missing mechanism. It is never
  downgraded to ``AUTO_INCREMENT``: the old ``format_identity_clause`` override
  rendered byte-identical output for all three cases, silently dropping the
  requested semantics (measured on 5.6 / 5.7 / 8.0 / 8.4 / 9.2 / 9.4 / 9.7);
* the raw standard clause is also sent to the server, so the refusal is shown
  to be a fact about MySQL rather than a missing formatter.

Every verdict is preceded by the sentinel: a deliberately invalid statement
must classify REJECTED, or a null result could be read as acceptance. The
helper's third outcome, NOT_RENDERED, is asserted deliberately rather than
treated as a skip: on MySQL, refusing an identity request is the designed
answer, and it must stay distinct from "rendered but rejected".
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.execution_testing import (
    ExecutionOutcome,
    classify_execution,
    confirm_expression_execution,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    AutoIncrementClause,
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    IdentityClause,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression import MySQLCreateTableOptions
from rhosocial.activerecord.base import IdentityAttribute


def _auto_increment_column(dialect, name="id"):
    """A PRIMARY KEY column carrying the parameterless marker."""
    return ColumnDefinition(
        dialect,
        name,
        IntegerType(dialect),
        constraints=[
            ColumnConstraint(
                dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True
            )
        ],
    )


class _DeclinedAutoIncrementDialect(MySQLDialect):
    """A MySQL dialect that withdraws the marker probe.

    The mutation exists to prove the DDL path consults the probe: if the column
    formatter still spelled ``AUTO_INCREMENT`` itself, withdrawing the probe
    would change nothing.
    """

    def supports_auto_increment_column(self) -> bool:
        return False


class TestSentinel:
    """The classifier must see rejection before any acceptance is trusted."""

    def test_invalid_statement_is_rejected(self, mysql_backend):
        """A deliberately wrong statement must be classified REJECTED.

        Without this sentinel, a classifier that swallowed every error and
        answered ACCEPTED would make every later confirmation vacuous.
        """
        assert (
            classify_execution(mysql_backend, "THIS IS NOT SQL")
            is ExecutionOutcome.REJECTED
        )

    def test_valid_statement_is_accepted(self, mysql_backend):
        """The same path must see acceptance, or the sentinel above proves nothing."""
        assert (
            classify_execution(mysql_backend, "SELECT 1")
            is ExecutionOutcome.ACCEPTED
        )


class TestAutoIncrementMarkerExecutes:
    """The marker renders, its CREATE TABLE executes, and the marker is in it."""

    def test_marker_renders(self, mysql_dialect):
        sql, params = AutoIncrementClause(mysql_dialect).to_sql()
        assert sql == " AUTO_INCREMENT"
        assert params == ()

    def test_rendered_create_table_executes(self, mysql_backend):
        dialect = mysql_backend.dialect
        table = Table(dialect, "_probe_ai_exec")
        expression = CreateTableExpression(
            dialect, table, [_auto_increment_column(dialect)]
        )
        sql, _ = expression.to_sql()
        assert "AUTO_INCREMENT" in sql.upper(), (
            f"the marker is missing from {sql!r}; an accepted CREATE TABLE "
            f"without it would confirm nothing"
        )

        outcome = confirm_expression_execution(
            mysql_backend, expression, teardown=[DropTableExpression(dialect, table)]
        )

        assert outcome is ExecutionOutcome.ACCEPTED
        # The teardown really ran: selecting from the dropped table is itself a
        # rejection the same classifier can see.
        assert (
            classify_execution(mysql_backend, "SELECT * FROM _probe_ai_exec")
            is ExecutionOutcome.REJECTED
        )


class TestProbeGatesTheDdl:
    """The column formatter consults the probe; it does not spell the marker."""

    def test_withdrawn_probe_refuses_the_column(self):
        dialect = _DeclinedAutoIncrementDialect((8, 0, 36))
        expression = CreateTableExpression(
            dialect, Table(dialect, "t"), [_auto_increment_column(dialect)]
        )
        with pytest.raises(UnsupportedFeatureError, match="AUTO_INCREMENT column"):
            expression.to_sql()

    def test_table_seed_option_is_not_a_column_clause(self):
        """``AUTO_INCREMENT=100`` is a table option, not a column clause.

        One protocol does one thing: the table-level seed must keep rendering
        even when the column marker is withdrawn, because it never goes through
        the column formatter's probe.
        """
        dialect = _DeclinedAutoIncrementDialect((8, 0, 36))
        expression = CreateTableExpression(
            dialect,
            Table(dialect, "t"),
            [ColumnDefinition(dialect, "id", IntegerType(dialect))],
            table_options=MySQLCreateTableOptions(dialect, auto_increment=100),
        )
        sql, _ = expression.to_sql()
        assert "AUTO_INCREMENT=100" in sql


class TestIdentityIsRefusedByName:
    """MySQL has no identity grammar; the refusal names the mechanism."""

    def test_mechanism_and_parameter_probes_are_declined(self, mysql_dialect):
        assert mysql_dialect.supports_identity_column() is False
        # The parameter probes are not applicable to MySQL -- it numbers rows
        # through the parameterless marker -- and every one fails closed rather
        # than answering for a mechanism the server does not have.
        for probe in (
            "supports_identity_generation_always",
            "supports_identity_start",
            "supports_identity_increment",
            "supports_identity_minvalue",
            "supports_identity_maxvalue",
            "supports_identity_cycle",
        ):
            assert getattr(mysql_dialect, probe)() is False, probe

    @pytest.mark.parametrize(
        "build",
        [
            pytest.param(lambda d: IdentityClause(d), id="bare"),
            pytest.param(lambda d: IdentityClause(d, "ALWAYS"), id="always"),
            pytest.param(
                lambda d: IdentityClause(d, start=100, increment=5),
                id="start-increment",
            ),
        ],
    )
    def test_request_is_refused_not_executed(self, mysql_backend, build):
        """Bare, ALWAYS and start/increment all refuse, naming the mechanism.

        ``NOT_RENDERED`` is the helper's third outcome and is asserted here as
        the correct one: the expression refused to render, so nothing was sent
        to the server. Treating this as a rejection would fail MySQL for
        behaving correctly.
        """
        expression = build(mysql_backend.dialect)
        with pytest.raises(UnsupportedFeatureError, match="IDENTITY column"):
            expression.to_sql()
        assert (
            confirm_expression_execution(mysql_backend, expression)
            is ExecutionOutcome.NOT_RENDERED
        )

    def test_identity_attribute_is_refused(self, mysql_backend):
        """The AR-layer attribute path used to silently drop ALWAYS and start."""
        dialect = mysql_backend.dialect
        expression = CreateTableExpression(
            dialect,
            Table(dialect, "_probe_identity_attr"),
            [
                ColumnDefinition(
                    dialect,
                    "id",
                    IntegerType(dialect),
                    attributes=[
                        IdentityAttribute(generation="ALWAYS", start=10, increment=2)
                    ],
                )
            ],
        )
        with pytest.raises(UnsupportedFeatureError, match="IDENTITY column"):
            expression.to_sql()

    def test_server_rejects_the_standard_clause(self, mysql_backend):
        """The refusal is a fact about MySQL, not a missing formatter.

        The raw SQL-standard clause is sent to the live server; every version
        measured answers with a syntax error. If a future MySQL accepts it, this
        test says so instead of letting the dialect's declaration drift.
        """
        outcome = classify_execution(
            mysql_backend,
            "CREATE TABLE _probe_raw_identity "
            "(id INT GENERATED BY DEFAULT AS IDENTITY)",
        )
        # Best effort: the statement should not have created anything.
        classify_execution(mysql_backend, "DROP TABLE IF EXISTS _probe_raw_identity")
        assert outcome is ExecutionOutcome.REJECTED
