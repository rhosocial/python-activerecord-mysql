# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_type_protocol.py
"""
MySQL type protocol conformance tests.

Verifies the two-level data-type contract between the core ``DataType``
system and the MySQL backend:

- ``supports_data_type_<name>`` / ``format_data_type_<name>`` 1:1
  correspondence on ``MySQLDialect``;
- ``supports_data_types()`` merges the ``mysql_*`` namespaced family with
  the core family;
- ``suggested_data_types()`` values are real ``DataType`` classes and its
  keys are disjoint from the supported keys;
- every core concept is either rendered or substituted (D9), with the
  substitutions MySQL genuinely needs spelled out;
- every ``format_data_type_<name>`` that takes a spelling says which
  spellings it accepts, and refuses the rest by naming them (D9 rule 3);
- ``parse_type()`` is canonical: one concept in, one class out, with the
  word that was used carried on the instance (D8);
- the five integer widths render ``[UNSIGNED] [ZEROFILL]`` in MySQL's own
  order and round-trip through ``parse_type`` unchanged, with ``MEDIUMINT``
  named as the 3-byte width it is rather than as a 4-byte ``INT``;
- the MySQL-exclusive type families are stated as a ``MySQLTypeSupport``
  protocol and the dialect satisfies it;
- ``MySQLEnumType`` renders ``ENUM('a','b')`` (with charset/collation
  extensions);
- dialect-specific range checks live in the formatters (DECIMAL
  precision/scale, the FLOAT(p) refusal, fractional-seconds precision);
- ``dialect_options`` forwards through construction and participates in
  equality.
"""

import inspect
import re

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import (
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.dialect.mixins import DataTypeMixin
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    DataType,
    CustomType,
    DecimalType,
    DoubleType,
    EnumType,
    FloatType,
    IntegerType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimestampType,
    TinyIntType,
    UUIDType,
    VarCharType,
    XmlType,
)
import rhosocial.activerecord.backend.expression.types as core_types
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLBigIntType,
    MySQLBinaryType,
    MySQLBitType,
    MySQLBlobType,
    MySQLEnumType,
    MySQLGeometryCollectionType,
    MySQLGeometryType,
    MySQLIntType,
    MySQLLongBlobType,
    MySQLLongTextType,
    MySQLMediumBlobType,
    MySQLMediumIntType,
    MySQLMediumTextType,
    MySQLSetType,
    MySQLSignedType,
    MySQLSmallIntType,
    MySQLTextType,
    MySQLTinyBlobType,
    MySQLTinyIntType,
    MySQLTinyTextType,
    MySQLUnsignedType,
    MySQLUUIDType,
    MySQLVarBinaryType,
    MySQLVectorType,
    MySQLYearType,
)
from rhosocial.activerecord.backend.impl.mysql.protocols import MySQLTypeSupport


@pytest.fixture
def dialect():
    return MySQLDialect()


class TestSupportFormatCorrespondence:
    """Every format_data_type_<name> has supports_data_type_<name>, 1:1."""

    def test_format_family_equals_supports_family(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MySQLDialect)
            if member.startswith("format_data_type_")
        }
        support_names = {
            member[len("supports_data_type_"):]
            for member in dir(MySQLDialect)
            if member.startswith("supports_data_type_")
        }
        assert format_names, "MySQLDialect must implement format_data_type_* members"
        assert format_names == support_names

    def test_supports_data_types_covers_every_formatter(self, dialect):
        format_names = {
            member[len("format_data_type_"):]
            for member in dir(MySQLDialect)
            if member.startswith("format_data_type_")
        }
        supported = dialect.supports_data_types()
        assert set(supported) == format_names

    def test_supports_data_types_returns_classes(self, dialect):
        for name, klass in dialect.supports_data_types().items():
            assert isinstance(klass, type), name
            assert issubclass(klass, DataType), name

    def test_inherits_mixin_scan_implementation(self, dialect):
        # The merge comes from DataTypeMixin's scan-based
        # supports_data_types(); MySQL only declares the per-type pairs.
        assert MySQLDialect.supports_data_types is DataTypeMixin.supports_data_types


class TestSupportsDataTypesMapping:
    """supports_data_types() merges mysql_* namespaced and core entries."""

    def test_includes_mysql_namespaced_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "mysql_int" in supported
        assert supported["mysql_int"] is MySQLIntType
        assert "mysql_enum" in supported
        assert "mysql_set" in supported
        assert "mysql_vector" in supported

    def test_includes_core_entries(self, dialect):
        supported = dialect.supports_data_types()
        assert "integer" in supported
        assert supported["integer"] is IntegerType
        assert "varchar" in supported
        assert "decimal" in supported
        assert "json" in supported

    def test_per_type_support_methods_are_truthful(self, dialect):
        supported = dialect.supports_data_types()
        for name in supported:
            checker = getattr(dialect, f"supports_data_type_{name}")
            assert checker() is True, name


