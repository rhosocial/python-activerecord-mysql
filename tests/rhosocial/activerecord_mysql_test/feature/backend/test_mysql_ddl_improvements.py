# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_ddl_improvements.py
"""Tests for MySQL DDL improvements: capability gating, UnsupportedFeatureError."""
import pytest
from unittest.mock import patch

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnDefinition,
    CreateTableStatement,
    QueryStatement,
    CreateViewStatement,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    ConstraintValidation,
    ForeignKeyConstraint,
    TableCheckConstraint,
    TableConstraint,
    TableForeignKeyConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddTableConstraint,
    AlterConstraint,
    DropTableConstraint,
    ValidateConstraint,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.expression.statements import ViewOptions, ViewCheckOption
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Table, View


class TestMySQLViewCapabilityGating:
    """Tests for MySQL VIEW DDL capability gating."""

    def test_create_or_replace_view_supported(self):
        """MySQL supports CREATE OR REPLACE VIEW."""
        dialect = MySQLDialect()
        assert dialect.supports_create_or_replace_view() is True

    def test_drop_view_if_exists_supported(self):
        """MySQL supports DROP VIEW IF EXISTS."""
        dialect = MySQLDialect()
        assert dialect.supports_if_exists_view() is True

    def test_drop_view_cascade_not_supported(self):
        """MySQL does not support DROP VIEW CASCADE."""
        dialect = MySQLDialect()
        assert dialect.supports_cascade_view() is False

    def test_materialized_view_not_supported(self):
        """MySQL does not support materialized views."""
        dialect = MySQLDialect()
        assert dialect.supports_materialized_view() is False

    def test_create_view_check_option_gated(self):
        """WITH CHECK OPTION must fail fast when the capability is off."""
        dialect = MySQLDialect()
        query = QueryStatement(
            dialect, select=[Column(dialect, "id")], from_=Table(dialect, "t")
        )
        expr = CreateViewStatement(
            dialect,
            view=View(dialect, "v"),
            query=query,
            options=ViewOptions(check_option=ViewCheckOption.CASCADED),
        )
        with patch.object(type(dialect), "supports_view_check_option", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="CHECK OPTION"):
                expr.to_sql()


class TestMySQLColumnCapabilityGating:
    """Tests for MySQL COLUMN DDL capability gating."""

    def test_foreign_key_on_delete_supported(self):
        """MySQL supports FK ON DELETE."""
        dialect = MySQLDialect()
        assert dialect.supports_foreign_key_on_delete() is True

    def test_foreign_key_on_update_supported(self):
        """MySQL supports FK ON UPDATE."""
        dialect = MySQLDialect()
        assert dialect.supports_foreign_key_on_update() is True

    def test_fk_match_not_supported(self):
        """MySQL does not support FK MATCH."""
        dialect = MySQLDialect()
        assert dialect.supports_fk_match() is False


class TestMySQLTriggerCapabilityGating:
    """Tests for MySQL TRIGGER DDL capability gating."""

    def test_trigger_referencing_not_supported(self):
        """MySQL does not support trigger REFERENCING clause."""
        dialect = MySQLDialect()
        assert dialect.supports_trigger_referencing() is False

    def test_trigger_when_not_supported(self):
        """MySQL does not support trigger WHEN clause."""
        dialect = MySQLDialect()
        assert dialect.supports_trigger_when() is False

    def test_instead_of_trigger_not_supported(self):
        """MySQL does not support INSTEAD OF triggers."""
        dialect = MySQLDialect()
        assert dialect.supports_instead_of_trigger() is False


class TestMySQLFunctionCapabilityGating:
    """Tests for MySQL FUNCTION DDL capability gating."""

    def test_stored_function_supported(self):
        """MySQL supports stored functions."""
        dialect = MySQLDialect()
        assert dialect.supports_stored_function() is True


class TestMySQLSchemaCapabilityGating:
    """Tests for MySQL SCHEMA DDL capability gating."""

    def test_create_schema_supported(self):
        """MySQL supports CREATE SCHEMA (alias for CREATE DATABASE)."""
        dialect = MySQLDialect()
        assert dialect.supports_create_schema() is True

    def test_drop_schema_supported(self):
        """MySQL supports DROP SCHEMA (alias for DROP DATABASE)."""
        dialect = MySQLDialect()
        assert dialect.supports_drop_schema() is True


class InheritedTable(ActiveRecord):
    __table_name__ = "inherited"

    id: int

    @classmethod
    def table_inherits(cls):
        return ["parent_a", "parent_b"]


class TablespacedTable(ActiveRecord):
    __table_name__ = "tablespaced"

    id: int

    @classmethod
    def table_tablespace(cls):
        return "ts_data"


