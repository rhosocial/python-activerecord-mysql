# src/rhosocial/activerecord/backend/impl/mysql/expression/types.py
"""MySQL-specific DataType subclasses.

Naming convention
-----------------
MySQL-specific types use the ``MySQL`` class-name prefix and a
``mysql_``-prefixed generic type ``name`` (the protocol dispatch key) to
distinguish them from the core types (which own pure names such as
``integer`` or ``varchar``).  This keeps the
``format_data_type_<name>`` dispatch families of core and backend
isolated and avoids ambiguity when both type families are used together.

Usage scope
-----------
These types are used **only** for MySQL backend DDL column definitions,
introspection result parsing, and schema comparison.  They should **not**
be used by application code directly — always use the core types for
DDL definition expressions (``ColumnDefinition.data_type``).

Value-object semantics
----------------------
Equality/hash live on the core ``DataType`` base (over ``PARAMETERS``, read in
order by :meth:`DataType.identity`); subclasses only declare their semantic
parameters through the ``PARAMETERS`` class constant and must **not** hand-write
``__eq__``/``__hash__``.

Inheritance
-----------
Inheriting from a core ``DataType`` is an *identity* claim, nothing else: "this
class **is** that SQL type". So a MySQL type derives from a core concept when
the MySQL DDL names the same storage — ``MySQLBigIntType`` is a
:class:`BigIntType`, ``MySQLEnumType`` is an :class:`EnumType` — and sits
directly on ``DataType`` when there is no core concept for what it stores, in
which case the class docstring has to say **why** (there is no exemption list
and no marker attribute; the reasoning *is* the rule).

Synonyms are never extra classes. ``INT`` is a spelling of
:class:`IntegerType`, ``NUMERIC`` of :class:`DecimalType`, and ``INT8`` of
:class:`BigIntType`; a type that MySQL spells several ways declares the way in
``spelling`` and the dialect decides which spellings it renders.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BinaryType,
    BlobType,
    DataType,
    EnumType,
    IntegerType,
    SmallIntType,
    TextType,
    TinyIntType,
    UUIDType,
    VarBinaryType,
)


# ---------------------------------------------------------------------------
# Integer variants with UNSIGNED / ZEROFILL
#
# ``unsigned`` is **not** redeclared here: it is a field on the core integer
# classes (``TinyIntType`` / ``SmallIntType`` / ``IntegerType`` /
# ``BigIntType``), because signedness is a property of the range a type can
# represent and every MySQL/MariaDB/ClickHouse backend shares that. Repeating it
# per subclass would let the two drift apart — a constructor that type-checks it
# in one class and not in the next, a ``PARAMETERS`` tuple that includes it in
# one class's identity and not the other's. ``zerofill`` *does* stay, because it
# is a MySQL-only display attribute that pads with zeros rather than changing the
# range, and core has no business knowing about it.
#
# ``PARAMETERS`` keeps its historical element order
# (``unsigned``, ``zerofill``) and appends ``spelling`` last: the tuple feeds
# ``__hash__``, so reordering it would invalidate every previously recorded
# hash. The same rule applies to every later addition.
# ---------------------------------------------------------------------------

class MySQLMediumIntType(IntegerType):
    """MySQL ``MEDIUMINT`` — 3 bytes, ``-8388608``..``16777215``.

    The manual's Table 13.1 gives ``MEDIUMINT`` three bytes of storage, signed
    range ``-8388608``..``8388607`` and unsigned range ``0``..``16777215`` — a
    width of its own, between the 2-byte ``SMALLINT`` and the 4-byte ``INT``.
    MySQL's grammar gives it the same attribute pair as every other integer
    (``MEDIUMINT[(M)] [UNSIGNED] [ZEROFILL]``), so it is handled exactly like
    its siblings.

    **Why it is not a spelling of an existing type.** A width is a class in this
    hierarchy (D5), and 3 bytes is neither the 1-, 2-, 4- nor 8-byte concept, so
    there is nothing for it to be a synonym of. It has to be its own class or a
    ``MEDIUMINT`` column would compare ``==`` to an ``INT`` column and the differ
    would report a change that was never made.

    **Why it nevertheless inherits :class:`IntegerType`.** Not to claim the
    width: 3 bytes is not 4. It is to reuse the *signedness* contract — the
    type-checked ``unsigned`` field, and its place in ``PARAMETERS`` — which is
    core's and which the module comment above says must not be re-declared per
    subclass. What a ``MEDIUMINT`` column *is* stays distinguishable because
    ``DataType.__eq__`` is class-exact, so this never compares equal to
    :class:`MySQLIntType`; the inheritance buys the shared field, and the
    separate ``name`` keeps the dispatch families apart.

    ``SPELLINGS`` is narrowed to the single word MySQL writes, so the class does
    not advertise the 4-byte concept's ``integer`` / ``int``, and no ``spelling``
    argument is taken because there is nothing to choose between.
    """

    name = "mysql_mediumint"

    SPELLINGS = ("mediumint",)

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False):
        super().__init__(dialect, unsigned=unsigned, spelling="mediumint")
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MySQLIntType(IntegerType):
    """MySQL ``INTEGER`` / ``INT`` with optional UNSIGNED / ZEROFILL.

    Inherits :class:`IntegerType` — the 4-byte signed integer *is* this
    concept; what MySQL adds is the two attributes the core class does not
    carry (``unsigned`` from the core, ``zerofill`` from here) and its own
    dispatch key, so that a DDL diff can tell ``INT`` from ``mysql_int``
    without confusing the concept with the spelling.
    """

    name = "mysql_int"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 spelling: str = IntegerType.SPELLINGS[0]):
        super().__init__(dialect, unsigned=unsigned, spelling=spelling)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MySQLSignedType(IntegerType):
    """MySQL ``SIGNED`` — the integer cast idiom ``CAST(x AS SIGNED)``.

    MySQL spells "cast this to a signed integer" as a cast to a type named
    SIGNED rather than to INTEGER, and rejects the two as different. Modelling
    it keeps ``cast`` from rendering something the server will not accept.

    **This is a cast *target*, not an unsigned/signed column type.** MySQL has
    no column type called ``SIGNED``; ``CREATE TABLE t (c SIGNED)`` is a syntax
    error. Unsigned *columns* are :class:`MySQLIntType` and friends carrying
    ``unsigned=True`` — the field is where that lives. So the base here is
    ``IntegerType`` (an integer concept) and the two must not be re-parented to
    each other or to any "unsigned" class: they name the two accepted spellings
    of one cast, and neither is a storage type.
    """

    # No signedness in identity: ``CAST(x AS SIGNED)`` is a cast
    # *target*, named by the word itself, not a column type with a range.
    # Declared empty so it does not inherit ``unsigned`` from the integer
    # concept it derives from for rendering purposes.
    PARAMETERS = ()

    name = "mysql_signed"


class MySQLUnsignedType(IntegerType):
    """MySQL ``UNSIGNED`` — the unsigned counterpart of :class:`MySQLSignedType`.

    Also a **cast target only**, not an unsigned column type: see
    :class:`MySQLSignedType`. It deliberately shares ``IntegerType`` with the
    signed cast target — they are the same concept ("an integer") under two
    names the server insists on distinguishing — and it deliberately carries no
    ``unsigned`` field of its own, because nothing about this cast target is
    unsigned; the word is simply the name of the target.
    """

    # No signedness in identity: ``CAST(x AS UNSIGNED)`` is a cast
    # *target*, named by the word itself, not a column type with a range.
    # Declared empty so it does not inherit ``unsigned`` from the integer
    # concept it derives from for rendering purposes.
    PARAMETERS = ()

    name = "mysql_unsigned"


class MySQLTinyIntType(TinyIntType):
    """MySQL ``TINYINT`` with optional UNSIGNED / ZEROFILL.

    Inherits :class:`TinyIntType`: 1 byte is 1 byte whatever the server, so the
    width *is* the concept. MySQL's extra words are attributes and a dispatch
    key.
    """

    name = "mysql_tinyint"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 spelling: str = TinyIntType.SPELLINGS[0]):
        super().__init__(dialect, unsigned=unsigned, spelling=spelling)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MySQLSmallIntType(SmallIntType):
    """MySQL ``SMALLINT`` with optional UNSIGNED / ZEROFILL.

    Inherits :class:`SmallIntType`; see :class:`MySQLIntType` for why the
    width stays on the core class and only the MySQL attributes live here.
    """

    name = "mysql_smallint"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 spelling: str = SmallIntType.SPELLINGS[0]):
        super().__init__(dialect, unsigned=unsigned, spelling=spelling)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

class MySQLBigIntType(BigIntType):
    """MySQL ``BIGINT`` with optional UNSIGNED / ZEROFILL.

    Inherits :class:`BigIntType`; see :class:`MySQLIntType` for why the
    width stays on the core class and only the MySQL attributes live here.
    """

    name = "mysql_bigint"

    zerofill: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 zerofill: bool = False,
                 spelling: str = BigIntType.SPELLINGS[0]):
        super().__init__(dialect, unsigned=unsigned, spelling=spelling)
        self.zerofill = zerofill

    PARAMETERS = ("unsigned", "zerofill",)

# ---------------------------------------------------------------------------
# BLOB size variants
# ---------------------------------------------------------------------------

class MySQLTinyBlobType(BlobType):
    """MySQL ``TINYBLOB`` — maximum 255 bytes."""

    name = "mysql_tinyblob"


class MySQLBlobType(BlobType):
    """MySQL ``BLOB`` — maximum 65,535 bytes."""

    name = "mysql_blob"


class MySQLMediumBlobType(BlobType):
    """MySQL ``MEDIUMBLOB`` — maximum 16,777,215 bytes."""

    name = "mysql_mediumblob"


class MySQLLongBlobType(BlobType):
    """MySQL ``LONGBLOB`` — maximum 4,294,967,295 bytes."""

    name = "mysql_longblob"


# ---------------------------------------------------------------------------
# TEXT size variants
# ---------------------------------------------------------------------------

class MySQLTinyTextType(TextType):
    """MySQL ``TINYTEXT`` — maximum 255 bytes."""

    name = "mysql_tinytext"


class MySQLTextType(TextType):
    """MySQL ``TEXT`` — maximum 65,535 bytes."""

    name = "mysql_text"


class MySQLMediumTextType(TextType):
    """MySQL ``MEDIUMTEXT`` — maximum 16,777,215 bytes."""

    name = "mysql_mediumtext"


class MySQLLongTextType(TextType):
    """MySQL ``LONGTEXT`` — maximum 4,294,967,295 bytes."""

    name = "mysql_longtext"


# ---------------------------------------------------------------------------
# Bit type
# ---------------------------------------------------------------------------

class MySQLBitType(DataType):
    """MySQL ``BIT[(n)]`` — a bit field of *n* bits.

    Sits directly on ``DataType`` rather than on :class:`BooleanType` because
    ``BIT(n)`` is a **bit string, not a truth value**. The concrete differences
    are not cosmetic:

    * ``n`` is part of the type. ``BIT(1)`` happens to hold a truth value, but
      ``BIT(64)`` holds a 64-bit number, and ``BIT(1)`` is only a boolean by
      coincidence of width — the same coincidence that makes ``TINYINT(1)`` a
      boolean, and which MySQL itself only supports by convention.
    * The values are written and read with MySQL's bit operators and literals:
      ``b'1010'``, ``col & 0x0F``, ``col | mask``, ``col ^ mask``,
      ``BIT_COUNT(col)``. A boolean has none of these; keeping ``n`` and the
      root placement keeps all of them available.

    There is no core concept to inherit: SQL:2016 has no bit-string *type* at
    all (``BIT`` there is a predicate and ``BIT_LENGTH`` an operator), and the
    nearest core neighbour, ``BooleanType``, is a two-state type — inheriting it
    would claim ``BIT(64)`` is a boolean.
    """

    name = "mysql_bit"

    n: Optional[int] = None

    def __init__(self, dialect=None, n: Optional[int] = None):
        super().__init__(dialect)
        self.n = n

    PARAMETERS = ("n",)

# ---------------------------------------------------------------------------
# Year type
# ---------------------------------------------------------------------------

class MySQLYearType(DataType):
    """MySQL ``YEAR[(4)]`` — a one-byte year, stored in 1901..2155 (plus 0000).

    Sits directly on ``DataType`` for two reasons, one about the type and one
    about the server:

    * **No other backend has it, so there is no core concept to inherit.**
      SQL:2016 has no ``YEAR`` type — a year is part of a ``DATE``. MySQL's
      ``YEAR`` is a genuinely narrower type: it occupies **one byte**, not
      three or four, its range is 1901-2155 plus the sentinel ``0000``, it has
      no month or day at all, and ``YEAR`` arithmetic is date arithmetic
      (adding one rolls no month), so ``SELECT YEAR + 1`` is a ``DATE``, not an
      integer.
    * **It is on its way out.** ``YEAR`` is deprecated as of MySQL 8.0 and the
      ``YEAR(2)`` display width has been deprecated since 5.7 — the field is
      carried so an existing schema round-trips, not because new DDL should
      reach for it.

    Putting it on ``DataType`` keeps the framework from implying that a ``DATE``
    and a ``YEAR`` are the same concept.
    """

    name = "mysql_year"

    display_width: Optional[int] = None

    def __init__(self, dialect=None, display_width: Optional[int] = None):
        super().__init__(dialect)
        self.display_width = display_width

    PARAMETERS = ("display_width",)

# ---------------------------------------------------------------------------
# Binary / VarBinary
# ---------------------------------------------------------------------------

class MySQLBinaryType(BinaryType):
    """MySQL ``BINARY[(M)]`` — fixed-length binary.

    ``M`` is optional here and **means something when it is omitted**: the
    manual's grammar is ``BINARY[(M)]`` — "An optional length *M* represents the
    column length in bytes. **If omitted, *M* defaults to 1.**" (§13.3.1) — so
    ``MySQLBinaryType()`` renders ``BINARY`` and the column the server creates is
    one byte wide. Verified against every scenario server this backend is tested
    against: ``CREATE TABLE t (c BINARY)`` reports ``binary(1)`` in
    ``information_schema.COLUMNS.COLUMN_TYPE`` on MySQL 5.6.51, 5.7.44, 8.0.46,
    8.4.11, 9.2.0, 9.4.0 and 26.7.0.

    That is a legal column and a legal answer for a caller that asked for a
    one-byte fixed byte string, so the length stays optional — but the default is
    a real storage width, and any concept whose *own* width is fixed must not
    come through here unparameterised. See :class:`MySQLUUIDType`, which is the
    case that went wrong: a UUID substitution reaching this class with no length
    rendered a one-byte column that cannot hold a UUID at all. A concept that
    knows its own width needs its own class.
    """

    name = "mysql_binary"

    def __init__(self, dialect=None, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = length


class MySQLVarBinaryType(VarBinaryType):
    """MySQL ``VARBINARY(n)`` — variable-length binary.

    ``length`` is **required**, because ``VARBINARY``'s grammar is
    ``VARBINARY(M)`` with ``M`` *not* optional (MySQL manual §13.3.1, "The
    VARBINARY type is similar to the VARCHAR type, but stores binary byte
    strings rather than nonbinary character strings. *M* represents the maximum
    column length in bytes."). ``CREATE TABLE t (c VARBINARY)`` is a syntax
    error on every server this backend is tested against (MySQL 5.6.51 and 26.7.0
    both answer error 1064), so there is no such thing as an unparameterised
    MySQL variable-length byte string — the same reasoning
    :class:`MySQLVectorType` follows for its ``dim``.

    This is deliberately **asymmetric with** :class:`MySQLBinaryType`, where the
    length genuinely is optional: MySQL's grammar there is ``BINARY[(M)]`` and
    the manual says what the omitted ``M`` means — "If omitted, *M* defaults to
    1" (§13.3.1). So ``MySQLBinaryType()`` renders ``BINARY`` and really is a
    one-byte column, which is a legal column and a legal answer for a caller
    that asked for one. For ``VARBINARY`` there is no default to fall back on.
    """

    name = "mysql_varbinary"

    def __init__(self, dialect=None, length: Optional[int] = None):
        super().__init__(dialect)
        if length is None:
            raise ValueError(
                "MySQLVarBinaryType requires a length: MySQL's grammar is "
                "VARBINARY(M) with M mandatory, so a column of this type "
                "cannot be declared without one"
            )
        self.length = length


class MySQLUUIDType(UUIDType):
    """MySQL's storage for a UUID — ``BINARY(16)``, the 16 raw bytes.

    MySQL has **no ``UUID`` data type**. Its data-types chapter is a closed
    list of categories — "numeric types, date and time types, string (character
    and byte) types, spatial types, and the JSON data type" (manual §13) — and
    ``UUID`` is in none of them. The concept therefore has to be substituted
    (D9), and *the substitute's size is part of the substitute*: a UUID is 128
    bits (RFC 9562, ISO/IEC 9834-8) and MySQL's own binary UUID form is 16
    bytes — ``UUID_TO_BIN()`` "return[s] [the] binary UUID [as] a
    ``VARBINARY(16)`` value" (§14.23).

    **Why this is its own class rather than ``MySQLBinaryType`` with a length.**
    ``suggested_data_types()`` names a *class*, and the generic ``UUIDType``
    carries no length for it to hand over. Naming the general byte-string class
    therefore yields a constructible substitute whose rendered SQL is ``BINARY``
    — which the manual defines as ``BINARY(1)``: "An optional length *M*
    represents the column length in bytes. **If omitted, *M* defaults to 1.**"
    (§13.3.1). A caller who asked for a UUID column through that mapping would
    silently get a one-byte column, and the server confirms it:
    ``CREATE TABLE t (c BINARY)`` yields ``binary(1)`` in
    ``information_schema.COLUMNS.COLUMN_TYPE`` on MySQL 5.6.51, 5.7.44, 8.0.46,
    8.4.11, 9.2.0, 9.4.0 and 26.7.0. Inserting a 16-byte UUID into it fails
    with error 1406 "Data too long for column", or on a non-strict server
    truncates to its first byte. Fixed here by making the width part of the
    class, where it cannot be forgotten.

    **Why ``BINARY(16)`` and not ``VARBINARY(16)``** — both are defensible, and
    the difference is real, so the choice is stated:

    * A UUID is *always* 16 bytes; there is no shorter one. So the width is
      not a ceiling, it is the only legal value. ``BINARY(16)``'s *M* "represents
      the column length in bytes" — a length. ``VARBINARY(16)``'s *M* "represents
      the **maximum** column length in bytes" (§13.3.1) — a bound, which
      ``VARBINARY(16)`` satisfies for a three-byte value that is not a UUID at
      all. The fixed form is the one whose type states the concept.
    * ``BINARY``'s 0x00 right-padding is the usual objection to it, and the
      manual raises it: "When BINARY values are stored, they are right-padded
      with the pad value to the specified length. The pad value is 0x00… If the
      value retrieved must be the same as the value specified for storage with
      no padding, it might be preferable to use VARBINARY" (§13.3.3). That caveat
      is about a value *shorter* than *M*. A UUID is never shorter than 16
      bytes, so no pad byte is ever added and no trailing byte is ever stripped:
      the caveat is checked and does not apply here.
    * Storage: ``BINARY(M)`` costs "M bytes" while ``VARCHAR(M), VARBINARY(M)``
      cost "L + 1 bytes" for values up to 255 bytes (§13.7) — 16 bytes versus 17
      for the same UUID, the extra one being a per-row length prefix.
    * Comparison is the same either way: for both types "all bytes are
      significant in comparisons, including ORDER BY and DISTINCT operations"
      (§13.3.3), so there is no trailing-zero stripping surprise in a key
      column. Fixed width adds the rest: every value the same size, so
      ``ORDER BY``, ``DISTINCT`` and index locality all work on constant-width
      data.
    * ``UUID_TO_BIN()``'s ``VARBINARY(16)`` is what that *function returns*, and
      a return type is not a column declaration. It is not evidence that a
      column should be ``VARBINARY(16)``; the manual's own guidance for storing
      a UUID in a column is the fixed form, which is also what MariaDB's ``UUID``
      documentation calls the pre-native emulation (``BINARY(16)``).

    **What introspection reads back.** ``BINARY(16)`` on the wire is this type
    (see ``MySQLTypeSupportMixin.parse_type``), so ``render`` → ``parse_type``
    returns an equal value object. A plain 16-byte column that is not meant as a
    UUID now introspects as ``mysql_uuid``; that is the same trade the framework
    already makes for ``TINYINT(1)``, which it reads as ``BooleanType``. The
    storage is unchanged either way — only the name the framework gives it.

    Official documentation:
    - Data type categories (no UUID among them):
      https://dev.mysql.com/doc/refman/8.4/en/data-types.html
    - ``BINARY[(M)]`` and "If omitted, *M* defaults to 1"; ``VARBINARY(M)``:
      https://dev.mysql.com/doc/refman/8.4/en/string-type-syntax.html
    - Padding, comparison and the VARBINARY caveat:
      https://dev.mysql.com/doc/refman/8.4/en/binary-varbinary.html
    - Storage per type:
      https://dev.mysql.com/doc/refman/8.4/en/storage-requirements.html
    - ``UUID_TO_BIN()`` / ``BIN_TO_UUID()``:
      https://dev.mysql.com/doc/refman/8.4/en/miscellaneous-functions.html
    """

    name = "mysql_uuid"

    #: A UUID is 128 bits, so it is 16 bytes in binary storage, always. This is
    #: the one number that decides the rendered SQL, and it is a class constant
    #: rather than a constructor argument because there is no UUID of any other
    #: width — it is a property of the concept, not a choice a caller makes.
    BYTE_LENGTH = 16

    #: Empty: the width is fixed, so two instances of this type are the same
    #: column by construction and there is no field left to disagree about.
    PARAMETERS = ()


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

class MySQLEnumType(EnumType):
    """MySQL ``ENUM('val', ...)`` with optional CHARACTER SET / COLLATE.

    Inherits the core ``EnumType`` (values validation and value-object
    semantics); the MySQL rendering (including charset/collation
    extensions) lives in the dialect's ``format_data_type_mysql_enum``.

    ``charset`` / ``collation`` are **fields on the type, not types of their
    own**, which is the framework-wide position: ``CHARACTER SET`` names an
    attribute a column may carry (a table default, a collation, even a single
    literal), so promoting a character set to a ``DataType`` would describe
    something that is not a storage class. The same three attributes ride on
    :class:`MySQLSetType`.
    """

    name = "mysql_enum"

    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None):
        if values is None:
            raise ValueError("MySQLEnumType requires values")
        if not values:
            raise ValueError("ENUM must have at least one value")
        super().__init__(dialect, values=values)
        self.charset = charset
        self.collation = collation

    PARAMETERS = ("values", "charset", "collation",)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# SET
# ---------------------------------------------------------------------------

class MySQLSetType(DataType):
    """MySQL ``SET('val', ...)`` — a combination of zero or more members.

    Sits directly on ``DataType`` and deliberately **not** on
    :class:`EnumType`, because a SET column holds *more than one* member at a
    time and that is a different concept, not a variant:

    * ``ENUM`` is single-valued: ``col = 'a'`` is the whole test, the value
      stores one index, and an invalid value is an error in strict mode.
    * ``SET`` is multi-valued: ``col = 'a,b'`` is normal, the value stores a
      **bitmap** over the member list (one bit per member, max 64), and
      ``FIND_IN_SET(col, 'a')`` answers membership. ``''`` is the empty set,
      which has no ``ENUM`` equivalent at all.

    Rendering is a different word (``SET(...)`` vs ``ENUM(...)``) and the
    operators differ, so inheriting ``EnumType`` would claim a set is an enum.
    SQL:2016 has no ``SET`` type either, so there is no core concept to
    inherit; the values list and the charset/collation fields are what make
    this a type rather than a free-text ``CustomType``.
    """

    name = "mysql_set"

    values: Tuple[str, ...] = ()
    charset: Optional[str] = None
    collation: Optional[str] = None

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 charset: Optional[str] = None, collation: Optional[str] = None):
        super().__init__(dialect)
        if values is None:
            raise ValueError("MySQLSetType requires values")
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = tuple(values)
        self.charset = charset
        self.collation = collation

    PARAMETERS = ("values", "charset", "collation",)

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(values={self.values!r}, "
                f"charset={self.charset!r}, collation={self.collation!r})")


# ---------------------------------------------------------------------------
# Spatial / Geometry types
# ---------------------------------------------------------------------------

class MySQLGeometryType(DataType):
    """MySQL ``GEOMETRY`` with optional SRID — any geometry, any shape.

    Sits directly on ``DataType`` because **geometry is not part of the SQL
    type system this framework models**: SQL:2016 has no geometric types, and
    every backend spells the family differently and disagrees on the storage
    format (MySQL and MariaDB store a WKB-ish internal layout with an SRID
    attribute, PostgreSQL/PostGIS stores it in PostGIS's own layout, Oracle has
    SDO_GEOMETRY). There is no core concept to inherit, and inventing one for
    fourteen types across five backends would be a much larger decision than
    this hierarchy refactor is making — so the family stays here, on the root,
    with the reasoning written down.

    ``POINT``, ``LINESTRING``, ``POLYGON``, the three ``MULTI*`` shapes and
    ``GEOMETRYCOLLECTION`` derive from here rather than from the root because
    that relationship *is* an identity claim and the server makes it too: a
    ``POINT`` column is a geometry whose value is always one point, every
    spatial function (``ST_Distance``, ``ST_Within``, …) accepts it, and
    ``GEOMETRYCOLLECTION`` of points is not a ``POINT``. Each subclass
    documents the value semantics that distinguish it.
    """

    name = "mysql_geometry"

    srid: Optional[int] = None

    def __init__(self, dialect=None, srid: Optional[int] = None):
        super().__init__(dialect)
        self.srid = srid

    PARAMETERS = ("srid",)

class MySQLPointType(MySQLGeometryType):
    """MySQL ``POINT`` — a geometry whose value is exactly one (x, y) pair.

    Not a ``GEOMETRY`` with an arbitrary shape: the value exposes ``ST_X`` /
    ``ST_Y``, serialises as a bare coordinate pair, and cannot be empty, so a
    ``POINT`` column is distinguishable from a ``GEOMETRY`` column that happens
    to hold a point.
    """

    name = "mysql_point"


class MySQLLineStringType(MySQLGeometryType):
    """MySQL ``LINESTRING`` — one open path of two or more vertices.

    Distinguished from ``MULTILINESTRING`` by cardinality: exactly one path, and
    ``ST_Length`` / ``ST_StartPoint`` / ``ST_EndPoint`` apply to the value
    directly rather than per member.
    """

    name = "mysql_linestring"


class MySQLPolygonType(MySQLGeometryType):
    """MySQL ``POLYGON`` — one closed area with an interior ring and holes.

    Distinct from ``MULTIPOLYGON`` because a single polygon carries one outer
    ring plus zero or more interior rings; ``ST_Area`` / ``ST_IsValid`` treat
    it as one region rather than a collection.
    """

    name = "mysql_polygon"


class MySQLMultiPointType(MySQLGeometryType):
    """MySQL ``MULTIPOINT`` — a set of points.

    Multiplicity is the difference: ``ST_X`` is meaningless on it while
    ``ST_NumGeometries`` / ``ST_GeometryN`` are the accessors, so a
    ``MULTIPOINT`` column is not a ``POINT`` column that may hold several.
    """

    name = "mysql_multipoint"


class MySQLMultiLineStringType(MySQLGeometryType):
    """MySQL ``MULTILINESTRING`` — a set of open paths.

    The multi- form of :class:`MySQLLineStringType`; every length/endpoint
    accessor is per member.
    """

    name = "mysql_multilinestring"


class MySQLMultiPolygonType(MySQLGeometryType):
    """MySQL ``MULTIPOLYGON`` — a set of polygons.

    The multi- form of :class:`MySQLPolygonType`; area and validity are
    per member, which is what makes the storage and the operators different
    from a single polygon.
    """

    name = "mysql_multipolygon"


class MySQLGeometryCollectionType(MySQLGeometryType):
    """MySQL ``GEOMETRYCOLLECTION`` — a heterogeneous bag of geometries.

    Distinct from every ``MULTI*`` type above because its members may be of
    *mixed* kinds: a collection of a point and a polygon is legal here and
    illegal in ``MULTIPOINT``. That heterogeneity is the reason the type
    exists at all.
    """

    name = "mysql_geometrycollection"


# ---------------------------------------------------------------------------
# VECTOR type (MySQL 9.0+)
# ---------------------------------------------------------------------------

class MySQLVectorType(DataType):
    """MySQL ``VECTOR(n)`` — a fixed-dimension vector, for nearest-neighbour
    search.

    Sits directly on ``DataType`` because the *other* backends' vector types
    are not the same concept, so no core concept is warranted:

    * PostgreSQL's pgvector stores a fixed-length float array and adds an HNSW
      index over it; ClickHouse renamed its equivalent to ``QBit``. Neither
      shares MySQL's storage layout, its ``VECTOR(n)`` dimension limit, or its
      ``DISTANCE`` operators (``EUCLIDEAN_DISTANCE``, ``COSINE_DISTANCE``,
      ``DOT_PRODUCT``), and the two projects' vector semantics have moved
      independently.

    ``dim`` is required: MySQL's ``VECTOR`` always carries its dimension in the
    DDL, so there is no such thing as an unparameterised MySQL vector.
    """

    name = "mysql_vector"

    dim: Optional[int] = None

    def __init__(self, dialect=None, dim: Optional[int] = None):
        super().__init__(dialect)
        if dim is None:
            raise ValueError("MySQLVectorType requires dim")
        self.dim = dim

    PARAMETERS = ("dim",)
