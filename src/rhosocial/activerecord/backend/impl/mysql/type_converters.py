from enum import Enum
from typing import Any, Optional
import datetime
import uuid

from ...typing import DatabaseType
from ...basic_type_converter import UUIDConverter, DateTimeConverter
from ...type_converters import BaseTypeConverter


class MySQLGeometryConverter(BaseTypeConverter):
    """
    MySQL geometry converter.
    Handles conversion between Python geometry objects and MySQL geometric types.
    """

    @property
    def priority(self) -> int:
        return 70

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle geometric data.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if target_type in (DatabaseType.POINT, DatabaseType.POLYGON,
                           DatabaseType.GEOMETRY, DatabaseType.LINE,
                           "POINT", "POLYGON", "GEOMETRY", "LINESTRING"):
            return True

        # Check if it's a geometry object with WKT representation
        if hasattr(value, 'wkt') or hasattr(value, '__geo_interface__'):
            return True

        # Check if it's a WKT string
        if isinstance(value, str) and any(value.upper().startswith(prefix) for prefix in
                                          ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]):
            return True

        return False


    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python geometry object to MySQL representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            bytes: The converted value ready for database storage (WKB format)
        """
        if value is None:
            return None

        # If it's already a WKB, return it
        if isinstance(value, bytes):
            return value

        # Convert WKT string to WKB
        if isinstance(value, str):
            # Use MySQL's ST_GeomFromText function
            # Note: This would actually be handled in SQL, not here
            return value

        # For objects with WKT representation
        if hasattr(value, 'wkt'):
            return value.wkt

        # For objects with __geo_interface__
        if hasattr(value, '__geo_interface__'):
            # Convert GeoJSON to WKT
            # This would require a GeoJSON to WKT converter
            geo = value.__geo_interface__
            if geo['type'] == 'Point':
                coords = geo['coordinates']
                return f"POINT({coords[0]} {coords[1]})"
            # Add other geometry types as needed

        return value  # Default: return unchanged


class MySQLDateTimeConverter(DateTimeConverter):
    """
    MySQL specific datetime converter that handles timedelta objects returned for TIME columns.
    
    MySQL's mysql-connector-python returns datetime.timedelta for TIME columns,
    but we want to convert these to datetime.time objects for consistency.
    """
    
    @property
    def priority(self) -> int:
        # Higher priority than the base DateTimeConverter to ensure this one is used for MySQL
        return 30
    
    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle the given value or type.
        
        Extends the base DateTimeConverter to also handle timedelta objects.
        
        Args:
            value: The value to check
            target_type: Optional target type
            
        Returns:
            bool: True if this converter can handle the conversion
        """
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            return True
            
        # Use the base class implementation for other types
        return super().can_handle(value, target_type)
    
    def from_database(self, value: Any, source_type: Any = None, timezone: Optional[str] = None) -> Any:
        """
        Convert a database value to its Python representation.
        
        Extends the base DateTimeConverter to handle timedelta objects returned by MySQL for TIME columns.
        
        Args:
            value: The database value to convert
            source_type: Optional source type hint
            timezone: Optional timezone name
            
        Returns:
            The converted Python value
        """
        if value is None:
            return None
            
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            # Convert timedelta to time
            # Extract hours, minutes, seconds and microseconds from timedelta
            total_seconds = value.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Handle negative timedeltas (can occur in MySQL)
            if hours < 0 or minutes < 0 or seconds < 0:
                # MySQL allows negative time values, but Python's time doesn't
                # For simplicity, we'll convert to the smallest valid time
                return datetime.time(0, 0, 0)
            # Ensure values are within valid ranges for time
            hours = min(23, int(hours))  # time() accepts 0-23 hours
            minutes = min(59, int(minutes))  # time() accepts 0-59 minutes
            seconds_int = int(seconds)
            microseconds = int((seconds - seconds_int) * 1000000)
            return datetime.time(hours, minutes, seconds_int, microseconds)
            
        # Use the base class implementation for other types
        return super().from_database(value, source_type, timezone)


def register_mysql_converters(backend):
    """
    Register MySQL-specific converters with the backend.
    
    Args:
        backend: The MySQL backend instance
    """
    mysql_datetime_converter = MySQLDateTimeConverter()
    backend.register_converter(
        mysql_datetime_converter,
        types=[DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME, DatabaseType.TIMESTAMP]
    )


    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a MySQL geometry value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        # MySQL typically returns geometry as WKB
        # Convert to appropriate Python type if a suitable library is available
        # For simplicity, we just return the WKB bytes or WKT string

        return value


class MySQLEnumConverter(BaseTypeConverter):
    """
    MySQL enum converter.
    Handles conversion between Python enum objects and MySQL ENUM/SET types.
    """

    @property
    def priority(self) -> int:
        return 65


