import datetime
import unittest
from unittest.mock import patch, MagicMock

import pytest

from src.rhosocial.activerecord.backend.typing import DatabaseType
from src.rhosocial.activerecord.backend.impl.mysql.type_converters import MySQLDateTimeConverter


class TestMySQLDateTimeConverter(unittest.TestCase):
    """Tests for the MySQL-specific DateTimeConverter"""

    def setUp(self):
        self.converter = MySQLDateTimeConverter()

    def test_priority(self):
        """Test that MySQL converter has higher priority than base converter"""
        from src.rhosocial.activerecord.backend.basic_type_converter import DateTimeConverter
        base_converter = DateTimeConverter()
        assert self.converter.priority > base_converter.priority

    def test_can_handle_timedelta(self):
        """Test that converter can handle timedelta objects"""
        # Create a timedelta object (like MySQL would return for TIME columns)
        td = datetime.timedelta(hours=2, minutes=30, seconds=15)
        assert self.converter.can_handle(td)

    def test_can_handle_regular_types(self):
        """Test that converter can still handle regular datetime types"""
        # Should still handle regular datetime types
        dt = datetime.datetime.now()
        d = datetime.date.today()
        t = datetime.time(14, 30, 45)

        assert self.converter.can_handle(dt)
        assert self.converter.can_handle(d)
        assert self.converter.can_handle(t)

    def test_from_database_timedelta_positive(self):
        """Test conversion from timedelta to time with positive values"""
        # Test with a positive timedelta
        td = datetime.timedelta(hours=2, minutes=30, seconds=15, microseconds=500000)
        result = self.converter.from_database(td)

        assert isinstance(result, datetime.time)
        assert result.hour == 2
        assert result.minute == 30
        assert result.second == 15
        assert result.microsecond == 500000

    def test_from_database_timedelta_negative(self):
        """Test conversion from timedelta to time with negative values"""
        # Test with a negative timedelta (MySQL can return these)
        td = datetime.timedelta(hours=-2, minutes=-30)
        result = self.converter.from_database(td)

        # Should convert to minimum valid time
        assert isinstance(result, datetime.time)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_from_database_timedelta_large_hours(self):
        """Test conversion from timedelta with hours > 24"""
        # MySQL can store TIME values > 24 hours, but Python time objects are limited to 0-23
        td = datetime.timedelta(hours=25, minutes=30)
        result = self.converter.from_database(td)

        # Should cap at 23 hours
        assert isinstance(result, datetime.time)
        assert result.hour == 23
        assert result.minute == 30

    def test_from_database_regular_types(self):
        """Test that converter still handles regular types correctly"""
        # Test with regular datetime string
        dt_str = "2023-01-15 14:30:45"
        result = self.converter.from_database(dt_str, DatabaseType.DATETIME)
        assert isinstance(result, datetime.datetime)

        # Test with date string
        date_str = "2023-01-15"
        result = self.converter.from_database(date_str, DatabaseType.DATE)
        assert isinstance(result, datetime.date)

        # Test with time string
        time_str = "14:30:45"
        result = self.converter.from_database(time_str, DatabaseType.TIME)
        assert isinstance(result, datetime.time)

    def test_to_database(self):
        """Test that to_database still works correctly"""
        # The to_database method should use the parent implementation
        t = datetime.time(14, 30, 45)
        result = self.converter.to_database(t)
        assert result == "14:30:45"

        # Test with datetime
        dt = datetime.datetime(2023, 1, 15, 14, 30, 45)
        result = self.converter.to_database(dt)
        assert result == "2023-01-15 14:30:45"
