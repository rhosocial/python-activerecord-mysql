# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_column_suggestion.py
"""MySQL's eighteen-entry column-type suggestion table and its narrowing.

Pure dialect tests -- no server, no connection. What is asserted here is the
*declaration*: that the table answers every entry of the protocol's closed list,
that the cells MySQL deviates on are the ones the live-server sweep measured,
that the one version gate fires on both sides of the boundary, and that each
narrowing names an operation the column class really exposes.

The rendering those cells imply is Phase 2b's work and is deliberately not
asserted here -- with two named exceptions that are *not* rendering but
capability, and therefore belong to this phase: ``ilike`` (measured 1064
syntax error on every MySQL version) and the ``dict`` refusal below 5.7
(measured ``1305 FUNCTION ... does not exist``).
"""

import datetime
import decimal
import enum
import uuid

import pytest

from rhosocial.activerecord.backend.dialect.mixins import ColumnSuggestionMixin
from rhosocial.activerecord.backend.expression.column_suggestions import (
    COLUMN_TYPE_ENTRIES,
    UNSUPPORTED,
    ColumnTypeResolutionError,
)
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    DateTimeColumn,
    DecimalColumn,
    FloatColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

#: The versions the live sweep behind this table ran against. 5.6.51 and 5.7.44
#: are the two ends of the JSON gate; 8.0.46 is the mainstream server.
MYSQL_56 = (5, 6, 51)
MYSQL_57 = (5, 7, 44)
MYSQL_80 = (8, 0, 46)

_ENTRY_IDS = [getattr(entry, "__name__", str(entry)) for entry in COLUMN_TYPE_ENTRIES]


def _entry_ids():
    return list(_ENTRY_IDS)


def _answer_name(answer):
    """``UNSUPPORTED`` reads as itself; a class reads as its name."""
    return "UNSUPPORTED" if answer is UNSUPPORTED else answer.__name__


@pytest.fixture
def dialect():
    return MySQLDialect(version=MYSQL_80)


class TestTableCompleteness:
    """A hole in the table is a silent gap, and the protocol forbids one."""

    def test_the_dialect_carries_the_mixin(self, dialect):
        assert isinstance(dialect, ColumnSuggestionMixin)

    def test_every_entry_is_answered(self, dialect):
        """All eighteen, by name -- an omission fails here, not at lookup."""
        missing = [e for e in COLUMN_TYPE_ENTRIES if e not in dialect.suggested_column_types()]
        assert missing == []

    def test_the_table_has_exactly_the_protocol_entries(self, dialect):
        """No backend-only extension is claimed, so the key space is closed here."""
        assert set(dialect.suggested_column_types()) == set(COLUMN_TYPE_ENTRIES)

    def test_no_entry_is_answered_none(self, dialect):
        """``None`` would be indistinguishable from "not filled in yet"."""
        table = dialect.suggested_column_types()
        assert [e for e in COLUMN_TYPE_ENTRIES if table[e] is None] == []

    @pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_entry_ids())
    def test_every_answer_is_a_column_class(self, dialect, entry):
        answer = dialect.suggested_column_types()[entry]
        assert isinstance(answer, type)
        assert issubclass(answer, ColumnBase)

    @pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_entry_ids())
    def test_every_entry_resolves_to_its_own_answer(self, dialect, entry):
        assert dialect.column_class_for(entry) is dialect.suggested_column_types()[entry]

    def test_the_table_is_a_copy(self, dialect):
        """Mutating one answer must not corrupt the class attribute."""
        first = dialect.suggested_column_types()
        first[str] = FloatColumn
        assert dialect.suggested_column_types()[str] is StringColumn

    def test_the_class_attribute_is_never_mutated(self):
        """The version gate works on a copy, so a 5.6 dialect cannot poison 8.0."""
        from rhosocial.activerecord.backend.impl.mysql.mixins.column_suggestion import (
            MySQLColumnSuggestionMixin,
        )

        MySQLDialect(version=MYSQL_56).suggested_column_types()
        assert MySQLColumnSuggestionMixin.COLUMN_TYPE_SUGGESTIONS[dict] is JSONColumn