class TestSuggestedDataTypes:
    """suggested_data_types(): real classes, disjoint from supported keys."""

    def test_values_are_data_type_classes(self, dialect):
        suggestions = dialect.suggested_data_types()
        for key, klass in suggestions.items():
            assert isinstance(klass, type), key
            assert issubclass(klass, DataType), key

    def test_keys_disjoint_from_supported(self, dialect):
        suggestions = dialect.suggested_data_types()
        supported = dialect.supports_data_types()
        assert not (set(suggestions) & set(supported))

    def test_uuid_is_suggested_as_a_sixteen_byte_binary(self, dialect):
        """MySQL has no UUID type, so the substitute is 16 raw bytes.

        **What was wrong.** This used to be
        ``suggested_data_types()["uuid"] is MySQLBinaryType`` — the *general*
        byte-string class — which renders ``BINARY`` when given no length. MySQL
        defines that: "An optional length *M* represents the column length in
        bytes. **If omitted, *M* defaults to 1.**" (manual §13.3.1). Every
        scenario server confirms it: ``CREATE TABLE t (c BINARY)`` reports
        ``binary(1)`` in ``information_schema.COLUMNS.COLUMN_TYPE``.

        So a caller who asked for a UUID column got a **one-byte** column,
        silently and with no error from the server either — inserting a 16-byte
        UUID fails with error 1406, or on a non-strict server truncates to its
        first byte. The mapping names a *class* and the generic ``UUIDType``
        carries no length to hand over, so the substitute has to be a class
        whose width is its own: :class:`MySQLUUIDType`.
        """
        suggestions = dialect.suggested_data_types()
        assert "uuid" in suggestions
        assert suggestions["uuid"] is MySQLUUIDType
        # Constructible with no arguments, because the width is a property of
        # the concept rather than something the caller has to supply.
        assert MySQLUUIDType(dialect).to_sql() == ("BINARY(16)", ())

    def test_the_uuid_substitute_holds_the_whole_uuid(self, dialect):
        """128 bits is 16 bytes, and the column is that wide.

        Asserted as arithmetic as well as as SQL, so the number cannot drift
        away from the rendering without a test noticing.
        """
        assert MySQLUUIDType.BYTE_LENGTH * 8 == 128
        assert MySQLUUIDType.BYTE_LENGTH == 16
        assert dialect.format_data_type(MySQLUUIDType(dialect))[0] == "BINARY(16)"

    def test_the_uuid_substitute_is_not_the_one_byte_binary(self, dialect):
        """The regression, pinned as the negative.

        ``MySQLBinaryType`` still renders a bare ``BINARY`` for a caller that
        asks for no length — that is legal and means one byte — which is exactly
        why the substitution had to stop pointing at it.
        """
        assert MySQLBinaryType(dialect).to_sql() == ("BINARY", ())
        assert MySQLUUIDType(dialect).to_sql()[0] != MySQLBinaryType(dialect).to_sql()[0]

    def test_the_uuid_substitute_is_the_uuid_concept(self, dialect):
        """Inheritance means identity: a UUID column is a ``UUIDType``.

        A caller asking "is this column a UUID?" gets one answer, whatever the
        backend. What MySQL stores — the 16 bytes — is a rendering detail and
        belongs in the formatter, not in the identity.
        """
        substitute = dialect.suggested_data_types()["uuid"]
        assert issubclass(substitute, UUIDType)
        assert isinstance(MySQLUUIDType(dialect), UUIDType)
        assert substitute.name == "mysql_uuid"
        assert substitute.name in dialect.supports_data_types()

    def test_the_uuid_substitute_round_trips_through_parse_type(self, dialect):
        """Render it, feed the rendered word back, get an equal value object.

        ``DataType.__eq__`` is class-exact, so this only holds if ``parse_type``
        recognises what the formatter emits. Before the fix the substitution
        rendered ``BINARY`` and parsed back to a ``MySQLBinaryType(length=None)``
        — equal by luck, while rendering a column that could not hold a UUID.
        """
        declared = dialect.suggested_data_types()["uuid"](dialect)
        rendered = declared.to_sql()[0]
        assert dialect.parse_type(rendered) == declared
        assert type(dialect.parse_type(rendered)) is MySQLUUIDType

    def test_binary_sixteen_introspects_as_the_uuid_type(self, dialect):
        """``BINARY(16)`` on the wire is this backend's UUID type.

        ``information_schema.COLUMNS.COLUMN_TYPE`` reports ``binary(16)``, so
        this is the string introspection hands to ``parse_type``. Reading it as
        a plain byte string would leave the declared UUID type unequal to its
        own column in any schema diff. It is the same width-specific reading
        the framework already applies to ``TINYINT(1)`` -> ``BooleanType``: a
        16-byte column that is not meant to be a UUID is now named
        ``mysql_uuid``, with the storage unchanged either way.
        """
        parsed = dialect.parse_type("BINARY(16)")
        assert isinstance(parsed, MySQLUUIDType)
        assert parsed.to_sql() == ("BINARY(16)", ())
        # ... and the neighbouring widths are untouched.
        for raw, klass in (("BINARY(1)", MySQLBinaryType),
                           ("BINARY(4)", MySQLBinaryType),
                           ("BINARY(32)", MySQLBinaryType),
                           ("BINARY", MySQLBinaryType)):
            assert type(dialect.parse_type(raw)) is klass, raw
            assert dialect.parse_type(raw).to_sql()[0] == raw

    def test_a_bare_binary_still_renders_bare_binary(self, dialect):
        """No existing rendering moves.

        ``BINARY`` with no length is a legal MySQL column and the manual defines
        what it means (one byte), so this dialect keeps writing it and keeps
        reading it back.
        """
        assert dialect.format_data_type(MySQLBinaryType(dialect))[0] == "BINARY"
        assert dialect.parse_type("BINARY") == MySQLBinaryType(dialect)
        assert dialect.format_data_type(MySQLBinaryType(dialect, 16))[0] == "BINARY(16)"

    def test_varbinary_requires_its_length(self, dialect):
        """``VARBINARY`` has no lengthless form, so neither does the type.

        MySQL's grammar is ``VARBINARY(M)`` with *M* mandatory (manual §13.3.1)
        and ``CREATE TABLE t (c VARBINARY)`` is a syntax error — error 1064 on
        every server checked, 5.6.51 through 26.7.0. Emitting ``VARBINARY`` for
        a value object with no length produced DDL the server refuses, so the
        constructor rejects it instead, the same way ``MySQLVectorType`` requires
        its ``dim`` and ``MySQLEnumType`` its ``values``.
        """
        assert dialect.format_data_type(MySQLVarBinaryType(dialect, 16)) == (
            "VARBINARY(16)", ()
        )
        with pytest.raises(ValueError, match="requires a length"):
            MySQLVarBinaryType(dialect)
        # A hand-written lengthless string is refused rather than guessed at.
        assert isinstance(dialect.parse_type("VARBINARY"), CustomType)

    def test_enum_is_rendered_not_suggested(self, dialect):
        """MySQL has a native ENUM, so the generic type is renderable here.

        It used to be suggested as MySQLEnumType, which is a mapping meaning
        "I cannot render this, use that instead" — said by a dialect that can.
        A name in both sets is one of the two being a lie, so the generic type
        is rendered and the suggestion went.
        """
        suggestions = dialect.suggested_data_types()
        assert "enum" not in suggestions
        assert dialect.supports_data_types()["enum"] is EnumType

    def test_xml_is_suggested_as_text(self, dialect):
        """MySQL has no XML type, and stores an XML document as text.

        ``suggested_data_types()["xml"]`` is the honest statement of that: not
        a compromise, and not silence. ``TextType`` is a type this dialect
        really renders, which is what makes the suggestion usable.
        """
        suggestions = dialect.suggested_data_types()
        assert "xml" in suggestions
        assert suggestions["xml"] is TextType
        # The concept itself is *not* renderable — that is why it is suggested,
        # and the error a caller gets has to say which substitute to use.
        assert "xml" not in dialect.supports_data_types()
        with pytest.raises(TypeError, match="TextType"):
            dialect.format_data_type(XmlType(dialect))

    def test_array_is_suggested_as_json(self, dialect):
        """MySQL has no array type; a list column is a JSON document."""
        suggestions = dialect.suggested_data_types()
        assert suggestions["array"] is JsonType

    def test_interval_is_suggested_as_an_integer_count(self, dialect):
        """MySQL's INTERVAL is a date-arithmetic keyword, not a column type.

        ``CREATE TABLE t (c INTERVAL)`` is a syntax error; what ``INTERVAL n
        DAY`` consumes is a plain number. So the substitute is the numeric
        count, and the unit travels with the expression rather than the type.
        """
        suggestions = dialect.suggested_data_types()
        assert suggestions["interval"] is IntegerType
        assert "interval" not in dialect.supports_data_types()

    def test_real_is_suggested_as_double_and_the_error_says_why(self, dialect):
        """``REAL`` cannot round-trip: MySQL resolves it to ``DOUBLE``.

        The manual puts ``REAL`` and ``DOUBLE PRECISION`` on one row as
        synonyms of ``DOUBLE`` ("Exception: If the ``REAL_AS_FLOAT`` SQL mode
        is enabled, ``REAL`` is a synonym for ``FLOAT``"), and every wired
        server reports a ``REAL`` column as ``double`` in
        ``information_schema`` — never as ``real``. The class is therefore
        *substituted* rather than rendered, and the advice text has to carry
        the vendor fact so the caller can pick the right class.
        """
        suggestions = dialect.suggested_data_types()
        assert suggestions["real"] is DoubleType
        assert "real" not in dialect.supports_data_types()
        with pytest.raises(TypeError) as excinfo:
            dialect.format_data_type(RealType(dialect))
        message = str(excinfo.value)
        assert "DoubleType" in message
        assert "FloatType" in message
        assert "REAL_AS_FLOAT" in message
        assert "synonym" in message
        assert "cannot round-trip" in message

    def test_every_suggested_substitute_is_rendered(self, dialect):
        """A suggestion a dialect cannot render is worse than no suggestion."""
        supported = dialect.supports_data_types()
        for key, substitute in dialect.suggested_data_types().items():
            assert issubclass(substitute, DataType), key
            assert substitute.name in supported, (
                f"suggested[{key!r}] is {substitute.__name__}, whose name "
                f"{substitute.name!r} this dialect does not render"
            )

    def test_every_core_concept_is_rendered_or_suggested(self, dialect):
        """D9: no core concept goes undeclared by this dialect."""
        import inspect

        concrete, seen, stack = [], set(), [DataType]
        while stack:
            klass = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            stack.extend(klass.__subclasses__())
            if klass is not DataType and not inspect.isabstract(klass) and (
                klass.__module__.startswith(
                    "rhosocial.activerecord.backend.expression.types"
                )
            ):
                concrete.append(klass)
        declared = set(dialect.supports_data_types()) | set(
            dialect.suggested_data_types()
        )
        undeclared = sorted(k.name for k in concrete if k.name not in declared)
        assert not undeclared, undeclared


#: The BLOB / TEXT *size* variants, each paired with the one inherited spelling
#: MySQL does not write: ``BYTEA`` is PostgreSQL's word for unbounded bytes and
#: ``CLOB`` is not a MySQL type at all.
_SIZE_VARIANT_UNSUPPORTED_SPELLING = (
    (MySQLTinyBlobType, "bytea"),
    (MySQLBlobType, "bytea"),
    (MySQLMediumBlobType, "bytea"),
    (MySQLLongBlobType, "bytea"),
    (MySQLTinyTextType, "clob"),
    (MySQLTextType, "clob"),
    (MySQLMediumTextType, "clob"),
    (MySQLLongTextType, "clob"),
)


#: Concepts whose constructor arguments MySQL's grammar makes mandatory.
#:
#: This is not a list of things the dialect does wrong -- it is the test
#: supplying what a declaration must state to be legal at all. ``VarCharType``'s
#: ``length`` is optional on the core class because PostgreSQL's bare
#: ``VARCHAR`` is legal, so "can this be declared without a length?" is the
#: dialect's question; MySQL's answer is no, and its formatter says so rather
#: than emitting ``CREATE TABLE t (c VARCHAR)``, which is error 1064.
REQUIRED_ARGS = {
    VarCharType: {"length": 255},
}


def _declared(concept, dialect, **kwargs):
    """Construct *concept* with the arguments this backend requires."""
    return concept(dialect, **{**REQUIRED_ARGS.get(concept, {}), **kwargs})


