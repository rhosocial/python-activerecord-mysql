# tests/rhosocial/activerecord_mysql_test/feature/rules/backend/conftest.py
"""Fixtures for MySQL's own rule suite.

MySQL is a standalone backend repository; unlike core's co-located SQLite it is
not part of core's generic rules. Every path is derived from the installed
packages, and ``source_roots`` names a single root: ``backend/impl/mysql``.
The shared rule library supplies the assertions; this conftest selects the
subject.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from rhosocial.activerecord.testsuite.feature.rules.backend.conftest import *  # noqa: F401,F403
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    uses_database=False,
    parallel=False,
    purpose="Executable assertions of the MySQL backend's formal constraints",
    passes_means="MySQL source obeys the mechanical and structural rule",
    fails_means="MySQL source introduces a forbidden construct or dependency",
)


def _python_files(root: Path) -> List[Path]:
    """Sorted Python files below *root*, excluding bytecode caches."""
    if not root.is_dir():
        return []
    return [path for path in sorted(root.rglob("*.py")) if "__pycache__" not in path.parts]


def mysql_expression_package() -> object:
    """The installed MySQL expression package."""
    return importlib.import_module("rhosocial.activerecord.backend.impl.mysql.expression")


def mysql_impl_root() -> Path:
    """The installed ``backend/impl/mysql`` directory."""
    package = mysql_expression_package()
    for search_path in vars(package).get("__path__", ()):
        current = Path(search_path).resolve()
        for candidate in [current] + list(current.parents):
            if candidate.name == "impl" and candidate.parent.name == "backend":
                return candidate / current.relative_to(candidate).parts[0]
    pytest.skip("MySQL impl root is not discoverable from the installed package")


def mysql_project_root() -> Path:
    """Project root inferred from the installed MySQL package layout."""
    for candidate in [mysql_impl_root()] + list(mysql_impl_root().parents):
        if (candidate / "tests").is_dir() and (candidate / "src").is_dir():
            return candidate
    pytest.skip("MySQL project root is not discoverable from the installed package")


@pytest.fixture
def backend_expression_package() -> object:
    """MySQL's expression package."""
    return mysql_expression_package()


@pytest.fixture
def backend_dialect() -> object:
    """An instantiated MySQL dialect."""
    from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

    return MySQLDialect()


@pytest.fixture
def backend_prefix() -> str:
    """MySQL's own naming prefix."""
    return "MySQL"


@pytest.fixture
def backend_impl_root() -> Path:
    """The MySQL ``impl`` root used by file-driven shared rules."""
    return mysql_impl_root()


@pytest.fixture
def source_roots() -> List[Tuple[str, Path]]:
    """One root only: the MySQL backend, never core or another backend."""
    return [("mysql", mysql_impl_root())]


@pytest.fixture
def backend_project_root() -> Path:
    """Project root for MySQL's tests."""
    return mysql_project_root()


@pytest.fixture
def backend_test_files(backend_project_root) -> List[Path]:
    """Every Python test file in the MySQL project."""
    files = _python_files(backend_project_root / "tests")
    assert files, f"no test files under {backend_project_root / 'tests'}"
    return files


@pytest.fixture
def backend_matrix_files(backend_test_files) -> List[Path]:
    """Round-trip matrices that declare an UNCONSTRUCTIBLE list."""
    return [
        path for path in backend_test_files if "UNCONSTRUCTIBLE" in path.read_text(encoding="utf-8")
    ]


