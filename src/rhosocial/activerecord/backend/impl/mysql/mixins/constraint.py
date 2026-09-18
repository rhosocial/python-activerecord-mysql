# src/rhosocial/activerecord/backend/impl/mysql/mixins/constraint.py
class MySQLConstraintMixin:
    """MySQL constraint feature support."""

    def supports_invisible_index(self) -> bool:
        """Whether INVISIBLE indexes are supported."""
        return self.version >= (8, 0, 0)

    def supports_descending_index(self) -> bool:
        """Whether descending indexes are supported."""
        return self.version >= (8, 0, 0)

    def supports_functional_index(self) -> bool:
        """Whether functional (expression) indexes are supported."""
        return self.version >= (8, 0, 0)

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are enforced."""
        return self.version >= (8, 0, 16)

    def supports_constraint_enforced(self) -> bool:
        """Whether ENFORCED/NOT ENFORCED constraint control is supported."""
        return self.version >= (8, 0, 16)

    def supports_fk_match(self) -> bool:
        """Whether MATCH {SIMPLE|PARTIAL|FULL} is supported."""
        return False

    def supports_deferrable_constraint(self) -> bool:
        """Whether DEFERRABLE constraints are supported."""
        return False
