# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_column_type.py
"""MySQL's eighteen-entry column-type table and its version gate.

Pure dialect tests -- no server, no connection. What is asserted here is the
*declaration*: that the table answers every entry of the protocol's common
list, that the cells MySQL deviates on are the ones the live-server sweep
measured, that the one version gate fires on both sides of the boundary, and
that any refusal is a deliberate answer rather than an omission.

The rendering those cells imply is Phase 2b's work and is deliberately not
asserted here -- with the one named exception that is *not* rendering but
capability: the ``dict`` refusal below 5.7 (measured ``1305 FUNCTION ... does
not exist``).
"""

import datetime
import decimal
import enum
import uuid

import pytest

from rhosocial.activerecord.backend.dialect.mixins import ColumnTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import ColumnTypeSupport
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    TimestampColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)
from rhosocial.activerecord.base.field_proxy import ColumnTypeResolutionError
from rhosocial.activerecord.base.fields import UseColumnType
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.mixins.column_type import (
    MYSQL_COLUMN_TYPES,
)

from rhosocial.activerecord.testsuite.feature.query.typed_column.column_helpers import (
    COMMON_TYPES,
)

#: The versions the live sweep behind this table ran against. 5.6.51 and 5.7.44
#: are the two ends of the JSON gate; 8.0.46 is the mainstream server.
MYSQL_56 = (5, 6, 51)
MYSQL_57 = (5, 7, 44)
MYSQL_80 = (8, 0, 46)

_ENTRY_IDS = [getattr(entry, "__name__", str(entry)) for entry in COMMON_TYPES]


def _entry_ids():
    return list(_ENTRY_IDS)


def _answer_name(answer):
    """``None`` reads as itself; a class reads as its name."""
    return "None" if answer is None else answer.__name__


@pytest.fixture
def dialect():
    return MySQLDialect(version=MYSQL_80)


def _select(dialect, annotation, declared=None):
    """The model layer's own selection step, invoked without a model.

    ``Model.c.<field>`` asks the field accessor to pick the class the active
    backend answers; this is that step, so a failure here is the failure the
    model layer would raise rather than a test-only shortcut.
    """
    from rhosocial.activerecord.base.field_proxy import FieldAccessor

    return FieldAccessor._select_column_class(dialect, annotation, declared)


class TestTableCompleteness:
    """A hole in the table is a silent gap, and the protocol forbids one."""

    def test_the_dialect_carries_the_mixin(self, dialect):
        assert isinstance(dialect, ColumnTypeSupport)
        assert isinstance(dialect, ColumnTypeMixin)

    def test_every_entry_is_answered(self, dialect):
        """All eighteen, by name -- an omission fails here, not at lookup."""
        missing = [e for e in COMMON_TYPES if e not in dialect.suggested_column_types()]
        assert missing == []

    def test_the_table_has_exactly_the_protocol_entries(self, dialect):
        """No backend-only extension is claimed, so the key space is closed here."""
        assert set(dialect.suggested_column_types()) == set(COMMON_TYPES)

    def test_no_entry_is_answered_none_on_a_modern_server(self, dialect):
        """8.0 answers all eighteen; a ``None`` here would be a refusal of a
        value this server demonstrably carries."""
        table = dialect.suggested_column_types()
        assert [e for e in COMMON_TYPES if table[e] is None] == []

    @pytest.mark.parametrize("entry", COMMON_TYPES, ids=_entry_ids())
    def test_every_answer_is_a_column_class_or_none(self, dialect, entry):
        """The protocol's two answer states, one entry at a time."""
        answer = dialect.suggested_column_types()[entry]
        assert answer is None or (
            isinstance(answer, type) and issubclass(answer, ColumnBase)
        )

    @pytest.mark.parametrize("entry", COMMON_TYPES, ids=_entry_ids())
    def test_every_entry_resolves_to_its_own_answer(self, dialect, entry):
        answer = dialect.suggested_column_types()[entry]
        if answer is None:
            pytest.skip("refused below the gate; asserted in TestJsonVersionGate")
        assert _select(dialect, entry) is answer

    def test_the_table_is_a_copy(self, dialect):
        """Mutating one answer must not corrupt the class attribute."""
        first = dialect.suggested_column_types()
        first[str] = NumericColumn
        assert dialect.suggested_column_types()[str] is StringColumn

    def test_the_class_attribute_is_never_mutated(self):
        """The version gate works on a copy, so a 5.6 dialect cannot poison 8.0."""
        MySQLDialect(version=MYSQL_56).suggested_column_types()
        assert MYSQL_COLUMN_TYPES[dict] is JSONColumn

    def test_the_class_attribute_carries_no_refusal(self):
        """``None`` is a per-version answer, so it lives in the method only.

        A class attribute carrying a refusal would make every dialect at every
        version look like it refused the entry.
        """
        assert None not in MYSQL_COLUMN_TYPES.values()


