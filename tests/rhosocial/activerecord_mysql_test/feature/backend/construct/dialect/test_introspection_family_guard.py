# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/dialect/test_introspection_family_guard.py
"""Guard the introspection-family reclassification this backend must carry.

Core split the single ``IntrospectionSupport`` protocol into four families and
deleted ``supports_partition_info``. This backend keeps one mixin, so the split
is a declaration change only -- but three things must stay true for it to be a
declaration change rather than a silent regression:

* the deleted partition probe is not resurrected anywhere on the dialect;
* the CLI's ``partitions`` family is gated on core's surviving metadata probe,
  which MySQL answers ``True`` (the old probe under-reported it);
* each family is imported from its own core module, and the retired aggregate
  names are not re-introduced as aliases.

These assertions read the public surfaces the rest of the suite reaches for
(the dialect, the CLI map and the protocols package), so a later edit cannot
quietly answer them differently.
"""

import importlib
import inspect

from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.impl.mysql.cli import introspect as cli_introspect
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

#: (core module, sync protocol, async twin), one row per family.
FAMILIES = [
    (
        "rhosocial.activerecord.backend.dialect.protocols.introspect.structure",
        "StructureIntrospectionSupport",
        "AsyncStructureIntrospectionSupport",
    ),
    (
        "rhosocial.activerecord.backend.dialect.protocols.introspect.operational_stats",
        "OperationalStatsIntrospectionSupport",
        "AsyncOperationalStatsIntrospectionSupport",
    ),
    (
        "rhosocial.activerecord.backend.dialect.protocols.introspect.data_profile",
        "DataProfileIntrospectionSupport",
        "AsyncDataProfileIntrospectionSupport",
    ),
    (
        "rhosocial.activerecord.backend.dialect.protocols.introspect.ddl_extraction",
        "DdlExtractionIntrospectionSupport",
        "AsyncDdlExtractionIntrospectionSupport",
    ),
]

#: The aggregate and probe names core removed, with no aliases left behind.
RETIRED_NAMES = ("IntrospectionSupport", "AsyncIntrospectionSupport", "supports_partition_info")


def test_retired_partition_probe_is_absent_from_a_constructed_dialect():
    """``supports_partition_info`` no longer exists, and MySQL adds none back."""
    dialect = MySQLDialect()
    for name in RETIRED_NAMES:
        assert not hasattr(dialect, name), (
            f"MySQLDialect exposes the retired name {name!r}; core deleted it and "
            f"kept no alias."
        )


def test_partitions_family_gates_on_the_metadata_probe():
    """The CLI's partitions type resolves to core's partition-metadata probe."""
    capability = cli_introspect._TYPE_CAPABILITIES["partitions"]
    assert capability == "supports_partition_metadata_introspection", (
        "the partitions family must be gated on the surviving metadata probe, "
        f"not {capability!r}"
    )
    assert "supports_partition_info" not in cli_introspect._TYPE_CAPABILITIES.values()

    dialect = MySQLDialect()
    assert dialect.supports_partition_metadata_introspection() is True
    # The backend's own spelling of the same question stays true beside it.
    assert dialect.supports_partition_introspection() is True


def test_families_import_from_their_own_core_modules():
    """Each family is defined in its own module, sync and async both."""
    for module_name, sync_name, async_name in FAMILIES:
        module = importlib.import_module(module_name)
        for name in (sync_name, async_name):
            assert hasattr(module, name), f"{module_name} does not export {name}"
            assert hasattr(dialect_protocols, name), f"protocols package does not export {name}"
            cls = getattr(dialect_protocols, name)
            assert cls.__module__ == module_name, (
                f"{name} resolves to {cls.__module__}, not its family module "
                f"{module_name}; it must not be re-exported from one aggregate module"
            )
            assert cls.__name__ == name, f"unexpected protocol alias for {name}"


def test_retired_names_are_not_aliased_in_the_protocols_package():
    """The old aggregate names are gone rather than aliased."""
    for name in RETIRED_NAMES:
        assert not hasattr(dialect_protocols, name), f"core's deleted name {name!r} is back"

    exported = getattr(dialect_protocols, "__all__", [])
    assert "IntrospectionSupport" not in exported
    assert "AsyncIntrospectionSupport" not in exported


def test_every_family_protocol_is_declared_on_the_dialect():
    """Both twins of every family resolve to a live implementation."""
    dialect = MySQLDialect()
    for _module_name, sync_name, async_name in FAMILIES:
        for name in (sync_name, async_name):
            cls = getattr(dialect_protocols, name)
            assert getattr(cls, "_is_runtime_protocol", False), f"{name} is not runtime-checkable"
            assert isinstance(dialect, cls), f"MySQLDialect does not satisfy {name}"
            # Every declared member must be a real method, not a bare annotation.
            for member in inspect.getmembers(cls, inspect.isfunction):
                assert callable(getattr(dialect, member[0], None)), (
                    f"MySQLDialect lacks {name}.{member[0]}"
                )


def test_info_surface_reports_all_four_families():
    """The ``info`` command groups all four families, not an inherited subset.

    Core's own SQLite ``info.py`` lists none of the four families, so the
    omission would have carried over silently: the split protocols exist, the
    dialect satisfies them, and the report still shows nothing. Read the map
    and the built report, so a later edit to either surface is caught.
    """
    from rhosocial.activerecord.backend.impl.mysql.cli import info as cli_info

    dialect = MySQLDialect(version=(8, 4, 13))
    reported: dict = {}
    for group_name, protocols in cli_info.PROTOCOL_FAMILY_GROUPS.items():
        reported.update(cli_info._build_protocol_info(dialect, group_name, protocols, verbose=1))

    for _module_name, sync_name, _async_name in FAMILIES:
        assert sync_name in reported, (
            f"{sync_name} is missing from PROTOCOL_FAMILY_GROUPS; the info "
            f"report would omit this family the way core's SQLite report omits all four"
        )
        assert reported[sync_name]["total"] > 0, f"{sync_name} was classified with no probes"
