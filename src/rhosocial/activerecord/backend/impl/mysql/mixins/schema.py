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
though no inner namespace is modelled. The statements themselves are rendered
here as the ``SCHEMA`` spelling of the database DDL; the equivalent
``DATABASE`` spelling lives in
:class:`~rhosocial.activerecord.backend.impl.mysql.mixins.ddl_database.MySQLDatabaseMixin`.
"""

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Schema

from .object_kind import require_kind

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import (
        CreateSchemaStatement,
        DropSchemaStatement,
    )

__all__ = ["MySQLSchemaMixin"]


class MySQLSchemaMixin:
    """Capability probes and formatters for the ``SCHEMA`` spelling of database DDL."""

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

    def supports_schema_authorization(self) -> bool:
        """Whether CREATE SCHEMA AUTHORIZATION is accepted.

        Always ``False``: MySQL's CREATE SCHEMA takes a name and the inline
        database options, and has no ``AUTHORIZATION`` owner clause. The grant
        model is a separate privilege statement, not a DDL attribute.
        """
        return False

    def supports_schema_cascade(self) -> bool:
        """Whether DROP SCHEMA CASCADE is accepted.

        Always ``False``: MySQL's DROP SCHEMA grammar ends at the name. Dropping
        a database always removes its contents, so there is no ``CASCADE``
        behaviour to opt into.
        """
        return False

    def supports_schema_restrict(self) -> bool:
        """Whether DROP SCHEMA RESTRICT is accepted.

        Always ``False``: MySQL's DROP SCHEMA grammar has no ``RESTRICT``
        clause.
        """
        return False

    def format_create_schema_statement(
        self, expr: "CreateSchemaStatement"
    ) -> Tuple[str, tuple]:
        """Format ``CREATE SCHEMA`` as the database synonym MySQL parses.

        Raises:
            TypeError: ``expr.schema`` is not a Schema. Another object kind
                would have had its own name rendered as the schema's.
            UnsupportedFeatureError: The dialect does not claim CREATE SCHEMA,
                the ``IF NOT EXISTS`` clause, or ``AUTHORIZATION``.
        """
        require_kind(expr.schema, Schema, "CreateSchemaStatement.schema")
        if not self.supports_create_schema():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA",
                f"{self.name} does not support CREATE SCHEMA."
            )
        if expr.if_not_exists and not self.supports_schema_if_not_exists():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA IF NOT EXISTS",
                f"{self.name} does not support CREATE SCHEMA IF NOT EXISTS."
            )
        if expr.authorization and not self.supports_schema_authorization():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA AUTHORIZATION",
                f"{self.name} does not support CREATE SCHEMA AUTHORIZATION; "
                "grant privileges with GRANT after the schema exists."
            )
        parts = ["CREATE SCHEMA"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(expr.schema.to_sql()[0])
        return " ".join(parts), ()

    def format_drop_schema_statement(
        self, expr: "DropSchemaStatement"
    ) -> Tuple[str, tuple]:
        """Format ``DROP SCHEMA`` as the database synonym MySQL parses.

        Raises:
            TypeError: ``expr.schema`` is not a Schema; another object kind
                would have been named as the schema's.
            UnsupportedFeatureError: The dialect does not claim DROP SCHEMA,
                the ``IF EXISTS`` clause, or ``CASCADE`` / ``RESTRICT``.
        """
        require_kind(expr.schema, Schema, "DropSchemaStatement.schema")
        if not self.supports_drop_schema():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA",
                f"{self.name} does not support DROP SCHEMA."
            )
        if expr.if_exists and not self.supports_schema_if_exists():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA IF EXISTS",
                f"{self.name} does not support DROP SCHEMA IF EXISTS."
            )
        if expr.cascade and not self.supports_schema_cascade():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA CASCADE",
                f"{self.name} does not support DROP SCHEMA CASCADE; dropping "
                "a MySQL database always removes its contents."
            )
        if expr.restrict and not self.supports_schema_restrict():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA RESTRICT",
                f"{self.name} does not support DROP SCHEMA RESTRICT."
            )
        parts = ["DROP SCHEMA"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.schema.to_sql()[0])
        return " ".join(parts), ()
