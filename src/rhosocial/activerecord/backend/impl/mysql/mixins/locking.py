# src/rhosocial/activerecord/backend/impl/mysql/mixins/locking.py
from typing import Tuple


class MySQLLockingMixin:
    """MySQL row-level locking mixin."""

    def supports_for_share(self) -> bool:
        return self.version >= (8, 0, 0)

    def supports_for_update_nowait(self) -> bool:
        return self.version >= (8, 0, 0)

    def supports_for_update_skip_locked(self) -> bool:
        return self.version >= (8, 0, 0)

    def format_for_update_clause(self, clause) -> Tuple[str, tuple]:
        """Format MySQL-specific FOR UPDATE / FOR SHARE clause."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression import LockStrength

        all_params = []

        strength = clause.strength

        if strength == LockStrength.SHARE:
            if not self.supports_for_share():
                raise UnsupportedFeatureError(self.name, "FOR SHARE (requires MySQL 8.0+)")
        elif strength != LockStrength.UPDATE:
            raise UnsupportedFeatureError(
                self.name, f"{strength.value} (unsupported lock strength)"
            )

        sql_parts = [strength.value]

        if clause.of_columns:
            of_parts = []
            for col in clause.of_columns:
                col_sql, col_params = col.to_sql()
                of_parts.append(col_sql)
                all_params.extend(col_params)
            if of_parts:
                sql_parts.append(f"OF {', '.join(of_parts)}")

        if clause.nowait:
            if not self.supports_for_update_nowait():
                raise UnsupportedFeatureError(self.name, "NOWAIT (requires MySQL 8.0+)")
            sql_parts.append("NOWAIT")
        elif clause.skip_locked:
            if not self.supports_for_update_skip_locked():
                raise UnsupportedFeatureError(self.name, "SKIP LOCKED (requires MySQL 8.0+)")
            sql_parts.append("SKIP LOCKED")

        return " ".join(sql_parts), tuple(all_params)
