# src/rhosocial/activerecord/backend/impl/mysql/mixins/schema.py
"""MySQL's answer to "does this engine have an inner schema namespace?".

It does not. MySQL's ``SCHEMA`` is a pure synonym for ``DATABASE``:
``CREATE SCHEMA app`` creates the database ``app``, ``DROP SCHEMA`` drops it,
and nothing lives inside a database under a further name. So the qualified
name for a table is `` `database`.`table` `` and never three parts.

The namespace slot that addresses a database is therefore ``catalog_name``,
not ``schema_name``. Passing ``catalog_name="app"`` renders `` `app`.`users` ``
and addresses the database ``app``; passing ``schema_name="app"`` cannot be
expressed at all and raises ``UnsupportedFeatureError`` rather than being
silently dropped. The naming half -- which slot holds the database, and the
single level ``format_qualified_name`` emits -- lives in
:class:`~rhosocial.activerecord.backend.impl.mysql.mixins.namespace.MySQLNamespaceMixin`.

What lives here is the *DDL spelling* switch: MySQL servers do accept the
``SCHEMA`` keyword in place of ``DATABASE``, so those probes stay True even
though no inner namespace is modelled. Use
:class:`~rhosocial.activerecord.backend.impl.mysql.mixins.ddl_database.MySQLDatabaseMixin`
for the statements themselves.
"""

__all__ = ["MySQLSchemaMixin"]


class MySQLSchemaMixin:
    """Capability probes for the ``SCHEMA`` spelling of database DDL."""

    def supports_schema(self) -> bool:
        """Whether MySQL models named schema namespaces *inside* a database.

        Always ``False``: MySQL has no inner namespace layer. The database is
        the outermost namespace, and it is modelled as the catalog -- see
        :class:`~rhosocial.activerecord.backend.impl.mysql.mixins.namespace.MySQLNamespaceMixin`.
        """
        return False

    def supports_create_schema(self) -> bool:
        """Whether CREATE SCHEMA is accepted.

        ``True``, because MySQL treats the keyword as a synonym for CREATE
        DATABASE. The object created is a database, not a schema.
        """
        return True

    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is accepted.

        ``True``, because MySQL treats the keyword as a synonym for DROP
        DATABASE. The object dropped is a database, not a schema.
        """
        return True

    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is accepted.

        ``True``, as the database spelling of the same clause.
        """
        return True

    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is accepted.

        ``True``, as the database spelling of the same clause.
        """
        return True