# src/rhosocial/activerecord/backend/impl/mysql/mixins/namespace.py
"""MySQL's naming side, as one answer.

MySQL has exactly one namespace level, and it is a **database**. ``CREATE SCHEMA``
is a synonym for ``CREATE DATABASE``, ``SHOW SCHEMAS`` for ``SHOW DATABASES``,
and nothing lives inside a database under a further name. So a qualified name is
`` `database`.`table` `` and never three parts.

Core's :class:`~rhosocial.activerecord.backend.dialect.mixins.schema_namespace.NamespaceMixin`
describes a two-slot shape -- a catalog outside a schema -- and renders each
level the object carries. That shape fits four of the nine dialects exactly,
fits MySQL well enough to work (the inner slot stays empty), and fits Oracle
only by accident. MySQL states its own arrangement here instead, for three
reasons:

* the outer slot is where MySQL's single level goes, and saying so once is
  clearer than leaving it to be inferred from which slot the caller filled;
* ``format_qualified_name`` is the spelling half, and a dialect with one level
  should not have to inherit a join that was written for two;
* the validation lives next to the spelling, so the rule "MySQL has no inner
  schema, so a ``schema_name`` is refused rather than dropped" can be read in
  one place.

The DDL switches stay in :class:`~...mixins.schema.MySQLSchemaMixin`, which
answers a different question -- whether MySQL accepts the ``SCHEMA`` *keyword*
-- and in :class:`~...mixins.ddl_database.MySQLDatabaseMixin`, which renders the
statements. Merging them would answer two unrelated questions with one boolean,
which is the name overloading this converges away from.

This mixin precedes :class:`NamespaceMixin` in ``MySQLDialect``'s base list:
it overrides ``supports_catalog`` and ``supports_catalog_qualification``, and
C3 requires an override to appear before what it overrides.
"""

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

__all__ = ["MySQLNamespaceMixin"]

#: MySQL caps database (and table, column, index) identifiers at 64 characters.
MAX_IDENTIFIER_LENGTH = 64

#: Characters MySQL refuses inside a database name because they separate the
#: parts of a qualified name.
_FORBIDDEN_IN_DATABASE_NAME = ("/", "\\", ".", "\x00")


class MySQLNamespaceMixin:
    """The database as MySQL's only namespace level.

    Replaces :class:`~rhosocial.activerecord.backend.impl.mysql.mixins.catalog.MySQLCatalogMixin`
    as this backend's naming-side mixin. The DDL probes that used to sit beside
    the naming ones moved to
    :class:`~rhosocial.activerecord.backend.impl.mysql.mixins.schema.MySQLSchemaMixin`,
    which already owned ``supports_schema``.
    """

    def supports_catalog(self) -> bool:
        """Whether MySQL models a namespace above the (absent) inner schema.

        ``True``: the database is that namespace, and it is the outer slot
        because there is nothing inside it.
        """
        return True

    def supports_catalog_qualification(self) -> bool:
        """Whether the database is rendered when a name carries one.

        ``True``. MySQL resolves ``db.tbl`` against the named database without
        changing the session's default database, so the qualifier is safe to
        emit unconditionally.
        """
        return True

    def validate_namespace(self, expr) -> None:
        """Accept or refuse the namespace levels *expr* carries.

        The outer slot is accepted and the inner one is not, because MySQL has
        nothing for it to name. A ``schema_name`` is refused rather than dropped:
        dropping it would render `` `users` `` for a caller who asked for
        ``reporting.users``, which is a different table in a different database.

        Raises:
            UnsupportedFeatureError: *expr* carries a ``schema_name``.
        """
        if expr.schema_name:
            raise UnsupportedFeatureError(
                self.name,
                "schema-qualified names",
                suggestion=(
                    f"{type(expr).__name__} carries schema_name="
                    f"{expr.schema_name!r}, but MySQL's only namespace level is "
                    f"the database, which is the catalog_name slot; pass "
                    f"catalog_name={expr.schema_name!r} instead"
                ),
            )
        if expr.catalog_name:
            self.validate_catalog_name(expr)
        return None

    def format_qualified_name(self, expr) -> tuple:
        """Spell *expr*'s name as `` `database`.`name` ``.

        One level, because MySQL has one. The separator is core's default ``.``
        and is not overridden: MySQL qualifies with a dot, so there is nothing
        to declare.

        Call :meth:`validate_namespace` first. This method assumes the levels
        are ones MySQL can express.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty because an
            identifier is never a bind parameter.
        """
        parts = []
        if expr.catalog_name:
            parts.append(
                self.format_identifier(expr.catalog_name, expr.catalog_need_quote)
            )
        parts.append(self.format_identifier(expr.name, expr.name_need_quote))
        return self.separator.join(parts), ()

    def validate_catalog_name(self, expr) -> None:
        """Accept or reject the database *expr* carries.

        Stricter than core's default, which accepts whatever the object already
        validated. MySQL adds two rules: a name longer than 64 characters is
        refused, and so is one containing a character MySQL reserves for
        separating the parts of a qualified name.

        Called while rendering rather than while constructing, because at
        construction the dialect may not be settled and the slot may not be
        filled in yet.

        Raises:
            UnsupportedFeatureError: The database name is empty, longer than
                MySQL's 64-character identifier limit, or contains one of the
                characters MySQL reserves for name qualification.
        """
        name = getattr(expr, "catalog_name", None)
        if not name:
            return
        if len(name) > MAX_IDENTIFIER_LENGTH:
            raise UnsupportedFeatureError(
                self.name,
                f"catalog names longer than {MAX_IDENTIFIER_LENGTH} characters",
                suggestion=(
                    f"catalog_name={name!r} is {len(name)} characters; MySQL "
                    f"limits database names to {MAX_IDENTIFIER_LENGTH}"
                ),
            )
        for char in _FORBIDDEN_IN_DATABASE_NAME:
            if char in name:
                raise UnsupportedFeatureError(
                    self.name,
                    "catalog names containing a name-separator character",
                    suggestion=(
                        f"catalog_name={name!r} contains {char!r}, which MySQL "
                        f"reserves for separating the parts of a qualified name"
                    ),
                )