class TestSpellingGates:
    """D9 rule 3: a formatter states which spellings it accepts.

    The gate lives in the formatter because which words a *backend* writes is a
    fact about the backend, not about the concept. A silent fallback to the
    default spelling would turn a caller's explicit request into a different
    type without saying so.
    """

    #: (concept class, spellings MySQL writes, spellings it refuses)
    ACCEPTED = (
        (IntegerType, ("integer", "int", "int4"), ()),
        (TinyIntType, ("tinyint", "int1"), ()),
        (SmallIntType, ("smallint", "int2"), ()),
        (BigIntType, ("bigint", "int8"), ()),
        (DecimalType, ("decimal", "numeric", "dec"), ()),
        (BooleanType, ("boolean", "bool"), ()),
        (TextType, ("text",), ("clob",)),
        (CharType, ("char",), ("character",)),
        (VarCharType, ("varchar",), ("character varying",)),
        (DoubleType, ("double", "double precision"), ()),
        (BlobType, ("blob",), ("bytea",)),
    )

    @pytest.mark.parametrize(
        "concept,accepted,refused",
        ACCEPTED,
        ids=[c.__name__ for c, _, _ in ACCEPTED],
    )
    def test_every_listed_spelling_is_either_accepted_or_refused(
        self, dialect, concept, accepted, refused
    ):
        assert set(accepted) | set(refused) == set(concept.SPELLINGS), (
            f"{concept.__name__}: the test does not account for every "
            f"spelling {concept.SPELLINGS!r}"
        )
        assert set(accepted) & set(refused) == set()

    @pytest.mark.parametrize(
        "concept,accepted,_refused",
        ACCEPTED,
        ids=[c.__name__ for c, _, _ in ACCEPTED],
    )
    def test_accepted_spellings_render(self, dialect, concept, accepted, _refused):
        for spelling in accepted:
            sql, params = dialect.format_data_type(
                _declared(concept, dialect, spelling=spelling)
            )
            assert sql, f"{concept.__name__} rendered empty for {spelling!r}"
            assert params == ()

    @pytest.mark.parametrize(
        "concept,_accepted,refused",
        ACCEPTED,
        ids=[c.__name__ for c, _, _ in ACCEPTED],
    )
    def test_refused_spelling_raises_and_names_itself(
        self, dialect, concept, _accepted, refused
    ):
        for spelling in refused:
            with pytest.raises(TypeError) as excinfo:
                dialect.format_data_type(concept(dialect, spelling=spelling))
            assert spelling in str(excinfo.value), (
                f"{concept.__name__}: refusing {spelling!r} must name the "
                f"spelling, got: {excinfo.value}"
            )

    def test_default_spelling_always_renders(self, dialect):
        """The spelling a plain construction carries must never be refused.

        A backend may *normalise* the concept's word to its own (``BlobType``
        renders ``BLOB`` here rather than ``BYTEA``), but it may not refuse it:
        that would make the concept unconstructible here for no reason the
        caller could act on.
        """
        for concept, accepted, _refused in self.ACCEPTED:
            default = _declared(concept, dialect)
            assert default.spelling == concept.SPELLINGS[0]
            assert default.spelling in accepted, (
                f"{concept.__name__}: the default spelling "
                f"{default.spelling!r} is not in the accepted set"
            )
            assert dialect.format_data_type(default)[0]

    def test_a_declared_length_is_what_makes_varchar_renderable(self, dialect):
        """The refusal is about the grammar, not about the concept.

        ``length`` is optional on the core class -- PostgreSQL's bare
        ``VARCHAR`` is legal -- so MySQL's formatter is the one that has to say
        it cannot do without one. Both halves are worth pinning: the refusal
        names what is missing, and a declared length renders.
        """
        with pytest.raises(ValueError) as excinfo:
            dialect.format_data_type(VarCharType(dialect))
        assert "VARCHAR(M)" in str(excinfo.value)
        assert "length" in str(excinfo.value)
        assert dialect.format_data_type(VarCharType(dialect, 255))[0] == "VARCHAR(255)"

    def test_mysql_integer_variants_gate_their_own_spellings(self, dialect):
        """The ``mysql_*`` variants carry a spelling too.

        They are the same concept as their core parent, so the same closed
        list applies — a caller who asks for ``INT8`` should not silently get
        the ``bigint`` spelling back without either rendering or being told.
        """
        for cls, spelling in (
            (MySQLTinyIntType, "int1"),
            (MySQLSmallIntType, "int2"),
            (MySQLIntType, "int"),
            (MySQLBigIntType, "int8"),
        ):
            assert dialect.format_data_type(cls(dialect, spelling=spelling))[0]

    @pytest.mark.parametrize(
        "cls,refused",
        _SIZE_VARIANT_UNSUPPORTED_SPELLING,
        ids=[c.__name__ for c, _s in _SIZE_VARIANT_UNSUPPORTED_SPELLING],
    )
    def test_size_variants_refuse_the_spelling_mysql_does_not_write(
        self, dialect, cls, refused
    ):
        """The BLOB/TEXT size variants inherit ``SPELLINGS`` from their core parent.

        The size is what makes ``LONGTEXT`` a different *type* from ``TEXT``, but
        the *concept* — unbounded bytes / unbounded characters — is the same one,
        spelling list included. ``BYTEA`` is PostgreSQL's word and ``CLOB`` is
        not a MySQL type at all, so neither is rendered as a silent rewrite into
        the MySQL one.
        """
        assert dialect.format_data_type(cls(dialect))[0]
        with pytest.raises(TypeError) as excinfo:
            dialect.format_data_type(cls(dialect, spelling=refused))
        assert refused in str(excinfo.value), excinfo.value

    def test_rendered_sql_is_unaffected_by_the_gate(self, dialect):
        """Adding the gates must not have moved a single rendering.

        MySQL's own word is rendered whatever spelling was asked for, which is
        what keeps ``IntegerType(d).to_sql()`` at ``INT`` exactly as before.
        """
        assert dialect.format_data_type(IntegerType(dialect))[0] == "INT"
        assert dialect.format_data_type(
            IntegerType(dialect, spelling="int")
        )[0] == "INT"
        assert dialect.format_data_type(BigIntType(dialect))[0] == "BIGINT"
        assert dialect.format_data_type(TinyIntType(dialect))[0] == "TINYINT"
        assert dialect.format_data_type(SmallIntType(dialect))[0] == "SMALLINT"
        assert dialect.format_data_type(VarCharType(dialect, 50))[0] == "VARCHAR(50)"
        assert dialect.format_data_type(CharType(dialect, 10))[0] == "CHAR(10)"
        assert dialect.format_data_type(TextType(dialect))[0] == "TEXT"
        assert dialect.format_data_type(DoubleType(dialect))[0] == "DOUBLE"
        assert dialect.format_data_type(BlobType(dialect))[0] == "BLOB"


