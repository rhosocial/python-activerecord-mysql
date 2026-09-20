# src/rhosocial/activerecord/backend/impl/mysql/mixins/charset_collation.py
"""MySQL charset / collation / storage-engine capability implementation.

Implements :class:`~...mysql.protocols.MySQLCharsetCollationSupport`: a
version-aware whitelist of character sets, collations and storage engines,
plus validation helpers used by table/column expressions at construction
time.
"""

from enum import Enum
from typing import FrozenSet, Optional, Tuple, TYPE_CHECKING

from ..collation import (
    MySQLCollationValidator,
    supported_mysql_collations,
    validate_mysql_collation_name,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.collation import CollateExpression

__all__ = [
    "MySQLCharset",
    "MySQLStorageEngine",
    "MySQLCharsetCollationMixin",
]


class MySQLCharset(Enum):
    """MySQL character sets for table/column ``CHARACTER SET``."""

    ARMSCII8 = "armscii8"
    ASCII = "ascii"
    BIG5 = "big5"
    BINARY = "binary"
    CP1250 = "cp1250"
    CP1251 = "cp1251"
    CP1256 = "cp1256"
    CP1257 = "cp1257"
    CP850 = "cp850"
    CP852 = "cp852"
    CP866 = "cp866"
    CP932 = "cp932"
    DEC8 = "dec8"
    EUCJPMS = "eucjpms"
    EUCKR = "euckr"
    GB18030 = "gb18030"
    GB2312 = "gb2312"
    GBK = "gbk"
    GEOSTD8 = "geostd8"
    GREEK = "greek"
    HEBREW = "hebrew"
    HP8 = "hp8"
    KEYBCS2 = "keybcs2"
    KOI8R = "koi8r"
    KOI8U = "koi8u"
    LATIN1 = "latin1"
    LATIN2 = "latin2"
    LATIN5 = "latin5"
    LATIN7 = "latin7"
    MACCE = "macce"
    MACROMAN = "macroman"
    SJIS = "sjis"
    SWE7 = "swe7"
    TIS620 = "tis620"
    UCS2 = "ucs2"
    UJIS = "ujis"
    UTF8 = "utf8"
    UTF8MB3 = "utf8mb3"
    UTF8MB4 = "utf8mb4"
    UTF16 = "utf16"
    UTF16LE = "utf16le"
    UTF32 = "utf32"


class MySQLStorageEngine(Enum):
    """Built-in MySQL storage engines for ``ENGINE=<name>``."""

    INNODB = "InnoDB"
    MYISAM = "MyISAM"
    MEMORY = "MEMORY"
    CSV = "CSV"
    ARCHIVE = "ARCHIVE"
    BLACKHOLE = "BLACKHOLE"
    MRG_MYISAM = "MRG_MyISAM"
    FEDERATED = "FEDERATED"
    NDB = "NDB"
    NDBCLUSTER = "NDBCLUSTER"
    EXAMPLE = "EXAMPLE"
    PERFORMANCE_SCHEMA = "PERFORMANCE_SCHEMA"
    TEMPORARY = "TEMPORARY"


_CHARSET_BY_VALUE = {member.value: member for member in MySQLCharset}
_ENGINE_BY_LOWER = {member.value.lower(): member for member in MySQLStorageEngine}

# Introduced-in server versions for version-gated values.
_CHARSET_MIN_VERSIONS: dict = {
    "utf8mb4": (5, 5, 3),
    "utf8mb3": (8, 0, 28),
}
_ENGINE_MIN_VERSIONS: dict = {}


class MySQLCharsetCollationMixin:
    """Version-aware charset / collation / storage-engine support."""

    def _mysql_capability_version(self) -> Optional[Tuple[int, ...]]:
        # Read the private attribute: the public ``version`` property raises
        # ``DialectNotAdaptedException`` when no version was supplied, but
        # validation only needs the version *if* it is known.
        return getattr(self, "_version", None)

    # --- expression-level COLLATE ---------------------------------------
    def supports_collate_expression(self) -> bool:
        """MySQL supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate a ``CollateExpression`` and return its collation SQL."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        return self.validate_collation_by_name(expr.collation_name)

    # --- charset ---------------------------------------------------------
    def supported_charsets(self) -> FrozenSet[str]:
        version = self._mysql_capability_version()
        return frozenset(
            member.value
            for member in MySQLCharset
            if version is None
            or _CHARSET_MIN_VERSIONS.get(member.value) is None
            or version >= _CHARSET_MIN_VERSIONS[member.value]
        )

    def supports_charset(self, name: object) -> bool:
        try:
            self.validate_charset_name(name)
        except (TypeError, ValueError):
            return False
        return True

    def validate_charset_name(self, name: object) -> str:
        version = self._mysql_capability_version()
        if isinstance(name, MySQLCharset):
            normalized = name.value
        elif isinstance(name, str):
            normalized = name.lower()
        else:
            raise TypeError(
                f"character set must be MySQLCharset or str, got {type(name).__name__}"
            )
        if normalized not in _CHARSET_BY_VALUE:
            raise ValueError(f"Unsupported MySQL character set: {name!r}")
        min_version = _CHARSET_MIN_VERSIONS.get(normalized)
        if version is not None and min_version is not None and version < min_version:
            formatted = ".".join(str(part) for part in min_version[:2])
            raise ValueError(f"MySQL character set requires MySQL {formatted}+: {name!r}")
        return normalized

    # --- collation -------------------------------------------------------
    def supported_collations(self, charset: Optional[str] = None) -> FrozenSet[str]:
        return supported_mysql_collations(self._mysql_capability_version(), charset)

    def supports_collation_name(self, name: str) -> bool:
        return MySQLCollationValidator.is_supported(name, self._mysql_capability_version())

    def validate_collation_by_name(self, name: str) -> str:
        return validate_mysql_collation_name(name, self._mysql_capability_version())

    # --- storage engine --------------------------------------------------
    def supported_storage_engines(self) -> FrozenSet[str]:
        version = self._mysql_capability_version()
        return frozenset(
            member.value
            for member in MySQLStorageEngine
            if version is None
            or _ENGINE_MIN_VERSIONS.get(member.value) is None
            or version >= _ENGINE_MIN_VERSIONS[member.value]
        )

    def supports_storage_engine(self, name: object) -> bool:
        try:
            self.validate_storage_engine_name(name)
        except (TypeError, ValueError):
            return False
        return True

    def validate_storage_engine_name(self, name: object) -> str:
        version = self._mysql_capability_version()
        if isinstance(name, MySQLStorageEngine):
            canonical = name.value
        elif isinstance(name, str):
            member = _ENGINE_BY_LOWER.get(name.lower())
            if member is None:
                raise ValueError(f"Unsupported MySQL storage engine: {name!r}")
            canonical = member.value
        else:
            raise TypeError(
                f"storage engine must be MySQLStorageEngine or str, "
                f"got {type(name).__name__}"
            )
        min_version = _ENGINE_MIN_VERSIONS.get(canonical)
        if version is not None and min_version is not None and version < min_version:
            formatted = ".".join(str(part) for part in min_version[:2])
            raise ValueError(f"MySQL storage engine requires MySQL {formatted}+: {name!r}")
        return canonical
