# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_database.py
"""MySQL database DDL mixin."""
from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Database

from .object_kind import require_kind

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_database import (
        AlterDatabaseExpression,
        CreateDatabaseExpression,
        DropDatabaseExpression,
    )


class MySQLDatabaseMixin:
    """MySQL database DDL support.

    MySQL's CREATE SCHEMA is synonymous with CREATE DATABASE.
    """

    def supports_database(self) -> bool:
        return True

    def supports_create_database(self) -> bool:
        return True

    def supports_drop_database(self) -> bool:
        return True

    def supports_alter_database(self) -> bool:
        return True

    def supports_database_if_not_exists(self) -> bool:
        return True

    def supports_database_if_exists(self) -> bool:
        return True

    def supports_database_encoding(self) -> bool:
        """MySQL supports CHARACTER SET."""
        return True

    def supports_database_collation(self) -> bool:
        """MySQL supports COLLATE."""
        return True

    def format_create_database_statement(
        self, expr: CreateDatabaseExpression
    ) -> Tuple[str, tuple]:
        """Format ``CREATE DATABASE``.

        Raises:
            TypeError: ``expr.database`` is not a
                :class:`~rhosocial.activerecord.backend.expression.objects.Database`.
                Another object kind would have had its own name rendered as the
                database's -- ``CREATE DATABASE `users``` is a well-formed
                statement addressing something else.
        """
        require_kind(expr.database, Database, "CreateDatabaseExpression.database")
        parts = ["CREATE DATABASE"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(expr.database.to_sql()[0])
        if expr.encoding:
            parts.append(f"CHARACTER SET {expr.encoding}")
        if expr.collation:
            parts.append(f"COLLATE {expr.collation}")
        return " ".join(parts), ()

    def format_drop_database_statement(
        self, expr: DropDatabaseExpression
    ) -> Tuple[str, tuple]:
        """Format ``DROP DATABASE``.

        Raises:
            TypeError: ``expr.database`` is not a Database; another object kind
                would be named as the database's.
        """
        require_kind(expr.database, Database, "DropDatabaseExpression.database")
        parts = ["DROP DATABASE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.database.to_sql()[0])
        return " ".join(parts), ()

    def format_alter_database_statement(
        self, expr: AlterDatabaseExpression
    ) -> Tuple[str, tuple]:
        """Format ``ALTER DATABASE``.

        Raises:
            TypeError: ``expr.database`` is not a Database; another object kind
                would be named as the database's.
        """
        from rhosocial.activerecord.backend.expression.statements.ddl_database import AlterDatabaseAction

        require_kind(expr.database, Database, "AlterDatabaseExpression.database")
        parts = ["ALTER DATABASE"]
        parts.append(expr.database.to_sql()[0])
        if expr.action == AlterDatabaseAction.CHARACTER_SET:
            parts.append(f"CHARACTER SET {expr.target}")
        elif expr.action == AlterDatabaseAction.COLLATION:
            parts.append(f"COLLATE {expr.target}")
        return " ".join(parts), ()


__all__ = ['MySQLDatabaseMixin']
