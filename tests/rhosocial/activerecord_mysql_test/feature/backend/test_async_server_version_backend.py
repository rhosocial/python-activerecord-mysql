# tests/rhosocial/activerecord_mysql_test/feature/backend/test_async_server_version.py
import pytest
import datetime
from rhosocial.activerecord.backend.impl.mysql.type_converters import ModernMySQLDateTimeConverter, LegacyMySQLDateTimeConverter


@pytest.mark.asyncio
async def test_async_get_server_version_format(async_mysql_backend):
    """
    Tests that get_server_version() returns a tuple of 3 integers.
    """
    # Get the server version asynchronously
    version = await async_mysql_backend.get_server_version()

    # Assert the format
    assert isinstance(version, tuple), "Version should be a tuple"
    assert len(version) == 3, "Version tuple should have 3 elements"
    assert all(isinstance(i, int) for i in version), "All elements in version tuple should be integers"


@pytest.mark.asyncio
async def test_async_datetime_converter_selection(async_mysql_backend):
    """
    Tests that the correct datetime converter is selected based on MySQL version using async backend.
    """
    version = await async_mysql_backend.get_server_version()
    
    # Find the converter for datetime
    converter = async_mysql_backend.type_registry.find_converter(datetime.datetime.now())

    if version >= (8, 0, 0):
        assert isinstance(converter, ModernMySQLDateTimeConverter), f"For MySQL {version}, expected ModernMySQLDateTimeConverter, but got {type(converter).__name__}"
    else:
        assert isinstance(converter, LegacyMySQLDateTimeConverter), f"For MySQL {version}, expected LegacyMySQLDateTimeConverter, but got {type(converter).__name__}"
