# src/rhosocial/activerecord/backend/impl/mysql/mixins/generated_column.py
class MySQLGeneratedColumnMixin:
    """MySQL generated column and auto-increment support."""

    def supports_generated_column(self) -> bool:
        """Whether generated (computed) columns are supported."""
        return self.version >= (5, 7, 0)

    def supports_auto_increment(self) -> bool:
        """Whether AUTO_INCREMENT column attributes are supported."""
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
