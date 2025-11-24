# src/rhosocial/activerecord/backend/impl/mysql/adapters.py
import datetime
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Type, Union, Optional
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
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.datetime: [datetime.datetime]}

    def to_database(self, value: datetime.datetime, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        # If the datetime object is timezone-aware, normalize to UTC and make it naive
        # for the database driver, which expects naive datetimes.
        if value.tzinfo is not None:
            return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        # If it's already naive, assume it's in the desired timezone (conventionally UTC)
        return value

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> datetime.datetime:
        if value is None:
            return None
        # The driver returns a naive datetime; we assume it's UTC and make it aware.
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value # It's already aware, respect it.
        if isinstance(value, str):
            dt = datetime.datetime.fromisoformat(str(value))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        # Fallback for unexpected types
        return datetime.datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)
