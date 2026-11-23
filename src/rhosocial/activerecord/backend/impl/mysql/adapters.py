# src/rhosocial/activerecord/backend/impl/mysql/adapters.py
import datetime
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from rhosocial.activerecord.backend.adapters import (
    BitString,
    BitStringAdapterBase,
    Geometry,
    GeometryAdapterBase,
    IPAddress,
    IPAddressAdapterBase,
    MacAddress,
    MacAddressAdapterBase,
    Multirange,
    Range,
    RangeAdapterBase,
    Vector,
    VectorAdapterBase,
)
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter

from .mixins.vector import MySQLVectorMixin


class MySQLBlobAdapter(SQLTypeAdapter):
    """
    Adapts Python bytes to MySQL BLOB and vice-versa.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bytes: [bytes]}

    def to_database(
        self, value: bytes, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return value

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[bytes]:
        if value is None:
            return None
        # MySQL connector usually returns bytes directly for BLOB types
        return value


class MySQLJSONAdapter(SQLTypeAdapter):
    """
    Adapts Python dict/list to MySQL JSON and vice-versa.
    Serializes to JSON string when writing, deserializes from JSON string when reading.

    ``default`` / ``object_hook`` are forwarded to ``json.dumps`` / ``json.loads``
    so callers can plug in neutral-type codecs (see
    ``rhosocial.activerecord.backend.adapters.json_codec``) without changing the
    default behaviour.
    """

    def __init__(self, default=None, object_hook=None):
        self._json_default = default
        self._json_object_hook = object_hook

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {dict: [str], list: [str]}

    def to_database(
        self, value: Union[dict, list], target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        # MySQL JSON type often stores as TEXT, so we serialize to string
        return json.dumps(value, ensure_ascii=False, default=self._json_default)

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[Union[dict, list]]:
        if value is None:
            return None
        # MySQL connector might return str for JSON, or already dict/list for some drivers
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value, object_hook=self._json_object_hook)


class MySQLUUIDAdapter(SQLTypeAdapter):
    """
    Adapts Python UUID to MySQL and vice-versa.

    Two carriers are supported, because MySQL has no UUID type and both are in
    use: the canonical text in ``CHAR(36)`` (target ``str``) and the raw 16
    bytes in ``BINARY(16)`` (target ``bytes``).  ``UUID_TO_BIN``/``BIN_TO_UUID``
    are the server-side spellings of the same pair.
    """

    #: A UUID is 128 bits; the binary carrier is exactly this many bytes.
    BYTE_LENGTH = 16

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {uuid.UUID: [str, bytes]}

    def to_database(
        self, value: uuid.UUID, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        if target_type is bytes:
            return value.bytes
        return str(value)

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[uuid.UUID]:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, (bytes, bytearray)):
            data = bytes(value)
            if len(data) != self.BYTE_LENGTH:
                raise ValueError(
                    f"binary UUID carrier must be {self.BYTE_LENGTH} bytes, got {len(data)}"
                )
            return uuid.UUID(bytes=data)
        return uuid.UUID(value)


class MySQLBooleanAdapter(SQLTypeAdapter):
    """
    Adapts Python bool to MySQL TINYINT(1) (or similar integer type) and vice-versa.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {bool: [int]}

    def to_database(
        self, value: bool, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return 1 if value else 0

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[bool]:
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

    def to_database(
        self, value: Decimal, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        if target_type is Decimal:
            return value
        if target_type is float:
            return float(value)
        if target_type is str:
            return str(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[Decimal]:
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

    def to_database(
        self, value: datetime.date, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return value.isoformat()  # "YYYY-MM-DD"

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[datetime.date]:
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value
        return datetime.date.fromisoformat(str(value))


class MySQLTimeAdapter(SQLTypeAdapter):
    """
    Adapts Python time to MySQL TIME string (HH:MM:SS) and vice-versa.

    MySQL connector-python returns timedelta for TIME columns, but accepts
    string format for insertion. This adapter handles both cases.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {datetime.time: [datetime.timedelta, str]}

    def to_database(
        self, value: datetime.time, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return value.isoformat(timespec="microseconds")  # "HH:MM:SS.ffffff"

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[datetime.time]:
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        if isinstance(value, timedelta):  # Handle timedelta returned by mysql-connector-python
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

    def to_database(
        self, value: datetime.datetime, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        # If the datetime object is timezone-aware, normalize to UTC and make it naive
        # for the database driver, which expects naive datetimes.
        if value.tzinfo is not None:
            utc_dt = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            # MySQL 5.7.8+ supports ISO 8601 format, older versions need traditional format
            if self._mysql_version >= (5, 7, 8):
                return utc_dt.isoformat()
            else:
                return utc_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        # If it's already naive, assume it's in the desired timezone (conventionally UTC)
        return value

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[datetime.datetime]:
        if value is None:
            return None
        # The driver returns a naive datetime; we assume it's UTC and make it aware.
        # Note: This assumes the MySQL session timezone is set to UTC (+00:00).
        # If your MySQL server uses a different timezone, you should configure
        # time_zone in the connection config or use TIMESTAMP column type.
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=datetime.timezone.utc)
            return value  # It's already aware, respect it.
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

    def to_database(
        self, value: Enum, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
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
        enum_values = options.get("enum_values") if options else None
        if enum_values and value.value not in enum_values:
            raise ValueError(f"Invalid enum value '{value.value}'. Allowed values: {enum_values}")

        # Note: mysql_enum_type option doesn't change behavior
        # because MySQL ENUM type accepts and returns strings by default
        # This option is just for documentation/validation purposes

        # Determine which representation to use
        use_int = (
            options.get("use_int_storage", self._use_int_storage)
            if options
            else self._use_int_storage
        )

        if target_type is str:
            # Default: use string representation (enum member value)
            # Works for both VARCHAR and MySQL ENUM fields
            return str(value.value)

        if target_type is int:
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
                    "Cannot convert string-based enum to int. "
                    "Set 'use_int_storage=True' to use MySQL internal index, "
                    "or ensure enum values are integers."
                )

        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")

    def from_database(
        self,
        value: Any,
        target_type: Type[Enum],
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[Enum]:
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
                raise ValueError(
                    f"Invalid enum value '{value}'. Valid values: {[m.value for m in target_type]}"
                ) from None

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
                    f"Invalid enum index {value}. Valid range: 1-{len(enum_members)} or matching enum values"
                ) from None

        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")


class MySQLSetAdapter(SQLTypeAdapter):
    """
    Adapts Python set/frozenset to MySQL SET type and vice-versa.

    MySQL SET is a string object that can have zero or more values,
    each chosen from a predefined list. Values are stored as integers
    (bit flags) internally but displayed/queried as comma-separated strings.

    Features:
    - Maximum 64 members (bit flags in BIGINT)
    - Values are automatically sorted on storage
    - Supports FIND_IN_SET and LIKE operations
    """

    def __init__(self, allowed_values: Optional[List[str]] = None):
        """
        Initialize MySQL SET adapter.

        Args:
            allowed_values: Optional list of allowed SET values for validation.
                           If None, no validation is performed during conversion.
        """
        self._allowed_values = allowed_values

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {set: [str], frozenset: [str]}

    def to_database(
        self,
        value: Union[set, frozenset],
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Convert Python set/frozenset to MySQL SET string.

        Args:
            value: Python set or frozenset
            target_type: Target database type (str)
            options: Optional settings:
                - 'allowed_values': Override instance allowed values for validation

        Returns:
            Comma-separated string of sorted values

        Raises:
            ValueError: If values exceed 64 members or contain invalid values
            TypeError: If target_type is not str
        """
        if value is None:
            return None

        if target_type is not str:
            raise TypeError(
                f"MySQL SET adapter only supports str target type, got {target_type.__name__}"
            )

        if len(value) > 64:
            raise ValueError(f"MySQL SET supports maximum 64 members, got {len(value)}")

        # Get allowed values from options or instance
        allowed_values = (
            options.get("allowed_values", self._allowed_values) if options else self._allowed_values
        )

        if allowed_values is not None:
            invalid_values = [v for v in value if v not in allowed_values]
            if invalid_values:
                raise ValueError(
                    f"Invalid SET values: {invalid_values}. Allowed values: {allowed_values}"
                )

        # MySQL automatically sorts SET values on storage
        sorted_values = sorted(str(v) for v in value)
        return ",".join(sorted_values) if sorted_values else ""

    def _decode_set_from_int(
        self, value: int, target_type: Type, allowed_values: Optional[List[str]]
    ) -> Union[set, frozenset]:
        """
        Decode MySQL SET from integer bit flags.

        Args:
            value: Integer bit flags
            target_type: Target Python type (set or frozenset)
            allowed_values: List of allowed values for decoding

        Returns:
            Python set or frozenset

        Raises:
            ValueError: If allowed_values is not provided
        """
        if allowed_values is None:
            raise ValueError(
                "Cannot decode SET from integer without allowed_values. "
                "Provide allowed_values in constructor or options."
            )

        result = set()
        for i, val in enumerate(allowed_values):
            if value & (1 << i):
                result.add(val)

        return frozenset(result) if target_type is frozenset else result

    def _decode_set_from_string(self, value: str, target_type: Type) -> Union[set, frozenset]:
        """
        Decode MySQL SET from comma-separated string.

        Args:
            value: Comma-separated string
            target_type: Target Python type (set or frozenset)

        Returns:
            Python set or frozenset
        """
        if not value:
            result = set()
        else:
            result = set(value.split(","))
        return frozenset(result) if target_type is frozenset else result

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[Union[set, frozenset]]:
        """
        Convert a MySQL SET value to Python set/frozenset.

        Args:
            value: Database value -- the driver's native ``set``, or the
                comma-separated string / bit-flag integer other callers hand back
            target_type: Target Python type (set or frozenset)
            options: Optional settings (currently unused)

        Returns:
            Python set or frozenset

        Raises:
            TypeError: If target_type is not set or frozenset
        """
        if value is None:
            return None

        # mysql-connector-python returns a native Python set for a SET column;
        # the earlier string/int branches cover the wire forms other callers
        # (and the same driver for older server series) hand back.
        if isinstance(value, (set, frozenset)):
            members = set(value)
            return frozenset(members) if target_type is frozenset else members

        # Handle integer storage (bit flags)
        if isinstance(value, int):
            allowed_values = self._allowed_values or (
                options.get("allowed_values") if options else None
            )
            return self._decode_set_from_int(value, target_type, allowed_values)

        # Handle string storage (comma-separated)
        if isinstance(value, str):
            return self._decode_set_from_string(value, target_type)

        raise TypeError(f"Cannot convert {type(value).__name__} to {target_type.__name__}")


class MySQLVectorAdapter(SQLTypeAdapter):
    """
    Adapts Python list of floats to MySQL VECTOR type and vice-versa.

    MySQL VECTOR type (9.0+) is used for AI/ML applications to store
    multi-dimensional vectors. Supports up to 16,384 dimensions.

    Storage format:
    - Binary format internally (optimized for similarity operations)
    - Can be read/written as string representation '[1.0,2.0,3.0]'

    Supported distance functions:
    - DISTANCE_EUCLIDEAN: Euclidean (L2) distance
    - DISTANCE_COSINE: Cosine similarity distance
    - DISTANCE_DOT: Dot product distance
    """

    # Maximum dimension supported by MySQL 9.0. Read from the mixin that also
    # enforces it at format time: one limit, two readers, and a second literal
    # here would be a second place to move when the engine's limit changes.
    MAX_VECTOR_DIMENSION = MySQLVectorMixin.MAX_VECTOR_DIMENSION

    def __init__(self, dimension: Optional[int] = None):
        """
        Initialize VECTOR adapter.

        Args:
            dimension: Optional expected vector dimension for validation.
                      If None, no dimension validation is performed.
        """
        self._dimension = dimension

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        # list[float] -> VECTOR (stored as binary or string)
        return {list: [bytes, str]}

    def to_database(
        self, value: List[float], target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Convert Python list of floats to MySQL VECTOR format.

        Args:
            value: List of float values
            target_type: Target database type (bytes or str)
            options: Optional settings:
                - 'dimension': Override expected dimension for validation

        Returns:
            String representation '[v1,v2,...]' or binary format

        Raises:
            ValueError: If dimension exceeds maximum or doesn't match expected
            TypeError: If value contains non-float elements
        """
        if value is None:
            return None

        dimension = options.get("dimension", self._dimension) if options else self._dimension

        if len(value) > self.MAX_VECTOR_DIMENSION:
            raise ValueError(
                f"Vector dimension {len(value)} exceeds maximum supported dimension {self.MAX_VECTOR_DIMENSION}"
            )

        if dimension is not None and len(value) != dimension:
            raise ValueError(
                f"Vector dimension {len(value)} doesn't match expected dimension {dimension}"
            )

        # Validate all elements are floats or can be converted
        for i, v in enumerate(value):
            if not isinstance(v, (int, float)):
                raise TypeError(f"Vector element at index {i} is not a number: {type(v).__name__}")

        # MySQL accepts string format '[1.0,2.0,3.0]' for VECTOR
        # or use STRING_TO_VECTOR function
        vector_str = "[" + ",".join(str(float(v)) for v in value) + "]"

        if target_type is bytes:
            return vector_str.encode("utf-8")
        return vector_str

    def _decode_vector_from_bytes(self, value: bytes) -> List[float]:
        """
        Decode MySQL VECTOR from binary format.

        Args:
            value: Binary data (either UTF-8 encoded string or packed floats)

        Returns:
            List of float values

        Raises:
            ValueError: If binary format is invalid
        """
        # Try UTF-8 decode first (string format stored as bytes)
        try:
            return self._decode_vector_from_string(value.decode("utf-8"))
        except UnicodeDecodeError:
            pass

        # Binary format: packed IEEE 754 float32 values (little-endian)
        import struct

        float_count = len(value) // 4
        if len(value) % 4 != 0:
            raise ValueError(
                f"Invalid VECTOR binary length: {len(value)} bytes (must be multiple of 4 for float32 values)"
            ) from None
        return list(struct.unpack(f"<{float_count}f", value))

    def _decode_vector_from_string(self, value: str) -> List[float]:
        """
        Decode MySQL VECTOR from string format.

        Args:
            value: String representation like '[1.0,2.0,3.0]'

        Returns:
            List of float values

        Raises:
            ValueError: If string cannot be parsed
        """
        # Remove brackets and split
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]

        if not value:
            return []

        # Split by comma and convert to floats
        try:
            return [float(v.strip()) for v in value.split(",")]
        except ValueError as e:
            raise ValueError(f"Cannot parse VECTOR value: {value}") from e

    def from_database(
        self,
        value: Any,
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[List[float]]:
        """
        Convert MySQL VECTOR to Python list of floats.

        Args:
            value: Database value (bytes, str, or already parsed list)
            target_type: Target Python type (list)
            options: Optional settings (currently unused)

        Returns:
            List of float values

        Raises:
            TypeError: If target_type is not list
            ValueError: If value cannot be parsed
        """
        if value is None:
            return None

        if target_type is not list:
            raise TypeError(
                f"MySQL VECTOR adapter only supports list target type, got {target_type.__name__}"
            )

        # Already a list (some drivers might parse it)
        if isinstance(value, list):
            return [float(v) for v in value]

        # Binary format
        if isinstance(value, bytes):
            return self._decode_vector_from_bytes(value)

        # String format
        if isinstance(value, str):
            return self._decode_vector_from_string(value)

        raise TypeError(f"Cannot convert {type(value).__name__} to vector (list of floats)")


# ---------------------------------------------------------------------------
# Neutral-type adapters (their neutral types live in the core package)
# ---------------------------------------------------------------------------
#
# MySQL has no range, MAC address or IP address column types, so those
# adapters carry their values in TEXT/BINARY columns. The spatial types are
# native to the server, but the adapter deliberately speaks WKT text rather
# than the server's internal binary geometry layout (see MySQLGeometryAdapter).


class MySQLGeometryAdapter(GeometryAdapterBase):
    """Carries neutral :class:`Geometry` values as WKT text.

    **This is not native geometry binding.** The adapter emits plain WKT, with
    an ``SRID=<n>;`` prefix when an SRID is known, and binds it as ``str``
    (or UTF-8 ``bytes``). It does not wrap the value in ``ST_GeomFromText``.

    Consequences, stated plainly rather than implied:

    * Whether a bound WKT string is accepted by a ``POINT``/``GEOMETRY`` column
      depends on the server's implicit string-to-geometry conversion. That
      conversion is **not** guaranteed for parameter placeholders. When the
      server rejects it, the value must go through
      ``ST_GeomFromText(?, srid)`` at the expression layer. No live-server
      verification of plain-text binding was done in this change.
    * ``SRID=n;`` is the EWKT spelling. MySQL's own spatial functions normally
      take the SRID as a second argument (``ST_GeomFromText(wkt, srid)``), so
      an EWKT-prefixed string is only usable where the server parses the
      prefix itself.
    * ``_decode`` reads WKT text only. MySQL drivers commonly return geometry
      columns in the server's internal binary format; that is not WKT and is
      rejected with :class:`TypeConversionError`. Select ``ST_AsText(col)``
      to read a geometry column through this adapter.

    Use this adapter when a WKT/TEXT carrier is acceptable, and treat native
    spatial-column round-trips as a follow-up (see the backend type-adapter
    plan's MySQL spatial gap).
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Geometry: [str]}

    def _effective_srid(self, geometry: Geometry, options: Dict[str, Any]) -> Optional[int]:
        """Column SRID from the options, unless the value carries its own."""
        if geometry.srid is not None:
            return geometry.srid
        srid = options.get("srid")
        if srid is None:
            return None
        if isinstance(srid, bool) or not isinstance(srid, int):
            self._conversion_error(geometry, "srid option must be int or None")
        if srid < 0:
            self._conversion_error(geometry, f"srid must be non-negative, got {srid}")
        return srid

    def _encode(self, geometry: Geometry, target_type: Type, options: Dict[str, Any]) -> Any:
        if target_type is not str and target_type is not bytes:
            raise TypeError(
                f"WKT text can only be bound as str or bytes, got {target_type.__name__}"
            )
        text = geometry.to_wkt()
        srid = self._effective_srid(geometry, options)
        if srid is not None:
            text = f"SRID={srid};{text}"
        if target_type is bytes:
            return text.encode("utf-8")
        return text

    def _decode(self, value: Any, options: Dict[str, Any]) -> Geometry:
        if isinstance(value, Geometry):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                text = bytes(value).decode("utf-8")
            except UnicodeDecodeError:
                self._conversion_error(
                    value,
                    "driver returned binary geometry (not WKT text); "
                    "select ST_AsText(col) or bind a WKT string",
                )
        elif isinstance(value, str):
            text = value
        else:
            raise TypeError(f"expected WKT str or UTF-8 bytes, got {type(value).__name__}")

        return Geometry.from_wkt(text, srid=options.get("srid"))


class MySQLNeutralVectorAdapter(VectorAdapterBase):
    """Adapts neutral :class:`Vector` values to MySQL ``VECTOR``/TEXT columns.

    MySQL's ``VECTOR`` type is a MySQL 9.0+ native type; older servers and
    TEXT/JSON carriers store the same textual form. This adapter reuses the
    wire format already defined by :class:`MySQLVectorAdapter`
    (``'[1.0,2.0,3.0]'``, or that text UTF-8 encoded when the target is
    ``bytes``), so there is exactly one format definition in this module.

    The pre-existing :class:`MySQLVectorAdapter` remains the ``list``-based
    adapter and is **not** registered: it claims ``list`` -> ``str``, which
    would silently replace ``MySQLJSONAdapter`` for every JSON list column.
    This neutral adapter registers only ``Vector`` -> ``str``/``bytes``.
    """

    def __init__(self, dimension: Optional[int] = None):
        super().__init__()
        self._dimension = dimension
        self._format = MySQLVectorAdapter(dimension)

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Vector: [str, bytes]}

    def _encode(self, vector: Vector, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        if target_type is not str and target_type is not bytes:
            raise TypeError(
                f"VECTOR text can only be bound as str or bytes, got {target_type.__name__}"
            )
        return self._format.to_database(list(vector.values), target_type, options)

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> Vector:
        if isinstance(value, Vector):
            return value
        decoded = self._format.from_database(value, list, options)
        return Vector.from_json_value(decoded)


class MySQLBitStringAdapter(BitStringAdapterBase):
    """Adapts neutral :class:`BitString` values to MySQL ``BIT``/binary columns.

    Encoding targets:

    * ``bytes`` -- the significant bits as a **big-endian unsigned number**,
      right-aligned (`to_int().to_bytes(ceil(n/8))`). MySQL interprets a binary
      parameter bound to ``BIT(n)`` as that number, so this form works for
      any width; for widths that are multiples of 8 it is identical to
      :attr:`BitString.data`. (``data`` itself pads the low bits of the last
      byte, which is right for a raw bit-preserving byte carrier but reads as
      a larger number to ``BIT(n)``: 13 bits worth ``0xA068`` is 41064, not
      5133.)
    * ``int`` -- :meth:`BitString.to_int`, the significant bits as an integer.
    * ``str`` -- :meth:`BitString.to_bits`, e.g. ``"10101"``. MySQL accepts a
      ``b'...'`` *literal* in SQL, not a text bind parameter, so the text form
      is a carrier, not a value this column accepts.

    Decoding reads bytes/int as a big-endian unsigned number and takes the
    declared width as the significant bits. A width can come from the
    constructor (``bit_length=...``) or per-call ``options={"bit_length": n}``.

    **A declared width is required to restore leading zeros** when the column
    width is not a multiple of 8; without one, decoding assumes the whole
    byte length is significant (``8 * len(data)`` bits), which is correct for
    BLOB carriers and for ``BIT(n)`` with ``n % 8 == 0`` only. The adapter
    cannot read the width back from the value, because a ``BIT`` value carries
    no length metadata.
    """

    def __init__(self, bit_length: Optional[int] = None):
        super().__init__()
        if bit_length is not None:
            if isinstance(bit_length, bool) or not isinstance(bit_length, int):
                raise TypeError(f"bit_length must be int or None, got {type(bit_length).__name__}")
            if bit_length < 1:
                raise ValueError(f"bit_length must be at least 1, got {bit_length}")
        self._bit_length = bit_length

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {BitString: [bytes, int, str]}

    def _resolve_bit_length(self, options: Optional[Dict[str, Any]]) -> Optional[int]:
        length = self._bit_length
        if options and "bit_length" in options:
            length = options["bit_length"]
        if length is not None:
            if isinstance(length, bool) or not isinstance(length, int):
                raise TypeError(f"bit_length option must be int, got {type(length).__name__}")
            if length < 1:
                raise ValueError(f"bit_length option must be at least 1, got {length}")
        return length

    def _encode(self, bits: BitString, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        if target_type is bytes:
            # Big-endian unsigned value, right-aligned: a binary parameter binds
            # as the number MySQL compares against BIT(n), and `data` would pad
            # the low end (turning 13 bits into a larger number).
            return bits.to_int().to_bytes((bits.bit_length + 7) // 8, "big")
        if target_type is int:
            return bits.to_int()
        if target_type is str:
            return bits.to_bits()
        raise TypeError(
            f"BIT values can only be bound as bytes, int or str, got {target_type.__name__}"
        )

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> BitString:
        if isinstance(value, BitString):
            return value
        length = self._resolve_bit_length(options)
        if isinstance(value, (bytes, bytearray)):
            data = bytes(value)
            if not data:
                raise ValueError("BIT/BLOB value is empty bytes")
            number = int.from_bytes(data, "big")
            return BitString.from_int(number, length if length is not None else len(data) * 8)
        if isinstance(value, int) and not isinstance(value, bool):
            if value < 0:
                raise ValueError(f"BIT value must be non-negative, got {value}")
            if length is None:
                raise ValueError("a declared bit_length is required to decode an int BIT value")
            return BitString.from_int(value, length)
        if isinstance(value, str):
            return BitString.from_bits(value)
        raise TypeError(f"expected bytes, int or bit text, got {type(value).__name__}")


class MySQLRangeAdapter(RangeAdapterBase):
    """Carries neutral :class:`Range`/:class:`Multirange` as JSON text.

    MySQL has no range column type, so values live in ``TEXT``/``JSON``
    columns. The payload is :meth:`Range.to_json_value` /
    :meth:`Multirange.to_json_value` (lossless, including ``element_type``).

    Multirange values require the target type to be ``Multirange`` or an
    untyped target; a bare JSON array cannot be restored as a ``Range``.
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Range: [str], Multirange: [str]}

    def _encode(
        self, value: Union[Range, Multirange], target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type is not str and target_type is not bytes:
            raise TypeError(
                f"range JSON text can only be bound as str or bytes, got {target_type.__name__}"
            )
        text = json.dumps(value.to_json_value(), ensure_ascii=False, separators=(",", ":"))
        if target_type is bytes:
            return text.encode("utf-8")
        return text

    def _decode(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Union[Range, Multirange]:
        if isinstance(value, (Range, Multirange)):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                value = bytes(value).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"range JSON text is not UTF-8: {exc}") from exc
        if isinstance(value, str):
            value = json.loads(value)
        if target_type is Range:
            return Range.from_json_value(value)
        if target_type is Multirange:
            return Multirange.from_json_value(value)
        if isinstance(value, dict):
            return Range.from_json_value(value)
        if isinstance(value, (list, tuple)):
            return Multirange.from_json_value(value)
        raise TypeError(f"expected range JSON object or array, got {type(value).__name__}")


class MySQLMacAddressAdapter(MacAddressAdapterBase):
    """Adapts neutral :class:`MacAddress` to text/binary MySQL columns.

    MySQL has no MAC address column type. The canonical text form (lowercase,
    colon separated) is used for ``CHAR``/``VARCHAR`` columns; the raw 6/8
    octets are used when the target is ``bytes`` (``BINARY``/``VARBINARY``).
    """

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {MacAddress: [str, bytes]}

    def _encode(self, mac: MacAddress, target_type: Type, options: Optional[Dict[str, Any]]) -> Any:
        if target_type is str:
            return str(mac)
        if target_type is bytes:
            return mac.octets
        raise TypeError(
            f"MAC address can only be bound as str or bytes, got {target_type.__name__}"
        )

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> MacAddress:
        if isinstance(value, MacAddress):
            return value
        if isinstance(value, (str, bytes, bytearray, int)) and not isinstance(value, bool):
            return MacAddress.parse(value)
        raise TypeError(f"expected MAC address text or bytes, got {type(value).__name__}")


class MySQLIPAddressAdapter(IPAddressAdapterBase):
    """Adapts neutral :class:`IPAddress` to a canonical-text MySQL column.

    MySQL has no IP address column type, so the address is carried in text:
    the compressed canonical form (``192.0.2.1`` / ``2001:db8::1``) fits a
    ``VARCHAR(45)`` for both IPv4 and IPv6. The core
    :class:`~rhosocial.activerecord.backend.adapters.IPAddressAdapterBase`
    handles coercion and conversion errors; this class only spells the wire
    format.
    """

    def __init__(self):
        super().__init__()
        self.register_type(IPAddress, str)

    def _encode(
        self, ip_addr: IPAddress, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> str:
        return str(ip_addr)

    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> IPAddress:
        return IPAddress.parse(self._require_text(value))
