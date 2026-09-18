# src/rhosocial/activerecord/backend/impl/mysql/mixins/cte.py
class MySQLCTEMixin:
    """MySQL CTE (Common Table Expression) support."""

    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_unconditional_cte_order_by(self) -> bool:
        """ORDER BY inside a CTE definition requires CTE support (8.0.0+)."""
        return self.version >= (8, 0, 0)
