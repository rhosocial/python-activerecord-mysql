# src/rhosocial/activerecord/backend/impl/mysql/adapters.py
import datetime
import json
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Tuple, Type, Union, Optional
from datetime import timezone, timedelta

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class MySQLBlobAdapter(SQLTypeAdapter):
    """
    Adapts Python bytes to MySQL BLOB and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bytes: [bytes]}

    def to_database(self, value: bytes, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        return value

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> bytes:
        if value is None:
            return None
        # MySQL connector usually returns bytes directly for BLOB types
        return value


class MySQLJSONAdapter(SQLTypeAdapter):
    """
    Adapts Python dict/list to MySQL JSON and vice-versa.
    Serializes to JSON string when writing, deserializes from JSON string when reading.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {dict: [str], list: [str]}

    def to_database(self, value: Union[dict, list], target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        # MySQL JSON type often stores as TEXT, so we serialize to string
        return json.dumps(value, ensure_ascii=False)

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Union[dict, list]:
        if value is None:
            return None
        # MySQL connector might return str for JSON, or already dict/list for some drivers
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)


class MySQLUUIDAdapter(SQLTypeAdapter):
    """
    Adapts Python UUID to MySQL CHAR(36) and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {uuid.UUID: [str]}

    def to_database(self, value: uuid.UUID, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        return str(value)

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> uuid.UUID:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class MySQLBooleanAdapter(SQLTypeAdapter):
    """
    Adapts Python bool to MySQL TINYINT(1) (or similar integer type) and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bool: [int]}

    def to_database(self, value: bool, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        return 1 if value else 0

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> bool:
        if value is None:
            return None
        # MySQL returns int (0 or 1) for TINYINT(1)
        return bool(value)


class MySQLDecimalAdapter(SQLTypeAdapter):
    """
    Adapts Python Decimal to MySQL DECIMAL/NUMERIC (or float/str) and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Decimal: [Decimal, float, str]}

    def to_database(self, value: Decimal, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        if target_type is Decimal:
            return value
        if target_type is float:
            return float(value)
        if target_type is str:
            return str(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Decimal:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        # Converts str, float, int to Decimal
        return Decimal(str(value))


class MySQLDateAdapter(SQLTypeAdapter):
    """
    Adapts Python date to MySQL DATE string (YYYY-MM-DD) and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.date: [datetime.date]}

    def to_database(self, value: datetime.date, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        return value.isoformat() # "YYYY-MM-DD"

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> datetime.date:
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value
        return datetime.date.fromisoformat(str(value))


class MySQLTimeAdapter(SQLTypeAdapter):
    """
    Adapts Python time to MySQL TIME string (HH:MM:SS) and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.time: [datetime.timedelta]}

    def to_database(self, value: datetime.time, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        return value.isoformat(timespec='microseconds') # "HH:MM:SS.ffffff"

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> datetime.time:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        if isinstance(value, timedelta): # Handle timedelta returned by mysql-connector-python
            total_seconds = int(value.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return datetime.time(hours, minutes, seconds, value.microseconds)
        return datetime.time.fromisoformat(str(value))


class MySQLDatetimeAdapter(SQLTypeAdapter):
    """
    Adapts Python datetime to MySQL DATETIME/TIMESTAMP string and vice-versa.
    Normalizes to UTC.
    """

    def __init__(self, mysql_version: Optional[Tuple[int, int, int]] = None):
        """
        Args:
            mysql_version: MySQL server version tuple (major, minor, patch).
                           If None, defaults to (8, 0, 0).
        """
        self._mysql_version = mysql_version or (8, 0, 0)

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.datetime: [datetime.datetime, str]}

    def to_database(self, value: datetime.datetime, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        import sys
        print(f"DEBUG MySQLDatetimeAdapter.to_database: version={self._mysql_version}, value={value}", file=sys.stderr)
        # If the datetime object is timezone-aware, normalize to UTC and make it naive
        # for the database driver, which expects naive datetimes.
        if value.tzinfo is not None:
            utc_dt = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            # MySQL 5.7.8+ supports ISO 8601 format, older versions need traditional format
            print(f"DEBUG: comparison result = {self._mysql_version >= (5, 7, 8)}", file=sys.stderr)
            if self._mysql_version >= (5, 7, 8):
                return utc_dt.isoformat()
            else:
                return utc_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        # If it's already naive, assume it's in the desired timezone (conventionally UTC)
        return value

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> datetime.datetime:
        if value is None:
            return None
        # The driver returns a naive datetime; we assume it's UTC and make it aware.
        # Note: This assumes the MySQL session timezone is set to UTC (+00:00).
        # If your MySQL server uses a different timezone, you should configure
        # time_zone in the connection config or use TIMESTAMP column type.
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=datetime.timezone.utc)
            return value # It's already aware, respect it.
        if isinstance(value, str):
            dt = datetime.datetime.fromisoformat(str(value))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        # Fallback for unexpected types
        return datetime.datetime.fromisoformat(str(value)).replace(tzinfo=datetime.timezone.utc)


class MySQLEnumAdapter(SQLTypeAdapter):
    """
    Adapts Python Enum to MySQL ENUM type and vice-versa.

    MySQL ENUM stores values as integers internally (1, 2, 3...) but displays as strings.
    This adapter supports both string and integer representations.

    By default, uses string representation for better readability and compatibility.
    Can optionally use MySQL's internal integer representation for performance.
    """

    def __init__(self, use_int_storage: bool = False):
        """
        Initialize MySQL ENUM adapter.

        Args:
            use_int_storage: If True, uses integer representation when writing to database
                           (MySQL stores ENUM as 1-based index). If False, uses string
                           representation (default, recommended).
        """
        self._use_int_storage = use_int_storage

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Enum: [str, int]}

    def to_database(self, value: Enum, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        """
        Convert Python Enum to database value.

        Supports three scenarios:
        1. Python Enum -> MySQL VARCHAR/TEXT (default): returns string
        2. Python Enum -> MySQL ENUM field: returns string (same as default)
        3. Python Enum -> MySQL INT: returns integer (requires use_int_storage or int-based enum)

        Args:
            value: Python Enum instance
            target_type: Target database type (str or int)
            options: Optional settings:
                - 'use_int_storage': Override instance setting for this call
                - 'enum_values': List of allowed values for validation
                - 'mysql_enum_type': Set to True if target field is MySQL ENUM type
                  (no behavioral change, but used for documentation/validation)

        Returns:
            str or int representation of the enum

        Raises:
            ValueError: If enum value is not in allowed values
            TypeError: If target_type is not str or int
        """
        if value is None:
            return None

        # Validate against allowed values if provided
        enum_values = options.get('enum_values') if options else None
        if enum_values and value.value not in enum_values:
            raise ValueError(
                f"Invalid enum value '{value.value}'. "
                f"Allowed values: {enum_values}"
            )

        # Note: mysql_enum_type option doesn't change behavior
        # because MySQL ENUM type accepts and returns strings by default
        # This option is just for documentation/validation purposes

        # Determine which representation to use
        use_int = (options.get('use_int_storage', self._use_int_storage)
                   if options else self._use_int_storage)

        if target_type == str:
            # Default: use string representation (enum member value)
            # Works for both VARCHAR and MySQL ENUM fields
            return str(value.value)

        if target_type == int:
            if use_int:
                # Use MySQL's internal integer index (1-based)
                # Get the enum class members in definition order
                enum_members = list(type(value))
                return enum_members.index(value) + 1
            else:
                # Use the enum's value if it's already an int
                if isinstance(value.value, int):
                    return value.value
                raise TypeError(
                    f"Cannot convert string-based enum to int. "
                    f"Set 'use_int_storage=True' to use MySQL internal index, "
                    f"or ensure enum values are integers."
                )

        raise TypeError(
            f"Cannot convert {type(value).__name__} to {target_type.__name__}"
        )

    def from_database(self, value: Any, target_type: Type[Enum], options: Optional[Dict[str, Any]] = None) -> Enum:
        """
        Convert database value to Python Enum.

        Args:
            value: Database value (str or int)
            target_type: Target Python Enum class
            options: Optional settings (currently unused)

        Returns:
            Python Enum instance

        Raises:
            ValueError: If value is invalid for the enum
            TypeError: If value type is not str or int
        """
        if value is None:
            return None

        if isinstance(value, str):
            # Lookup by value (for string enums)
            # First try to match the value directly
            for member in target_type:
                if str(member.value) == value:
                    return member
            # If not found, try name lookup as fallback
            try:
                return target_type[value]
            except KeyError:
                raise ValueError(f"Invalid enum value '{value}'. "
                               f"Valid values: {[m.value for m in target_type]}")

        if isinstance(value, int):
            # Try to interpret as MySQL ENUM index (1-based)
            enum_members = list(target_type)
            if 1 <= value <= len(enum_members):
                return enum_members[value - 1]

            # If out of range, try direct value lookup
            # (in case enum values themselves are integers)
            try:
                return target_type(value)
            except ValueError:
                raise ValueError(
                    f"Invalid enum index {value}. "
                    f"Valid range: 1-{len(enum_members)} or matching enum values"
                )

        raise TypeError(
            f"Cannot convert {type(value).__name__} to {target_type.__name__}"
        )
