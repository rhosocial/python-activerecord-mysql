# src/rhosocial/activerecord/backend/impl/mysql/mixins/cte.py
class MySQLCTEMixin:
    """MySQL CTE (Common Table Expression) support."""

    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_materialized_cte(self) -> bool:
        """Whether the CTE ``MATERIALIZED`` / ``NOT MATERIALIZED`` hint exists.

        MySQL has no such grammar at any version measured (5.6.51, 5.7.44,
        8.0.46, 8.4.11, 9.2.0, 9.4.0, 26.7.0): both spellings are syntax
        errors on every server, and below 8.0.1 a CTE itself is not parseable
        (plain ``WITH name AS (...)`` also errors). Core's CTE formatter
        consults this probe, so a requested hint is refused by name.
        """
        return False

    def supports_unconditional_cte_order_by(self) -> bool:
        """ORDER BY inside a CTE definition requires CTE support (8.0.0+)."""
        return self.version >= (8, 0, 0)
