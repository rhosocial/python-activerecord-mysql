# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/introspection/test_introspection_state_parity.py
"""Offline guard: the sync and async introspectors must not drift apart.

The two state methods are I/O-shaped, so ``get_table_state`` /
``get_partition_state`` and their siblings are written once per twin. The
reductions they apply are pure Python and belong to the shared
:class:`MySQLIntrospectorMixin`; a helper defined on only one concrete class
is invisible to the other twin and cannot be caught locally, because the
async live fixture is skipped when no MySQL server is reachable. These tests
compare the classes themselves, so they need no server and fail before the
live run exposes the asymmetry.
"""

import inspect
import re

from rhosocial.activerecord.backend.introspection.types import TableType

from rhosocial.activerecord.backend.impl.mysql.introspection import (
    AsyncMySQLIntrospector,
    MySQLIntrospector,
)
from rhosocial.activerecord.backend.impl.mysql.introspection.introspector import (
    MySQLIntrospectorMixin,
)
from rhosocial.activerecord.backend.impl.mysql.introspection.types import (
    MySQLTableOptions,
)

#: The reductions every state method relies on. They are pure Python and have
#: no sync/async flavour, so they must be defined once, on the shared mixin.
SHARED_REDUCTIONS = (
    "table_state_kind",
    "charset_from_collation",
    "parse_storage_options_state",
)

#: The state methods whose ``self.<helper>`` references are audited. Each one
#: exists on both twins and reaches the shared reductions.
STATE_METHODS = (
    "get_table_info",
    "list_table_options",
    "get_table_options",
    "get_table_state",
    "get_partition_state",
    "list_index_states",
    "list_constraint_states",
    "list_derived_objects",
    "list_schemas",
    "item_exists",
)

_SELF_ATTRIBUTE = re.compile(r"\bself\.([A-Za-z_][A-Za-z0-9_]*)")


def _own_members(cls):
    """Names a class itself defines, i.e. excluding inherited members."""
    return {name for name in vars(cls) if not name.startswith("__")}


def _defining_class(cls, name):
    """The first class in the MRO that defines *name*, or ``None``."""
    for base in cls.__mro__:
        if name in vars(base):
            return base
    return None


def _self_attributes(method):
    """The ``self.<name>`` attributes a method's body reads or calls."""
    return set(_SELF_ATTRIBUTE.findall(inspect.getsource(method)))


class TestSharedReductions:
    """The kind mapping and storage projection are shared, not duplicated."""

    def test_reductions_are_defined_on_the_mixin(self):
        mixin_members = _own_members(MySQLIntrospectorMixin)
        for name in SHARED_REDUCTIONS:
            assert name in mixin_members, f"{name} must live on MySQLIntrospectorMixin"

    def test_neither_concrete_class_redefines_a_reduction(self):
        for cls in (MySQLIntrospector, AsyncMySQLIntrospector):
            own = _own_members(cls)
            for name in SHARED_REDUCTIONS:
                assert name not in own, (
                    f"{cls.__name__} must reach {name} through the shared mixin, "
                    "not define its own copy"
                )

    def test_both_twins_resolve_the_reductions_to_the_same_function(self):
        for name in SHARED_REDUCTIONS:
            sync_reduction = inspect.getattr_static(MySQLIntrospector, name)
            async_reduction = inspect.getattr_static(AsyncMySQLIntrospector, name)
            assert sync_reduction is async_reduction, (
                f"{name} is not the same object on both twins: "
                f"{sync_reduction!r} vs {async_reduction!r}"
            )

    def test_the_async_twin_answers_the_kind_mapping(self):
        # The exact regression CI reported: the async state method called a
        # helper that only the sync class had.
        assert AsyncMySQLIntrospector.table_state_kind(TableType.BASE_TABLE) == "regular"
        assert AsyncMySQLIntrospector.table_state_kind(TableType.VIEW) == "view"
        assert AsyncMySQLIntrospector.table_state_kind(TableType.SYSTEM_TABLE) == "system_view"
        assert AsyncMySQLIntrospector.table_state_kind(TableType.PARTITIONED_TABLE) == "regular"

    def test_the_async_twin_projects_storage_options(self):
        options = MySQLTableOptions(
            schema="shop",
            table_name="users",
            engine="InnoDB",
            table_collation="utf8mb4_0900_ai_ci",
            data_length=16384,
        )
        # The projection is pure Python: it never touches the backend or the
        # executor, so the twin can be constructed without either.
        introspector = AsyncMySQLIntrospector(None, None)
        state = introspector.parse_storage_options_state(options)

        assert state.engine == "InnoDB"
        assert state.collation == "utf8mb4_0900_ai_ci"
        assert state.charset == "utf8mb4"


class TestClassSurfaceParity:
    """The concrete classes define the same surface, only the I/O twin differs."""

    def test_both_classes_define_the_same_members(self):
        sync_only = _own_members(MySQLIntrospector) - _own_members(AsyncMySQLIntrospector)
        async_only = _own_members(AsyncMySQLIntrospector) - _own_members(MySQLIntrospector)

        assert not sync_only, f"members only the sync twin defines: {sorted(sync_only)}"
        assert not async_only, f"members only the async twin defines: {sorted(async_only)}"

    def test_every_state_method_exists_on_both_twins(self):
        for name in STATE_METHODS:
            assert name in vars(MySQLIntrospector), f"{name} missing from MySQLIntrospector"
            assert name in vars(
                AsyncMySQLIntrospector
            ), f"{name} missing from AsyncMySQLIntrospector"


class TestStateMethodReachability:
    """Every helper a state method reaches resolves on both twins alike."""

    def test_no_state_method_reaches_a_sync_or_async_only_helper(self):
        for method_name in STATE_METHODS:
            sync_method = vars(MySQLIntrospector)[method_name]
            async_method = vars(AsyncMySQLIntrospector)[method_name]
            referenced = _self_attributes(sync_method) | _self_attributes(async_method)

            for attribute in sorted(referenced):
                if attribute.startswith("__"):
                    continue
                sync_definer = _defining_class(MySQLIntrospector, attribute)
                async_definer = _defining_class(AsyncMySQLIntrospector, attribute)

                # Instance attributes (``self._executor``, ``self._cache``) are
                # assigned in ``__init__`` and are not class members.
                if sync_definer is None and async_definer is None:
                    continue

                assert sync_definer is not None and async_definer is not None, (
                    f"{method_name} reaches self.{attribute}, which only one twin "
                    f"resolves (sync: {sync_definer}, async: {async_definer})"
                )

                defined_on_sync = attribute in vars(MySQLIntrospector)
                defined_on_async = attribute in vars(AsyncMySQLIntrospector)
                assert defined_on_sync == defined_on_async, (
                    f"self.{attribute} is defined by only one concrete class "
                    f"(sync: {defined_on_sync}, async: {defined_on_async}); "
                    "share it through MySQLIntrospectorMixin or define both twins"
                )
