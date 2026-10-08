# src/rhosocial/activerecord/backend/impl/mysql/expression/rename_table.py
"""MySQL RENAME TABLE statement expression.

MySQL supports atomic renaming of one or more tables in a single statement:

    RENAME TABLE t1 TO t2 [, t3 TO t4, ...]

Both ends of every pair are schema objects, so a rename may cross databases::

    RENAME TABLE `old_db`.`users` TO `new_db`.`users`

This is distinct from ``ALTER TABLE ... RENAME TO`` which only renames a
single table. The statement is atomic: all renames either succeed or fail
together.
"""

from typing import List, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class MySQLRenameTableExpression(BaseExpression):
    """Represent a MySQL ``RENAME TABLE ...`` atomic multi-table statement.

    Attributes:
        renames: Sequence of ``(old_table, new_table)`` schema object pairs.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        renames: List[Tuple[Table, Table]],
    ):
        """Bind the statement to its rename pairs.

        Args:
            dialect: SQL dialect.
            renames: ``(old, new)`` pairs, both of them
                :class:`~rhosocial.activerecord.backend.expression.objects.Table`
                objects. The pair may name different databases on either end,
                which is how a cross-database rename becomes expressible;
                MySQL rejects the rename if the two databases are on different
                servers, and that check belongs to the server.
        """
        super().__init__(dialect)
        self.renames: List[Tuple[Table, Table]] = list(renames)

    def validate(self, strict: bool = True) -> None:
        """Validate the rename pair list.

        Raises:
            ValueError: If the rename list is empty or contains an invalid pair.
            TypeError: If either end of a pair is not a :class:`Table`. Bare
                strings are refused because they cannot express a database,
                and a rename that quietly drops one would move the table
                somewhere the caller did not ask for.
        """
        if not strict:
            return
        if not self.renames:
            raise ValueError("RENAME TABLE requires at least one <table> TO <table> pair")
        for pair in self.renames:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError(f"Invalid rename pair: {pair!r}")
            old_table, new_table = pair
            for label, value in (("old", old_table), ("new", new_table)):
                if not isinstance(value, Table):
                    raise TypeError(
                        f"RENAME TABLE {label} table must be a Table object, "
                        f"got {type(value).__name__}; pass "
                        f"Table(self.dialect, 'users', catalog_name='app') to qualify the name"
                    )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rename_table_statement"
