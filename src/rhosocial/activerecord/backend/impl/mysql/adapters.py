# src/rhosocial/activerecord/backend/impl/mysql/adapters.py
import datetime
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Type, Union

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class MySQLBlobAdapter(SQLTypeAdapter):
    """
    Adapts Python bytes to MySQL BLOB and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bytes: ["BLOB", "TINYBLOB", "MEDIUMBLOB", "LONGBLOB"]}

    def to_database(self, value: bytes, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        return value

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> bytes:
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
        return {dict: ["JSON", "TEXT"], list: ["JSON", "TEXT"]}

    def to_database(self, value: Union[dict, list], target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        # MySQL JSON type often stores as TEXT, so we serialize to string
        return json.dumps(value, ensure_ascii=False)

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> Union[dict, list]:
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
        return {uuid.UUID: ["CHAR(36)", "VARCHAR(36)", "TEXT"]}

    def to_database(self, value: uuid.UUID, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        return str(value)

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> uuid.UUID:
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
        # MySQL typically uses TINYINT(1) for boolean
        return {bool: ["TINYINT(1)", "BOOLEAN", "BIT(1)", "SMALLINT", "INT"]}

    def to_database(self, value: bool, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        return 1 if value else 0

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> bool:
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
        # DECIMAL, NUMERIC are native, but sometimes float or string can be used
        return {Decimal: ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "VARCHAR", "TEXT"]}

    def to_database(self, value: Decimal, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        # Convert to string to preserve precision if target is not a true DECIMAL type
        # Or let driver handle native Decimal for DECIMAL/NUMERIC types
        if target_type in ["FLOAT", "DOUBLE"]:
            return float(value)
        return str(value) # Default to string to avoid float precision issues

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> Decimal:
        if value is None:
            return None
        # MySQL connector might return str, float or already Decimal
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class MySQLDateAdapter(SQLTypeAdapter):
    """
    Adapts Python date to MySQL DATE string (YYYY-MM-DD) and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.date: ["DATE", "DATETIME", "TIMESTAMP", "VARCHAR", "TEXT"]}

    def to_database(self, value: datetime.date, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        return value.isoformat() # "YYYY-MM-DD"

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> datetime.date:
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
        return {datetime.time: ["TIME", "DATETIME", "TIMESTAMP", "VARCHAR", "TEXT"]}

    def to_database(self, value: datetime.time, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        return value.isoformat(timespec='microseconds') # "HH:MM:SS.ffffff"

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> datetime.time:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        return datetime.time.fromisoformat(str(value))


class MySQLDatetimeAdapter(SQLTypeAdapter):
    """
    Adapts Python datetime to MySQL DATETIME/TIMESTAMP string and vice-versa.
    """
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.datetime: ["DATETIME", "TIMESTAMP", "VARCHAR", "TEXT"]}

    def to_database(self, value: datetime.datetime, target_type: Type, options: Dict[str, Any]) -> Any:
        if value is None:
            return None
        # MySQL handles native datetime objects well, but ISO format is a safe fallback
        return value.isoformat(timespec='microseconds')

    def from_database(self, value: Any, target_type: Type, options: Dict[str, Any]) -> datetime.datetime:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value
        return datetime.datetime.fromisoformat(str(value))
