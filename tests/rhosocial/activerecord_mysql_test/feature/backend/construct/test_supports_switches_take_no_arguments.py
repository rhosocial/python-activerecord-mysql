# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/test_supports_switches_take_no_arguments.py
"""Guard: every ``supports_*`` in this backend's ``src`` tree is a pure switch.

A support switch answers "does this dialect configuration have capability k",
so its only input is the dialect instance and its only output is a bool. A
question that needs a name or a kind is either a separate switch over a closed
vocabulary (one method per format word, one per storage engine) or a format-time
``validate_*`` call -- never an argument to ``supports_*``. A catalogue is not
a switch either: it is a ``suggest_*`` value, such as ``FunctionSuggestion``.

The two halves are checked together because either one alone lets a catalogue
dress up as a switch: a method that demands a name fails the argument half, and
a method that returns a mapping fails the annotation half. The check is done
with :mod:`ast` on the real tree, not by importing, so a module that cannot be
imported still gets checked.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List

import pytest


def _src_dir() -> Path:
    """Locate the repository's ``src`` tree above this test file."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "src"
        if candidate.is_dir():
            return candidate
    raise AssertionError(f"cannot locate src above {__file__}")


def _src_modules() -> List[Path]:
    return sorted(_src_dir().rglob("*.py"))


def _required_arguments(func: ast.FunctionDef) -> List[str]:
    """Parameters that must be passed, excluding ``self``."""
    args = func.args
    required = list(args.posonlyargs) + list(args.args)
    required = required[1 : len(required) - len(args.defaults)]
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is None:
            required.append(arg)
    return [a.arg for a in required]


def _annotates_bool(func: ast.FunctionDef) -> bool:
    """A switch declares ``-> bool`` -- the return annotation is mandatory."""
    annotation = func.returns
    if isinstance(annotation, ast.Name) and annotation.id == "bool":
        return True
    if isinstance(annotation, ast.Constant) and annotation.value == "bool":
        return True
    return False


def _offenders(tree: ast.AST, label: str) -> List[str]:
    """Every ``supports_*`` in ``tree`` that is not a pure switch, as text."""
    found: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if not item.name.startswith("supports_"):
                continue
            missing = _required_arguments(item)
            if missing:
                found.append(f"{label}:{item.lineno} {item.name}({', '.join(missing)})")
            elif not _annotates_bool(item):
                found.append(f"{label}:{item.lineno} {item.name} does not return bool")
    return found


def test_the_scan_reaches_the_source_tree():
    modules = _src_modules()
    assert len(modules) > 50, f"only {len(modules)} modules found under {_src_dir()}"


def test_no_support_switch_requires_an_argument():
    offenders: List[str] = []
    for path in _src_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders.extend(_offenders(tree, path.name))
    assert not offenders, (
        "``supports_*`` is a parameterless support switch returning bool; split "
        "it into one switch per value, validate the value in a ``validate_*`` "
        "method, or answer it as a ``suggest_*`` value:\n" + "\n".join(offenders)
    )


def test_the_scan_flags_a_planted_required_argument(tmp_path):
    """Self-check: the fabricated violation below must be reported."""
    probe = tmp_path / "_fabricated_violation.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self, name) -> bool:\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _offenders(tree, probe.name)
    assert offenders, "the scan did not flag a supports_* method that needs a name"
    assert offenders[0].startswith(f"{probe.name}:2 supports_thing(name")


def test_the_scan_flags_a_planted_non_bool_annotation(tmp_path):
    """Self-check: a switch answering a mapping must be reported."""
    probe = tmp_path / "_fabricated_catalogue.py"
    probe.write_text(
        "from typing import Dict\n"
        "class P:\n"
        "    def supports_thing(self) -> Dict[str, bool]:\n"
        "        return {}\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _offenders(tree, probe.name)
    assert offenders, "the scan did not flag a supports_* that returns a mapping"
    assert "does not return bool" in offenders[0]


def test_the_scan_flags_a_planted_missing_annotation(tmp_path):
    """Self-check: an unannotated switch is not provably a switch."""
    probe = tmp_path / "_fabricated_unannotated.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _offenders(tree, probe.name)
    assert offenders, "the scan accepted a supports_* with no return annotation"


@pytest.mark.parametrize(
    "source",
    [
        "class P:\n    def supports_thing(self, name=None) -> bool:\n        return False\n",
        "class P:\n    def supports_thing(self, *, name=None) -> bool:\n        return False\n",
    ],
)
def test_the_scan_accepts_a_defaulted_parameter(tmp_path, source):
    """A defaulted parameter is still callable as a switch, so it is allowed."""
    probe = tmp_path / "_defaulted.py"
    probe.write_text(source, encoding="utf-8")
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, probe.name)


def test_the_scan_accepts_a_quoted_bool_annotation(tmp_path):
    """``-> "bool"`` is the same claim as ``-> bool``."""
    probe = tmp_path / "_quoted.py"
    probe.write_text(
        'class P:\n    def supports_thing(self) -> "bool":\n        return False\n',
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, probe.name)
