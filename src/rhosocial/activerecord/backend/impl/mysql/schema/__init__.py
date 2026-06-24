# src/rhosocial/activerecord/backend/impl/mysql/schema/__init__.py
"""MySQL schema differ."""

from .differ import MySQLSchemaDiffer

__all__ = ["MySQLSchemaDiffer"]
