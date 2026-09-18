# src/rhosocial/activerecord/backend/impl/mysql/mixins/join.py
class MySQLJoinMixin:
    """MySQL join type support."""

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        return self.version >= (8, 0, 14)

    def supports_right_join(self) -> bool:
        """RIGHT JOIN is supported."""
        return True

    def supports_straight_join(self) -> bool:
        """MySQL-specific STRAIGHT_JOIN is supported."""
        return True
