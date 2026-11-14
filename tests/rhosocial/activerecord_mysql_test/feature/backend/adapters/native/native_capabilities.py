# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/native_capabilities.py
"""Server-version probes the native-type tests gate on.

Every probe answers "what does this server have", never "does MySQL support
this": a missing capability is an environment fact and the skip reason has to
say which one (plan §4.1 item 2 and §4.12).
"""

from typing import Tuple

#: VECTOR first shipped in MySQL 9.0 as a general-availability type.
VECTOR_MIN_VERSION: Tuple[int, ...] = (9, 0, 0)


def server_version(database) -> Tuple[int, ...]:
    """The scenario server's version, as reported after introspection."""
    version = getattr(database.dialect, "version", None)
    return tuple(version) if version else ()


def format_version(version: Tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version) or "unknown"


def supports_vector(database) -> bool:
    """Whether the server has the ``VECTOR`` type."""
    return server_version(database) >= VECTOR_MIN_VERSION


def vector_skip_reason(database) -> str:
    """A skip reason that names what the environment is missing."""
    return (
        f"environment: server reports MySQL {format_version(server_version(database))}; "
        f"VECTOR requires >= {format_version(VECTOR_MIN_VERSION)} (plan §4.3)"
    )
