# src/rhosocial/activerecord/backend/impl/mysql/mixins/column_type.py
"""MySQL's answer to "which column class does this Python type mean here".

This is the **column** half of the column-type protocol (the storage half is
:meth:`MySQLDialect.suggested_data_types`), and it answers a different question
from that one. A column class says what a value can *do*; how it is stored is
the DDL layer's separate decision, and neither reads the other. Two of MySQL's
best-known divergences from a textbook server are therefore **absent** from the
table below and are stated here instead, so their absence reads as a decision
rather than an oversight:

* **``UUID``** is native on MariaDB from 10.7 and on **no MySQL version at all**.
  MySQL's data-types chapter is a closed list of categories ("numeric types,
  date and time types, string (character and byte) types, spatial types, and
  the JSON data type", manual §13) and ``UUID`` is in none of them; the
  substitute ``BINARY(16)`` is :class:`MySQLUUIDType`'s business, and the answer
  here is :class:`UUIDColumn` on every version -- a UUID carries the same
  operations (equality, ``IN``) wherever it is kept, so gating the column class
  on a storage fact would be the exact confusion the two-layer split removes.
* **``JSON``** *is* native here from 5.7.8, where MariaDB's is a ``LONGTEXT``
  alias with a ``CHECK``. That difference is likewise a storage fact and the
  column answer is the same on both servers.

What does reach the table is MySQL's lack of a **native array type** -- there is
none on any version, so a column cannot be declared ``INT[]`` -- and its single
**version-gated refusal**, the ``dict`` entry below 5.7.

The table answers all eighteen entries of the framework's common Python types
(:data:`~rhosocial.activerecord.testsuite.feature.query.typed_column.column_helpers.COMMON_TYPES`
is where that contract list lives). An entry left out is indistinguishable from
one nobody thought about, and only the first of those is actionable; where MySQL
genuinely has no workaround the value is ``None``, which resolution turns into a
definition-time failure naming ``UseColumnType`` -- the only place a ``None``
appears in this table is the ``dict`` entry below 5.7, and the comment on
:meth:`MySQLColumnTypeMixin.suggested_column_types` says why.

Evidence is the measured live-server sweep recorded in
``.claude/plan/2026-10-08/`` of the core repository
(``suggested-pairing-json.md`` §"发现" items 3 and 7,
``suggested-pairing-array.md`` §"发现" items 3, 5 and 8,
``suggested-pairing-string-enum.md`` §"发现" item 1), against MySQL 5.6.51,
5.7.44, 8.0.46 and later. Where a gate is read from
:class:`~...json.MySQLJSONFunctionMixin` rather than written here, it is so the
column-level answer and the expression-level one cannot drift apart.
"""