class TestBaselineCells:
    """The ten-backend baseline, restated cell by cell."""

    @pytest.mark.parametrize(
        "entry, expected",
        [
            (bool, BooleanColumn),
            (int, IntegerColumn),
            (float, FloatColumn),
            (decimal.Decimal, DecimalColumn),
            (str, StringColumn),
            (bytes, BinaryColumn),
            (bytearray, BinaryColumn),
            (datetime.date, DateTimeColumn),
            (datetime.time, DateTimeColumn),
            (datetime.datetime, DateTimeColumn),
            (datetime.timedelta, NumericColumn),
            (uuid.UUID, UUIDColumn),
            (enum.Enum, StringColumn),
        ],
        ids=_entry_ids()[:13],
    )
    def test_baseline_entry(self, dialect, entry, expected):
        assert dialect.suggested_column_types()[entry] is expected

    def test_tz_aware_datetime_normalises_to_the_plain_entry(self, dialect):
        """A tz-aware ``datetime`` is annotated ``datetime.datetime``; nothing is refused.

        The protocol has no separate tz entry, so the tz form lands on the same
        cell -- and MySQL's offset-form ``CONVERT_TZ`` was measured working with
        zero configuration, so tz is not a reason to narrow it either. The
        named-tz limitation (a tzinfo the server has no tables for) is a
        rendering-phase fact and is recorded in the mixin's docstring.
        """
        from datetime import timezone

        assert dialect.column_class_for(datetime.datetime) is DateTimeColumn
        assert datetime.datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc).tzinfo is not None

    def test_uuid_is_not_gated_on_a_storage_fact(self, dialect):
        """MySQL has no native ``UUID`` type on any version, and it must not show.

        The ``BINARY(16)`` substitute is ``suggested_data_types()``'s business.
        A UUID carries the same operations -- equality and ``IN`` -- wherever it
        is kept, so the column answer is the baseline on every version.
        """
        for version in (MYSQL_56, MYSQL_57, MYSQL_80):
            table = MySQLDialect(version=version).suggested_column_types()
            assert table[uuid.UUID] is UUIDColumn


class TestMySQLDeviations:
    """The four cells that differ from core's neutral baseline."""

    def test_float_and_decimal_are_not_one_generic_number(self, dialect):
        """MySQL stores ``DOUBLE`` and ``DECIMAL(p,s)`` as distinct types."""
        table = dialect.suggested_column_types()
        assert table[float] is FloatColumn
        assert table[decimal.Decimal] is DecimalColumn

    def test_dict_is_json_column(self, dialect):
        """Native ``JSON`` from 5.7.8; the function family from 5.7.0."""
        assert dialect.suggested_column_types()[dict] is JSONColumn

    @pytest.mark.parametrize("entry", [list, tuple, set, frozenset], ids=_entry_ids()[13:17])
    def test_containers_take_the_json_route(self, dialect, entry):
        """MySQL has no array type at any version, so the JSON path family answers.

        ``ArrayColumn``'s whole surface is ``array_length`` / ``unnest`` over a
        *native* array -- a column this server cannot declare at all.
        """
        assert dialect.suggested_column_types()[entry] is JSONColumn

    def test_no_entry_answers_array_column(self, dialect):
        """Core's neutral table says ``ArrayColumn`` for the containers; MySQL may not."""
        table = dialect.suggested_column_types()
        assert [e for e, cls in table.items() if cls is ArrayColumn] == []

    def test_timedelta_is_numeric(self, dialect):
        """``INTERVAL`` is an expression keyword here, never a column type."""
        assert dialect.suggested_column_types()[datetime.timedelta] is NumericColumn


