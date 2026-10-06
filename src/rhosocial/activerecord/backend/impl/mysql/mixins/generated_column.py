# src/rhosocial/activerecord/backend/impl/mysql/mixins/generated_column.py
class MySQLGeneratedColumnMixin:
    """MySQL generated column and auto-increment support."""

    def supports_generated_column(self) -> bool:
        """Whether generated (computed) columns are supported."""
        return self.version >= (5, 7, 0)

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
        return self.version >= (8, 0, 0)
