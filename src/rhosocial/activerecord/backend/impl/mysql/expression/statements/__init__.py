# src/rhosocial/activerecord/backend/impl/mysql/expression/statements/__init__.py
"""MySQL-specific statement expressions.

Public names are re-exported lazily (PEP 562), declared by each concrete
submodule in its ``__all__``. Importing this namespace never imports the
submodules, so a module may import a sibling namespace without an import cycle.
"""

import importlib as _importlib

_MODULES = (
    "admin",
    "alter_column",
    "alter_table_modifiers",
    "alter_table_options",
    "dml",
    "fulltext",
    "json_duality_view",
    "load_data",
    "load_xml",
    "maintenance",
    "partition_lifecycle",
    "rename_table",
    "routine",
    "show",
    "table_expr",
    "table_statement",
    "vector",

)


def __getattr__(_name):
    """Resolve a declared public name from one of this namespace's submodules."""
    for _mod in _MODULES:
        _sub = _importlib.import_module("." + _mod, __name__)
        if _name in vars(_sub).get("__all__", ()):
            return vars(_sub)[_name]
    raise AttributeError("module " + repr(__name__) + " has no attribute " + repr(_name))


def __dir__():
    _names = set(globals())
    for _mod in _MODULES:
        _sub = _importlib.import_module("." + _mod, __name__)
        _names.update(vars(_sub).get("__all__", ()))
    return sorted(_names)
