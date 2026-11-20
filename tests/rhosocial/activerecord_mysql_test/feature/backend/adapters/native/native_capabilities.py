# tests/rhosocial/activerecord_mysql_test/feature/backend/adapters/native/native_capabilities.py
"""Capability gates for the native-type tests the dialect cannot answer.

The dialect owns the version boundaries for the SQL types these tests use
(``supports_json_type`` for ``JSON``, ``supports_vector_type`` for ``VECTOR``),
so the fixtures ask it and the skip reason names the probe.  What is left here
is the one question no dialect probe answers: whether the server ships
``UUID_TO_BIN`` / ``BIN_TO_UUID``, which the UUID tests read to compare the two
carriers.  Below 8.0.0 MySQL answers ``1305 (42000): FUNCTION ... does not
exist``.
"""

from typing import Tuple

#: ``UUID_TO_BIN`` / ``BIN_TO_UUID`` first shipped in MySQL 8.0.0.
UUID_FUNCTIONS_MIN_VERSION: Tuple[int, ...] = (8, 0, 0)


def server_version(database) -> Tuple[int, ...]:
    """The scenario server's version, as reported after introspection."""
    version = getattr(database.dialect, "version", None)
    return tuple(version) if version else ()


def format_version(version: Tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version) or "unknown"


def supports_uuid_functions(database) -> bool:
    """Whether the server has ``UUID_TO_BIN`` and ``BIN_TO_UUID``."""
    return server_version(database) >= UUID_FUNCTIONS_MIN_VERSION


def uuid_functions_skip_reason(database) -> str:
    """A skip reason that names what the environment is missing."""
    return (
        f"environment: server reports MySQL {format_version(server_version(database))}; "
        f"UUID_TO_BIN/BIN_TO_UUID require >= {format_version(UUID_FUNCTIONS_MIN_VERSION)}"
    )
