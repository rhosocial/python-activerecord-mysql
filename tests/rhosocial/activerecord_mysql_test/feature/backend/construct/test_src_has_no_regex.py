# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/test_src_has_no_regex.py
"""Guard: the backend's ``src`` tree never imports or uses the regex module.

``src`` reads a server-reported string by scanning its characters (the shared
helpers live in ``impl/mysql/_scan.py``). Tests may keep regexes, but only to
assert generated SQL; production code may not, because a pattern silently
accepts spellings a scanner would have to name explicitly and because the
read direction is a per-character contract.

Two layers are checked so neither can be routed around:

* every module under ``src`` is parsed with :mod:`ast` and fails on an
  ``import re`` / ``import re.x`` / ``from re import ...`` node;
* the raw text is scanned for a standalone ``re.<name>`` use, which catches a
  module that reaches the regex module through ``__import__("re")`` and
  therefore has no import node to inspect.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple


def _src_dir() -> Path:
    """Locate the repository's ``src`` tree above this test file."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "src"
        if candidate.is_dir():
            return candidate
    raise AssertionError(f"cannot locate src above {__file__}")


def _src_modules() -> List[Path]:
    return sorted(_src_dir().rglob("*.py"))


def _import_offences(tree: ast.AST) -> List[Tuple[int, str]]:
    """Every regex-module import in ``tree``, as ``(line, what)``."""
    offences: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "re" or alias.name.startswith("re."):
                    offences.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "re":
            names = ", ".join(alias.name for alias in node.names)
            offences.append((node.lineno, f"from re import {names}"))
    return offences


def _attribute_offences(text: str) -> List[Tuple[int, str]]:
    """Every standalone ``re.<name>`` use in ``text``, as ``(line, snippet)``.

    The scan is deliberately plain text: it sees a use even when the module
    was obtained indirectly. A hit preceded by a letter, digit or underscore
    is the tail of another word (``there.``, ``core.``) rather than a use of
    the module, and is ignored.
    """
    offences: List[Tuple[int, str]] = []
    index = text.find("re.")
    while index >= 0:
        previous = text[index - 1] if index else ""
        if not previous or not (previous.isalnum() or previous == "_"):
            line = text.count("\n", 0, index) + 1
            snippet = text[index : index + 24].split("\n", 1)[0]
            offences.append((line, snippet))
        index = text.find("re.", index + 1)
    return offences


def test_src_imports_no_regular_expression_module():
    modules = _src_modules()
    assert modules, f"no modules found under {_src_dir()}"
    offenders: List[str] = []
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, what in _import_offences(tree):
            offenders.append(f"{path}:{line}: {what}")
    assert not offenders, (
        "src must not import the regular-expression module; read the string by "
        "scanning characters instead (see impl/mysql/_scan.py):\n" + "\n".join(offenders)
    )


def test_src_has_no_standalone_re_attribute_use():
    offenders: List[str] = []
    for path in _src_modules():
        text = path.read_text(encoding="utf-8")
        for line, snippet in _attribute_offences(text):
            offenders.append(f"{path}:{line}: {snippet}")
    assert not offenders, (
        "src must not use the regular-expression module's attributes; an "
        "indirect import still has to be written as an attribute use:\n" + "\n".join(offenders)
    )


def test_the_guard_detects_its_own_offences():
    """Self-check: the two scans must recognise the shapes they exist to catch."""
    tree = ast.parse("import re as rx\nfrom re import compile as _compile\n")
    assert [what for _, what in _import_offences(tree)] == [
        "import re",
        "from re import compile",
    ]
    text = "pattern = re.compile('x')\nsee there.\n"
    assert [line for line, _ in _attribute_offences(text)] == [1]
