# tests/rhosocial/activerecord_mysql_test/feature/backend/test_concurrency_protocol.py
"""
Test for ConcurrencyAware protocol implementation in MySQL backend.

This test verifies that MySQLBackend correctly implements the ConcurrencyAware
protocol by fetching max_connections during connect and returning the appropriate
concurrency hint.
"""
import pytest

from rhosocial.activerecord.backend.protocols import ConcurrencyAware, ConcurrencyHint


class TestMySQLConcurrencyAware:
    """Test ConcurrencyAware protocol implementation for MySQL backend."""

    def test_mysql_backend_implements_protocol(self, mysql_backend_single):
        """Test that MySQLBackend implements ConcurrencyAware protocol."""
        assert isinstance(mysql_backend_single, ConcurrencyAware)

    def test_mysql_get_concurrency_hint(self, mysql_backend_single):
        """Test MySQLBackend returns correct concurrency hint."""
        hint = mysql_backend_single.get_concurrency_hint()

        assert hint is not None
        assert isinstance(hint, ConcurrencyHint)
        assert hint.max_concurrency is not None
        assert hint.max_concurrency > 0
        assert "max_connections" in hint.reason
        assert "pool_size" in hint.reason

    def test_mysql_concurrency_hint_value(self, mysql_backend_single):
        """Test concurrency hint value is bounded by pool_size."""
        pool_size = mysql_backend_single.config.pool_size or 5
        hint = mysql_backend_single.get_concurrency_hint()

        assert hint.max_concurrency <= pool_size
        assert hint.max_concurrency > 0

    def test_mysql_concurrency_hint_not_none_after_connect(self, mysql_backend_single):
        """Test that concurrency hint is populated after connect."""
        assert mysql_backend_single._connection is not None
        assert mysql_backend_single.get_concurrency_hint() is not None


class TestAsyncMySQLConcurrencyAware:
    """Test ConcurrencyAware protocol implementation for async MySQL backend."""

    @pytest.mark.asyncio
    async def test_async_mysql_backend_implements_protocol(self, async_mysql_backend_single):
        """Test that AsyncMySQLBackend implements ConcurrencyAware protocol."""
        assert isinstance(async_mysql_backend_single, ConcurrencyAware)

    @pytest.mark.asyncio
    async def test_async_mysql_get_concurrency_hint(self, async_mysql_backend_single):
        """Test AsyncMySQLBackend returns correct concurrency hint."""
        hint = async_mysql_backend_single.get_concurrency_hint()

        assert hint is not None
        assert isinstance(hint, ConcurrencyHint)
        assert hint.max_concurrency is not None
        assert hint.max_concurrency > 0
        assert "max_connections" in hint.reason
        assert "pool_size" in hint.reason

    @pytest.mark.asyncio
    async def test_async_mysql_concurrency_hint_value(self, async_mysql_backend_single):
        """Test async concurrency hint value is bounded by pool_size."""
        pool_size = async_mysql_backend_single.config.pool_size or 5
        hint = async_mysql_backend_single.get_concurrency_hint()

        assert hint.max_concurrency <= pool_size
        assert hint.max_concurrency > 0

    @pytest.mark.asyncio
    async def test_async_mysql_concurrency_hint_not_none_after_connect(
        self, async_mysql_backend_single
    ):
        """Test that async concurrency hint is populated after connect."""
        assert async_mysql_backend_single._connection is not None
        assert async_mysql_backend_single.get_concurrency_hint() is not None