# src/rhosocial/activerecord/backend/impl/mysql/mixins/grouping.py
class MySQLGroupingMixin:
    """MySQL advanced grouping support (ROLLUP)."""

    def supports_rollup(self) -> bool:
        """ROLLUP is supported using WITH ROLLUP syntax since early MySQL versions."""
        return True  # Supported since MySQL 4.0.0
