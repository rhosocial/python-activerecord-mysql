# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_constraint_switches.py
"""MySQL constraint capability switches: values and their locality.

Every verdict asserted here was measured against a live Community Server
26.7.0 at 192.168.1.3:14686 by running the ``ALTER TABLE`` statement and
reading ``SHOW CREATE TABLE`` / ``information_schema`` back. The docstring
each switch carries records the same measurement, errno included, so a
verdict can be re-checked without re-measuring the family.

Two things are asserted for every switch, and the second is the one that
is easy to lose:

* **the value** -- what this server does;
* **the locality** -- that the verdict resolves to a class in *this*
  backend's package. A switch that silently falls back to core's
  ``ConstraintMixin`` can have its default moved out from under MySQL
  without anything in this repository noticing. Declaring the switch here
  is what makes that move a visible test failure instead of a quiet
  contract change.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.mixins.constraint import (
    MySQLConstraintMixin,
)
from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)

#: The server the verdicts below were measured on. Every value here is a
#: statement about *this* version, not about MySQL in general.
MEASURED_VERSION = (26, 7, 0)

#: Every constraint switch this backend relies on, with the verdict measured
#: on 26.7.0. This mapping is the contract; the locality test below walks it
#: so a switch cannot leave the backend without failing first.
CONSTRAINT_SWITCHES = {
    # Constraint kinds.
    "supports_primary_key_constraint": True,
    "supports_unique_constraint": True,
    "supports_not_null_constraint": True,
    "supports_foreign_key_constraint": True,
    "supports_check_constraint": True,
    "supports_exclude_constraint": False,
    # Referential actions.
    "supports_fk_on_delete": True,
    "supports_fk_on_update": True,
    "supports_fk_match": False,
    # Clause attributes.
    "supports_deferrable_constraint": False,
    "supports_constraint_enforced": True,
    "supports_alter_constraint_enforced": True,
    "supports_constraint_novalidate": False,
    # ALTER TABLE lifecycle.
    "supports_add_constraint": True,
    "supports_drop_constraint": True,
    "supports_drop_constraint_if_exists": False,
    "supports_rename_constraint": False,
    "supports_alter_constraint": True,
    "supports_enable_disable_constraint": False,
    "supports_validate_constraint": False,
}

#: The substring that must appear in each switch's docstring: the errno or
#: the exact error text the server answered with. A verdict that cannot be
#: traced to an observation is a guess.
EVIDENCE = {
    "supports_primary_key_constraint": "1068",
    "supports_unique_constraint": "DROP CONSTRAINT uq",
    "supports_not_null_constraint": "26.7.0",
    "supports_foreign_key_constraint": "1452",
    "supports_check_constraint": "3819",
    "supports_exclude_constraint": "1064",
    "supports_fk_on_delete": "DELETE_RULE",
    "supports_fk_on_update": "UPDATE_RULE",
    "supports_fk_match": "parsed and discarded",
    "supports_deferrable_constraint": "DEFERRABLE",
    "supports_constraint_enforced": "NOT ENFORCED",
    "supports_alter_constraint_enforced": "3941",
    "supports_constraint_novalidate": "VALID",
    "supports_add_constraint": "26.7.0",
    "supports_drop_constraint": "3940",
    "supports_drop_constraint_if_exists": "1064",
    "supports_rename_constraint": "1064",
    "supports_alter_constraint": "1064",
    "supports_enable_disable_constraint": "1064",
    "supports_validate_constraint": "1064",
}


def _dialect():
    return MySQLDialect(version=MEASURED_VERSION)


class TestConstraintSwitchValues:
    """What the server was measured to do."""

    @pytest.mark.parametrize("switch, expected", CONSTRAINT_SWITCHES.items(), ids=sorted(CONSTRAINT_SWITCHES))
    def test_switch_answers_the_measured_value(self, switch, expected):
        dialect = _dialect()
        assert getattr(dialect, switch)() is expected

    def test_alter_constraint_enforced_is_version_gated(self):
        """The probe answers the verb's existence; the version decides.

        ``ALTER CONSTRAINT ... [NOT] ENFORCED`` exists from 8.0.16 on and on
        nothing earlier, so the probe is a version gate that carries no
        kind: which kinds the verb may address is the formatter's
        narrowing, not the probe's.
        """
        assert _dialect().supports_alter_constraint_enforced() is True
        assert (
            MySQLDialect(version=(8, 0, 15)).supports_alter_constraint_enforced()
            is False
        )

    def test_alter_constraint_addresses_check_only(self):
        """Only CHECK takes the alteration; the FK answer is 3941.

        Measured on 26.7.0: a CHECK accepts both keywords, while a FOREIGN
        KEY answers ``3941 (HY000): Altering constraint enforcement is not
        supported for the constraint 'fkZ'. Enforcement state alter is not
        supported for the PRIMARY, UNIQUE and FOREIGN KEY type
        constraints.`` The server names the three kinds it refuses, so the
        formatter narrows to CHECK by name instead of sending a statement
        the server rejects.
        """
        from rhosocial.activerecord.backend.expression import AlterConstraintAction

        dialect = _dialect()
        sql, _ = AlterConstraintAction(
            dialect,
            constraint_name="ck",
            not_enforced=True,
            constraint_kind=TableCheckConstraint,
        ).to_sql()
        assert sql == "ALTER CONSTRAINT `ck` NOT ENFORCED"

        with pytest.raises(UnsupportedFeatureError, match="3941"):
            AlterConstraintAction(
                dialect,
                constraint_name="fk",
                not_enforced=True,
                constraint_kind=TableForeignKeyConstraint,
            ).to_sql()

    def test_alter_constraint_normalises_a_string_kind_at_construction(self):
        """A string kind is the constructor's to normalise, not the probe's.

        ``AlterConstraintAction`` declares ``str`` in its ``constraint_kind``
        union and normalises at construction, so a spelling that matches a
        branch reaches the formatter as the branch *class* -- and the
        formatter, not the probe, is what narrows it to CHECK on this
        server. The dialect no longer sniffs signatures to guess which layer
        should answer: the probe is ``(self)`` and the kind narrowing is the
        formatter's.

        The spelling the constructor matches is the branch's own name minus
        the ``Table`` prefix, upper-cased -- ``CHECKCONSTRAINT`` -- not the
        SQL keyword ``CHECK``. That is what makes the read side round-trip
        (core's ``constraint_kind`` view, and PostgreSQL's, both derive the
        string by that same rule), so the test asserts the spelling that
        actually round-trips instead of the one the constructor's docstring
        advertises. ``"CHECK"`` is refused by the constructor with a
        ``ValueError``; the expression layer owns that mapping and this
        backend has no say in it.
        """
        from rhosocial.activerecord.backend.expression import AlterConstraintAction

        sql, _ = AlterConstraintAction(
            _dialect(),
            constraint_name="ck",
            not_enforced=True,
            constraint_kind="CheckConstraint",
        ).to_sql()
        assert sql == "ALTER CONSTRAINT `ck` NOT ENFORCED"

        with pytest.raises(ValueError):
            AlterConstraintAction(
                _dialect(),
                constraint_name="ck",
                not_enforced=True,
                constraint_kind="CHECK",
            )


class TestConstraintSwitchesAreDeclaredLocally:
    """The verdict must be this backend's, not an inherited default.

    This is the guard against a core change moving MySQL's contract: if a
    switch below were deleted here and picked up from core's
    ``ConstraintMixin``, its value could be changed by a commit in another
    repository with nothing failing in this one.
    """

    @pytest.mark.parametrize("switch", sorted(CONSTRAINT_SWITCHES), ids=sorted(CONSTRAINT_SWITCHES))
    def test_switch_is_declared_by_this_backend(self, switch):
        assert hasattr(MySQLConstraintMixin, switch), (
            f"{switch} is not declared by MySQLConstraintMixin: it would "
            f"fall through to a core default that this repository cannot "
            f"pin"
        )

    @pytest.mark.parametrize("switch", sorted(CONSTRAINT_SWITCHES), ids=sorted(CONSTRAINT_SWITCHES))
    def test_resolved_switch_is_owned_by_this_backend(self, switch):
        dialect = _dialect()
        owner = getattr(dialect, switch).__qualname__
        assert owner.startswith("MySQLConstraintMixin."), (
            f"{switch} resolves to {owner}, not to this backend's mixin"
        )

    def test_backend_mixin_precedes_the_core_constraint_mixin(self):
        """MRO order is what makes the local declaration win at all.

        ``MySQLConstraintMixin`` has to precede core's ``ConstraintMixin``;
        if that ordering were disturbed the local values would silently lose
        to the inherited ones even though both classes define the switch.
        """
        from rhosocial.activerecord.backend.dialect.mixins.ddl_table import (
            ConstraintMixin,
        )

        mro = MySQLDialect.__mro__
        assert mro.index(MySQLConstraintMixin) < mro.index(ConstraintMixin)


class TestConstraintSwitchDocstringsCarryTheMeasurement:
    """A probe without its evidence is a number with no source."""

    @pytest.mark.parametrize("switch", sorted(EVIDENCE), ids=sorted(EVIDENCE))
    def test_docstring_records_the_observation(self, switch):
        doc = getattr(MySQLConstraintMixin, switch).__doc__ or ""
        assert doc, f"{switch} has no docstring: the measurement has nowhere to live"
        assert "26.7.0" in doc, f"{switch} names no measured server version"

    @pytest.mark.parametrize("switch, marker", EVIDENCE.items(), ids=sorted(EVIDENCE))
    def test_docstring_records_the_errno_or_exact_answer(self, switch, marker):
        doc = getattr(MySQLConstraintMixin, switch).__doc__ or ""
        assert marker in doc, f"{switch} docstring does not record {marker!r}"


class TestMeasurementsThatAreNotMerelyUnsupported:
    """The two cases where ``False`` does not mean "the server refused".

    A caller treating either of these as an ordinary unsupported feature
    gets different behaviour than the switch's value suggests, so the
    distinction is asserted rather than left to the docstring alone.
    """

    def test_fk_match_is_parsed_and_discarded_not_rejected(self):
        """The clause is accepted and then dropped -- the wording matters.

        Measured on 26.7.0, ``ADD CONSTRAINT fk FOREIGN KEY (d) REFERENCES p
        (id) MATCH FULL`` succeeds, and ``SHOW CREATE TABLE`` then renders
        the constraint with no MATCH in it. ``MATCH_OPTION`` in
        ``information_schema.REFERENTIAL_CONSTRAINTS`` still reads ``FULL``,
        so the server records the mode and enforces nothing from it.

        A rejected clause raises ``1064`` and the caller can catch it; a
        discarded one succeeds, so the caller believes MATCH is in force.
        That is the whole reason this switch is ``False``.
        """
        doc = MySQLConstraintMixin.supports_fk_match.__doc__ or ""
        assert "parsed and discarded" in doc
        assert "not \"unsupported\"" in doc
        assert "MATCH_OPTION" in doc
        assert "FULL" in doc and "PARTIAL" in doc and "NONE" in doc

    def test_enforced_clause_is_undetectable_in_the_rendered_ddl(self):
        """``ENFORCED`` is accepted but leaves no trace, so the caveat is carried.

        Measured on 26.7.0, ``CHECK (v > 0) NOT ENFORCED`` round-trips as
        ``CHECK ((`v` > 0)) /*!80016 NOT ENFORCED */`` while ``CHECK (v > 0)
        ENFORCED`` renders identically to a constraint where the clause was
        never typed. The switch is still ``True`` -- the clause is accepted --
        but any switch claiming ENFORCED support must say the rendering
        cannot prove it, and both switches that claim it do.
        """
        for switch in ("supports_constraint_enforced", "supports_alter_constraint_enforced"):
            doc = getattr(MySQLConstraintMixin, switch).__doc__ or ""
            assert "ENFORCED" in doc
            assert "cannot" in doc or "identical" in doc, (
                f"{switch} claims ENFORCED support without saying the "
                f"rendered DDL cannot show that it was written"
            )


class TestMySQLIsNotConflatedWithMariaDB:
    """The two servers differ on exactly the clauses that look portable.

    Both are MySQL-family and share a ``CREATE TABLE`` surface, so these are
    the verdicts most likely to be copied between them by mistake. Measured
    against MariaDB 13.1 in the same session as the MySQL measurements.
    """

    #: MariaDB 13.1: rejects ENFORCED/NOT ENFORCED outright, but *does*
    #: accept the idempotent drop spelling. MySQL is the reverse on both.
    MARIADB_DIFFERS = (
        "supports_constraint_enforced",
        "supports_alter_constraint_enforced",
        "supports_drop_constraint_if_exists",
    )

    @pytest.mark.parametrize("switch", MARIADB_DIFFERS)
    def test_docstring_separates_this_backend_from_mariadb(self, switch):
        doc = getattr(MySQLConstraintMixin, switch).__doc__ or ""
        assert "MariaDB" in doc, (
            f"{switch} is one of the clauses where MariaDB answers "
            f"differently, so the docstring has to say which server it "
            f"measured"
        )