# src/rhosocial/activerecord/backend/impl/mysql/suggestion/table_options_suggestion.py
"""MySQL's CREATE TABLE option answers: the text encoding and engine it recommends."""
from rhosocial.activerecord.backend.suggestion.definitions import (
    StorageEngineSuggestion,
    TextEncodingSuggestion,
)


class MySQLTextEncodingSuggestionMixin:
    """``utf8mb4``, spelled with the collation this server version defaults to.

    ``utf8mb4`` is available on every version this backend supports (5.5.3 is
    the floor and the backend's floor is 5.6), so no fallback charset is
    needed. The collation is version-specific rather than fixed: 8.0 shipped
    the ``0900`` series and made ``utf8mb4_0900_ai_ci`` the server's default,
    while an earlier server's default for that charset is
    ``utf8mb4_general_ci``. Recommending the server's own default keeps the
    suggestion honest on both sides of that boundary.
    """

    #: MySQL 8.0+'s default collation for utf8mb4.
    _UTF8MB4_DEFAULT_COLLATION_0900 = "utf8mb4_0900_ai_ci"
    #: MySQL 5.6/5.7's default collation for utf8mb4.
    _UTF8MB4_DEFAULT_COLLATION_LEGACY = "utf8mb4_general_ci"

    def suggest_text_encoding(self) -> TextEncodingSuggestion:
        """Return ``utf8mb4`` and the version's own default collation."""
        if self.version_at_least((8, 0, 0)):
            collation = self._UTF8MB4_DEFAULT_COLLATION_0900
            reason = "MySQL 8.0+ defaults utf8mb4 to this collation"
        else:
            collation = self._UTF8MB4_DEFAULT_COLLATION_LEGACY
            reason = "MySQL 5.6/5.7 defaults utf8mb4 to this collation"
        return TextEncodingSuggestion(
            charset="utf8mb4",
            collation=collation,
            reason=f"{reason}; utf8mb4 stores the full BMP and emoji",
        )


class MySQLStorageEngineSuggestionMixin:
    """``InnoDB``, the engine that carries transactions and foreign keys."""

    def suggest_storage_engine(self) -> StorageEngineSuggestion:
        return StorageEngineSuggestion(
            engine="InnoDB",
            transactional=True,
            reason=(
                "InnoDB is MySQL's default engine and the built-in one that "
                "provides transactions, row-level locking and foreign keys"
            ),
        )


__all__ = [
    "MySQLTextEncodingSuggestionMixin",
    "MySQLStorageEngineSuggestionMixin",
]
