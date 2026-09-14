# src/rhosocial/activerecord/backend/impl/mysql/mixins/dql.py
from typing import Any, List, Optional, Tuple


class MySQLDQLMixin:
    """MySQL DQL (Data Query Language) formatting support."""

    def format_limit_offset(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Tuple[Optional[str], List[Any]]:
        """Format LIMIT and OFFSET clause for MySQL.

        MySQL requires LIMIT when using OFFSET.
        """
        params = []
        sql_parts = []

        if limit is not None:
            sql_parts.append(f"LIMIT {self.p()}")
            params.append(limit)

        if offset is not None:
            if limit is None:
                sql_parts.append(f"LIMIT {self.p()}")
                params.append(18446744073709551615)
            sql_parts.append(f"OFFSET {self.p()}")
            params.append(offset)

        if not sql_parts:
            return None, []

        return " ".join(sql_parts), params

    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported in SELECT statements."""
        return True
