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
from typing import List, Tuple

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
        path for path in backend_test_files
        if "UNCONSTRUCTIBLE" in path.read_text(encoding="utf-8")
    ]