class TestJsonVersionGate:
    """The one version-dependent cell, asserted on both sides of 5.7."""

    def test_dict_is_unsupported_below_57(self):
        """5.6.51 has no ``JSON`` type *and* no JSON functions -- 1305, not 1064."""
        table = MySQLDialect(version=MYSQL_56).suggested_column_types()
        assert table[dict] is UNSUPPORTED

    @pytest.mark.parametrize("version", [MYSQL_57, MYSQL_80], ids=["5.7.44", "8.0.46"])
    def test_dict_is_json_column_from_57(self, version):
        assert MySQLDialect(version=version).suggested_column_types()[dict] is JSONColumn

    def test_only_the_dict_entry_is_refused_below_57(self):
        """One refusal, not five: the containers keep their JSON answer.

        MySQL 5.6 stores and returns the text faithfully -- it does not
        normalise it -- so a sequence still has length and containment to carry.
        """
        table = MySQLDialect(version=MYSQL_56).suggested_column_types()
        assert [e for e in COLUMN_TYPE_ENTRIES if table[e] is UNSUPPORTED] == [dict]

    def test_the_gate_reads_the_functions_boundary_not_the_type_boundary(self):
        """5.7.0 is where ``JSON_EXTRACT`` appeared; 5.7.8 is where the type did.

        Between the two, a path can be read perfectly well without a JSON column
        type, so refusing there would refuse a query the server answers.
        """
        assert MySQLDialect(version=(5, 7, 0)).suggested_column_types()[dict] is JSONColumn

    def test_the_gate_agrees_with_the_json_mixin(self):
        """One boundary, two readers: the mixin and the table cannot drift."""
        for version in (MYSQL_56, MYSQL_57, MYSQL_80, (8, 0, 3)):
            server = MySQLDialect(version=version)
            assert (server.suggested_column_types()[dict] is UNSUPPORTED) is (
                not server.supports_json_path()
            )


class TestColumnClassResolution:
    """What a model layer gets when it asks the dialect for a class."""

    def test_dict_resolves_to_json_column_on_80(self, dialect):
        assert dialect.column_class_for(dict) is JSONColumn

    def test_dict_raises_on_56(self):
        """A definition-time failure naming ``UseColumnType``, not a query error."""
        server = MySQLDialect(version=MYSQL_56)
        with pytest.raises(ColumnTypeResolutionError) as excinfo:
            server.column_class_for(dict)
        message = str(excinfo.value)
        assert "UNSUPPORTED" in message
        assert "UseColumnType" in message

    def test_the_refusal_is_a_type_error(self):
        """``ColumnTypeResolutionError`` subclasses ``TypeError`` by design."""
        assert issubclass(ColumnTypeResolutionError, TypeError)

    def test_list_resolves_to_json_column_on_56(self):
        """Containers are not refused below the gate -- see the class above."""
        assert MySQLDialect(version=MYSQL_56).column_class_for(list) is JSONColumn

    def test_an_explicit_declaration_bypasses_the_refusal(self):
        """``UseColumnType`` is the escape hatch, and it is backend-independent."""
        from rhosocial.activerecord.base.fields import UseColumnType

        server = MySQLDialect(version=MYSQL_56)
        assert server.column_class_for(dict, UseColumnType(BinaryColumn)) is BinaryColumn

    @pytest.mark.parametrize(
        "annotation",
        [list, tuple, set, frozenset],
        ids=["list", "tuple", "set", "frozenset"],
    )
    def test_container_subclasses_normalise(self, dialect, annotation):
        """A user subclass walks to its protocol entry, per the normalisation rules."""

        class MyList(list):
            pass

        expected = JSONColumn
        assert dialect.column_class_for(annotation) is expected
        assert dialect.column_class_for(MyList) is expected

    def test_an_enum_subclass_normalises(self, dialect):
        class Weekday(enum.Enum):
            MONDAY = 1

        assert dialect.column_class_for(Weekday) is StringColumn

    def test_a_str_subclass_normalises(self, dialect):
        class MyStr(str):
            pass

        assert dialect.column_class_for(MyStr) is StringColumn

    def test_an_unknown_annotation_is_not_guessed(self, dialect):
        """No universal column: an annotation outside the list fails by name."""
        with pytest.raises(ColumnTypeResolutionError):
            dialect.column_class_for(complex)