class TestMySQLTableDeclarationGating:
    def test_table_declaration_defaults_are_absent(self):
        class Plain(ActiveRecord):
            __table_name__ = "plain_table_defaults"

            id: int

        dialect = MySQLDialect()
        expression = CreateTableStatement(
            dialect,
            Table(dialect, Plain.__table_name__),
            columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
            inherits=Plain.table_inherits(),
            tablespace=Plain.table_tablespace(),
        )
        assert expression.inherits == []
        assert expression.tablespace is None

    def test_table_inherits_is_propagated_and_rejected(self):
        dialect = MySQLDialect(version=(8, 0, 0))
        assert dialect.supports_table_inheritance() is False
        expression = CreateTableStatement(
            dialect,
            Table(dialect, InheritedTable.__table_name__),
            columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
            inherits=InheritedTable.table_inherits(),
            tablespace=InheritedTable.table_tablespace(),
        )
        assert expression.inherits == ["parent_a", "parent_b"]
        with pytest.raises(UnsupportedFeatureError, match="INHERITS"):
            expression.to_sql()

    def test_table_tablespace_is_propagated_and_rejected(self):
        dialect = MySQLDialect(version=(8, 0, 0))
        assert dialect.supports_table_tablespace() is False
        expression = CreateTableStatement(
            dialect,
            Table(dialect, TablespacedTable.__table_name__),
            columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
            inherits=TablespacedTable.table_inherits(),
            tablespace=TablespacedTable.table_tablespace(),
        )
        assert expression.tablespace == "ts_data"
        with pytest.raises(UnsupportedFeatureError, match="TABLESPACE"):
            expression.to_sql()


