# tests/rhosocial/activerecord_mysql_test/feature/backend/test_async_type_mapping.py
import json
from datetime import datetime

import pytest

from rhosocial.activerecord.backend import DatabaseType
from rhosocial.activerecord.backend.errors import TypeConversionError


@pytest.mark.asyncio
async def test_boolean_conversion(async_mysql_backend):
    """Test boolean value conversion"""
    mapper = async_mysql_backend.dialect
    assert mapper.to_database(True, DatabaseType.BOOLEAN) == 1
    assert mapper.to_database(False, DatabaseType.BOOLEAN) == 0


@pytest.mark.asyncio
async def test_datetime_conversion(async_mysql_backend):
    """Test date time conversion"""
    mapper = async_mysql_backend.dialect
    now = datetime.now()
    converted = mapper.to_database(now, DatabaseType.DATETIME)
    assert isinstance(converted, str)


@pytest.mark.asyncio
async def test_array_conversion(async_mysql_backend):
    """Test array conversion"""
    mapper = async_mysql_backend.dialect
    data = [1, 2, 3]
    converted = mapper.to_database(data, DatabaseType.ARRAY)
    assert isinstance(converted, str)
    assert json.loads(converted) == data


@pytest.mark.asyncio
async def test_invalid_array_conversion(async_mysql_backend):
    """Test invalid array conversion"""
    mapper = async_mysql_backend.dialect
    with pytest.raises(TypeConversionError):
        mapper.to_database(123, DatabaseType.ARRAY)