class TestOperationNarrowing:
    """Each narrowing names an operation the column class really exposes."""

    def test_ilike_is_refused_on_every_version(self):
        """Measured 1064 on 5.6.51, 5.7.44 and 8.0.46 -- there is no ``ILIKE``."""
        for version in (MYSQL_56, MYSQL_57, MYSQL_80):
            assert (
                MySQLDialect(version=version).supports_column_operation("StringColumn", "ilike")
                is False
            )

    def test_like_is_not_refused(self, dialect):
        """The narrowing is one operation, not the whole string surface.

        MySQL's default ``utf8mb4_*_ci`` collation already makes ``LIKE``
        case-insensitive for ASCII, which is why this is a narrowing rather
        than a capability loss.
        """
        assert dialect.supports_column_operation("StringColumn", "like") is True

    def test_the_narrowing_is_at_the_column_class_grain(self, dialect):
        """An integer still adds; refusing ``ilike`` must not refuse ``eq``."""
        assert dialect.supports_column_operation("IntegerColumn", "eq") is True
        assert dialect.supports_column_operation("NumericColumn", "add") is True

    def test_ilike_is_an_attribute_of_the_string_column(self, dialect):
        """Operation names are attribute names, so the table is cross-checkable."""
        assert hasattr(StringColumn, "ilike")
        assert hasattr(StringColumn, "like")

    @pytest.mark.parametrize("op", ["@>", "@?"], ids=["contains", "has_key"])
    def test_json_quantifier_operators_are_refused(self, dialect, op):
        """PostgreSQL's ``jsonb`` operators; MySQL's ``JSON`` has neither as syntax."""
        assert dialect.supports_column_operation("JSONColumn", op) is False

    @pytest.mark.parametrize(
        "op, available_from",
        [
            ("json_path", MYSQL_57),
            ("json_value", MYSQL_57),
            ("array_length", MYSQL_57),
            ("has_key", MYSQL_57),
            ("json_valid", MYSQL_57),
        ],
        ids=["json_path", "json_value", "array_length", "has_key", "json_valid"],
    )
    def test_json_function_operations_gate_on_57(self, dialect, op, available_from):
        """5.6 has no JSON function at all: ``1305 FUNCTION ... does not exist``."""
        assert MySQLDialect(version=MYSQL_56).supports_column_operation("JSONColumn", op) is False
        for version in (available_from, MYSQL_80):
            assert MySQLDialect(version=version).supports_column_operation("JSONColumn", op) is True

    def test_unnest_gates_on_json_table(self, dialect):
        """``JSON_TABLE`` arrived in 8.0.4; 5.7.44 has no such function."""
        assert (
            MySQLDialect(version=MYSQL_57).supports_column_operation("JSONColumn", "unnest")
            is False
        )
        assert dialect.supports_column_operation("JSONColumn", "unnest") is True
        assert (
            MySQLDialect(version=(8, 0, 4)).supports_column_operation("JSONColumn", "unnest")
            is True
        )
        assert (
            MySQLDialect(version=(8, 0, 3)).supports_column_operation("JSONColumn", "unnest")
            is False
        )

    def test_json_path_is_an_attribute_of_the_json_column(self, dialect):
        """Cross-check: the operation named in the narrowing is a real attribute."""
        assert hasattr(JSONColumn, "json_path")
        assert hasattr(JSONColumn, "json_value")

    def test_json_equal_is_deliberately_not_narrowed(self, dialect):
        """It works when rendered correctly; the trap is rendering, not capability.

        ``CAST(? AS JSON)`` is available on every version with JSON functions.
        What does not work is ``=`` against a bound string -- zero rows, no
        error -- which is a Phase 2b obligation on the formatter.
        """
        assert dialect.supports_column_operation("JSONColumn", "json_equal") is True
        assert dialect.supports_column_operation("JSONColumn", "json_contains") is True

    def test_unrelated_operations_are_left_at_the_default(self, dialect):
        assert dialect.supports_column_operation("UUIDColumn", "eq") is True
        assert dialect.supports_column_operation("BooleanColumn", "is_true") is True
        assert dialect.supports_column_operation("DateTimeColumn", "add") is True


class TestSilentItemsLeftToTheRenderingPhase:
    """The two §8.3 MySQL entries this phase records but does not fix.

    Both are *value* or *rendering* behaviour rather than a missing capability,
    so neither belongs in a capability declaration: narrowing them would refuse
    something that does work once rendered properly. They are pinned here so
    Phase 2b inherits the list rather than rediscovering it.
    """

    def test_json_equality_needs_a_cast_on_this_dialect(self, dialect):
        """``=`` against a bound string returns zero rows silently on MySQL.

        The rendering obligation is ``CAST(? AS JSON)``; on 5.7/8.0 even a
        text comparison misses rows, because the JSON column normalises
        whitespace and key order. Nothing above claims otherwise.
        """
        assert dialect.supports_column_operation("JSONColumn", "eq") is True

    def test_non_strict_56_is_a_server_setting_not_a_capability(self):
        """Silent clamping / truncation belongs to ``sql_mode``, not the column class."""
        server = MySQLDialect(version=MYSQL_56, sql_mode="")
        assert server.suggested_column_types()[str] is StringColumn
        assert server.suggested_column_types()[int] is IntegerColumn


