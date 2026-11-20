# src/rhosocial/activerecord/backend/impl/mysql/mixins/generated_column.py
class MySQLGeneratedColumnMixin:
    """MySQL generated column and auto-increment support."""

    def supports_generated_column(self) -> bool:
        """Whether generated (computed) columns are supported."""
        return self.version_at_least((5, 7, 0))

    def supports_auto_increment_column(self) -> bool:
        """Whether the parameterless ``AUTO_INCREMENT`` column marker is supported.

        MySQL accepts the marker on every version measured (5.6 through 9.x),
        and the marker carries no parameters: its seed and increment are
        table-level options (``AUTO_INCREMENT=100``), which is a different
        mechanism. The SQL-standard ``GENERATED ... AS IDENTITY`` clause is
        *not* this marker and is declined -- MySQL rejects that grammar on
        every version measured, so :class:`IdentityColumnMixin`'s probes stay
        at their ``False`` defaults.
        """
        return True

    def supports_database_assigned_integer_column(self) -> bool:
        """Whether an integer column's value comes from the database.

        ``True``: ``AUTO_INCREMENT`` supplies the value when the INSERT omits
        it, and the row can return it. This is the capability a declaration
        asks about; the marker above is one of its spellings -- PostgreSQL
        spells the same capability ``SERIAL`` while declining that marker, so
        the two questions are separate probes.

        Not guaranteed as a portable behaviour: when an explicit value larger
        than the current counter is inserted, MySQL raises ``AUTO_INCREMENT``
        to ``max + 1``, while a sequence-backed column leaves its sequence
        untouched. Anything relying on that belongs to the MySQL family.
        """
        return True

    def supports_generated_columns(self) -> bool:
        """Whether generated (computed) columns are supported."""
        return self.supports_generated_column()

    def supports_stored_generated_columns(self) -> bool:
        """Whether STORED generated columns are supported."""
        return self.supports_generated_column()

    def supports_virtual_generated_columns(self) -> bool:
        """Whether VIRTUAL generated columns are supported."""
        return self.supports_generated_column()

    def supports_default_column_value_expression(self) -> bool:
        """Whether DEFAULT column values can use expressions."""
        return self.version_at_least((8, 0, 0))