# Reflection is banned on expression objects: a format_* must read declared
# attributes. Every call below is on a NON-expression object (argparse namespace,
# connector config, driver error, backend/dialect client, enum/strategy value, or
# a plain scalar), where a declared attribute either does not exist or cannot
# cover the optional keys a driver/CLI may supply. Keys are (label, relative
# path, enclosing scope, builtin) and carry the measured count: removals pass,
# line shifts pass, new calls and growth fail. No prefix or blanket exemption.
MYSQL_REFLECTION_ALLOWLIST: Dict[Tuple[str, str, str, str], Tuple[int, str]] = {
    ("mysql", "backend/async_backend.py", "AsyncMySQLBackend", "getattr"): (
        10,
        "config object carries optional connector kwargs (charset, sql_mode, autocommit, ...) with no "
        "declared attribute for every driver; not an expression field",
    ),
    ("mysql", "backend/async_backend.py", "AsyncMySQLBackend", "hasattr"): (
        1,
        "config object carries optional connector kwargs; no declared attribute covers every driver, "
        "and the object is not an expression",
    ),
    ("mysql", "backend/backend.py", "MySQLBackend", "getattr"): (
        11,
        "config object carries optional connector kwargs (charset, sql_mode, autocommit, ...) with no "
        "declared attribute for every driver; not an expression field",
    ),
    ("mysql", "backend/backend.py", "MySQLBackend", "hasattr"): (
        1,
        "config object carries optional connector kwargs; no declared attribute covers every driver, "
        "and the object is not an expression",
    ),
    ("mysql", "cli/connection.py", "resolve_connection_config_from_args", "getattr"): (
        3,
        "argparse namespace has no declared attributes for optional named-connection flags",
    ),
    ("mysql", "cli/info.py", "check_protocol_support", "getattr"): (
        1,
        "CLI probes an optional method on a dialect client object, not an expression field",
    ),
    ("mysql", "cli/info.py", "check_protocol_support", "hasattr"): (
        1,
        "CLI probes an optional method on a dialect client object, not an expression field",
    ),
    ("mysql", "cli/info.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attributes for optional named-connection flags",
    ),
    ("mysql", "cli/introspect.py", "_require_capability", "getattr"): (
        2,
        "CLI reads optional capability switches on a backend/dialect client object, not declared "
        "expression fields",
    ),
    ("mysql", "cli/introspect.py", "_serialize_for_output", "hasattr"): (
        1,
        "CLI serializer probes an optional model_dump method on a result object, not an expression "
        "node",
    ),
    ("mysql", "cli/introspect.py", "_validate_options", "getattr"): (
        2,
        "argparse namespace has no declared attributes for optional CLI switches; the target is not "
        "an expression",
    ),
    ("mysql", "cli/introspect.py", "_value_sample_arguments", "getattr"): (
        1,
        "CLI reads optional capability switches on a backend/dialect client object, not declared "
        "expression fields",
    ),
    ("mysql", "cli/introspect.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attributes for optional named-connection flags",
    ),
    ("mysql", "cli/named_connection.py", "handle", "getattr"): (
        2,
        "argparse namespace has no declared attributes for optional output-format flags",
    ),
    ("mysql", "cli/named_expression.py", "_get_requested_version", "getattr"): (
        1,
        "argparse namespace has no declared attribute for the optional version flag",
    ),
    ("mysql", "cli/named_expression.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attribute for the optional async flag",
    ),
    ("mysql", "cli/named_migration.py", "disconnect", "getattr"): (
        1,
        "backend object exposes an optional connection attribute; not an expression field",
    ),
    ("mysql", "cli/named_migration.py", "disconnect_async", "getattr"): (
        1,
        "backend object exposes an optional connection attribute; not an expression field",
    ),
    ("mysql", "cli/named_migration.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attribute for the optional async flag",
    ),
    ("mysql", "cli/named_procedure.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attribute for the optional async flag",
    ),
    ("mysql", "cli/named_procedure_graph.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attribute for the optional async flag",
    ),
    ("mysql", "cli/query.py", "handle", "getattr"): (
        1,
        "argparse names a logging level looked up on the logging module; neither is an expression "
        "with a declared attribute",
    ),
    ("mysql", "cli/status.py", "_display_status_rich", "hasattr"): (
        2,
        "status client object exposes optional session/connection attributes, not declared expression "
        "fields",
    ),
    ("mysql", "cli/status.py", "_serialize_for_output", "hasattr"): (
        1,
        "CLI serializer probes an optional model_dump method on a result object, not an expression "
        "node",
    ),
    ("mysql", "cli/status.py", "handle", "getattr"): (
        1,
        "argparse namespace has no declared attributes for optional named-connection flags",
    ),
    ("mysql", "column_types.py", "_require", "getattr"): (
        1,
        "capability probe reads an optional switch on a dialect client object, not a declared "
        "expression field",
    ),
    ("mysql", "config.py", "MySQLConnectionConfig", "getattr"): (
        1,
        "config merges optional connector settings by name; a declared attribute cannot cover every "
        "optional driver keyword, and the config is not an expression",
    ),
    ("mysql", "expression/partition.py", "MySQLPartitionClause", "getattr"): (
        1,
        "dialect object's optional name is read only for an error message; the dialect is not an "
        "expression and declares no uniform name attribute",
    ),
    ("mysql", "expression/partition.py", "_normalize_subpartition_strategy", "getattr"): (
        1,
        "strategy may be a plain string or an enum, so .value is optional on a non-expression value "
        "object with no declared attribute",
    ),
    ("mysql", "introspection/introspector.py", "MySQLIntrospectorMixin", "hasattr"): (
        2,
        "introspection probes optional config/database attributes on backend client objects, not "
        "expressions",
    ),
    ("mysql", "introspection/status_introspector.py", "AsyncMySQLStatusIntrospector", "getattr"): (
        1,
        "server version is an optional attribute on a backend client object, not a declared "
        "expression field",
    ),
    ("mysql", "introspection/status_introspector.py", "MySQLStatusIntrospector", "getattr"): (
        1,
        "server version is an optional attribute on a backend client object, not a declared "
        "expression field",
    ),
    ("mysql", "mixins/backend_mixin.py", "MySQLBackendMixin", "getattr"): (
        3,
        "config object carries optional connector kwargs with no declared attribute for every driver; "
        "backend mixin, not an expression",
    ),
    ("mysql", "mixins/backend_mixin.py", "MySQLBackendMixin", "hasattr"): (
        1,
        "driver error objects expose errno optionally; a declared attribute cannot cover every "
        "connector exception, and the error is not an expression",
    ),
    ("mysql", "mixins/charset_collation.py", "MySQLCharsetCollationMixin", "getattr"): (
        1,
        "backend exposes an optional cached server version; not a declared expression field",
    ),
    ("mysql", "mixins/concurrency.py", "AsyncMySQLConcurrencyMixin", "getattr"): (
        1,
        "pool size is an optional connector config keyword; no declared config attribute covers every "
        "driver, and the config is not an expression",
    ),
    ("mysql", "mixins/concurrency.py", "MySQLConcurrencyMixin", "getattr"): (
        1,
        "pool size is an optional connector config keyword; no declared config attribute covers every "
        "driver, and the config is not an expression",
    ),
    ("mysql", "mixins/explain.py", "MySQLExplainMixin", "getattr"): (
        1,
        "backend mixin dispatches an optional capability-probe method declared by sibling mixins, not "
        "a declared expression field",
    ),
    ("mysql", "mixins/function.py", "MySQLFunctionMixin", "getattr"): (
        1,
        "function registry reads the module's declared __all__ by reflection; the module is not an "
        "expression",
    ),
    ("mysql", "mixins/maintenance.py", "MySQLMaintenanceMixin", "getattr"): (
        5,
        "backend mixin dispatches optional capability-probe methods by name, not declared expression "
        "fields",
    ),
    ("mysql", "mixins/maintenance.py", "MySQLMaintenanceMixin", "hasattr"): (
        5,
        "backend mixin dispatches optional capability-probe methods by name, not declared expression "
        "fields",
    ),
    ("mysql", "mixins/partition.py", "MySQLPartitionMixin", "getattr"): (
        1,
        "legacy formatter probes an optional declared attribute on a core subpartition node; some "
        "subclasses omit options, so a direct read would break them",
    ),
    ("mysql", "mixins/routine.py", "MySQLRoutineMixin", "hasattr"): (
        1,
        "routine argument may be a literal rather than an expression, so to_sql is optional on a "
        "non-expression value with no declared attribute",
    ),
    ("mysql", "show/backend_mixin.py", "AsyncMySQLShowMixin", "getattr"): (
        1,
        "backend reads an optional cached server version; not a declared expression field",
    ),
    ("mysql", "show/backend_mixin.py", "AsyncMySQLShowMixin", "hasattr"): (
        1,
        "backend probes an optional version method; not a declared expression field",
    ),
    ("mysql", "show/backend_mixin.py", "MySQLShowMixin", "getattr"): (
        1,
        "backend reads an optional cached server version; not a declared expression field",
    ),
    ("mysql", "show/backend_mixin.py", "MySQLShowMixin", "hasattr"): (
        1,
        "backend probes an optional cached version attribute; not a declared expression field",
    ),
    ("mysql", "suggestion/_change_projection.py", "_params", "getattr"): (
        1,
        "suggestion reads an optional get_params method on a value that may be a plain scalar, not an "
        "expression field",
    ),
    ("mysql", "suggestion/_change_projection.py", "fingerprint", "getattr"): (
        1,
        "suggestion reads an optional get_params method on a value that may be a plain scalar, not an "
        "expression field",
    ),
    ("mysql", "suggestion/_common.py", "_get", "getattr"): (
        1,
        "suggestion reads optional attributes on a plan/dict-like object, not a declared expression "
        "field",
    ),
    ("mysql", "suggestion/_common.py", "_upper_bound_value", "getattr"): (
        1,
        "suggestion reads optional enum attributes on a bound object, not an expression field",
    ),
    ("mysql", "suggestion/_common.py", "_word", "getattr"): (
        3,
        "suggestion reads optional enum attributes (word/method/value) on strategy objects, not "
        "expressions with declared attributes",
    ),
}


@pytest.fixture
def reflection_allowlist() -> Dict[Tuple[str, str, str, str], Tuple[int, str]]:
    """Core's entries plus MySQL's measured surface, one reason per location.

    The shared rule module's synthetic controls probe core-labelled locations,
    so its own entries must stay; they exempt no MySQL file (MySQL entries are
    keyed by this repository's ``mysql`` label). Each MySQL entry names why the
    reflected object is not an expression and why a declared attribute cannot be
    used. The guard stays monotonic: new scopes, builtins or extra calls fail.
    """
    from rhosocial.activerecord.testsuite.feature.rules.backend import (
        test_no_reflection_in_expression_layer as reflection_rules,
    )

    return {**reflection_rules.REFLECTION_ALLOWLIST, **MYSQL_REFLECTION_ALLOWLIST}