class TestParseTypeIsCanonical:
    """D8: one concept in, one class out, with the word that was used kept.

    A second class for a synonym would make ``parse_type("int8")`` and
    ``parse_type("bigint")`` disagree about the same storage, and the schema
    differ would then need a table of strings to tell them apart.
    """

    @pytest.mark.parametrize(
        "raw,concept,spelling",
        [
            ("INT1", MySQLTinyIntType, "int1"),
            ("TINYINT", MySQLTinyIntType, "tinyint"),
            ("INT2", MySQLSmallIntType, "int2"),
            ("SMALLINT", MySQLSmallIntType, "smallint"),
            ("INT", MySQLIntType, "int"),
            ("INTEGER", MySQLIntType, "integer"),
            ("BIGINT", MySQLBigIntType, "bigint"),
            ("INT8", MySQLBigIntType, "int8"),
        ],
    )
    def test_integer_widths_keep_their_spelling(self, dialect, raw, concept, spelling):
        parsed = dialect.parse_type(raw)
        assert isinstance(parsed, concept), raw
        assert parsed.spelling == spelling, raw

    def test_synonyms_are_the_same_class_not_sibling_classes(self, dialect):
        assert type(dialect.parse_type("INT8")) is type(dialect.parse_type("BIGINT"))
        # ... and they compare equal, because the only thing that differs is
        # which word was used. A schema differ compares what the server reports
        # against what was declared, and MySQL reports one word for both, so
        # counting the spelling would invent a change on every such column.
        assert dialect.parse_type("INT8") == dialect.parse_type("BIGINT")
        # The difference is still real, and visible where it belongs:
        assert dialect.parse_type("INT8").to_sql()[0] == "BIGINT"

    def test_int1_is_not_mistaken_for_tinyint_1(self, dialect):
        """The digits of ``INT1`` are part of the name, not a display width.

        Reading them as a width would hand back a boolean — a 1-bit type — for
        a column that is a full byte.
        """
        parsed = dialect.parse_type("INT1")
        assert isinstance(parsed, MySQLTinyIntType)
        assert not isinstance(parsed, BooleanType)

    def test_tinyint_1_still_parses_as_boolean(self, dialect):
        """The long-standing ``TINYINT(1)`` → BOOLEAN reading is unchanged."""
        assert isinstance(dialect.parse_type("TINYINT(1)"), BooleanType)
        assert isinstance(dialect.parse_type("TINYINT(1) UNSIGNED"), MySQLTinyIntType)

    def test_boolean_spellings_are_covered(self, dialect):
        assert dialect.parse_type("BOOL").spelling == "bool"
        assert dialect.parse_type("BOOLEAN").spelling == "boolean"

    @pytest.mark.parametrize(
        "raw,spelling", [("DECIMAL", "decimal"), ("NUMERIC", "numeric"), ("DEC", "dec")]
    )
    def test_decimal_spellings_are_covered(self, dialect, raw, spelling):
        parsed = dialect.parse_type(raw)
        assert isinstance(parsed, DecimalType)
        assert parsed.spelling == spelling

    def test_decimal_precision_survives_every_spelling(self, dialect):
        parsed = dialect.parse_type("NUMERIC(10,2)")
        assert (parsed.precision, parsed.scale, parsed.spelling) == (10, 2, "numeric")

    def test_unsigned_and_zerofill_are_read_as_fields(self, dialect):
        parsed = dialect.parse_type("BIGINT UNSIGNED ZEROFILL")
        assert isinstance(parsed, MySQLBigIntType)
        assert parsed.unsigned is True
        assert parsed.zerofill is True

    @pytest.mark.parametrize(
        "raw",
        [
            "CHARACTER VARYING(10)",   # no such MySQL type
            "CLOB",                     # no such MySQL type
            "BYTEA",                    # PostgreSQL's word for BLOB
            "FIXED(10,2)",              # a MySQL word outside the closed list
            "SOMETHING_ELSE",
        ],
    )
    def test_words_the_framework_does_not_model_stay_custom(self, dialect, raw):
        """Honest ignorance, not a guess.

        ``FIXED`` is worth its own line: MySQL really does treat it as a
        synonym for ``DECIMAL``, but the concept's spelling list is closed and
        does not contain it. Mapping it on anyway would make the closed list
        decorative — so it falls through to ``CustomType``, which says "this
        string is a MySQL type the framework does not model" and leaves the
        decision to the caller.
        """
        assert isinstance(dialect.parse_type(raw), CustomType), raw

    def test_double_precision_is_a_spelling_of_double(self, dialect):
        """``DOUBLE PRECISION`` is a synonym MySQL accepts and reports as double.

        The formatter used to refuse the spelling on the claim that MySQL's
        grammar rejects it; measured on every wired server, 5.6.51 through
        26.7.0, ``CREATE TABLE t (c DOUBLE PRECISION)`` is accepted and the
        catalog reports ``double``. Both spellings now render the catalog's own
        word, and both parse to :class:`DoubleType`.
        """
        for raw in ("DOUBLE PRECISION", "double precision"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, DoubleType), raw
            assert not isinstance(parsed, CustomType), raw
        assert dialect.format_data_type(
            DoubleType(dialect, spelling="double precision")
        ) == ("DOUBLE", ())
        assert dialect.format_data_type(
            DoubleType(dialect, spelling="double", unsigned=True)
        ) == ("DOUBLE UNSIGNED", ())

    def test_real_canonicalises_to_double(self, dialect):
        """``REAL`` is the server's documented default synonym for ``DOUBLE``.

        The manual's row is "``DOUBLE PRECISION``, ``REAL`` — These types are
        synonyms for ``DOUBLE``. Exception: If the ``REAL_AS_FLOAT`` SQL mode is
        enabled, ``REAL`` is a synonym for ``FLOAT`` rather than ``DOUBLE``."
        The default reading is therefore ``DoubleType``; under the mode the
        server builds a FLOAT column and the catalog reports ``float`` (which
        this parser reads as :class:`FloatType`), so the word ``real`` is never
        what introspection hands back.
        """
        for raw in ("REAL", "real"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, DoubleType), raw
            assert not isinstance(parsed, CustomType), raw
        assert dialect.parse_type("REAL UNSIGNED") == DoubleType(
            dialect, unsigned=True
        )

    def test_float_precision_is_canonicalised_to_the_class_it_selects(self, dialect):
        """``FLOAT(p)`` is storage-class selection, not a parameter to keep.

        The manual: "If *p* is from 0 to 24, the data type becomes ``FLOAT``
        with no *M* or *D* values. If *p* is from 25 to 53, the data type
        becomes ``DOUBLE`` with no *M* or *D* values." A one-argument FLOAT is
        therefore read that way — p<=24 keeps :class:`FloatType` (the p itself
        dropped, because the catalog does not record it) and p>=25 becomes
        :class:`DoubleType`.
        """
        assert dialect.parse_type("FLOAT(0)") == FloatType(dialect)
        assert dialect.parse_type("FLOAT(24)") == FloatType(dialect)
        assert dialect.parse_type("FLOAT(25)") == DoubleType(dialect)
        assert dialect.parse_type("FLOAT(53)") == DoubleType(dialect)
        assert dialect.parse_type("FLOAT(24) UNSIGNED") == FloatType(
            dialect, unsigned=True
        )

    def test_float_md_is_single_precision_regardless_of_the_first_number(self, dialect):
        """The deprecated ``FLOAT(M,D)`` is *not* ``FLOAT(p)``.

        Measured on the wired servers: ``FLOAT(25,17)`` and ``FLOAT(53,17)``
        both store single-precision values (1.2345678806304932, against
        ``DOUBLE``'s 1.2345678901234567), and both report
        ``NUMERIC_PRECISION = M``, while one-argument ``FLOAT(25)`` resolves to
        ``double``. The first number is M (total decimal digits), not p (bits),
        so the declaration is the 4-byte concept and the parser returns
        :class:`FloatType` with the (M,D) display spec dropped.
        """
        for raw in ("FLOAT(10,2)", "FLOAT(24,2)", "FLOAT(25,2)", "FLOAT(53,2)"):
            parsed = dialect.parse_type(raw)
            assert isinstance(parsed, FloatType), raw
            assert parsed.precision is None, raw
        assert dialect.parse_type("FLOAT(53,2) UNSIGNED") == FloatType(
            dialect, unsigned=True
        )

    def test_round_trip_of_a_rendered_type(self, dialect):
        """What this dialect renders, it can parse back to the same class."""
        for raw in ("INT", "BIGINT", "SMALLINT", "TINYINT", "VARCHAR(30)",
                    "CHAR(4)", "TEXT", "BOOLEAN", "DECIMAL(10,2)", "BLOB",
                    "DOUBLE PRECISION", "REAL", "FLOAT(53)"):
            parsed = dialect.parse_type(raw)
            assert dialect.format_data_type(parsed)[0], raw


class TestMySQLTypeProtocolShape:
    """D9 rule 2: an exclusive type family states its own shape."""

    def test_dialect_satisfies_the_protocol(self, dialect):
        assert isinstance(dialect, MySQLTypeSupport)

    def test_every_protocol_member_exists_on_the_dialect(self):
        missing = [
            name for name in vars(MySQLTypeSupport)
            if not name.startswith("_") and not hasattr(MySQLDialect, name)
        ]
        assert not missing, missing

    def test_protocol_declares_both_halves_of_each_pair(self):
        """A support switch with no formatter (or the reverse) is a broken promise.

        The per-type names are generated by naming convention, so the protocol
        is where the family says out loud that both halves exist.
        """
        declared = {
            name for name in vars(MySQLTypeSupport)
            if not name.startswith("_")
        }
        format_names = {
            name[len("format_data_type_"):]
            for name in declared
            if name.startswith("format_data_type_")
        }
        supports_names = {
            name[len("supports_data_type_"):]
            for name in declared
            if name.startswith("supports_data_type_")
        }
        assert format_names == supports_names, (
            f"format-only: {sorted(format_names - supports_names)}, "
            f"supports-only: {sorted(supports_names - format_names)}"
        )

    def test_protocol_covers_the_families_no_other_protocol_declares(self):
        """SET, spatial and VECTOR are declared elsewhere; do not double up."""
        declared = set(vars(MySQLTypeSupport))
        for covered in ("mysql_set", "mysql_point", "mysql_vector"):
            assert f"format_data_type_{covered}" not in declared, covered

    def test_protocol_format_family_is_implemented(self):
        format_re = re.compile(r"^format_data_type_([a-z][a-z0-9_]*)$")
        declared = {
            format_re.match(name).group(1)
            for name in vars(MySQLTypeSupport)
            if format_re.match(name)
        }
        assert declared, "the protocol must declare at least one formatter"
        for name in declared:
            assert hasattr(MySQLDialect, f"format_data_type_{name}"), name


