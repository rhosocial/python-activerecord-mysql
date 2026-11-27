# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_alter_modifiers.py
"""MySQL's ``ALTER TABLE ... ALGORITHM=..., LOCK=...`` execution modifiers.

The node is MySQL's own (:class:`~...expression.alter_table_modifiers.MySQLAlterTableStatement`);
this mixin is where every decision about it lives: which words exist, which
server versions accept them, which combinations the server refuses, and the
kind of each slot. The constructor only collects parameters (§3.1).
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING, Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AlterTableAction

from ..expression.alter_table_modifiers import MYSQL_ALGORITHM_WORDS, MYSQL_LOCK_WORDS
from .object_kind import require_kind

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.alter_table_modifiers import MySQLAlterTableStatement


class MySQLAlterTableModifierMixin:
    """Version gates and rendering for MySQL's online-DDL execution modifiers.

    Sources (MySQL 8.0 Reference Manual):

    * §15.1.9 ``ALTER TABLE`` -- grammar; ``ALGORITHM [=] {DEFAULT | INSTANT |
      INPLACE | COPY}`` and ``LOCK [=] {DEFAULT | NONE | SHARED | EXCLUSIVE}``
      are alter_options, comma-separated with the ordinary actions.
    * §17.12 ``InnoDB and Online DDL`` -- "ALGORITHM=INSTANT support is
      available for ADD COLUMN and other operations in MySQL 8.0.12" and
      "Only LOCK=DEFAULT is supported for operations that are performed
      instantly".
    """

    def supports_alter_table_algorithm(self) -> bool:
        """Whether ``ALTER TABLE ... ALGORITHM=`` is available.

        The clause came in with online DDL (§17.12) in MySQL 5.6; below that
        every alteration copied the table and no algorithm could be chosen.
        The words ``DEFAULT``, ``INPLACE`` and ``COPY`` all share this floor;
        ``INSTANT`` has its own, later gate.
        """
        return self.version_at_least((5, 6, 0))

    def supports_alter_table_algorithm_instant(self) -> bool:
        """Whether ``ALGORITHM=INSTANT`` is available: MySQL 8.0.12 (§17.12).

        The general ALGORITHM gate is not enough: 8.0.11 parses the clause but
        rejects ``INSTANT`` with an error, so the later floor is a separate
        probe rather than a spelling detail of the formatter.
        """
        return self.version_at_least((8, 0, 12))

    def supports_alter_table_lock(self) -> bool:
        """Whether ``ALTER TABLE ... LOCK=`` is available: MySQL 5.6 (§17.12).

        All four words share this floor. Which of them a given alteration can
        actually honour is a property of the operation and storage engine,
        not of the server version, so it is not decided here.
        """
        return self.version_at_least((5, 6, 0))

    def format_mysql_alter_table_statement(
        self, expr: "MySQLAlterTableStatement"
    ) -> Tuple[str, tuple]:
        """Render one statement with the modifiers ahead of the action.

        With neither modifier supplied the call is handed to core's
        ``format_alter_table_statement`` unchanged, so an unmodified wrapper
        is byte-identical to the core statement it wraps. With modifiers, the
        action renderer is used and the clauses join into MySQL's single
        comma-separated form.

        Raises:
            TypeError: the table is not a ``Table``, or the action is not an
                ``AlterTableAction``. A wrong kind would otherwise render a
                well-formed statement against the wrong object or silently
                skip the clause that cannot be dispatched.
            UnsupportedFeatureError: a modifier word is unknown, its server
                version is too old, or ``INSTANT`` is combined with a lock
                other than ``DEFAULT`` (§17.12).
        """
        require_kind(expr.table, Table, "MySQLAlterTableStatement.table")
        if not isinstance(expr.action, AlterTableAction):
            raise TypeError(
                "MySQLAlterTableStatement.action must be an AlterTableAction "
                f"implementation, got {type(expr.action).__name__}"
            )

        if expr.algorithm is None and expr.lock is None:
            return super().format_alter_table_statement(expr)

        algorithm_word = self._mysql_modifier_word(expr.algorithm)
        lock_word = self._mysql_modifier_word(expr.lock)

        modifiers = []
        if algorithm_word is not None:
            if algorithm_word not in MYSQL_ALGORITHM_WORDS:
                raise UnsupportedFeatureError(
                    self.name,
                    f"ALTER TABLE ALGORITHM={algorithm_word}",
                    "ALGORITHM accepts DEFAULT, INSTANT, INPLACE or COPY.",
                )
            if not self.supports_alter_table_algorithm():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE ALGORITHM",
                    "The ALGORITHM clause requires MySQL 5.6 or later.",
                )
            if algorithm_word == "INSTANT" and not self.supports_alter_table_algorithm_instant():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE ALGORITHM=INSTANT",
                    "ALGORITHM=INSTANT requires MySQL 8.0.12 or later.",
                )
            modifiers.append(f"ALGORITHM={algorithm_word}")

        if lock_word is not None:
            if lock_word not in MYSQL_LOCK_WORDS:
                raise UnsupportedFeatureError(
                    self.name,
                    f"ALTER TABLE LOCK={lock_word}",
                    "LOCK accepts DEFAULT, NONE, SHARED or EXCLUSIVE.",
                )
            if not self.supports_alter_table_lock():
                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE LOCK",
                    "The LOCK clause requires MySQL 5.6 or later.",
                )
            if algorithm_word == "INSTANT" and lock_word != "DEFAULT":
                raise UnsupportedFeatureError(
                    self.name,
                    f"ALTER TABLE ALGORITHM=INSTANT, LOCK={lock_word}",
                    "Only LOCK=DEFAULT is supported for instant operations (§17.12).",
                )
            modifiers.append(f"LOCK={lock_word}")

        all_params = []
        action_sql, action_params = expr.action.to_sql()
        all_params.extend(action_params)
        table_sql = expr.table.to_sql()[0]
        clauses = ", ".join([*modifiers, action_sql])
        return f"ALTER TABLE {table_sql} {clauses}", tuple(all_params)

    @staticmethod
    def _mysql_modifier_word(value: object) -> Optional[str]:
        """Normalise a modifier value to the uppercase word the server spells.

        A ``str``-valued enum member is accepted as well as the word itself;
        ``None`` keeps meaning "clause omitted", so it must not become the
        string ``"None"``.
        """
        if value is None:
            return None
        raw = value.value if isinstance(value, Enum) else value
        return str(raw).strip().upper()