class TestMeasuredConstraintLifecycleCapabilities:
    """The constraint-lifecycle probes answer what the server was measured to do.

    Every verdict asserted here was measured on Community Server 26.7.0
    (192.168.1.3:14686) by running the ``ALTER TABLE`` statement and reading
    ``SHOW CREATE TABLE`` back; the probe docstrings in
    ``MySQLConstraintMixin`` record the same measurements, errnos included.

    One of them is the reason this class exists: a switch that answers
    ``False`` for a spelling the server *accepts* (FK ``MATCH``) is not
    conservative, it is the difference between output the caller can trust and
    output that silently means less than it looks.
    """

    MEASURED_VERSION = (26, 7, 0)

    def _dialect(self):
        return MySQLDialect(version=self.MEASURED_VERSION)

    def _check(self, dialect, **kw):
        return TableConstraint(
    dialect,
    branch=TableCheckConstraint(dialect, ComparisonPredicate( dialect, "=", Column(dialect, "a"), Column(dialect, "b") )),
    name="ck",
    **kw
)

    def _fk(self, dialect, **kw):
        return ForeignKeyConstraint(
            dialect,
            name="fk",
            columns=["a"],
            foreign_key_table=Table(dialect, "t2"),
            foreign_key_columns=["b"],
            **kw,
        )

    def test_add_constraint_is_declared_true(self):
        """ADD CONSTRAINT works for all four kinds, so the master switch is on."""
        dialect = self._dialect()
        assert dialect.supports_add_constraint() is True

    def test_drop_constraint_is_declared_true(self):
        """DROP CONSTRAINT works (for UNIQUE and FK), so the master switch is on."""
        dialect = self._dialect()
        assert dialect.supports_drop_constraint() is True

    def test_drop_constraint_if_exists_is_declined_and_refused_by_name(self):
        """``DROP CONSTRAINT IF EXISTS`` is a parser error, so it is refused here.

        The server answers ``1064 (42000) ... near 'IF EXISTS x'``, so the
        failure precedes name resolution and no errno can be caught to make
        the drop re-runnable.
        """
        dialect = self._dialect()
        assert dialect.supports_drop_constraint_if_exists() is False
        action = DropTableConstraint(dialect, "uq_content", if_exists=True)
        with pytest.raises(UnsupportedFeatureError, match="IF EXISTS"):
            action.to_sql()

    def test_novalidate_is_declined_and_refused_by_name(self):
        """``NOT VALID`` is a parser error (``1064 ... near 'VALID'``)."""
        dialect = self._dialect()
        assert dialect.supports_constraint_novalidate() is False
        constraint = self._check(dialect, validation=ConstraintValidation.NOVALIDATE)
        with pytest.raises(UnsupportedFeatureError, match="NOT VALID"):
            AddTableConstraint(dialect, constraint).to_sql()

    def test_validate_constraint_is_declined_and_refused_by_name(self):
        """``VALIDATE CONSTRAINT`` is a parser error (``1064 ... near 'VALIDATE``)."""
        dialect = self._dialect()
        assert dialect.supports_validate_constraint() is False
        with pytest.raises(UnsupportedFeatureError, match="VALIDATE CONSTRAINT"):
            ValidateConstraint(dialect, "ck").to_sql()

    def test_alter_constraint_enforced_is_declared_for_check_only(self):
        """``ALTER CONSTRAINT [NOT] ENFORCED`` is the one form the server takes.

        Measured: a CHECK accepts both keywords (and the ``/*!80016 NOT
        ENFORCED */`` marker follows), while a FOREIGN KEY answers ``3941
        (HY000): Altering constraint enforcement is not supported ...``.
        The probe answers the verb's existence and is version-gated; the
        CHECK-only narrowing is the formatter's, which refuses the other
        kinds by name.
        """
        dialect = self._dialect()
        assert dialect.supports_alter_constraint_enforced() is True
        assert (
            MySQLDialect(version=(8, 0, 15)).supports_alter_constraint_enforced()
            is False
        )

    def test_alter_constraint_enforced_renders_for_check_only(self):
        """The rendering follows the probe: CHECK renders, FOREIGN KEY refuses."""
        dialect = self._dialect()
        sql, params = AlterConstraint(
            dialect, "ck", not_enforced=True, constraint_kind=TableCheckConstraint
        ).to_sql()
        assert sql == "ALTER CONSTRAINT `ck` NOT ENFORCED"
        assert params == ()

        with pytest.raises(UnsupportedFeatureError, match="ENFORCED"):
            AlterConstraint(
                dialect, "fk", enforced=True, constraint_kind=TableForeignKeyConstraint
            ).to_sql()

    def test_alter_constraint_defers_to_the_deferrable_probe(self):
        """``ALTER CONSTRAINT ck DEFERRABLE`` is a 1064, not an ENFORCED answer."""
        dialect = self._dialect()
        assert dialect.supports_deferrable_constraint() is False
        # The enforcement verb exists, but DEFERRABLE is not an attribute it
        # alters -- that refusal belongs to the deferrable family, which is
        # False on the same 1064.
        assert dialect.supports_alter_constraint_enforced() is True

    def test_fk_match_is_parsed_and_dropped_not_merely_refused(self):
        """FK ``MATCH`` parses and is discarded, so it is refused *by name*.

        The server accepts ``MATCH FULL`` and then drops the clause, so the
        rendering is not emitted: a caller reading ``MATCH FULL`` back from
        the DDL would believe something no engine enforces.
        """
        dialect = self._dialect()
        assert dialect.supports_fk_match() is False
        constraint = self._fk(dialect, match_type="FULL")
        with pytest.raises(UnsupportedFeatureError, match="MATCH"):
            constraint.to_sql()

    def test_enforcement_is_version_gated_and_check_only(self):
        """``[NOT] ENFORCED`` needs 8.0.16, and only CHECK takes it."""
        assert MySQLDialect(version=(8, 0, 15)).supports_constraint_enforced() is False
        assert MySQLDialect(version=(8, 0, 16)).supports_constraint_enforced() is True
        dialect = self._dialect()
        sql, params = self._check(dialect, not_enforced=True).to_sql()
        assert sql.endswith("NOT ENFORCED")
        # The params are a tuple: core's branch-level formatters hand back
        # tuples, and the production-level renderer normalises to one. The old
        # fat-tag collector returned a list here.
        assert params == ()

        with pytest.raises(UnsupportedFeatureError, match="FOREIGN KEY NOT ENFORCED"):
            self._fk(dialect, not_enforced=True).to_sql()


class TestConstraintProbeDocstringsCarryTheMeasurement:
    """A probe without its evidence is a number with no source.

    Each switch asserted here is answered from a live server, so the
    docstring has to say which version, and what the server answered --
    errno or error text -- or the verdict cannot be re-checked without
    re-measuring everything.
    """

    #: The probe name, and the marker that must appear in its docstring: the
    #: measured server version, an errno, or the shape of the refusal.
    EVIDENCE = {
        "supports_check_constraint": "26.7.0",
        "supports_add_constraint": "26.7.0",
        "supports_drop_constraint": "3940",
        "supports_drop_constraint_if_exists": "1064",
        "supports_constraint_novalidate": "1064",
        "supports_validate_constraint": "1064",
        "supports_alter_constraint_enforced": "3941",
        "supports_constraint_enforced": "26.7.0",
        "supports_fk_match": "parsed away",
        "supports_deferrable_constraint": "1064",
    }

    @pytest.mark.parametrize("probe, marker", EVIDENCE.items(), ids=sorted(EVIDENCE))
    def test_docstring_records_the_measured_evidence(self, probe, marker):
        doc = getattr(MySQLDialect, probe).__doc__ or ""
        assert doc, f"{probe} has no docstring: the measurement has nowhere to live"
        assert marker in doc, f"{probe} docstring does not record {marker!r}"
        assert "26.7.0" in doc, f"{probe} names no measured server version"