class TestIntegerVariantParams:
    """The five ``UNSIGNED`` / ``ZEROFILL`` variants.

    ``unsigned`` is a field on the *core* integer class, so it must reach
    equality and hashing through it — and ``PARAMETERS`` must append new
    elements rather than reorder the existing ones, because the tuple feeds
    ``__hash__`` and reordering would invalidate every hash ever recorded.
    """

    def test_signed_and_unsigned_are_different_types(self, dialect):
        assert MySQLBigIntType(dialect, unsigned=True) != MySQLBigIntType(dialect)
        assert hash(MySQLBigIntType(dialect, unsigned=True)) != hash(
            MySQLBigIntType(dialect)
        )

    def test_identity_fields_append_rather_than_reorder(self, dialect):
        """Signedness and zerofill are identity; the spelling is not.

        The declaration is a class constant, so it is readable as data rather
        than only observable through a comparison.
        """
        assert MySQLBigIntType.PARAMETERS == ("unsigned", "zerofill")
        assert MySQLBigIntType(dialect).identity() == (False, False)
        assert MySQLBigIntType(
            dialect, unsigned=True, zerofill=True
        ).identity() == (True, True)
        # and each field on its own is enough to make a different column
        assert MySQLBigIntType(dialect) != MySQLBigIntType(dialect, unsigned=True)
        assert MySQLBigIntType(dialect) != MySQLBigIntType(dialect, zerofill=True)

    def test_rendered_sql_is_byte_identical(self, dialect):
        """The refactor must not have moved a single character of DDL.

        The one deliberate exception is the combined ``unsigned`` +
        ``zerofill`` case, pinned below in
        :meth:`test_both_attributes_render_in_mysql_order`; the other three
        combinations per width are unchanged from before the refactor and are
        asserted here.
        """
        assert MySQLBigIntType(dialect, unsigned=True).to_sql() == (
            "BIGINT UNSIGNED", ()
        )
        assert MySQLIntType(dialect, unsigned=True).to_sql() == ("INT UNSIGNED", ())
        assert MySQLTinyIntType(dialect, unsigned=True).to_sql() == (
            "TINYINT UNSIGNED", ()
        )
        assert MySQLSmallIntType(dialect, unsigned=True).to_sql() == (
            "SMALLINT UNSIGNED", ()
        )
        assert MySQLMediumIntType(dialect, unsigned=True).to_sql() == (
            "MEDIUMINT UNSIGNED", ()
        )
        assert MySQLBigIntType(dialect, zerofill=True).to_sql() == (
            "BIGINT ZEROFILL", ()
        )
        assert MySQLBigIntType(dialect).to_sql() == ("BIGINT", ())

    @pytest.mark.parametrize(
        "cls,word",
        [
            (MySQLTinyIntType, "TINYINT"),
            (MySQLSmallIntType, "SMALLINT"),
            (MySQLMediumIntType, "MEDIUMINT"),
            (MySQLIntType, "INT"),
            (MySQLBigIntType, "BIGINT"),
        ],
    )
    def test_both_attributes_render_in_mysql_order(self, dialect, cls, word):
        """The correct form is ``<TYPE> UNSIGNED ZEROFILL``, and both words go in.

        MySQL's grammar for every integer type is ``TYPE[(M)] [UNSIGNED]
        [ZEROFILL]`` (manual §13.1.1, "Numeric Data Type Syntax") — ``UNSIGNED``
        first — and the server writes both back in that order:
        ``SHOW CREATE TABLE`` and ``information_schema.COLUMNS.COLUMN_TYPE``
        report ``bigint(20) unsigned zerofill``.

        **What was wrong.** The formatters tested ``zerofill`` first and
        returned immediately, so ``zerofill`` acted as a *replacement* for
        ``unsigned`` rather than an addition to it, and a column that declared
        both attributes rendered as ``BIGINT ZEROFILL`` — silently dropping a
        field that is part of the type's identity.

        **Why it mattered even though MySQL infers it.** The manual does say
        "If you specify ZEROFILL for a numeric column, MySQL automatically adds
        the UNSIGNED attribute" (§13.1.6, and repeated in §13.1.1), so the
        *stored* column would have had the unsigned range either way — the
        emitted DDL alone did not claim otherwise. But ``parse_type`` reads
        ``unsigned`` from the literal presence of ``UNSIGNED`` in the string, so
        the emitted SQL parsed back to ``unsigned=False`` — a different value
        object from the one the caller declared, and a spurious entry in any
        schema diff. That is the defect, and it is pinned by
        :meth:`test_render_parse_round_trip_for_every_combination`.
        """
        assert cls(dialect, unsigned=True, zerofill=True).to_sql() == (
            f"{word} UNSIGNED ZEROFILL", ()
        )
        # the three single-attribute cases keep their exact previous spelling
        assert cls(dialect).to_sql() == (word, ())
        assert cls(dialect, unsigned=True).to_sql() == (f"{word} UNSIGNED", ())
        assert cls(dialect, zerofill=True).to_sql() == (f"{word} ZEROFILL", ())

    @pytest.mark.parametrize(
        "cls", [MySQLTinyIntType, MySQLSmallIntType, MySQLMediumIntType,
                MySQLIntType, MySQLBigIntType]
    )
    def test_render_parse_round_trip_for_every_combination(self, dialect, cls):
        """Whatever is rendered must parse back to the very same type object.

        ``DataType.__eq__`` is class-exact and reads ``PARAMETERS``, and
        introspection hands ``parse_type`` the ``COLUMN_TYPE`` string the server
        reports — so a spelling that does not survive the round trip shows up
        as a column that differs from the one the framework declared. Before
        the fix the ``(unsigned=True, zerofill=True)`` cell of this matrix was
        the one that broke.
        """
        for unsigned in (False, True):
            for zerofill in (False, True):
                declared = cls(dialect, unsigned=unsigned, zerofill=zerofill)
                sql, _ = declared.to_sql()
                assert dialect.parse_type(sql) == declared, (cls.__name__, sql)

    def test_get_params_reports_both_mysql_attributes(self, dialect):
        """Serialisation is signature-driven, so the signature is the contract.

        ``get_params()`` walks ``__init__``; both attributes must be visible
        there or a round-trip through it would silently drop the MySQL-only
        half of the type.
        """
        params = MySQLBigIntType(dialect, unsigned=True, zerofill=True).get_params()
        assert params["unsigned"] is True
        assert params["zerofill"] is True

    def test_unsigned_is_type_checked(self, dialect):
        """``unsigned`` becomes a type modifier in the rendered DDL.

        The core integer class accepts only a real ``bool``, so
        ``unsigned="yes"`` is an error rather than a truthy string reaching
        ``BIGINT yes UNSIGNED``.
        """
        with pytest.raises(TypeError, match="unsigned must be a bool"):
            MySQLBigIntType(dialect, unsigned="yes")

    @pytest.mark.parametrize(
        "cls,base",
        [
            (MySQLTinyIntType, TinyIntType),
            (MySQLSmallIntType, SmallIntType),
            (MySQLMediumIntType, IntegerType),
            (MySQLIntType, IntegerType),
            (MySQLBigIntType, BigIntType),
        ],
    )
    def test_each_variant_derives_from_its_core_concept(self, cls, base):
        """Inheritance means identity: ``mysql_bigint`` *is* the bigint concept.

        ``MySQLBigIntType`` adds attributes MySQL has and core does not; the
        width itself is the core class's business, so the variant must not sit
        on the root where it would claim to be a concept no other backend has.

        ``MySQLMediumIntType`` is the documented exception: there is no core
        3-byte width, so it borrows :class:`IntegerType` purely for the shared
        type-checked ``unsigned`` field and takes its identity from being a
        distinct class (see :class:`TestMediumIntWidth`).
        """
        assert cls.__bases__ == (base,)
        assert cls.name.startswith("mysql_")
        assert base.name != cls.name

    def test_no_synonyms_classmethod_survives(self, dialect):
        """Synonyms are a closed ``SPELLINGS`` list, never extra classes."""
        for cls in (MySQLTinyIntType, MySQLSmallIntType, MySQLMediumIntType,
                    MySQLIntType, MySQLBigIntType):
            assert "synonyms" not in vars(cls), cls.__name__