class MySQLEnumConverter(BaseTypeConverter):
    """
    MySQL enum converter.
    Handles conversion between Python enum objects and MySQL ENUM/SET types.
    """

    @property
    def priority(self) -> int:
        return 65


    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle ENUM data.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if target_type in (DatabaseType.ENUM, DatabaseType.SET, "ENUM", "SET"):
            return True
        if isinstance(value, Enum):
            return True
        return False


    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python enum to MySQL ENUM representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            str: The enum value as string
        """
        if value is None:
            return None

        if isinstance(value, Enum):
            return value.value

        # For SET types (multiple values)
        if isinstance(value, (list, tuple, set)) and all(isinstance(item, Enum) for item in value):
            return ','.join(str(item.value) for item in value)

        return value  # Default: return unchanged


class MySQLDateTimeConverter(DateTimeConverter):
    """
    MySQL specific datetime converter that handles timedelta objects returned for TIME columns.
    
    MySQL's mysql-connector-python returns datetime.timedelta for TIME columns,
    but we want to convert these to datetime.time objects for consistency.
    """
    
    @property
    def priority(self) -> int:
        # Higher priority than the base DateTimeConverter to ensure this one is used for MySQL
        return 30
    
    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle the given value or type.
        
        Extends the base DateTimeConverter to also handle timedelta objects.
        
        Args:
            value: The value to check
            target_type: Optional target type
            
        Returns:
            bool: True if this converter can handle the conversion
        """
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            return True
            
        # Use the base class implementation for other types
        return super().can_handle(value, target_type)
    
    def from_database(self, value: Any, source_type: Any = None, timezone: Optional[str] = None) -> Any:
        """
        Convert a database value to its Python representation.
        
        Extends the base DateTimeConverter to handle timedelta objects returned by MySQL for TIME columns.
        
        Args:
            value: The database value to convert
            source_type: Optional source type hint
            timezone: Optional timezone name
            
        Returns:
            The converted Python value
        """
        if value is None:
            return None
            
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            # Convert timedelta to time
            # Extract hours, minutes, seconds and microseconds from timedelta
            total_seconds = value.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Handle negative timedeltas (can occur in MySQL)
            if hours < 0 or minutes < 0 or seconds < 0:
                # MySQL allows negative time values, but Python's time doesn't
                # For simplicity, we'll convert to the smallest valid time
                return datetime.time(0, 0, 0)
            # Ensure values are within valid ranges for time
            hours = min(23, int(hours))  # time() accepts 0-23 hours
            minutes = min(59, int(minutes))  # time() accepts 0-59 minutes
            seconds_int = int(seconds)
            microseconds = int((seconds - seconds_int) * 1000000)
            return datetime.time(hours, minutes, seconds_int, microseconds)
            
        # Use the base class implementation for other types
        return super().from_database(value, source_type, timezone)


def register_mysql_converters(backend):
    """
    Register MySQL-specific converters with the backend.
    
    Args:
        backend: The MySQL backend instance
    """
    mysql_datetime_converter = MySQLDateTimeConverter()
    backend.register_converter(
        mysql_datetime_converter,
        types=[DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME, DatabaseType.TIMESTAMP]
    )


class MySQLDateTimeConverter(DateTimeConverter):
    """
    MySQL specific datetime converter that handles timedelta objects returned for TIME columns.
    
    MySQL's mysql-connector-python returns datetime.timedelta for TIME columns,
    but we want to convert these to datetime.time objects for consistency.
    """
    
    @property
    def priority(self) -> int:
        # Higher priority than the base DateTimeConverter to ensure this one is used for MySQL
        return 30
    
    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle the given value or type.
        
        Extends the base DateTimeConverter to also handle timedelta objects.
        
        Args:
            value: The value to check
            target_type: Optional target type
            
        Returns:
            bool: True if this converter can handle the conversion
        """
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            return True
            
        # Use the base class implementation for other types
        return super().can_handle(value, target_type)
    
    def from_database(self, value: Any, source_type: Any = None, timezone: Optional[str] = None) -> Any:
        """
        Convert a database value to its Python representation.
        
        Extends the base DateTimeConverter to handle timedelta objects returned by MySQL for TIME columns.
        
        Args:
            value: The database value to convert
            source_type: Optional source type hint
            timezone: Optional timezone name
            
        Returns:
            The converted Python value
        """
        if value is None:
            return None
            
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            # Convert timedelta to time
            # Extract hours, minutes, seconds and microseconds from timedelta
            total_seconds = value.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Handle negative timedeltas (can occur in MySQL)
            if hours < 0 or minutes < 0 or seconds < 0:
                # MySQL allows negative time values, but Python's time doesn't
                # For simplicity, we'll convert to the smallest valid time
                return datetime.time(0, 0, 0)
            # Ensure values are within valid ranges for time
            hours = min(23, int(hours))  # time() accepts 0-23 hours
            minutes = min(59, int(minutes))  # time() accepts 0-59 minutes
            seconds_int = int(seconds)
            microseconds = int((seconds - seconds_int) * 1000000)
            return datetime.time(hours, minutes, seconds_int, microseconds)
            
        # Use the base class implementation for other types
        return super().from_database(value, source_type, timezone)


def register_mysql_converters(backend):
    """
    Register MySQL-specific converters with the backend.
    
    Args:
        backend: The MySQL backend instance
    """
    mysql_datetime_converter = MySQLDateTimeConverter()
    backend.register_converter(
        mysql_datetime_converter,
        types=[DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME, DatabaseType.TIMESTAMP]
    )


    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a MySQL ENUM/SET value to Python.

        For full conversion to Enum objects, we would need the actual Enum class,
        which is not available in this context. This would typically be handled
        by a more specialized converter that knows the specific Enum type.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The value (unchanged in base implementation)
        """
        # We can't convert to specific Enum types without knowing the Enum class
        return value


