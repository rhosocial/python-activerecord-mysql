# src/rhosocial/activerecord/backend/impl/mysql/protocols.py
"""MySQL dialect-specific protocol definitions.

This module defines protocols for features exclusive to MySQL,
which are not part of the SQL standard and not supported by other
mainstream databases.
"""
from typing import Protocol, runtime_checkable, Tuple, Any


@runtime_checkable
class MySQLTriggerSupport(Protocol):
    """MySQL trigger DDL protocol.

    Feature Source: Native support (no extension required)

    MySQL trigger features and restrictions:
    - FOR EACH ROW only (no FOR EACH STATEMENT)
    - No INSTEAD OF triggers
    - No WHEN condition
    - No REFERENCING clause
    - Single event per trigger (no OR syntax)
    - Trigger body is BEGIN...END block
    - Requires same definer as table

    Official Documentation:
    - CREATE TRIGGER: https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html
    - Trigger Restrictions: https://dev.mysql.com/doc/refman/8.0/en/trigger-restrictions.html

    Version Requirements:
    - Basic triggers: MySQL 5.0+
    - Multiple triggers per event: MySQL 5.7+
    """

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported.

        MySQL does NOT support INSTEAD OF triggers.
        """
        ...

    def supports_statement_trigger(self) -> bool:
        """Whether FOR EACH STATEMENT triggers are supported.

        MySQL does NOT support FOR EACH STATEMENT triggers.
        Only FOR EACH ROW is supported.
        """
        ...

    def supports_trigger_referencing(self) -> bool:
        """Whether REFERENCING clause is supported.

        MySQL does NOT support REFERENCING clause.
        OLD and NEW are implicit references.
        """
        ...

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition is supported.

        MySQL does NOT support WHEN condition in triggers.
        """
        ...

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported.

        MySQL 5.7+ supports IF NOT EXISTS.
        """
        ...

    def format_create_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement (MySQL syntax)."""
        ...

    def format_drop_trigger_statement(self, expr) -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement (MySQL syntax)."""
        ...


@runtime_checkable
class MySQLTableSupport(Protocol):
    """MySQL table DDL protocol.

    Feature Source: Native support (no extension required)

    MySQL table features beyond SQL standard:
    - ENGINE storage engine selection
    - CHARSET/COLLATE character set options
    - AUTO_INCREMENT column attribute
    - Inline index definitions in CREATE TABLE
    - Table-level COMMENT
    - CREATE TABLE ... LIKE syntax
    - Row format options

    Official Documentation:
    - CREATE TABLE: https://dev.mysql.com/doc/refman/8.0/en/create-table.html
    - CREATE TABLE ... LIKE: https://dev.mysql.com/doc/refman/8.0/en/create-table-like.html

    Version Requirements:
    - Basic features: All versions
    - Various storage engines: MySQL 5.5+
    """

    def supports_table_like_syntax(self) -> bool:
        """Whether CREATE TABLE ... LIKE is supported.

        MySQL supports copying table structure with LIKE syntax.
        """
        ...

    def supports_inline_index(self) -> bool:
        """Whether inline index definitions are supported.

        MySQL allows INDEX/KEY definitions within CREATE TABLE.
        """
        ...

    def supports_storage_engine_option(self) -> bool:
        """Whether ENGINE option is supported.

        MySQL supports multiple storage engines (InnoDB, MyISAM, etc.).
        """
        ...

    def supports_charset_option(self) -> bool:
        """Whether CHARSET/COLLATE options are supported.

        MySQL supports character set and collation at table level.
        """
        ...

    def format_create_table_statement(self, expr) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement (MySQL syntax)."""
        ...
