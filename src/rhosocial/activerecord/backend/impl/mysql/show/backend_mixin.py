# src/rhosocial/activerecord/backend/impl/mysql/show/backend_mixin.py
"""
MySQL backend mixins for SHOW functionality.

This module provides mixin classes that add the show() factory method
to MySQL backends. The show() method returns a MySQLShowFunctionality
instance that provides all MySQL SHOW commands.
"""

from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import MySQLBackend
    from ..async_backend import AsyncMySQLBackend
    from .functionality import MySQLShowFunctionality, AsyncMySQLShowFunctionality


class MySQLShowMixin:
    """MySQL backend mixin for SHOW functionality.

    Provides the show() factory method that returns a MySQLShowFunctionality
    instance for executing MySQL SHOW commands.
    """

    def show(self) -> "MySQLShowFunctionality":
        """Return a MySQLShowFunctionality instance."""
        return self._create_show_functionality()

    def _create_show_functionality(self) -> "MySQLShowFunctionality":
        """Create MySQL SHOW functionality instance.

        Returns:
            MySQLShowFunctionality instance with version awareness.
        """
        from .functionality import MySQLShowFunctionality
        # Get server version for feature adaptation
        version = getattr(self, "_version", None)
        if version is None and hasattr(self, "get_server_version"):
            try:
                version = self.get_server_version()
            except Exception:
                version = None
        return MySQLShowFunctionality(self, version)


class AsyncMySQLShowMixin:
    """Async MySQL backend mixin for SHOW functionality.

    Provides the show() factory method that returns an AsyncMySQLShowFunctionality
    instance for executing MySQL SHOW commands asynchronously.
    """

    def show(self) -> "AsyncMySQLShowFunctionality":
        """Return an AsyncMySQLShowFunctionality instance."""
        return self._create_show_functionality()

    def _create_show_functionality(self) -> "AsyncMySQLShowFunctionality":
        """Create async MySQL SHOW functionality instance.

        Returns:
            AsyncMySQLShowFunctionality instance with version awareness.
        """
        from .functionality import AsyncMySQLShowFunctionality
        # Get server version for feature adaptation
        version = getattr(self, "_version", None)
        if version is None and hasattr(self, "_version"):
            version = self._version
        return AsyncMySQLShowFunctionality(self, version)