class TestBaselineCells:
    """The portable baseline, restated cell by cell."""

    @pytest.mark.parametrize(
        "entry, expected",
        [
            (bool, BooleanColumn),
            (int, IntegerColumn),
            (float, NumericColumn),
            (decimal.Decimal, NumericColumn),
            (str, StringColumn),
            (bytes, BinaryColumn),
            (bytearray, BinaryColumn),
            (datetime.date, TimestampColumn),
            (datetime.time, TimestampColumn),
            (datetime.datetime, TimestampColumn),
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

        assert _select(dialect, datetime.datetime) is TimestampColumn
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
    """The cells that differ from the portable baseline."""

    def test_float_and_decimal_are_both_numbers(self, dialect):
        """MySQL stores ``DOUBLE`` and ``DECIMAL(p,s)`` as distinct types.

        That measurement is recorded on the DDL side, where the two are still
        two classes; core now models both width families with one
        :class:`NumericColumn`, because the operation surface is the same and
        the width belongs to the ``DataType``. Asserting the shared answer keeps
        the merge deliberate rather than an accident of the refactor.
        """
        table = dialect.suggested_column_types()
        assert table[float] is NumericColumn
        assert table[decimal.Decimal] is NumericColumn

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
        """The portable baseline says ``ArrayColumn`` for the containers; MySQL may not."""
        table = dialect.suggested_column_types()
        assert [e for e, cls in table.items() if cls is ArrayColumn] == []

    def test_timedelta_is_numeric(self, dialect):
        """``INTERVAL`` is an expression keyword here, never a column type."""
        assert dialect.suggested_column_types()[datetime.timedelta] is NumericColumn


class TestJsonVersionGate:
    """The one version-dependent answer, asserted on both sides of 5.7."""

    def test_dict_is_refused_below_57(self):
        """5.6.51 has no ``JSON`` type *and* no JSON functions -- 1305, not 1064."""
        table = MySQLDialect(version=MYSQL_56).suggested_column_types()
        assert table[dict] is None

    @pytest.mark.parametrize("version", [MYSQL_57, MYSQL_80], ids=["5.7.44", "8.0.46"])
    def test_dict_is_json_column_from_57(self, version):
        assert MySQLDialect(version=version).suggested_column_types()[dict] is JSONColumn

    def test_only_the_dict_entry_is_refused_below_57(self):
        """One refusal, not five: the containers keep their JSON answer.

        MySQL 5.6 stores and returns the text faithfully -- it does not
        normalise it -- so a sequence still has length and containment to carry.
        """
        table = MySQLDialect(version=MYSQL_56).suggested_column_types()
        assert [e for e in COMMON_TYPES if table[e] is None] == [dict]

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
            assert (server.suggested_column_types()[dict] is None) is (
                not server.supports_json_path()
            )


class TestColumnClassResolution:
    """What a model layer gets when it asks the dialect for a class."""

    def test_dict_resolves_to_json_column_on_80(self, dialect):
        assert _select(dialect, dict) is JSONColumn

    def test_dict_raises_on_56(self):
        """A definition-time failure naming ``UseColumnType``, not a query error."""
        server = MySQLDialect(version=MYSQL_56)
        with pytest.raises(ColumnTypeResolutionError) as excinfo:
            _select(server, dict)
        message = str(excinfo.value)
        assert "no column class for" in message
        assert "UseColumnType" in message

    def test_the_refusal_names_the_type_that_has_no_answer(self):
        """The message says which entry was refused, not just that one was."""
        server = MySQLDialect(version=MYSQL_56)
        with pytest.raises(ColumnTypeResolutionError) as excinfo:
            _select(server, dict)
        assert "dict" in str(excinfo.value)

    def test_the_refusal_is_a_type_error(self):
        """``ColumnTypeResolutionError`` subclasses ``TypeError`` by design."""
        assert issubclass(ColumnTypeResolutionError, TypeError)

    def test_list_resolves_to_json_column_on_56(self):
        """Containers are not refused below the gate -- see the class above."""
        assert _select(MySQLDialect(version=MYSQL_56), list) is JSONColumn

    def test_an_explicit_declaration_bypasses_the_refusal(self):
        """``UseColumnType`` is the escape hatch, and it is backend-independent."""
        server = MySQLDialect(version=MYSQL_56)
        assert _select(server, dict, UseColumnType(BinaryColumn)) is BinaryColumn

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
        assert _select(dialect, annotation) is expected
        assert _select(dialect, MyList) is expected

    def test_an_enum_subclass_normalises(self, dialect):
        class Weekday(enum.Enum):
            MONDAY = 1

        assert _select(dialect, Weekday) is StringColumn

    def test_a_str_subclass_normalises(self, dialect):
        class MyStr(str):
            pass

        assert _select(dialect, MyStr) is StringColumn

    def test_an_unknown_annotation_is_not_guessed(self, dialect):
        """No universal column: an annotation outside the list fails by name."""
        with pytest.raises(ColumnTypeResolutionError):
            _select(dialect, complex)


class TestSilentItemsLeftToTheRenderingPhase:
    """The two §8.3 MySQL entries this phase records but does not fix.

    Both are *value* or *rendering* behaviour rather than a missing capability,
    so neither belongs in a column-type answer: refusing them would refuse
    something that does work once rendered properly. They are pinned here so
    Phase 2b inherits the list rather than rediscovering it.
    """

    def test_json_equality_needs_a_cast_on_this_dialect(self):
        """``=`` against a bound string returns zero rows silently on MySQL.

        The rendering obligation is ``CAST(? AS JSON)``; on 5.7/8.0 even a
        text comparison misses rows, because the JSON column normalises
        whitespace and key order. Both facts are recorded next to the ``dict``
        entry so the formatter inherits them -- and the entry is still answered
        with a class, because the capability is there and only the spelling is
        missing.
        """
        import inspect

        import rhosocial.activerecord.backend.impl.mysql.mixins.column_type as module

        source = inspect.getsource(module)
        assert "CAST(? AS JSON)" in source
        assert "zero rows" in source

    def test_non_strict_56_is_a_server_setting_not_a_capability(self):
        """Silent clamping / truncation belongs to ``sql_mode``, not the column class."""
        server = MySQLDialect(version=MYSQL_56, sql_mode="")
        assert server.suggested_column_types()[str] is StringColumn
        assert server.suggested_column_types()[int] is IntegerColumn


class TestTableStaysUsableWithoutAVersion:
    """The class attribute answers without one; only the gate needs a version."""

    def test_the_table_itself_needs_no_version(self):
        table = MYSQL_COLUMN_TYPES
        missing = [e for e in COMMON_TYPES if e not in table]
        assert missing == []

    def test_the_mixin_overrides_the_table_method(self):
        """The gate is an override, not an inherited default."""
        from rhosocial.activerecord.backend.impl.mysql.mixins import (
            MySQLColumnTypeMixin,
        )

        assert (
            MySQLColumnTypeMixin.suggested_column_types
            is not ColumnTypeMixin.suggested_column_types
        )
        assert (
            MySQLColumnTypeMixin.suggested_extra_column_types
            is ColumnTypeMixin.suggested_extra_column_types
        )


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
            is None
        )


def test_the_summary_table_reads_the_way_the_spec_writes_it():
    """One test that states the whole answer, so a diff is legible at a glance."""
    table = MySQLDialect(version=MYSQL_80).suggested_column_types()
    summary = {entry.__name__: _answer_name(table[entry]) for entry in COMMON_TYPES}
    assert summary == {
        "bool": "BooleanColumn",
        "int": "IntegerColumn",
        "float": "NumericColumn",
        "Decimal": "NumericColumn",
        "str": "StringColumn",
        "bytes": "BinaryColumn",
        "bytearray": "BinaryColumn",
        "date": "TimestampColumn",
        "time": "TimestampColumn",
        "datetime": "TimestampColumn",
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
    differing = [e for e in COMMON_TYPES if old[e] is not new[e]]
    assert differing == [dict]


def test_the_mixin_module_docstring_names_the_contract_list():
    """The module says where the entry contract lives, after the move.

    ``COLUMN_TYPE_ENTRIES``, ``UNSUPPORTED`` and the operation-narrowing method
    were all deleted from the core protocol; a docstring still citing any of
    them is a docstring describing a protocol that no longer exists.
    """
    import rhosocial.activerecord.backend.impl.mysql.mixins.column_type as module

    doc = module.__doc__ or ""
    assert "column_helpers" in doc
    assert "COLUMN_TYPE_ENTRIES" not in doc
    assert "UNSUPPORTED" not in doc
    assert "supports_column_operation" not in doc
    assert "column_suggestion" not in doc