class TestNumericSignednessIsHonoured:
    """``DECIMAL``, ``FLOAT`` and ``DOUBLE`` carry ``unsigned`` too, and MySQL
    has the attribute for all three.

    MySQL's manual says so of the numeric types in the same breath as the
    integers — "Floating point and fixed-point types also can be ``UNSIGNED``" —
    and writes each of them with the attribute in its own grammar:
    ``DECIMAL[(M[,D])] [UNSIGNED] [ZEROFILL]`` (and the same for ``DEC``,
    ``NUMERIC`` and ``FIXED``), ``FLOAT[(M,D)] [UNSIGNED] [ZEROFILL]``,
    ``FLOAT(p) [UNSIGNED] [ZEROFILL]``, ``DOUBLE[(M,D)] [UNSIGNED] [ZEROFILL]``.
    https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html
    https://dev.mysql.com/doc/refman/9.7/en/numeric-type-attributes.html

    So honouring is the right answer here, not refusing, and these three
    formatters used to render the signed column for an unsigned request — which
    is the same paradigm violation the integer widths had: the declared column
    is not the column the caller gets, the SQL is byte-identical to the signed
    declaration, and nothing reports it. Measured on all fifteen wired MariaDB
    servers, the same defect showed up in introspection too:
    ``decimal(10,2) unsigned zerofill`` came back as ``DecimalType(10, 2)`` — the
    signedness simply gone — so a column the server had changed to unsigned
    compared equal to its own declaration.

    **The attribute goes after the ``(M[,D])`` group**, which is where MySQL's
    grammar puts it and where ``SHOW CREATE TABLE`` reports it, which is what
    makes ``parse_type`` able to read this backend's own output back.
    """

    #: (concept, extra constructor kwargs, signed SQL, unsigned SQL)
    CASES = [
        (DecimalType, {}, "DECIMAL", "DECIMAL UNSIGNED"),
        (DecimalType, {"precision": 10}, "DECIMAL(10)",
         "DECIMAL(10) UNSIGNED"),
        (DecimalType, {"precision": 10, "scale": 2}, "DECIMAL(10, 2)",
         "DECIMAL(10, 2) UNSIGNED"),
        (FloatType, {}, "FLOAT", "FLOAT UNSIGNED"),
        (DoubleType, {}, "DOUBLE", "DOUBLE UNSIGNED"),
    ]
    IDS = [f"{k.__name__}{''.join(sorted(kw))}" for k, kw, _s, _u in CASES]

    @pytest.mark.parametrize("klass,kwargs,signed_sql,unsigned_sql", CASES,
                             ids=IDS)
    def test_the_attribute_is_written_after_the_parameter_group(
            self, dialect, klass, kwargs, signed_sql, unsigned_sql):
        assert dialect.format_data_type(klass(dialect, **kwargs)) == (
            signed_sql, ())
        assert dialect.format_data_type(
            klass(dialect, unsigned=False, **kwargs)) == (signed_sql, ())
        assert dialect.format_data_type(
            klass(dialect, unsigned=True, **kwargs)) == (unsigned_sql, ())

    @pytest.mark.parametrize("klass,kwargs,signed_sql,unsigned_sql", CASES,
                             ids=IDS)
    def test_flipping_the_flag_changes_the_sql(self, dialect, klass, kwargs,
                                              signed_sql, unsigned_sql):
        """The rule in one line: two declarations, two different columns.

        Anything less — a rewritten word, a clamped number, a silently dropped
        field — would render the same SQL twice, and a differ built on this
        rendering could not tell a column the server changed from one it did not.
        """
        assert signed_sql != unsigned_sql

    @pytest.mark.parametrize("klass,kwargs,signed_sql,unsigned_sql", CASES,
                             ids=IDS)
    def test_signedness_is_part_of_identity(self, dialect, klass, kwargs,
                                           signed_sql, unsigned_sql):
        assert "unsigned" in klass.PARAMETERS, klass.__name__
        signed = klass(dialect, **kwargs)
        unsigned = klass(dialect, unsigned=True, **kwargs)
        assert signed != unsigned
        assert hash(signed) != hash(unsigned)
        assert klass(dialect, **kwargs) == signed

    @pytest.mark.parametrize("klass,kwargs,signed_sql,unsigned_sql", CASES,
                             ids=IDS)
    def test_unsigned_is_type_checked(self, dialect, klass, kwargs, signed_sql,
                                     unsigned_sql):
        """It becomes a type modifier in the rendered DDL, so ``1`` is not a
        truthy ``True`` and ``"yes"`` is not a spelling of one."""
        with pytest.raises(TypeError, match="unsigned must be a bool"):
            klass(dialect, unsigned=1, **kwargs)
        with pytest.raises(TypeError, match="unsigned must be a bool"):
            klass(dialect, unsigned="yes", **kwargs)

    @pytest.mark.parametrize("klass,kwargs,signed_sql,unsigned_sql", CASES,
                             ids=IDS)
    def test_render_then_parse_comes_back_equal(self, dialect, klass, kwargs,
                                                signed_sql, unsigned_sql):
        """Round trip, both directions of the flag.

        ``parse_type`` reads ``UNSIGNED`` out of the float family and the decimal
        family for exactly this reason: the catalog hands it
        ``COLUMN_TYPE`` verbatim, so ``decimal(10,2) unsigned`` used to come back
        as a signed ``DecimalType`` and the differ reported no change for a change
        the server had made.
        """
        for flag in (False, True):
            declared = klass(dialect, unsigned=flag, **kwargs)
            parsed = dialect.parse_type(dialect.format_data_type(declared)[0])
            assert parsed == declared
            assert hash(parsed) == hash(declared)

    @pytest.mark.parametrize(
        "raw", ["DECIMAL(10,2) UNSIGNED", "decimal(10,2) unsigned",
                "NUMERIC(10,2) UNSIGNED", "DEC(10,2) UNSIGNED",
                "FLOAT UNSIGNED", "FLOAT(24) UNSIGNED", "DOUBLE UNSIGNED",
                "DOUBLE(10,2) UNSIGNED ZEROFILL"])
    def test_parse_type_reads_the_attribute_off_the_catalogs_own_words(
            self, dialect, raw):
        """``information_schema`` reports ``COLUMN_TYPE`` verbatim and lower-cased.

        That is the string this branch exists for, so it is spelled out here in
        the forms MySQL actually writes rather than in the forms this formatter
        emits.
        """
        parsed = dialect.parse_type(raw)
        assert parsed.unsigned is True, raw
        assert "UNSIGNED" in dialect.format_data_type(parsed)[0]

    def test_a_signed_numeric_is_still_signed_when_parsed_back(self, dialect):
        """The flag is not inferred: ``UNSIGNED`` absent means signed."""
        for raw in ("DECIMAL(10,2)", "FLOAT(24)", "DOUBLE"):
            assert dialect.parse_type(raw).unsigned is False, raw

    def test_zerofill_on_a_numeric_is_read_as_unsigned_and_nothing_more(self,
                                                                        dialect):
        """MySQL: "If you specify ZEROFILL for a numeric column, MySQL
        automatically adds the UNSIGNED attribute to the column."

        So ``decimal(10,2) unsigned zerofill`` -- what the catalog reports for a
        zero-padded decimal -- must parse to ``unsigned=True``. It is *not* read
        as a ``zerofill`` field, because these three concepts have no such field:
        ``zerofill`` is a MySQL display attribute, and a concept must not gain a
        field for it. The one-cell reasoning from the integer widths therefore
        holds unchanged -- there is no reachable ``(unsigned=False,
        zerofill=True)`` declaration for these concepts at all.
        """
        parsed = dialect.parse_type("decimal(10,2) unsigned zerofill")
        assert isinstance(parsed, DecimalType)
        assert parsed.unsigned is True
        assert (parsed.precision, parsed.scale) == (10, 2)
        assert not hasattr(parsed, "zerofill")

    @pytest.mark.parametrize("klass,kwargs,signed_sql,unsigned_sql", CASES,
                             ids=IDS)
    def test_the_precision_checks_are_untouched(self, dialect, klass,
                                                kwargs, signed_sql,
                                                unsigned_sql):
        """A new rendering path must not have swallowed the old refusals.

        ``FloatType`` used to render ``FLOAT(p)`` and refuse only an
        out-of-range ``p`` with ``ValueError`` — a wrong value, not an
        inexpressible declaration. Under the new contract *every* precision is
        refused the same way (``ValueError``, never
        ``UnsupportedFeatureError``), and the bare concept still renders.
        """
        if klass is not FloatType:
            return
        with pytest.raises(ValueError) as excinfo:
            dialect.format_data_type(FloatType(dialect, 99))
        assert not isinstance(excinfo.value, UnsupportedFeatureError)
        for precision in (24, 53):
            with pytest.raises(ValueError) as excinfo:
                dialect.format_data_type(FloatType(dialect, precision))
            assert not isinstance(excinfo.value, UnsupportedFeatureError)
        # ...and the precision-free renderings, signed and unsigned alike, are
        # unchanged.
        assert dialect.format_data_type(FloatType(dialect)) == ("FLOAT", ())
        assert dialect.format_data_type(FloatType(dialect, unsigned=True)) == (
            "FLOAT UNSIGNED", ())

    def test_the_refusals_still_fire_alongside_an_unsigned_request(
            self, dialect):
        """Both faults at once, and the flag does not swallow the number.

        MySQL honours ``unsigned`` on the decimal and float families, so the
        flag alone is not a refusal; a *precision* fault is, and it must still
        be the answer when both are present. The ``ValueError`` must not have
        become an ``UnsupportedFeatureError``: the two do not share a base
        class, so a caller catching one cannot catch the other.
        """
        with pytest.raises(ValueError) as excinfo:
            dialect.format_data_type(
                DecimalType(dialect, precision=99, unsigned=True))
        assert not isinstance(excinfo.value, UnsupportedFeatureError)
        with pytest.raises(ValueError):
            dialect.format_data_type(
                DecimalType(dialect, precision=10, scale=99, unsigned=True))
        with pytest.raises(ValueError):
            dialect.format_data_type(
                DecimalType(dialect, precision=10, scale=11, unsigned=True))
        with pytest.raises(ValueError):
            dialect.format_data_type(FloatType(dialect, 99, unsigned=True))
        with pytest.raises(ValueError):
            dialect.format_data_type(FloatType(dialect, 24, unsigned=True))


