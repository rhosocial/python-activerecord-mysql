# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/statements/test_mixin_shared_renderers_guard.py
"""Guard: a private renderer may not re-couple two public MySQL formatters.

The defect this guard closes was a private ``_render_*`` helper that read the
whole statement node, carried the capability gates and built the SQL, with
five public ``format_*`` entries delegating to it. That let one change to a
shared renderer silently alter several independent expression kinds at once,
and it hid the per-kind gate inside a helper instead of the formatter that
owns the kind.

A private ``_render_*`` / ``_format_*`` method called by two or more public
``format_*`` methods in the same class is therefore a failure unless it is on
``ALLOWED_SHARED_HELPERS`` with a written reason. Only value-level utilities
over a node's field are allowed: no statement node, no capability gate.

The allow-list is asserted to equal the detected set exactly, so adding a new
shared renderer fails even if it looks harmless, and deleting one of the
listed utilities also fails instead of leaving a stale exemption behind.
"""

from __future__ import annotations

import ast
from pathlib import Path

MIXINS_SUBDIR = Path("src") / "rhosocial" / "activerecord" / "backend" / "impl" / "mysql" / "mixins"

#: Every detected shared private renderer, keyed by ``<file>::<Class>.<method>``.
#: Each entry must say why it is a value-level utility rather than a renderer
#: of an independent statement kind.
ALLOWED_SHARED_HELPERS = {
    "admin.py::MySQLAdminCommandMixin._format_accounts": (
        "Value-level joiner: formats user/host pairs from an account field; "
        "never reads the statement node and has no capability gate."
    ),
    "admin.py::MySQLAdminCommandMixin._format_admin_table": (
        "Table-name renderer shared by the HANDLER entries: renders one Table "
        "field through its own formatter. The require_kind check is a field-kind "
        "assertion, not a capability gate, and no statement node is read."
    ),
    "admin.py::MySQLAdminCommandMixin._format_cache_entries": (
        "Value-level joiner over cache-entry mappings; no capability gate and "
        "no statement node read."
    ),
    "ddl_table.py::MySQLTableMixin._render_storage_options": (
        "Pure primitive list joining: option name/value pairs from a mapping; "
        "no node and no capability gate."
    ),
    "routine.py::MySQLRoutineMixin._format_param": (
        "Value-level normaliser for the str / 2-tuple / 3-tuple parameter "
        "shapes; no capability gate and no statement node read."
    ),
    "spatial.py::MySQLSpatialMixin._format_spatial_literal_parts": (
        "Pure primitive assembly: a WKT string plus an optional SRID; no node "
        "and no capability gate."
    ),
    "types.py::MySQLTypeSupportMixin._format_mysql_integer": (
        "Literal keyword plus DataType attribute rendering; its local unsigned "
        "check is a value assertion, not a capability gate, and no statement "
        "node is read."
    ),
}

#: Helpers that were inlined into each public formatter by this change; they
#: must not come back in any form.
INLINED_HELPERS = (
    "_render_mysql_table_maintenance",
    "_format_statement_clauses",
    "_format_maintenance_table",
)


def _mixins_dir() -> Path:
    """Locate the mixins package from this test file without a fixed depth."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / MIXINS_SUBDIR
        if candidate.is_dir():
            return candidate
    raise AssertionError(f"cannot locate {MIXINS_SUBDIR} above {__file__}")


def _private_renderers(class_def: ast.ClassDef) -> set:
    return {
        item.name
        for item in class_def.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name.startswith(("_render_", "_format_"))
    }


def _public_callers(class_def: ast.ClassDef, helper_names: set) -> dict:
    callers = {name: set() for name in helper_names}
    for method in class_def.body:
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not method.name.startswith("format_"):
            continue
        for node in ast.walk(method):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
                and node.func.attr in callers
            ):
                callers[node.func.attr].add(method.name)
    return callers


def shared_private_renderers() -> set:
    """Return every private renderer used by two or more public formatters."""
    found = set()
    for path in sorted(_mixins_dir().rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for class_def in tree.body:
            if not isinstance(class_def, ast.ClassDef):
                continue
            helpers = _private_renderers(class_def)
            if not helpers:
                continue
            for helper, callers in _public_callers(class_def, helpers).items():
                if len(callers) >= 2:
                    found.add(f"{path.name}::{class_def.name}.{helper}")
    return found


def test_every_shared_renderer_is_allow_listed_with_a_reason():
    found = shared_private_renderers()
    allowed = set(ALLOWED_SHARED_HELPERS)
    assert found == allowed, (
        "private renderers shared by two or more public formatters changed. "
        "Inline a new one into each formatter, or add it to "
        "ALLOWED_SHARED_HELPERS with a written value-level reason. "
        f"new: {sorted(found - allowed)}; stale: {sorted(allowed - found)}"
    )
    for key, reason in ALLOWED_SHARED_HELPERS.items():
        assert reason.strip(), f"{key} is allow-listed without a written reason"


def test_expression_kind_renderers_are_inlined():
    """The two renderers this change removed must not reappear."""
    sources = "\n".join(path.read_text(encoding="utf-8") for path in _mixins_dir().rglob("*.py"))
    for name in INLINED_HELPERS:
        assert name not in sources, f"{name} must stay inlined in each formatter"
