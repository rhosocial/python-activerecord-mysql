# src/rhosocial/activerecord/backend/impl/mysql/mixins/literal.py
"""MySQL's tier-2 value literals.

``SQLDialectBase.format_literal`` is the single entry point for writing a
value as SQL text, and it resolves in three tiers: the portable scalars it
knows, the types a backend spells for themselves, and the
literal-construction protocol. This module is MySQL's second tier, and it
carries the two spellings measured on the live servers (8.0.46 at
192.168.1.3:14682, and the server at 192.168.1.3:14686 which answers
``SELECT VERSION()`` with ``26.7.0``):

* ``bytes`` becomes ``X'0102FF'``, the hex form from MySQL's literal
  grammar. ``SELECT X'0102FF'`` returns ``b'\\x01\\x02\\xff'`` and a
  ``VARBINARY(16) DEFAULT X'0102FF'`` fills the column with those bytes on
  insert (likewise ``TINYBLOB DEFAULT (X'0102FF')`` through the
  expression-default syntax). Lower-case ``x'0102ff'`` is accepted too, and
  upper-case is what this dialect renders. Quoting the bytes as text would
  read back as text -- the wrong value in a binary column and the wrong
  length besides.
* ``UUID`` becomes the bare quoted canonical text. MySQL has no UUID
  column type (it numbers rows with ``AUTO_INCREMENT`` and spells UUIDs as
  ``CHAR(36)``/``BINARY(16)`` storage conventions) and no literal form other
  than the text: measured, ``CHAR(36) DEFAULT '550e8400-e29b-41d4-a716-446655440000'``
  reads the hyphenated text back verbatim.

**INTERVAL stays unimplemented on purpose.** ``timedelta`` has no branch
here, so the base's explicit refusal is the answer: measured on both
servers, ``SELECT INTERVAL 1 DAY`` is a syntax error (errno 1064) and so is
a ``DEFAULT INTERVAL 1 DAY`` in every column shape tried. ``INTERVAL``
exists only as the keyword parameter of date arithmetic
(``DATE_ADD('2026-10-17', INTERVAL 1 DAY)`` is accepted), never as a value
with a literal form of its own, and this module adds no spelling rather
than inventing one.

The tier-1 forms (NULL / booleans / numbers / strings / dates / times /
datetimes) are the base's, reached through this dialect's backslash-doubling
``_escape_sql_string``: measured on both servers as ``DEFAULT`` values
accepted by ``CREATE TABLE`` (``TRUE`` / ``FALSE`` / ``42`` / ``1.5`` /
``1.25`` / ``'x''y'`` / ``'2026-10-17'`` / ``'10:30:00'`` /
``'2026-10-17 10:00:00'``), each reading back unchanged -- so none of them
is overridden here.
"""

import uuid
from typing import Any


class MySQLLiteralValueMixin:
    """MySQL's tier-2 branches of :meth:`format_literal`.

    Stands alone rather than inheriting the base, and the dialect composes
    it ahead of :class:`SQLDialectBase` -- the one base that defines
    ``format_literal`` -- because a mixin placed after the class it
    overrides never wins.
    """

    def format_literal(self, value: Any) -> str:
        """Render *value* as inline SQL text, MySQL's spelling where it has one.

        Args:
            value: The host value to write into the statement.

        Returns:
            The escaped literal text, without a bind parameter.

        Raises:
            TypeError: The base implementation refuses a type MySQL has no
                literal form for -- ``timedelta`` among them, which is the
                measured answer rather than a gap.
        """
        if isinstance(value, (bytes, bytearray)):
            return f"X'{bytes(value).hex().upper()}'"
        if isinstance(value, uuid.UUID):
            return self.format_literal(str(value))
        return super().format_literal(value)
