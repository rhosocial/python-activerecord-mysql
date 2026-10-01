# src/rhosocial/activerecord/backend/impl/mysql/mixins/schema.py
class MySQLSchemaMixin:
    """MySQL schema (database) support."""

    def supports_schema(self) -> bool:
        """Whether a schema qualifier can be rendered and used.

        True, and what it names needs saying plainly: on MySQL a *schema is a
        database*. ``CREATE SCHEMA`` and ``SHOW SCHEMAS`` are accepted and list
        databases -- verified against 5.6 and 5.7, where ``SHOW DATABASES`` and
        ``SHOW SCHEMAS`` return identical lists.

        So ``schema_name="app"`` renders as ```app```.```users``` and addresses
        the database ``app``. This is not the same thing as PostgreSQL's schema,
        which is a namespace *inside* a database; the two cannot be assumed
        interchangeable even though both fill the same parameter.
        """
        return True

    def supports_create_schema(self) -> bool:
        """Whether CREATE SCHEMA is supported."""
        return True

    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is supported."""
        return True

    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is supported."""
        return True

    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is supported."""
        return True
