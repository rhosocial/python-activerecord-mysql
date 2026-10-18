# src/rhosocial/activerecord/backend/impl/mysql/mixins/typed_value.py
"""MySQL's spellings for the value types whose literal form is its own.

MySQL agrees with the base on NULL, booleans, numbers, strings and
date/time values -- measured, not assumed: on 8.0.46 (192.168.1.3:14682)
and on the server at 192.168.1.3:14686 (which answers ``SELECT VERSION()``
with ``26.7.0``), a ``CREATE TABLE`` carrying ``DEFAULT TRUE`` /
``DEFAULT FALSE`` / ``DEFAULT 42`` / ``DEFAULT 1.5`` / ``DEFAULT 1.25`` /
``DEFAULT 'x''y'`` / ``DEFAULT '2026-10-17'`` / ``DEFAULT '10:30:00'`` /
``DEFAULT '2026-10-17 10:00:00'`` is accepted and the defaults read back
as the same values, so no tier-1 method is overridden here. One tier-1
detail is MySQL's and is already where it belongs rather than here:
under the default ``sql_mode`` the backslash is an escape character
(measured: ``'a\\b'`` read back as ``'a\\x08'``), so ``format_literal``
routes strings through this dialect's ``_escape_sql_string``, which
doubles backslashes unless ``NO_BACKSLASH_ESCAPES`` is active.

Two value types differ, and both differ because MySQL's grammar says so:

* **binary** -- ``X'0102FF'``, the hex form from MySQL's literal grammar.
  Measured on both servers: ``SELECT X'0102FF'`` returns ``b'\\x01\\x02\\xff'``
  and a ``VARBINARY(16) DEFAULT X'0102FF'`` fills the column with those
  bytes on insert (likewise ``TINYBLOB DEFAULT (X'0102FF')`` through the
  expression-default syntax). Lower-case ``x'0102ff'`` is accepted too; the
  upper-case spelling is what this dialect renders. Quoting the bytes as
  text would produce a string that reads back as text -- the wrong value in
  a binary column and the wrong length besides.
* **UUID** -- the bare quoted canonical text. MySQL has no UUID column
  type (it numbers rows with ``AUTO_INCREMENT`` and spells UUIDs as
  ``CHAR(36)``/``BINARY(16)`` storage conventions) and no literal form
  other than the text. Measured on both servers: ``CHAR(36) DEFAULT
  '550e8400-e29b-41d4-a716-446655440000'`` reads the hyphenated text back
  verbatim, so one spelling serves the text home and no ``::uuid``-style
  suffix exists to add.

**INTERVAL stays unimplemented on purpose.** Measured on both servers:
``SELECT INTERVAL 1 DAY`` is a syntax error (errno 1064), and so is a
``DEFAULT INTERVAL 1 DAY`` in every column shape tried -- ``INTERVAL``
exists only as the keyword parameter of date arithmetic
(``DATE_ADD('2026-10-17', INTERVAL 1 DAY)`` is accepted), never as a
value with a literal form of its own. A DDL position that needs one
cannot be written for this engine, so this mixin defines no
``format_interval_value`` -- leaving the method absent is what makes the
base's explicit failure the answer here.
"""

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.values import TypedValue


class MySQLTypedValueMixin:
    """MySQL's tier-2 value literals.

    Stands alone rather than inheriting :class:`TypedValueMixin`, like every
    other MySQL mixin: the dialect composes the specific mixin ahead of the
    generic one, and these two methods win by that position. Inheriting would
    put the base ahead of the other generic mixins and make the ordering the
    dialect has to reason about depend on this class instead.
    """

    def format_binary_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A binary literal: ``X'0102FF'``, upper-case hex.

        Rendered from the bytes the node holds, because this conversion has
        to happen somewhere and the dialect is the only layer that knows
        which form its engine accepts.
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        return f"X'{bytes(expr.value).hex().upper()}'", ()

    def format_uuid_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A UUID as the bare quoted canonical text.

        MySQL has no UUID type and no literal other than the text, so the
        quoted canonical form is the whole spelling; a ``CHAR(36)`` column
        reads it back verbatim (measured).
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        return self.format_literal(str(expr.value)), ()
