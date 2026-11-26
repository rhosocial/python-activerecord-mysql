# src/rhosocial/activerecord/backend/impl/mysql/catalogue.py
"""Which ``information_schema`` relations and columns each MySQL release answers.

The introspection queries in ``mixins.introspection`` read MySQL's own
catalogue. That catalogue is not frozen: a relation a newer release adds does
not exist on an older one, and a column a newer release adds is refused by name
on an older one (``1109 unknown table`` / ``1054 unknown column``). A statement
that names such a relation or column is not answered with a partial row -- the
whole statement fails -- so the version has to decide what the statement asks.

The facts below were measured, not inferred, by reading
``information_schema.COLUMNS`` on servers started for this purpose:

* **5.6.51** -- ``information_schema.CHECK_CONSTRAINTS`` does not exist.
  ``TABLE_CONSTRAINTS`` answers ``CONSTRAINT_CATALOG``, ``CONSTRAINT_SCHEMA``,
  ``CONSTRAINT_NAME``, ``TABLE_SCHEMA``, ``TABLE_NAME``, ``CONSTRAINT_TYPE``
  but **not** ``ENFORCED``. Everything else this backend names exists with the
  columns listed below.
* **5.7.44** -- the same surface as 5.6.51 for every relation and column this
  backend names (``COLUMNS`` gains ``GENERATION_EXPRESSION`` and
  ``SYS`` arrives, neither of which is read here).
* **8.0.15** -- ``CHECK_CONSTRAINTS`` still absent and ``TABLE_CONSTRAINTS``
  still without ``ENFORCED``; CHECK clauses parse and are discarded below the
  enforcement floor.
* **8.0.16** -- ``CHECK_CONSTRAINTS`` appears with ``CONSTRAINT_CATALOG``,
  ``CONSTRAINT_SCHEMA``, ``CONSTRAINT_NAME``, ``CHECK_CLAUSE``, and
  ``TABLE_CONSTRAINTS`` gains ``ENFORCED``. This is the first release that can
  answer a CHECK constraint as a declaration rather than discard it.
* **8.4.13** -- the 8.0.16 surface for every relation and column read here
  (``STATISTICS`` gains ``IS_VISIBLE`` / ``EXPRESSION`` and ``COLUMNS`` gains
  ``SRS_ID``, neither of which is read here).

What this table records is the set of columns **this backend may name**, not
every column the server happens to have. A release is added here only after the
columns have been measured against it, and every statement this backend renders
is checked against this table by ``test_catalogue_capabilities.py``.

The matrix is keyed by the exact version at which the surface changes
(``8.0.16``), not by release line: the boundary between 8.0.15 and 8.0.16 is a
patch, so a ``(major, minor)`` key could not express it. An unrecorded version
is answered with the newest recorded version at or below it, and a version older
than every recorded one with the oldest recorded one. That direction is
deliberate: the fallback may *omit* a column the server actually has, which is
an honest "not asked", but it never names a column the server may not have. A
version nobody knows yet (``None``) therefore answers the oldest surface -- for
example, a dialect that has not run ``introspect_and_adapt`` never names
``CHECK_CONSTRAINTS`` it cannot prove exists.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import FrozenSet, Mapping, Optional, Tuple

#: A MySQL server version, as ``(major, minor, patch)``.
Version = Tuple[int, int, int]


@dataclass(frozen=True)
class MySQLCatalogueCapabilities:
    """The ``information_schema`` surface this backend may name on one release.

    ``relations`` maps a relation name to the columns this backend may name on
    it. A relation absent from the mapping does not exist on this release, and
    a statement that names it would be refused by the server -- which is why
    :meth:`columns_of` answers ``None`` rather than an empty set: "does not
    exist" and "exists but has no readable column" are different answers, and
    only the first is a refusal.
    """

    #: The version these sets were measured on.
    version: Version
    #: Relation name -> the columns this backend may name on it.
    relations: Mapping[str, FrozenSet[str]]

    def columns_of(self, relation: str) -> Optional[FrozenSet[str]]:
        """The columns of *relation* this backend may name, or ``None`` absent."""
        return self.relations.get(relation)

    def has_relation(self, relation: str) -> bool:
        """Whether *relation* exists on this release."""
        return relation in self.relations


_SCHEMATA = frozenset(
    {
        "SCHEMA_NAME",
        "DEFAULT_CHARACTER_SET_NAME",
        "DEFAULT_COLLATION_NAME",
    }
)

#: ``TABLES`` carries the table list, the storage options and the storage split
#: from one relation; the union of the three projections is what is recorded.
_TABLES = frozenset(
    {
        "TABLE_SCHEMA",
        "TABLE_NAME",
        "TABLE_TYPE",
        "TABLE_COMMENT",
        "TABLE_ROWS",
        "DATA_LENGTH",
        "INDEX_LENGTH",
        "AUTO_INCREMENT",
        "CREATE_TIME",
        "UPDATE_TIME",
        "ENGINE",
        "ROW_FORMAT",
        "TABLE_COLLATION",
        "CREATE_OPTIONS",
    }
)

_COLUMNS = frozenset(
    {
        "TABLE_SCHEMA",
        "TABLE_NAME",
        "COLUMN_NAME",
        "ORDINAL_POSITION",
        "COLUMN_DEFAULT",
        "IS_NULLABLE",
        "DATA_TYPE",
        "CHARACTER_MAXIMUM_LENGTH",
        "NUMERIC_PRECISION",
        "NUMERIC_SCALE",
        "COLUMN_TYPE",
        "COLUMN_KEY",
        "EXTRA",
        "COLUMN_COMMENT",
        "CHARACTER_SET_NAME",
        "COLLATION_NAME",
    }
)

_STATISTICS = frozenset(
    {
        "TABLE_SCHEMA",
        "TABLE_NAME",
        "INDEX_NAME",
        "NON_UNIQUE",
        "SEQ_IN_INDEX",
        "COLUMN_NAME",
        "INDEX_TYPE",
        "SUB_PART",
        "NULLABLE",
    }
)

#: ``TABLE_CONSTRAINTS`` below the CHECK-enforcement floor (5.6 -- 8.0.15).
_TABLE_CONSTRAINTS_WITHOUT_ENFORCED = frozenset(
    {
        "CONSTRAINT_SCHEMA",
        "TABLE_SCHEMA",
        "TABLE_NAME",
        "CONSTRAINT_NAME",
        "CONSTRAINT_TYPE",
    }
)

#: ``TABLE_CONSTRAINTS`` from 8.0.16 on: ``ENFORCED`` joins the declaration.
_TABLE_CONSTRAINTS_WITH_ENFORCED = _TABLE_CONSTRAINTS_WITHOUT_ENFORCED | {"ENFORCED"}

_KEY_COLUMN_USAGE = frozenset(
    {
        "CONSTRAINT_SCHEMA",
        "CONSTRAINT_NAME",
        "TABLE_SCHEMA",
        "TABLE_NAME",
        "COLUMN_NAME",
        "ORDINAL_POSITION",
        "REFERENCED_TABLE_NAME",
        "REFERENCED_COLUMN_NAME",
    }
)

_REFERENTIAL_CONSTRAINTS = frozenset(
    {
        "CONSTRAINT_SCHEMA",
        "CONSTRAINT_NAME",
        "UPDATE_RULE",
        "DELETE_RULE",
    }
)

#: ``CHECK_CONSTRAINTS`` from 8.0.16 on; absent below the enforcement floor.
_CHECK_CONSTRAINTS = frozenset(
    {
        "CONSTRAINT_SCHEMA",
        "CONSTRAINT_NAME",
        "CHECK_CLAUSE",
    }
)

#: The partition declaration plus the statistics ``include_stats`` can ask for.
_PARTITIONS = frozenset(
    {
        "TABLE_SCHEMA",
        "TABLE_NAME",
        "PARTITION_NAME",
        "SUBPARTITION_NAME",
        "PARTITION_METHOD",
        "SUBPARTITION_METHOD",
        "PARTITION_EXPRESSION",
        "PARTITION_DESCRIPTION",
        "PARTITION_ORDINAL_POSITION",
        "SUBPARTITION_ORDINAL_POSITION",
        "TABLE_ROWS",
        "DATA_LENGTH",
        "INDEX_LENGTH",
    }
)

_ROUTINES = frozenset(
    {
        "ROUTINE_SCHEMA",
        "ROUTINE_NAME",
        "ROUTINE_TYPE",
        "DATA_TYPE",
        "DTD_IDENTIFIER",
        "ROUTINE_BODY",
        "EXTERNAL_LANGUAGE",
        "IS_DETERMINISTIC",
        "SQL_DATA_ACCESS",
        "SECURITY_TYPE",
        "ROUTINE_COMMENT",
        "DEFINER",
        "CREATED",
        "LAST_ALTERED",
        "SQL_MODE",
    }
)

_PARAMETERS = frozenset(
    {
        "SPECIFIC_SCHEMA",
        "SPECIFIC_NAME",
        "ROUTINE_TYPE",
        "ORDINAL_POSITION",
        "PARAMETER_MODE",
        "PARAMETER_NAME",
        "DATA_TYPE",
        "DTD_IDENTIFIER",
    }
)

#: The relations every supported release answers with the columns this backend
#: names. 5.6 and 5.7 were measured identical for all of them.
_COMMON_RELATIONS = {
    "SCHEMATA": _SCHEMATA,
    "TABLES": _TABLES,
    "COLUMNS": _COLUMNS,
    "STATISTICS": _STATISTICS,
    "KEY_COLUMN_USAGE": _KEY_COLUMN_USAGE,
    "REFERENTIAL_CONSTRAINTS": _REFERENTIAL_CONSTRAINTS,
    "PARTITIONS": _PARTITIONS,
    "ROUTINES": _ROUTINES,
    "PARAMETERS": _PARAMETERS,
}

#: The surface below the CHECK-enforcement floor: ``TABLE_CONSTRAINTS`` without
#: ``ENFORCED``, and no ``CHECK_CONSTRAINTS`` at all.
_WITHOUT_CHECK_CATALOGUE = MappingProxyType(
    dict(_COMMON_RELATIONS, TABLE_CONSTRAINTS=_TABLE_CONSTRAINTS_WITHOUT_ENFORCED)
)

#: The surface from 8.0.16 on: the declaration is answerable, so both the
#: ``ENFORCED`` column and the ``CHECK_CONSTRAINTS`` relation join the surface.
_WITH_CHECK_CATALOGUE = MappingProxyType(
    dict(
        _COMMON_RELATIONS,
        TABLE_CONSTRAINTS=_TABLE_CONSTRAINTS_WITH_ENFORCED,
        CHECK_CONSTRAINTS=_CHECK_CONSTRAINTS,
    )
)


#: Measured surface, one entry per version at which the surface changes.
#: Keys are ordered by version; :func:`capabilities_for_version` relies on
#: ordinary tuple ordering, not on dict insertion order.
CAPABILITY_MATRIX = {
    (5, 6, 0): MySQLCatalogueCapabilities(version=(5, 6, 0), relations=_WITHOUT_CHECK_CATALOGUE),
    (5, 7, 0): MySQLCatalogueCapabilities(version=(5, 7, 0), relations=_WITHOUT_CHECK_CATALOGUE),
    (8, 0, 16): MySQLCatalogueCapabilities(version=(8, 0, 16), relations=_WITH_CHECK_CATALOGUE),
    (8, 4, 0): MySQLCatalogueCapabilities(version=(8, 4, 0), relations=_WITH_CHECK_CATALOGUE),
}

#: The oldest measured version, also the answer when no version is known yet.
_BASELINE_VERSION = min(CAPABILITY_MATRIX)


def capabilities_for_version(
    version: Optional[Version],
) -> MySQLCatalogueCapabilities:
    """The recorded surface in force for *version*.

    An unrecorded version resolves to the newest recorded version at or below
    it; a version older than every recorded one, or one nobody knows yet,
    resolves to the oldest recorded one. See the module docstring for why the
    fallback never moves forward.

    ``8.0.0`` .. ``8.0.15`` deliberately resolve to the 5.7 surface: those
    releases exist, but they have neither ``CHECK_CONSTRAINTS`` nor
    ``TABLE_CONSTRAINTS.ENFORCED``, and the 5.7 entry is the measured answer
    that says so.
    """
    if version is None:
        return CAPABILITY_MATRIX[_BASELINE_VERSION]
    recorded = [key for key in CAPABILITY_MATRIX if key <= version]
    if recorded:
        return CAPABILITY_MATRIX[max(recorded)]
    return CAPABILITY_MATRIX[_BASELINE_VERSION]


def version_label(version: Optional[Version]) -> str:
    """A version as a dotted release, or ``unknown`` when none is known."""
    if version is None:
        return "unknown"
    return f"{version[0]}.{version[1]}.{version[2]}"
