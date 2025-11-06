# tests/rhosocial/activerecord_mysql_test/feature/backend/test_async_type_converters.py
import datetime
import uuid
from enum import Enum

import pytest

from rhosocial.activerecord.backend.typing import DatabaseType
from rhosocial.activerecord.backend.impl.mysql.type_converters import (
    ModernMySQLDateTimeConverter,
    LegacyMySQLDateTimeConverter,
    MySQLEnumConverter,
    MySQLUUIDConverter
)


class TestModernMySQLDateTimeConverter:
    """Tests for the ModernMySQLDateTimeConverter"""

    def test_from_database_timedelta_to_time(self):
        """Test that timedelta objects from the DB are converted to time objects."""
        converter = ModernMySQLDateTimeConverter()
        # MySQL can return timedelta for TIME columns
        td = datetime.timedelta(hours=14, minutes=30, seconds=45)
        result = converter.from_database(td)
        assert isinstance(result, datetime.time)
        assert result == datetime.time(14, 30, 45)

    def test_from_database_datetime_gets_localized(self):
        """Test that naive datetime objects get localized."""
        converter = ModernMySQLDateTimeConverter()
        naive_dt = datetime.datetime(2023, 1, 15, 14, 30, 45)
        result = converter.from_database(naive_dt)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None

    def test_from_database_negative_timedelta(self):
        """Test that negative timedelta is handled gracefully."""
        converter = ModernMySQLDateTimeConverter()
        td = datetime.timedelta(hours=-1)
        result = converter.from_database(td)
        assert result == datetime.time(0, 0, 0)


class TestLegacyMySQLDateTimeConverter:
    """Tests for the LegacyMySQLDateTimeConverter"""

    def test_to_database_datetime_with_microseconds(self):
        """Test that datetimes are formatted with microseconds."""
        converter = LegacyMySQLDateTimeConverter()
        dt = datetime.datetime(2023, 1, 15, 14, 30, 45, 123456)
        result = converter.to_database(dt)
        assert result == "2023-01-15 14:30:45.123456"

    def test_to_database_datetime_without_microseconds(self):
        """Test that datetimes are formatted without microseconds if they are zero."""
        converter = LegacyMySQLDateTimeConverter()
        dt = datetime.datetime(2023, 1, 15, 14, 30, 45)
        result = converter.to_database(dt)
        assert result == "2023-01-15 14:30:45"


class Color(Enum):
    RED = "r"
    GREEN = "g"
    BLUE = "b"


class TestMySQLEnumConverter:
    """Tests for the MySQLEnumConverter"""

    def test_to_database_enum_member(self):
        """Test that enum members are converted to their value."""
        converter = MySQLEnumConverter()
        result = converter.to_database(Color.RED)
        assert result == "r"

    def test_to_database_set_of_enums(self):
        """Test that a set of enums is converted to a comma-separated string."""
        converter = MySQLEnumConverter()
        value = {Color.RED, Color.BLUE}
        result = converter.to_database(value)
        # The order is not guaranteed for sets
        assert set(result.split(',')) == {"r", "b"}


class TestMySQLUUIDConverter:
    """Tests for the MySQLUUIDConverter"""

    def test_to_database_string_mode(self):
        """Test UUID conversion in string mode."""
        converter = MySQLUUIDConverter(binary_mode=False)
        test_uuid = uuid.uuid4()
        result = converter.to_database(test_uuid)
        assert result == str(test_uuid)

    def test_to_database_binary_mode(self):
        """Test UUID conversion in binary mode."""
        converter = MySQLUUIDConverter(binary_mode=True)
        test_uuid = uuid.uuid4()
        result = converter.to_database(test_uuid)
        assert result == test_uuid.bytes

    def test_from_database_string_mode(self):
        """Test UUID conversion from string."""
        converter = MySQLUUIDConverter(binary_mode=False)
        test_uuid = uuid.uuid4()
        result = converter.from_database(str(test_uuid), source_type=DatabaseType.UUID)
        assert isinstance(result, uuid.UUID)
        assert result == test_uuid

    def test_from_database_binary_mode(self):
        """Test UUID conversion from bytes."""
        converter = MySQLUUIDConverter(binary_mode=True)
        test_uuid = uuid.uuid4()
        # The can_handle method should detect the bytes and allow conversion
        result = converter.from_database(test_uuid.bytes)
        assert isinstance(result, uuid.UUID)
        assert result == test_uuid
