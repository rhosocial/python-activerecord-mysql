# src/rhosocial/activerecord/backend/impl/mysql/mixins/constraint.py
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
        AlterConstraint,
    )
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        ColumnConstraint,
    )


class MySQLConstraintMixin:
    """MySQL constraint capability probes.

    Every verdict in this mixin was measured against a live server, and the
    docstring of a switch records what the server did with the exact spelling
    in question. Two of those measurements explain why several answers are
    ``False`` even though the statement is *accepted*:

    * ``MATCH`` parses and is then discarded, so rendering the clause would
      tell the caller it is in effect when nothing enforces it.
    * ``ENFORCED`` is accepted but renders identically to the default, so the
      rendered DDL cannot show that it was written.

    The third is that ``ALTER CONSTRAINT`` exists in exactly one form, for
    exactly one kind of constraint, and that a primary key is not in the
    constraint-name space that ``DROP CONSTRAINT`` addresses.

    **Every constraint verdict this backend relies on is declared *here*.**
    The values below agree with core's ``ConstraintMixin`` defaults, but the
    agreement is the point rather than an accident: a switch this backend
    depends on must resolve to a class in this package, so a core default that
    moves cannot silently move MySQL's contract with it. ``test_constraint_
    switches_are_declared_locally`` in this backend's test suite fails if any
    of them is ever dropped and falls back to inheriting.

    A note on MariaDB, which is **not** this backend and must never be folded
    into it: MariaDB 13.1 rejects ``[NOT] ENFORCED`` outright (this MySQL
    accepts it on CHECK), and MariaDB *does* accept ``DROP CONSTRAINT IF
    EXISTS`` (MySQL answers ``1064``). The two disagree on exactly the two
    clauses a caller would most expect to be portable, so each verdict below
    is stated for MySQL only.
    """

    def supports_invisible_index(self) -> bool:
        """Whether INVISIBLE indexes are supported."""
        return self.version >= (8, 0, 0)

    def supports_descending_index(self) -> bool:
        """Whether descending indexes are supported."""
        return self.version >= (8, 0, 0)

    def supports_functional_index(self) -> bool:
        """Whether functional (expression) indexes are supported."""
        return self.version >= (8, 0, 0)

    # Basic constraint types (SQL-86/SQL-92)

    def supports_primary_key_constraint(self) -> bool:
        """Whether PRIMARY KEY constraints are supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686):
        ``ALTER TABLE t ADD CONSTRAINT pk PRIMARY KEY (v)`` is accepted and
        rendered back by ``SHOW CREATE TABLE`` as ``PRIMARY KEY (`v`)``.

        Two measured details belong to the *name space*, not to this switch,
        and are recorded in :meth:`supports_drop_constraint` and
        :meth:`supports_alter_constraint_enforced`: MySQL discards the
        ``CONSTRAINT pk`` symbol for a primary key (the rendered DDL contains
        no ``pk``), and a second one is refused with
        ``1068 (42000): Multiple primary key defined``.
        """
        return True

    def supports_unique_constraint(self) -> bool:
        """Whether UNIQUE constraints are supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686):
        ``ALTER TABLE t ADD CONSTRAINT uq UNIQUE (v)`` is accepted, the symbol
        survives in ``SHOW CREATE TABLE`` as ``CONSTRAINT `uq` UNIQUE (`v`)``,
        and ``ALTER TABLE t DROP CONSTRAINT uq`` removes it.
        """
        return True

    def supports_not_null_constraint(self) -> bool:
        """Whether NOT NULL column constraints are supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686):
        ``CREATE TABLE t (x INT NOT NULL)`` is accepted and renders
        ``x int NOT NULL``. Trivial for the server, but declared here so the
        verdict is this backend's rather than an inherited default.
        """
        return True

    def supports_foreign_key_constraint(self) -> bool:
        """Whether FOREIGN KEY constraints are supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686):
        ``ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (d) REFERENCES p (id)``
        is accepted, rendered back, and enforced -- a dangling child row is
        refused with
        ``1452 (23000): Cannot add or update a child row: a foreign key
        constraint fails``, and adding the constraint over such a row fails the
        same way.
        """
        return True

    def supports_fk_on_delete(self) -> bool:
        """Whether ``ON DELETE`` referential actions are supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686): all five
        ``reference_option`` values are accepted on ``ADD CONSTRAINT``, and
        ``information_schema.REFERENTIAL_CONSTRAINTS.DELETE_RULE`` reads back
        ``CASCADE`` for the action that was written.

        Independent of :meth:`supports_fk_match`, which is ``False``: that
        clause is discarded, while these actions survive even when a ``MATCH``
        is written alongside them (measured -- see ``supports_fk_match``).
        """
        return True

    def supports_fk_on_update(self) -> bool:
        """Whether ``ON UPDATE`` referential actions are supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686): ``ON
        UPDATE CASCADE`` is accepted and
        ``information_schema.REFERENTIAL_CONSTRAINTS.UPDATE_RULE`` reads back
        ``CASCADE``. Measured even together with ``MATCH FULL``, where the
        manual claims the referential actions are ignored (see
        :meth:`supports_fk_match`).
        """
        return True

    def supports_exclude_constraint(self) -> bool:
        """Whether EXCLUDE table constraints are supported.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686),
        ``ALTER TABLE t ADD CONSTRAINT ex EXCLUDE (a WITH =)`` answers

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'E'

        This is a backend-owned ``False`` rather than the inherited default, so
        that no core change can hand MySQL a constraint kind it cannot spell.
        """
        return False

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are supported and enforced.

        Measured on Community Server 26.7.0 (192.168.1.3:14686):
        ``ALTER TABLE t ADD CONSTRAINT ck CHECK (v > 0)`` is accepted and
        rendered back by ``SHOW CREATE TABLE`` as
        ``CONSTRAINT ck CHECK ((v > 0))``, and it is really enforced -- adding
        it over a row that violates it is refused with
        ``3819 (HY000): Check constraint 'ck3' is violated.`` and a violating
        insert afterwards with ``3819 (HY000): Check constraint 'ck3' is
        violated.`` (measured). The same addition with ``NOT ENFORCED`` is
        accepted over the violating row and admits it.

        Below 8.0.16 the clause parses and is discarded, so the probe is
        version-gated rather than a flat ``True``.
        """
        return self.version >= (8, 0, 16)

    def supports_add_constraint(self) -> bool:
        """Whether ``ALTER TABLE ADD CONSTRAINT`` is supported.

        True. Measured on Community Server 26.7.0 (192.168.1.3:14686): all
        four kinds are accepted by the ALTER path -- ``ADD CONSTRAINT ck
        CHECK (v > 0)``, ``ADD CONSTRAINT pk PRIMARY KEY (id)`` (on a table
        that has no primary key yet; a second one is refused with
        ``1068 (42000): Multiple primary key defined``), ``ADD CONSTRAINT uq
        UNIQUE (v)`` and ``ADD CONSTRAINT fk FOREIGN KEY (d) REFERENCES p
        (id) ON DELETE CASCADE`` each succeed and are rendered back by
        ``SHOW CREATE TABLE``.

        Adding validates the rows already present: a CHECK over a violating
        row fails with ``3819 (HY000)`` and a FOREIGN KEY over a dangling
        row with ``1452 (23000): Cannot add or update a child row: a foreign
        key constraint fails``. There is therefore no "add first, check
        later" spelling here (see ``supports_constraint_novalidate``), and the
        clause-level attributes are not additive (see
        ``supports_deferrable_constraint``).
        """
        return True

    def supports_drop_constraint(self) -> bool:
        """Whether ``ALTER TABLE DROP CONSTRAINT`` is supported.

        True, but the name space is narrower than it looks. Measured on
        Community Server 26.7.0 (192.168.1.3:14686):

        * ``DROP CONSTRAINT uq`` (UNIQUE) and ``DROP CONSTRAINT fk``
          (FOREIGN KEY) both work.
        * ``DROP CONSTRAINT pk2`` answers
          ``3940 (HY000): Constraint 'pk2' does not exist.`` even though the
          table really does have that primary key -- ``SHOW CREATE TABLE``
          renders ``PRIMARY KEY (`v`)`` on a table where
          ``ADD CONSTRAINT pk2 PRIMARY KEY (v)` had just succeeded. The
          symbol ``pk2`` never appears anywhere in the rendered DDL: MySQL
          drops the ``CONSTRAINT`` symbol for a PRIMARY KEY outright, so the
          name space ``DROP CONSTRAINT`` addresses never contained it. The
          working spelling is ``ALTER TABLE t DROP PRIMARY KEY`` (measured --
          it removes the key). This is a genuine per-kind gap: one boolean
          cannot say "drop everything except the primary key", and a caller
          that treats ``supports_drop_constraint() is True`` as "any named
          constraint can be dropped" is wrong for that one kind.
        * Dropping an FK leaves its auto-created helper index behind:
          ``KEY fkm (d)`` survives ``DROP CONSTRAINT fkm``, with the
          ``CONSTRAINT ... FOREIGN KEY`` line gone (measured).
        * A missing name answers ``3940 (HY000): Constraint 'x' does not
          exist.`` while ``DROP CHECK x`` answers ``3821 (HY000): Check
          constraint 'x' is not found in the table.`` -- the same "not
          there" outcome under **two different errnos**, so error mapping
          keyed on a single errno silently misses half the cases. Neither can
          be caught in a way that makes the drop re-runnable (see
          ``supports_drop_constraint_if_exists``).

        MariaDB 13.1 diverges from this backend on the idempotent spelling --
        it *does* accept ``DROP CONSTRAINT IF EXISTS`` -- so a value copied
        from the MariaDB backend into this one would be wrong. See
        :meth:`supports_drop_constraint_if_exists`.
        """
        return True

    def supports_drop_constraint_if_exists(self) -> bool:
        """Whether ``ALTER TABLE DROP CONSTRAINT IF EXISTS`` is supported.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686),
        ``ALTER TABLE t DROP CONSTRAINT IF EXISTS x`` answers

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'IF EXISTS x' at line 1

        The failure is in the parser, before the name is looked up, so no
        errno can be caught to make a drop idempotent: **there is no
        idempotent drop spelling for a MySQL constraint at all.**
        ``MySQLDDLColumnMixin.format_drop_table_constraint_action`` refuses
        the ``if_exists=True`` request by name for this reason; pre-check
        ``information_schema.TABLE_CONSTRAINTS`` instead.

        MariaDB 13.1 measured ``True`` for the same switch, so the two must not
        be conflated: this is MySQL only.
        """
        return False

    def supports_rename_constraint(self) -> bool:
        """Whether ``ALTER TABLE ... RENAME CONSTRAINT ... TO ...`` is supported.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686),
        ``ALTER TABLE t RENAME CONSTRAINT ck TO ck2`` answers

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'CONSTRAINT ck TO ck2' at line 1

        The failure is at the parser, before either name is resolved, so
        renaming has to be done as a drop-and-re-add.

        The name of this switch is provisional: core S3 owns the final
        ``AlterTableConstraintSupport`` spelling and may rename it.
        """
        return False

    def supports_enable_disable_constraint(self) -> bool:
        """Whether ``ALTER TABLE ... {ENABLE|DISABLE} CONSTRAINT`` is supported.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686), both
        halves are parser errors:

            1064 (42000): ... near 'CONSTRAINT ck' at line 1

        ``ENABLE`` and ``DISABLE`` are parseable keywords in MySQL (they belong
        to ``ENABLE KEYS``, ``DISABLE KEYS`` and to the ``ALTER TABLE
        ENABLE|DISABLE KEYS`` forms), so the failure lands on the trailing
        ``CONSTRAINT ck`` rather than on the keyword -- worth knowing when
        reading the error, which does not name the real problem.

        Only Oracle has this of the backends measured. The name of this switch
        is provisional: core S3 owns the final spelling and may rename it.
        """
        return False

    def supports_constraint_novalidate(self) -> bool:
        """Whether ``ADD CONSTRAINT ... NOT VALID`` is accepted.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686),
        ``ALTER TABLE t ADD CONSTRAINT ck CHECK (v > 0) NOT VALID`` answers

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'VALID' at line 1

        and the same for ``ADD CONSTRAINT fk FOREIGN KEY (d) REFERENCES p
        (id) NOT VALID``. There is nothing to defer to: an added CHECK is
        validated against the rows already present (``3819``) and so is an
        added FOREIGN KEY (``1452``).
        """
        return False

    def supports_validate_constraint(self) -> bool:
        """Whether ``ALTER TABLE ... VALIDATE CONSTRAINT`` is supported.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686),
        ``ALTER TABLE t VALIDATE CONSTRAINT ck`` answers

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'VALIDATE CONSTRAINT ck' at line 1

        MySQL has no deferred-constraint state to validate -- see
        ``supports_deferrable_constraint`` and
        ``supports_constraint_novalidate``, both refused by the same 1064.
        """
        return False

    def supports_alter_constraint_enforced(self) -> bool:
        """Whether the ``ALTER CONSTRAINT ... [NOT] ENFORCED`` verb exists.

        Version-only, per the rule that a switch answers a family and the
        kinds it can address are narrowed in the formatter: this backend's
        :meth:`format_alter_constraint_action` refuses every kind but CHECK
        by name before the shared rendering runs.

        The verb exists from 8.0.16 on. Measured on Community Server 26.7.0
        (192.168.1.3:14686):

        * ``ALTER TABLE t ALTER CONSTRAINT ck NOT ENFORCED`` is accepted and
          ``SHOW CREATE TABLE`` then renders
          ``CONSTRAINT `ck` CHECK ((`v` > 0)) /*!80016 NOT ENFORCED */``.
        * ``ALTER TABLE t ALTER CONSTRAINT ck ENFORCED`` is accepted and the
          marker is dropped again -- but note the asymmetry with
          :meth:`supports_constraint_enforced`: here ``ENFORCED`` is at
          least *observable* as the loss of the ``NOT ENFORCED`` marker,
          whereas on the ``ADD`` path a freshly written ``ENFORCED`` leaves
          DDL that is identical to a constraint where the clause was never
          typed. Either way the rendered DDL cannot prove ``ENFORCED`` was
          written.
        * On a FOREIGN KEY the server answers, rather than the parser:
          ``3941 (HY000): Altering constraint enforcement is not supported
          for the constraint 'fkZ'. Enforcement state alter is not supported
          for the PRIMARY, UNIQUE and FOREIGN KEY type constraints.`` (errno
          ``3941``, measured). The server itself names the three kinds it
          refuses, which is the evidence the formatter's CHECK-only
          narrowing stands on.

        ``ALTER CONSTRAINT ck [NOT] ENFORCED`` is the **only** working
        ``ALTER CONSTRAINT`` form MySQL has (see
        :meth:`supports_alter_constraint`); ``ALTER CONSTRAINT ck
        DEFERRABLE`` is a parser error (1064) and belongs to
        :meth:`supports_deferrable_constraint`, not here.

        MariaDB 13.1 has no ``ALTER CONSTRAINT`` at all and rejects
        ``[NOT] ENFORCED`` on every path, so this ``True`` is MySQL only.
        """
        return self.version >= (8, 0, 16)

    def format_alter_constraint_action(
        self, action: "AlterConstraint"
    ) -> Tuple[str, tuple]:
        """``ALTER CONSTRAINT`` addresses CHECK only on this server.

        The server refuses the other kinds rather than the parser (errno
        ``3941`` names PRIMARY, UNIQUE and FOREIGN KEY -- measured, see
        :meth:`supports_alter_constraint_enforced`), so the dialect refuses
        them by name instead of sending a statement the server rejects.

        Raises:
            TypeError: ``constraint_type`` is not a ``TableConstraintType``.
            UnsupportedFeatureError: The kind is anything but CHECK.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import (
            UnsupportedFeatureError,
        )
        from rhosocial.activerecord.backend.expression.statements import (
            TableConstraintType,
        )

        constraint_type = action.constraint_type
        if not isinstance(constraint_type, TableConstraintType):
            raise TypeError(
                "constraint_type must be a TableConstraintType, got "
                f"{type(constraint_type).__name__}"
            )
        if constraint_type is not TableConstraintType.CHECK:
            raise UnsupportedFeatureError(
                self.name,
                f"ALTER CONSTRAINT {constraint_type.name} ENFORCED/NOT ENFORCED",
                "MySQL alters the enforcement state of CHECK constraints only; the "
                "server answers errno 3941 on PRIMARY KEY, UNIQUE and FOREIGN KEY.",
            )
        return super().format_alter_constraint_action(action)

    def supports_alter_constraint(self) -> bool:
        """Whether ``ALTER TABLE ... ALTER CONSTRAINT`` is supported at all.

        True, for exactly one attribute. Measured on Community Server 26.7.0
        (192.168.1.3:14686) the statement exists and ``ALTER CONSTRAINT ck
        [NOT] ENFORCED`` works on a CHECK; every other attribute -- ``DEFERRABLE``,
        ``INITIALLY DEFERRED``, ``VALIDATE``, ``NOVALIDATE``, ``RELY`` -- is a
        ``1064 (42000)`` parser error.

        So ``True`` here means "one form exists", not "constraints are
        alterable": the attribute-level answer is
        :meth:`supports_alter_constraint_enforced`, and the deferred/validate
        answers are :meth:`supports_deferrable_constraint`,
        :meth:`supports_constraint_novalidate` and
        :meth:`supports_validate_constraint`, all ``False`` on the same 1064.

        The name of this switch is provisional: core S3 owns the final
        ``AlterTableConstraintSupport`` spelling and may rename it.
        """
        return True

    # Constraint enforcement control (SQL:2016)

    def supports_constraint_enforced(self) -> bool:
        """Whether ``[NOT] ENFORCED`` on a CHECK constraint is supported.

        True from 8.0.16 on. Measured on Community Server 26.7.0
        (192.168.1.3:14686) on the ``ADD CONSTRAINT`` / ``CREATE TABLE``
        path:

        * ``CHECK (v > 0) NOT ENFORCED`` is accepted and round-trips as
          ``CHECK ((v > 0)) /*!80016 NOT ENFORCED */``.
        * ``CHECK (v > 0) ENFORCED`` is accepted but renders *identically to
          the default* -- no clause at all in ``SHOW CREATE TABLE``. Only
          ``information_schema.TABLE_CONSTRAINTS.ENFORCED`` distinguishes
          them ('YES' / 'NO', measured); the rendered DDL cannot.

        Check only: ``ADD CONSTRAINT fk FOREIGN KEY ... NOT ENFORCED`` and
        ``ADD CONSTRAINT uq UNIQUE (v) NOT ENFORCED`` are both answered by

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'NOT ENFORCED' at line 1

        The per-kind half of that lives in the formatter, which renders the
        clause for CHECK and refuses the FOREIGN KEY request by name; the
        ALTER-path half lives in ``supports_alter_constraint_enforced``.

        **The caveat on ``ENFORCED`` above applies to every caller of this
        switch.** Saying "this backend supports ENFORCED" is true and still
        not enough to make a round-trip assertion: a rendered ``ENFORCED`` and
        a rendered default are the same string, so a caller cannot prove from
        the DDL that the clause was accepted, only that nothing is missing.

        MariaDB 13.1 rejects ``[NOT] ENFORCED`` outright on every path, so this
        ``True`` is MySQL only.
        """
        return self.version >= (8, 0, 16)

    def _format_constraint_enforcement(self, constraint: "ColumnConstraint") -> str:
        """Narrow the ENFORCABLE kinds to CHECK for this server.

        The shared helper renders whatever the standard-derived whitelist
        allows; MySQL's parser accepts the trait on CHECK only (measured on
        Community Server 26.7.0: UNIQUE and FOREIGN KEY answer ``1064`` --
        see :meth:`supports_constraint_enforced`), so the kind is narrowed
        here and everything else is refused by name. The table-level path
        renders through this backend's own ``format_table_constraint``,
        which makes the same refusal inline.
        """
        if constraint.enforced or constraint.not_enforced:
            from rhosocial.activerecord.backend.dialect.exceptions import (
                UnsupportedFeatureError,
            )
            from rhosocial.activerecord.backend.expression.statements import (
                ColumnConstraintType,
                TableConstraintType,
            )

            kind = constraint.constraint_type
            if not isinstance(kind, (ColumnConstraintType, TableConstraintType)):
                raise TypeError(
                    "constraint_type must be a ColumnConstraintType or "
                    f"TableConstraintType, got {type(kind).__name__}"
                )
            if kind.name != "CHECK" or not self.supports_constraint_enforced():
                raise UnsupportedFeatureError(
                    self.name,
                    "ENFORCED/NOT ENFORCED constraint",
                    "MySQL carries [NOT] ENFORCED on CHECK constraints only; the "
                    "server answers 1064 on every other kind (measured on 26.7.0).",
                )
        return super()._format_constraint_enforcement(constraint)

    # FK match modes (SQL:1999)

    def supports_fk_match(self) -> bool:
        """Whether ``MATCH {SIMPLE|PARTIAL|FULL}`` is supported.

        False -- and not because the spelling is rejected. Measured on
        Community Server 26.7.0 (192.168.1.3:14686),
        ``ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (d) REFERENCES p (id)
        MATCH FULL`` is *accepted*, and the MATCH clause is then parsed away:
        ``SHOW CREATE TABLE`` renders

            CONSTRAINT `fk` FOREIGN KEY (`d`) REFERENCES `p` (`id`)

        with no MATCH in it. Three FKs added to one table by ``MATCH FULL``,
        ``MATCH PARTIAL`` and no clause at all all render the *same* three
        lines, so ``MATCH`` is absent from the DDL entirely.

        **``MATCH_OPTION`` does retain the requested mode.** Measured on 26.7.0,
        ``information_schema.REFERENTIAL_CONSTRAINTS.MATCH_OPTION`` reads
        ``FULL`` for the ``MATCH FULL`` FK, ``PARTIAL`` for the ``MATCH
        PARTIAL`` one, and ``NONE`` for the FK written with no MATCH clause
        (measured on the same server, 192.168.1.3:14686). So the server
        records the mode in its catalog even though it renders and enforces
        nothing from it -- reading it back proves what was *written*, never
        what is in *force*. (Earlier notes on this switch said ``MATCH_OPTION``
        came back ``NONE``; that is the value for a FK with no MATCH clause,
        and the full-vs-none distinction is the measurement above.)

        The referential actions survive, which is narrower than the manual
        claims. MySQL 8.0 manual 15.1.20.5 says an explicit MATCH "also causes
        ON DELETE and ON UPDATE clauses to be ignored"; measured on 26.7.0,
        ``ADD CONSTRAINT fk FOREIGN KEY (d) REFERENCES p (id) MATCH FULL ON
        DELETE CASCADE ON UPDATE CASCADE`` renders
        ``... ON DELETE CASCADE ON UPDATE CASCADE``, and the catalog reads
        ``DELETE_RULE='CASCADE'``, ``UPDATE_RULE='CASCADE'`` (measured). The
        manual's MATCH half holds; its side-effect half does not, on this
        version.

        So this is **parsed and discarded, not "unsupported"** -- the clause
        is accepted by the grammar and then dropped, and the distinction
        matters to callers: an unsupported clause raises a ``1064`` the caller
        can catch and report, whereas a discarded clause is accepted silently,
        so a caller who wrote it believes MATCH is in force when no engine
        recognizes it. That is why the refusal this switch drives is by name
        rather than by letting the server take it.

        Official, MySQL 8.0 manual 15.1.20.5 ("FOREIGN KEY Constraints"):

            no storage engine, including InnoDB, recognizes or enforces the
            MATCH clause ... specifying MATCH should be avoided.

        MariaDB 13.1 was measured to discard ``MATCH`` the same way, so the
        ``False`` is not what separates the two servers here.
        """
        return False

    # Constraint deferral (SQL:1999)

    def supports_deferrable_constraint(self) -> bool:
        """Whether ``DEFERRABLE`` / ``INITIALLY DEFERRED|IMMEDIATE`` is
        supported.

        False. Measured on Community Server 26.7.0 (192.168.1.3:14686), every
        spelling is a parser error: ``ADD CONSTRAINT ck CHECK (v > 0)
        DEFERRABLE``, ``ADD CONSTRAINT ck CHECK (v > 0) NOT DEFERRABLE
        INITIALLY DEFERRED`` and ``ADD CONSTRAINT fk FOREIGN KEY (d)
        REFERENCES p (id) DEFERRABLE`` all answer

            1064 (42000): You have an error in your SQL syntax; check the
            manual that corresponds to your MySQL server version for the
            right syntax to use near 'DEFERRABLE' at line 1

        ``ALTER CONSTRAINT ck DEFERRABLE`` answers the same 1064, which is
        what distinguishes it from the one ``ALTER CONSTRAINT`` form MySQL
        does accept (``supports_alter_constraint_enforced``).

        This is a whole-family ``False``, and the reason is uniform: **no
        spelling of constraint deferral exists in MySQL.** Measured on 26.7.0,
        every one of these is ``1064 (42000)``:

        ==============================  ==================================
        ``ADD CONSTRAINT ... DEFERRABLE``  ``near 'DEFERRABLE'``
        ``ADD CONSTRAINT ... NOT VALID``   ``near 'VALID'``
        ``VALIDATE CONSTRAINT ck``          ``near 'VALIDATE CONSTRAINT ck'``
        ``ALTER CONSTRAINT ck DEFERRABLE``  ``near 'DEFERRABLE'``
        ``RENAME CONSTRAINT ck TO ck2``     ``near 'CONSTRAINT ck TO ck2'``
        ``ENABLE CONSTRAINT ck``            ``near 'CONSTRAINT ck'``
        ``DISABLE CONSTRAINT ck``           ``near 'CONSTRAINT ck'``
        ``NOCHECK CONSTRAINT ck``           ``near 'NOCHECK CONSTRAINT ck'``
        ``CHECK CONSTRAINT ck``             ``near 'CONSTRAINT ck'``
        ``DROP CONSTRAINT IF EXISTS ck``    ``near 'IF EXISTS ck'``
        ==============================  ==================================

        Note the last one is this backend's lack of an idempotent drop spelling
        rather than part of the deferral family; it is listed because it is
        the same errno and the same fix (no such grammar). The remaining
        switches in the family each record their own measurement:
        ``supports_constraint_novalidate``, ``supports_validate_constraint``,
        ``supports_rename_constraint``, ``supports_enable_disable_constraint``
        and ``supports_drop_constraint_if_exists``.
        """
        return False
