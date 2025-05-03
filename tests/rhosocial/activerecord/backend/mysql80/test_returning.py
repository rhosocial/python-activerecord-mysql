from unittest.mock import patch, MagicMock

import pytest

from src.rhosocial.activerecord.backend.errors import ReturningNotSupportedError
from src.rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from src.rhosocial.activerecord.backend.impl.mysql.dialect import MySQLReturningHandler
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


def test_returning_not_supported():
    """Test RETURNING clause is not supported in any MySQL version"""
    # Test with various MySQL versions
    versions = [(5, 7, 0), (8, 0, 0), (8, 0, 20), (8, 0, 21), (8, 1, 0)]

    for version in versions:
        handler = MySQLReturningHandler(version)
        # Verify is_supported always returns False
        assert not handler.is_supported

        # Verify format_clause always raises ReturningNotSupportedError
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            handler.format_clause()
        assert "RETURNING clause is not supported by MySQL. This is a fundamental limitation of the database engine, not a driver issue." in str(exc_info.value)

        # Test with specific columns
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            handler.format_clause(columns=["id", "name"])
        assert "RETURNING clause is not supported by MySQL. This is a fundamental limitation of the database engine, not a driver issue." in str(exc_info.value)


@pytest.fixture
def mock_mysql_backend():
    """Create mock MySQL backend"""
    config = ConnectionConfig(host="localhost", database="test", username="test", password="test")
    config.version = (8, 0, 0)  # Version doesn't matter as RETURNING is never supported

    # Create mock backend
    with patch("mysql.connector.connect") as mock_connect:
        conn_mock = MagicMock()
        cursor_mock = MagicMock()
        conn_mock.cursor.return_value = cursor_mock
        mock_connect.return_value = conn_mock

        backend = MySQLBackend(connection_config=config)
        backend._connection = conn_mock
        backend._server_version_cache = (8, 0, 0)

        # Add cursor_mock attribute for test access
        conn_mock.cursor_mock = cursor_mock

        yield backend


def test_backend_returning_not_supported(mock_mysql_backend):
    """
    Test MySQL backend RETURNING functionality is not supported in any version.
    """
    backend = mock_mysql_backend

    # Test supports_returning property
    assert not backend.supports_returning

    # Test execute with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.execute(
            "INSERT INTO users (name) VALUES (%s)",
            params=("test",),
            returning=True
        )
    assert "RETURNING clause is not supported" in str(exc_info.value)

    # Test insert with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.insert(
            "users",
            {"name": "test"},
            returning=True
        )
    assert "RETURNING clause is not supported" in str(exc_info.value)

    # Test update with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.update(
            "users",
            {"name": "updated"},
            "id = %s",
            (1,),
            returning=True
        )
    assert "RETURNING clause is not supported" in str(exc_info.value)

    # Test delete with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.delete(
            "users",
            "id = %s",
            (1,),
            returning=True
        )
    assert "RETURNING clause is not supported" in str(exc_info.value)


@pytest.mark.parametrize("version_info", [
    (5, 7, 0),
    (8, 0, 0),
    (8, 0, 20),
    (8, 0, 21),
    (8, 1, 0),
])
def test_version_specific_support(version_info):
    """
    Test RETURNING is not supported across any MySQL versions.

    Args:
        version_info: MySQL version tuple
    """
    handler = MySQLReturningHandler(version_info)
    assert not handler.is_supported  # Should always be False