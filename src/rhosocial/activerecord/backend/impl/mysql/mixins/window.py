# src/rhosocial/activerecord/backend/impl/mysql/mixins/window.py
class MySQLWindowMixin:
    """MySQL window function support."""

    def supports_window_functions(self) -> bool:
        """Window functions are supported since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported, since MySQL 8.0.0."""
        return self.version >= (8, 0, 0)