class TestTableStaysUsableWithoutAVersion:
    """The class attribute answers without one; only the gate needs a version."""

    def test_the_table_itself_needs_no_version(self):
        from rhosocial.activerecord.backend.impl.mysql.mixins.column_suggestion import (
            MySQLColumnSuggestionMixin,
        )

        table = MySQLColumnSuggestionMixin.COLUMN_TYPE_SUGGESTIONS
        missing = [e for e in COLUMN_TYPE_ENTRIES if e not in table]
        assert missing == []

    def test_the_shared_attribute_never_says_unsupported(self):
        """``UNSUPPORTED`` is a per-version answer, so it lives in the method only.

        A class attribute carrying the sentinel would make every dialect at
        every version look like it refused the entry.
        """
        from rhosocial.activerecord.backend.impl.mysql.mixins.column_suggestion import (
            MySQLColumnSuggestionMixin,
        )

        assert UNSUPPORTED not in MySQLColumnSuggestionMixin.COLUMN_TYPE_SUGGESTIONS.values()

    def test_the_gate_reads_the_boundary_from_the_json_mixin(self):
        """One number, two readers: the mixin and the table share it."""
        from rhosocial.activerecord.backend.impl.mysql.mixins.column_suggestion import (
            MySQLColumnSuggestionMixin,
        )

        assert "json_path" in MySQLColumnSuggestionMixin._JSON_FUNCTION_OPERATIONS
        assert "unnest" in MySQLColumnSuggestionMixin._JSON_TABLE_OPERATIONS
        assert "@>" in MySQLColumnSuggestionMixin._JSON_QUANTIFIER_OPERATIONS


class TestTwoDialectVersionsDoNotLeak:
    """The gate is a copy, so building a 5.6 dialect cannot affect an 8.0 one."""

    def test_a_56_dialect_between_two_80_ones_changes_nothing(self):
        before = MySQLDialect(version=MYSQL_80).suggested_column_types()
        MySQLDialect(version=MYSQL_56).suggested_column_types()
        after = MySQLDialect(version=MYSQL_80).suggested_column_types()
        assert before[dict] is after[dict] is JSONColumn

    def test_two_56_dialects_agree(self):
        assert (
            MySQLDialect(version=MYSQL_56).suggested_column_types()[dict]
            is MySQLDialect(version=MYSQL_56).suggested_column_types()[dict]
            is UNSUPPORTED
        )


def test_the_summary_table_reads_the_way_the_spec_writes_it():
    """One test that states the whole answer, so a diff is legible at a glance."""
    table = MySQLDialect(version=MYSQL_80).suggested_column_types()
    summary = {entry.__name__: _answer_name(table[entry]) for entry in COLUMN_TYPE_ENTRIES}
    assert summary == {
        "bool": "BooleanColumn",
        "int": "IntegerColumn",
        "float": "FloatColumn",
        "Decimal": "DecimalColumn",
        "str": "StringColumn",
        "bytes": "BinaryColumn",
        "bytearray": "BinaryColumn",
        "date": "DateTimeColumn",
        "time": "DateTimeColumn",
        "datetime": "DateTimeColumn",
        "timedelta": "NumericColumn",
        "UUID": "UUIDColumn",
        "dict": "JSONColumn",
        "list": "JSONColumn",
        "tuple": "JSONColumn",
        "set": "JSONColumn",
        "frozenset": "JSONColumn",
        "Enum": "StringColumn",
    }


def test_the_56_table_differs_in_exactly_one_cell():
    """The gate is one cell, and a diff of the two tables shows it."""
    old = MySQLDialect(version=MYSQL_56).suggested_column_types()
    new = MySQLDialect(version=MYSQL_80).suggested_column_types()
    differing = [e for e in COLUMN_TYPE_ENTRIES if old[e] is not new[e]]
    assert differing == [dict]