class MySQLUUIDConverter(UUIDConverter):
    """
    MySQL UUID converter.

    Handles conversion between Python UUID objects and MySQL storage formats:
    - CHAR(36) for string representation
    - BINARY(16) for binary representation
    """

    def __init__(self, binary_mode: bool = False):
        """
        Initialize MySQL UUID converter.

        Args:
            binary_mode: If True, use binary representation (BINARY(16)) instead of
                         string representation (CHAR(36))
        """
        super().__init__()
        self._binary_mode = binary_mode

    @property
    def priority(self) -> int:
        return 45  # Higher priority than base UUID converter

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """Extended can_handle to recognize MySQL-specific UUID formats"""
        if super().can_handle(value, target_type):
            return True

        # Handle MySQL binary format
        if isinstance(value, bytes) and len(value) == 16:
            return True

        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python UUID to MySQL format.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            str or bytes: The converted value ready for database storage
        """
        if value is None:
            return None

        # Convert to UUID object first
        uuid_obj = None
        if isinstance(value, uuid.UUID):
            uuid_obj = value
        elif isinstance(value, str) and self._is_uuid_string(value):
            try:
                uuid_obj = uuid.UUID(value)
            except ValueError:
                return value
        elif isinstance(value, bytes) and len(value) == 16:
            try:
                uuid_obj = uuid.UUID(bytes=value)
            except ValueError:
                return value

        # Convert UUID to appropriate format
        if uuid_obj is not None:
            if self._binary_mode:
                return uuid_obj.bytes
            else:
                return str(uuid_obj)

        return value  # Default: return unchanged

class MySQLDateTimeConverter(DateTimeConverter):
    """
    MySQL specific datetime converter that handles timedelta objects returned for TIME columns.
    
    MySQL's mysql-connector-python returns datetime.timedelta for TIME columns,
    but we want to convert these to datetime.time objects for consistency.
    """
    
    @property
    def priority(self) -> int:
        # Higher priority than the base DateTimeConverter to ensure this one is used for MySQL
        return 30
    
    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle the given value or type.
        
        Extends the base DateTimeConverter to also handle timedelta objects.
        
        Args:
            value: The value to check
            target_type: Optional target type
            
        Returns:
            bool: True if this converter can handle the conversion
        """
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            return True
            
        # Use the base class implementation for other types
        return super().can_handle(value, target_type)
    
    def from_database(self, value: Any, source_type: Any = None, timezone: Optional[str] = None) -> Any:
        """
        Convert a database value to its Python representation.
        
        Extends the base DateTimeConverter to handle timedelta objects returned by MySQL for TIME columns.
        
        Args:
            value: The database value to convert
            source_type: Optional source type hint
            timezone: Optional timezone name
            
        Returns:
            The converted Python value
        """
        if value is None:
            return None
            
        # Handle timedelta objects (MySQL TIME columns)
        if isinstance(value, datetime.timedelta):
            # Convert timedelta to time
            # Extract hours, minutes, seconds and microseconds from timedelta
            total_seconds = value.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Handle negative timedeltas (can occur in MySQL)
            if hours < 0 or minutes < 0 or seconds < 0:
                # MySQL allows negative time values, but Python's time doesn't
                # For simplicity, we'll convert to the smallest valid time
                return datetime.time(0, 0, 0)
            # Ensure values are within valid ranges for time
            hours = min(23, int(hours))  # time() accepts 0-23 hours
            minutes = min(59, int(minutes))  # time() accepts 0-59 minutes
            seconds_int = int(seconds)
            microseconds = int((seconds - seconds_int) * 1000000)
            return datetime.time(hours, minutes, seconds_int, microseconds)
            
        # Use the base class implementation for other types
        return super().from_database(value, source_type, timezone)