import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.dialect.mixins.column_type import ColumnTypeMixin
from rhosocial.activerecord.backend.expression.column_types import (
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

#: MySQL's complete answer for every entry of the framework's common types.
#:
#: The deviations from the portable baseline core's :mod:`dummy` dialect states
#: are the four containers and ``timedelta``, and each is a fact about this
#: server rather than a preference. ``None`` appears nowhere here: a class
#: attribute carrying a refusal would make every dialect at every version look
#: like it refused the entry, so the one version-dependent refusal lives in
#: :meth:`MySQLColumnTypeMixin.suggested_column_types` alone.
MYSQL_COLUMN_TYPES: Dict[Any, Optional[Type[ColumnBase]]] = {
    # --- numbers core keeps together ------------------------------------
    # §1 calls `float` the DOUBLE family here and `Decimal` the DECIMAL(p,s)
    # family. MySQL stores the two as distinct types and their arithmetic
    # differs -- a DECIMAL is exact and a DOUBLE is not, and the rounding rules
    # differ with them (`suggested-pairing-numeric.md`). Core now models both
    # width families with one :class:`NumericColumn` -- the width belongs to
    # the DDL layer's ``DataType`` and the operation surface is the same -- so
    # both entries answer it here. The measurement that told them apart is
    # recorded on the DDL side, where ``DOUBLE`` and ``DECIMAL(p,s)`` are still
    # two different classes.
    float: NumericColumn,
    decimal.Decimal: NumericColumn,
    # --- booleans ------------------------------------------------------
    # `BOOL` is an alias for `TINYINT(1)`, not an independent type, but the
    # column class is unaffected: `is_true` / `is_false` / `&` / `|` / `~`
    # and comparison are BooleanColumn's, and core renders the literals as
    # TRUE / FALSE. Measured on 5.6.51 and 8.0.46 with 21 probes
    # (`suggested-mappings.md` §7): the boolean family works on every MySQL
    # version with no version difference.
    bool: BooleanColumn,
    # --- integers ------------------------------------------------------
    # `INT` in the width axis, with `unsigned` as a separate field rather
    # than a separate class: overflow semantics ride with the DataType
    # declaration, and `UNSIGNED` subtraction raising is a storage
    # behaviour, not a different operation surface. The whole-number
    # answer is the baseline every backend gives.
    int: IntegerColumn,
    # --- text and bytes ------------------------------------------------
    # `VARCHAR(n)`; the default `utf8mb4_*_ci` collation already makes
    # `LIKE` case-insensitive, which is why the missing `ilike` is a
    # narrowing rather than a capability loss. MySQL's `LENGTH` measures
    # bytes, not characters.
    str: StringColumn,
    # `BLOB` / the `*BLOB` width family; equality, byte length, substring,
    # concatenation and hex were all measured present. Read-back shape is
    # a value-layer fact (Phase 4), not a column-class one.
    bytes: BinaryColumn,
    bytearray: BinaryColumn,
    # --- date / time ---------------------------------------------------
    # `DATE`, `TIME` and `DATETIME(6)` are three real storage types and
    # TimestampColumn is the one class core has for all three; core has no
    # DateColumn / TimeColumn yet, so this is the shared baseline rather
    # than a statement that the three are one type. A tz-aware `datetime`
    # normalises to the same entry (core has no separate tz entry), and
    # MySQL's offset-form `CONVERT_TZ` needs no tz tables -- measured
    # working with zero configuration (`suggested-mappings.md` §8.1), so
    # nothing about tz is narrowed either.
    datetime.date: TimestampColumn,
    datetime.time: TimestampColumn,
    datetime.datetime: TimestampColumn,
    # A timedelta is a number of seconds here. MySQL's `INTERVAL` is an
    # *expression* keyword (`DATE_ADD(d, INTERVAL 30 DAY)`) and never a
    # column type -- `CREATE TABLE t (c INTERVAL)` is a syntax error -- so
    # a span must be stored as a count or as its character form. There is
    # no `IntervalColumn` class yet, which is the same answer core's
    # baseline gives, reached here from measurement: on 5.7+ and later the
    # driver rejects a bound timedelta outright (`suggested-mappings.md`
    # §8.2 item 4), so the value layer serialises it to seconds.
    datetime.timedelta: NumericColumn,
    # No native UUID type on any MySQL version (see the module docstring),
    # and the column answer is unchanged by that: equality and `IN` are
    # portable SQL. The `BINARY(16)` substitute and the `CHAR(36)` /
    # `BINARY(16)` double convention belong to `suggested_data_types()`.
    uuid.UUID: UUIDColumn,
    # --- documents -----------------------------------------------------
    # Native `JSON` from 5.7.8, and the JSON function family from 5.7.0.
    # On 5.7.44 and 8.0.46 the whole measured set passes: plain DDL, a
    # bound JSON text parameter, scalar and nested path extraction
    # (`JSON_UNQUOTE(JSON_EXTRACT(...))` / `->>`), key existence
    # (`JSON_CONTAINS_PATH`), array length (`JSON_LENGTH(col,'$.arr')`),
    # validity (`JSON_VALID`), containment (`JSON_CONTAINS`) and array
    # building (`JSON_ARRAY_APPEND`, `JSON_OBJECT`).
    #
    # **Below 5.7 this entry is `None`** -- see
    # `suggested_column_types`, which is the one version-dependent cell.
    #
    # Two measured traps belong to the rendering / value phase and are
    # recorded here so they are not lost (Phase 2b): a directly bound
    # parameter compared with `=` returns **zero rows silently** on MySQL,
    # so equality must render `CAST(? AS JSON)`; and on 5.7 a whole-column
    # *text* equality returns zero rows on rows that do match, because the
    # JSON column normalises whitespace and key order -- semantic equality
    # is `JSON_CONTAINS(x, all) AND JSON_LENGTH(x) = n`
    # (`suggested-mappings.md` §8.3 rows 1 and 2).
    dict: JSONColumn,
    # --- arrays ----------------------------------------------------------
    # MySQL has **no array type at any version**; there is nothing to
    # declare a column as. The operations a sequence carries -- length,
    # element access, containment, whole-column equality -- are all
    # reachable through the JSON path family measured working from 5.7, so
    # `ArrayColumn`, whose whole surface is `array_length` / `unnest` over
    # a *native* array, would name operations this server answers by
    # refusing. Note `unnest` narrows to 8.0.4+ below: it goes through
    # `JSON_TABLE`, which 5.7 does not have.
    list: JSONColumn,
    # A tuple is heterogeneous and a set is de-duplicated by Python before
    # it ever reaches the server; neither changes the storage family, which
    # is a JSON document.
    tuple: JSONColumn,
    set: JSONColumn,
    frozenset: JSONColumn,
    # Native `ENUM(...)`, so the value semantics are text: comparison, `IN`
    # and `ORDER BY` render, and the driver hands back a `str`. Two
    # measured facts a caller must not assume away, both from the value
    # layer rather than this table: `ORDER BY` on a native enum is
    # **declaration order**, not lexicographic, and on a **non-strict 5.6**
    # server an illegal member is stored as `''` instead of being refused
    # (`suggested-mappings.md` §8.3 row 5).
    enum.Enum: StringColumn,
}


class MySQLColumnTypeMixin(ColumnTypeMixin):
    """MySQL's full eighteen-entry column-type table, and its narrowing.

    Composed into :class:`~...dialect.MySQLDialect` **ahead of** core's
    :class:`ColumnTypeMixin`, so its :meth:`suggested_column_types` is the one a
    model layer reaches.

    The table is a class attribute because it does not vary by version; the one
    version-dependent entry (:meth:`suggested_column_types` below) is handled by
    copying the dict rather than mutating the shared one, so a per-version
    answer cannot leak into the next dialect built at another version.
    """

    def suggested_column_types(self) -> Dict[Any, Optional[Type[ColumnBase]]]:
        """The table above, with ``dict`` refused below MySQL 5.7.

        The one version-dependent entry, and it is a refusal rather than a
        different class.

        **Below 5.7** MySQL 5.6.51 has neither the ``JSON`` column type nor any
        JSON function: the measured failures are ``1064`` for the DDL and
        ``1305 FUNCTION ... JSON_EXTRACT / JSON_VALID / JSON_OBJECT does not
        exist`` for the operations. What a value would bind as is plain text
        that reads back as a ``str``, while every operation a
        :class:`~...column_types.JSONColumn` offers -- ``json_path``,
        ``json_value``, key existence, array length, validity -- failed at the
        server. That is precisely the silent degradation the protocol forbids:
        a default that renders SQL the server rejects, with the error pointing
        at the column rather than at the annotation that asked for it. The
        honest answer is ``None``, which fails at model definition time and
        points the author at ``UseColumnType``.

        The gate is read from :meth:`MySQLJSONFunctionMixin.supports_json_path`
        (5.7.0, where ``JSON_EXTRACT`` appeared) rather than written here as a
        number, so the column-level answer and the expression-level one cannot
        disagree. It is deliberately the **functions**' boundary and not the
        native type's (5.7.8): between the two the server reads a JSON path
        perfectly well without a JSON column type, and refusing there would
        refuse queries it answers.

        **5.7 and above** :class:`~...column_types.JSONColumn`, measured
        working end to end on 5.7.44 and 8.0.46.

        The containers (``list`` / ``tuple`` / ``set`` / ``frozenset``) keep
        their :class:`~...column_types.JSONColumn` answer below 5.7 as well.
        The same argument as on MariaDB applies, and slightly more strongly
        here: a Python sequence still has length and containment to carry, and
        MySQL 5.6 will store and return the text faithfully (it does not
        normalise it, so whole-column text equality is even *correct* there).
        Refusing five entries to protect one would be a wider refusal than the
        measurement supports -- the measurement refuses the JSON *function*
        family, which is what ``dict`` is made of and what a bare sequence is
        not obliged to use.
        """
        table = dict(MYSQL_COLUMN_TYPES)

        if not self.supports_json_path():
            table[dict] = None

        return table


__all__ = ["MYSQL_COLUMN_TYPES", "MySQLColumnTypeMixin"]