class TestMediumIntWidth:
    """``MEDIUMINT`` is 3 bytes and must not be reported as the 4-byte ``INT``.

    Evidence that the parser really is reached: ``CREATE TABLE t (c MEDIUMINT)``
    succeeds on every server this backend is tested against (MySQL 8.0.46, 8.4.11,
    9.4.0 and 26.7.0 all accepted it), and ``information_schema.COLUMNS`` then
    reports ``COLUMN_TYPE`` verbatim — ``mediumint``, ``mediumint unsigned``, or
    ``mediumint(8) unsigned zerofill`` for a zero-padded one. Introspection
    hands that string straight to ``parse_type``, so this is not a hypothetical
    input. The manual's Table 13.1 gives the storage as **3** bytes, signed
    range ``-8388608``..``8388607``, unsigned ``0``..``16777215``.
    """

    @pytest.mark.parametrize(
        "raw",
        ["MEDIUMINT", "mediumint", "MEDIUMINT UNSIGNED", "MEDIUMINT ZEROFILL",
         "MEDIUMINT UNSIGNED ZEROFILL", "mediumint(8) unsigned zerofill"],
    )
    def test_parses_to_its_own_class(self, dialect, raw):
        parsed = dialect.parse_type(raw)
        assert isinstance(parsed, MySQLMediumIntType), raw
        assert parsed.unsigned == ("UNSIGNED" in raw.upper())
        assert parsed.zerofill == ("ZEROFILL" in raw.upper())

    def test_is_not_the_four_byte_integer(self, dialect):
        """The false identity this replaces: MEDIUMINT diffed clean against INT.

        ``DataType.__eq__`` is class-exact, so a distinct class is exactly what
        makes the differ report a real change here. Signedness is compared too,
        so an unsigned MEDIUMINT does not quietly equal an unsigned INT.
        """
        mediumint = dialect.parse_type("MEDIUMINT")
        assert not isinstance(mediumint, MySQLIntType)
        assert mediumint != MySQLIntType(dialect)
        assert mediumint != MySQLIntType(dialect, unsigned=True)
        assert dialect.parse_type("MEDIUMINT UNSIGNED") != MySQLIntType(
            dialect, unsigned=True
        )
        assert hash(mediumint) != hash(MySQLIntType(dialect))

    def test_differs_from_every_other_width(self, dialect):
        """Width is a class here (D5), so all five widths are pairwise distinct."""
        widths = (
            MySQLTinyIntType, MySQLSmallIntType, MySQLMediumIntType,
            MySQLIntType, MySQLBigIntType,
        )
        for a in widths:
            for b in widths:
                assert (a(dialect) == b(dialect)) is (a is b), (a.__name__, b.__name__)

    def test_takes_no_spelling_and_does_not_inherit_the_four_byte_words(self):
        """``MEDIUMINT`` is one word, so there is nothing to choose between.

        ``SPELLINGS`` is narrowed rather than left inherited: taking
        :class:`IntegerType` would otherwise advertise ``integer`` / ``int``,
        which MySQL does not accept for this width, and
        ``_check_spelling(data_type, MySQLMediumIntType)`` would then hold a
        MEDIUMINT to a word it is not.
        """
        assert MySQLMediumIntType.SPELLINGS == ("mediumint",)
        assert "spelling" not in inspect.signature(
            MySQLMediumIntType.__init__).parameters
        assert MySQLMediumIntType(dialect=None).spelling == "mediumint"

    def test_unsigned_is_handled_like_its_siblings(self, dialect):
        """Same field, same type check, same place in identity."""
        assert MySQLMediumIntType.PARAMETERS == ("unsigned", "zerofill")
        assert MySQLMediumIntType(dialect).identity() == (False, False)
        with pytest.raises(TypeError, match="unsigned must be a bool"):
            MySQLMediumIntType(dialect, unsigned="yes")


class TestCastTargets:
    """``SIGNED`` / ``UNSIGNED`` are CAST targets, not unsigned column types.

    ``CREATE TABLE t (c SIGNED)`` is a syntax error, so neither class is a
    storage type; modelling them keeps ``cast`` from rendering a target the
    server rejects. They must therefore stay on ``IntegerType`` — the concept
    they cast *to* — and must not grow a signedness field of their own.
    """

    @pytest.mark.parametrize("cls", (MySQLSignedType, MySQLUnsignedType))
    def test_derive_from_integer_type(self, cls):
        assert cls.__bases__ == (IntegerType,)

    def test_render_the_two_words_the_server_accepts(self, dialect):
        assert MySQLSignedType(dialect).to_sql() == ("SIGNED", ())
        assert MySQLUnsignedType(dialect).to_sql() == ("UNSIGNED", ())

    @pytest.mark.parametrize("cls", (MySQLSignedType, MySQLUnsignedType))
    def test_carry_no_parameters(self, cls, dialect):
        """No signedness field: the word names the target, it is not one.

        Declared explicitly rather than left to inherit the integer concept's
        ``unsigned``, so the cast target's identity is stated where it is
        defined instead of being an accident of what it derives from.
        """
        assert cls.PARAMETERS == ()
        assert cls(dialect).identity() == ()
        assert cls(dialect) == cls(dialect)

    def test_unsigned_columns_are_the_integer_variants(self, dialect):
        """The unsigned *column* type is ``mysql_*`` with ``unsigned=True``."""
        unsigned_column = MySQLBigIntType(dialect, unsigned=True)
        assert unsigned_column.to_sql() == ("BIGINT UNSIGNED", ())
        assert unsigned_column is not MySQLUnsignedType(dialect)


class TestRootSittingTypesAreDocumented:
    """D7: sitting on ``DataType`` is legitimate, but it must be *justified*.

    There is no exemption list, no marker attribute and no allowlist
    anywhere — the rule is that the class docstring says why this is not a core
    concept. This test is the guard on that: a root-sitting type that has been
    added or whose reasoning was trimmed would otherwise pass unnoticed.
    """

    ROOT_SITTING = (
        MySQLBitType,
        MySQLYearType,
        MySQLSetType,
        MySQLGeometryType,
        MySQLVectorType,
    )

    @pytest.mark.parametrize("cls", ROOT_SITTING, ids=[c.__name__ for c in ROOT_SITTING])
    def test_sits_directly_on_data_type(self, cls):
        assert cls.__bases__ == (DataType,), cls.__name__

    @pytest.mark.parametrize("cls", ROOT_SITTING, ids=[c.__name__ for c in ROOT_SITTING])
    def test_docstring_explains_why_not_a_core_concept(self, cls):
        doc = cls.__doc__ or ""
        assert len(doc) > 200, (
            f"{cls.__name__} sits directly on DataType, so its docstring has "
            f"to say why there is no core concept for it — this one is "
            f"{len(doc)} characters"
        )
        assert "DataType" in doc, cls.__name__
        assert "core concept" in doc, cls.__name__

    @pytest.mark.parametrize("cls", ROOT_SITTING, ids=[c.__name__ for c in ROOT_SITTING])
    def test_no_exemption_marker_is_carried(self, cls):
        """The rule has no opt-out: nothing marks a type as allowed to sit
        on the root, so there must be nothing to find."""
        markers = ("exempt", "is_core_type", "allowlist", "needs_docstring")
        for name in vars(cls):
            assert not any(marker in name.lower() for marker in markers), name

    def test_bit_is_not_a_boolean(self, dialect):
        """``BIT(n)`` is a bit string: the width is part of the type.

        ``BIT(1)`` is a boolean only by coincidence of width, which is why this
        is not a ``BooleanType`` — the same coincidence that makes
        ``TINYINT(1)`` one does not survive ``BIT(64)``.
        """
        assert not issubclass(MySQLBitType, BooleanType)
        assert MySQLBitType(dialect, n=64).to_sql() == ("BIT(64)", ())
        assert MySQLBitType(dialect, n=8) != MySQLBitType(dialect, n=16)

    def test_set_is_not_an_enum(self, dialect):
        """``SET`` holds several members at once; ``ENUM`` holds one."""
        assert not issubclass(MySQLSetType, EnumType)
        assert not issubclass(MySQLSetType, MySQLEnumType)
        assert MySQLSetType(dialect, ["a", "b"]).to_sql() == ("SET('a','b')", ())

    def test_enum_keeps_its_charset_and_collation_fields(self, dialect):
        """A character set is a *field* here, not a type — the framework-wide
        position, and the reason ``NCHAR`` is not a spelling of ``char``."""
        enum_type = MySQLEnumType(
            dialect, values=["a"], charset="utf8mb4", collation="utf8mb4_bin"
        )
        assert enum_type.charset == "utf8mb4"
        assert enum_type.collation == "utf8mb4_bin"
        assert enum_type != MySQLEnumType(dialect, values=["a"])


class TestNoIntTypeRemains:
    """``IntType`` is gone: ``INT`` is a spelling of ``IntegerType``.

    A second class for ``INT`` would make ``parse_type("INT")`` and
    ``parse_type("INTEGER")`` disagree about one storage.
    """

    def test_core_no_longer_exports_int_type(self):
        assert not hasattr(core_types, "IntType")
        assert not hasattr(core_types, "is_equivalent")
        assert not hasattr(core_types.DataType, "synonyms")

    def test_dialect_has_no_int_only_dispatch_key(self):
        assert not hasattr(MySQLDialect, "format_data_type_int")
        assert not hasattr(MySQLDialect, "supports_data_type_int")
        assert "int" not in MySQLDialect().supports_data_types()


class TestMySQLEnumRendering:
    """MySQLEnumType inherits core EnumType; rendering keeps extensions."""

    def test_simple_enum(self, dialect):
        enum_type = MySQLEnumType(dialect, values=["a", "b"])
        assert enum_type.name == "mysql_enum"
        sql, params = enum_type.to_sql()
        assert sql == "ENUM('a','b')"
        assert params == ()

    def test_enum_with_charset_and_collation(self, dialect):
        enum_type = MySQLEnumType(
            dialect, values=["a", "b"],
            charset="utf8mb4", collation="utf8mb4_bin",
        )
        sql, _ = enum_type.to_sql()
        assert "ENUM('a','b')" in sql
        assert "CHARACTER SET utf8mb4" in sql
        assert "COLLATE utf8mb4_bin" in sql

    def test_enum_requires_non_empty_values(self, dialect):
        with pytest.raises(ValueError):
            MySQLEnumType(dialect, values=[])
        with pytest.raises(ValueError):
            MySQLEnumType(dialect, values=None)

    def test_set_type_still_renders_set(self, dialect):
        set_type = MySQLSetType(dialect, values=["read", "write"])
        sql, _ = set_type.to_sql()
        assert sql == "SET('read','write')"


class TestDialectRangeValidation:
    """Dialect-specific range checks live inside the formatters."""

    def test_decimal_precision_over_65_raises(self, dialect):
        data_type = DecimalType(dialect, 66, 2)
        with pytest.raises(ValueError, match="between 1 and 65"):
            dialect.format_data_type(data_type)

    def test_decimal_scale_over_30_raises(self, dialect):
        data_type = DecimalType(dialect, 65, 31)
        with pytest.raises(ValueError, match="between 0 and 30"):
            dialect.format_data_type(data_type)

    def test_decimal_scale_over_precision_raises(self, dialect):
        data_type = DecimalType(dialect, 10, 11)
        with pytest.raises(ValueError, match="cannot exceed"):
            dialect.format_data_type(data_type)

    def test_decimal_valid_range_renders(self, dialect):
        sql, _ = dialect.format_data_type(DecimalType(dialect, 65, 30))
        assert sql == "DECIMAL(65, 30)"

    def test_float_precision_is_refused_not_range_checked(self, dialect):
        """``FLOAT(p)`` is refused because the catalog drops p entirely.

        A wrong ``p`` and a round-trippable-looking one are refused by the same
        ``ValueError``, and it names the class to declare for each range:
        ``FloatType`` (without a precision) for p<=24 and ``DoubleType`` for
        p>=25.
        """
        with pytest.raises(ValueError, match="cannot round-trip FLOAT") as excinfo:
            dialect.format_data_type(FloatType(dialect, 54))
        assert "FloatType" in str(excinfo.value)
        assert "DoubleType" in str(excinfo.value)

    @pytest.mark.parametrize("precision", [0, 24, 25, 53])
    def test_float_precision_is_refused_and_names_single_and_double(
            self, dialect, precision):
        with pytest.raises(ValueError) as excinfo:
            dialect.format_data_type(FloatType(dialect, precision))
        message = str(excinfo.value)
        assert "FloatType(dialect)" in message, message
        assert "DoubleType(dialect)" in message, message

    def test_timestamp_precision_over_6_raises(self, dialect):
        with pytest.raises(ValueError, match="between 0 and 6"):
            dialect.format_data_type(TimestampType(dialect, 7))

    def test_timestamp_valid_precision_renders(self, dialect):
        sql, _ = dialect.format_data_type(TimestampType(dialect, 6))
        assert sql == "TIMESTAMP(6)"


class TestDialectOptions:
    """The data-type value objects no longer carry a dialect_options bag."""



    def test_constructor_rejects_dialect_options(self, dialect):
        with pytest.raises(TypeError):
            MySQLIntType(dialect, unsigned=True, dialect_options={"display_width": 10})

    def test_equality_ignores_dialect(self, dialect):
        other = MySQLDialect()
        assert MySQLIntType(dialect, unsigned=True) == MySQLIntType(other, unsigned=True)

    def test_semantic_params_drive_equality(self, dialect):
        assert MySQLIntType(dialect, unsigned=True) != MySQLIntType(dialect)
        assert MySQLEnumType(dialect, values=["a"]) != MySQLEnumType(dialect, values=["b"])
        assert MySQLEnumType(dialect, values=["a"]) == MySQLEnumType(dialect, values=["a"])


# ---------------------------------------------------------------------------
# parse_type: spatial dispatch, and the shared round-trip sweep


class TestSpatialWordsParseBackAsTheirOwnShape:
    """Dispatch is on the leading word, not a prefix scanned in map order.

    ``GEOMETRYCOLLECTION`` begins with ``GEOMETRY``, and the map put
    ``GEOMETRY`` first, so the ``startswith`` loop read a collection column
    as the generic geometry type -- the same defect MariaDB's branch of
    this family fixed, measured there on fifteen live servers, and here
    found by the render-parse-re-render sweep over this backend's own
    registry. It is a false identity claim in the worst direction for a
    differ: it reported *no* change between two columns MySQL can
    certainly tell apart.
    """

    @pytest.mark.parametrize("raw,expected", [
        ("geometry", "MySQLGeometryType"),
        ("geometrycollection", "MySQLGeometryCollectionType"),
        ("point", "MySQLPointType"),
        ("linestring", "MySQLLineStringType"),
        ("polygon", "MySQLPolygonType"),
        ("multipoint", "MySQLMultiPointType"),
        ("multilinestring", "MySQLMultiLineStringType"),
        ("multipolygon", "MySQLMultiPolygonType"),
    ])
    def test_each_word_reads_back_as_its_own_shape(self, dialect, raw, expected):
        parsed = dialect.parse_type(raw)
        assert type(parsed).__name__ == expected, raw
        assert dialect.format_data_type(parsed) == (raw.upper(), ())

    def test_a_collection_is_not_the_generic_geometry_type(self, dialect):
        collection = dialect.parse_type("geometrycollection")
        generic = dialect.parse_type("geometry")
        assert isinstance(collection, MySQLGeometryCollectionType)
        assert collection != generic
        assert type(collection) is not type(generic)

    def test_srid_survives_the_dispatch(self, dialect):
        parsed = dialect.parse_type("GEOMETRYCOLLECTION SRID 4326")
        assert isinstance(parsed, MySQLGeometryCollectionType)
        assert parsed.srid == 4326


class TestParseRoundTripSweep:
    """The shared sweep: every rendered type parses back coherently.

    Uses the testsuite's ``parse_roundtrip_failures`` over this backend's
    round-trip registry, so the whole declared surface is asserted at
    once: **string stability** -- parsing a rendering and re-rendering
    the answer produces the identical string -- and **class honesty** --
    the answer is the declared instance, or the documented widening
    answer recorded below with its reason.
    """

    #: The documented widening answers. The four integer widths are four
    #: MySQL classes because ``unsigned`` / ``zerofill`` have no field on
    #: the core concept, so the backend class is the only lossless answer;
    #: ``timetz``/``timestamptz`` collapse into MySQL's single TIME /
    #: TIMESTAMP storages; ``jsonb`` is stored as the JSON type; ``text``
    #: and ``blob`` are the sized MySQL families' bases. Each answer
    #: re-renders the identical string, which the sweep asserts.
    WIDENING_ANSWERS = {
        "TinyIntType": "MySQLTinyIntType",
        "SmallIntType": "MySQLSmallIntType",
        "IntegerType": "MySQLIntType",
        "BigIntType": "MySQLBigIntType",
        "TextType": "MySQLTextType",
        "BlobType": "MySQLBlobType",
        "TimeTzType": "TimeType",
        "TimestampTzType": "TimestampType",
        "JsonBType": "JsonType",
    }

    #: CAST targets, not column types: ``CAST(x AS SIGNED)`` is the only
    #: grammar that writes these words, so a column-introspection parse
    #: answering ``CustomType`` for them is honest rather than a gap.
    SKIP = ("MySQLSignedType", "MySQLUnsignedType")

    @pytest.fixture(scope="class")
    def registry(self):
        """The round-trip module's registry, loaded from beside this file.

        Executing it also registers its special constructors, which the
        sweep's ``make_instance`` consults -- the same registrations the
        full suite performs at collection time, repeated here so the
        sweep also holds when this file runs alone.
        """
        import importlib.util
        from pathlib import Path

        path = Path(__file__).with_name("test_expression_roundtrip_all.py")
        spec = importlib.util.spec_from_file_location("mysql_rt_registry", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        registry = getattr(module, "ALL_CLASSES", None) or module.REGISTERED
        assert registry, "the round-trip module exposes no registry"
        return registry

    def test_every_rendered_type_parses_back_coherently(self, dialect, registry):
        from rhosocial.activerecord.testsuite.utils.parse_contract import (
            parse_roundtrip_failures,
        )

        failures = parse_roundtrip_failures(
            dialect,
            registry,
            widening=self.WIDENING_ANSWERS,
            skip=self.SKIP,
        )
        assert failures == [], "\n".join(failures)
