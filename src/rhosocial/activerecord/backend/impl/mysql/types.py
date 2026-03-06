# src/rhosocial/activerecord/backend/impl/mysql/types.py
"""
MySQL-specific type definitions and helpers.

This module provides type-safe helpers for defining MySQL-specific data types
such as ENUM and SET.
"""
from typing import List, Optional


class MySQLEnumType:
    """Helper class for defining MySQL ENUM column types.

    MySQL ENUM is a string object with a value chosen from a list of permitted values.

    Example:
        >>> status = MySQLEnumType(['pending', 'processing', 'ready', 'failed'])
        >>> status.to_sql()
        "ENUM('pending','processing','ready','failed')"

        >>> # With charset and collation
        >>> status = MySQLEnumType(['active', 'inactive'], charset='utf8mb4', collation='utf8mb4_bin')
        >>> status.to_sql()
        "ENUM('active','inactive') CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"
    """

    def __init__(
        self,
        values: List[str],
        charset: Optional[str] = None,
        collation: Optional[str] = None
    ):
        """
        Initialize ENUM type definition.

        Args:
            values: List of allowed enum values (must have at least one value)
            charset: Optional character set specification
            collation: Optional collation specification

        Raises:
            ValueError: If values list is empty
        """
        if not values:
            raise ValueError("ENUM must have at least one value")
        self.values = values
        self.charset = charset
        self.collation = collation

    def to_sql(self) -> str:
        """
        Generate the SQL type definition string.

        Returns:
            SQL type definition for use in CREATE TABLE statements
        """
        values_str = ','.join(f"'{v}'" for v in self.values)
        result = f"ENUM({values_str})"

        if self.charset:
            result += f" CHARACTER SET {self.charset}"
        if self.collation:
            result += f" COLLATE {self.collation}"

        return result

    def __str__(self) -> str:
        return self.to_sql()

    def __repr__(self) -> str:
        return f"MySQLEnumType(values={self.values!r}, charset={self.charset!r}, collation={self.collation!r})"


class MySQLSetType:
    """Helper class for defining MySQL SET column types.

    MySQL SET is a string object that can have zero or more values,
    each of which must be chosen from a list of permitted values.

    Example:
        >>> tags = MySQLSetType(['tag1', 'tag2', 'tag3'])
        >>> tags.to_sql()
        "SET('tag1','tag2','tag3')"

        >>> # With charset
        >>> tags = MySQLSetType(['a', 'b'], charset='utf8mb4')
        >>> tags.to_sql()
        "SET('a','b') CHARACTER SET utf8mb4"
    """

    def __init__(
        self,
        values: List[str],
        charset: Optional[str] = None,
        collation: Optional[str] = None
    ):
        """
        Initialize SET type definition.

        Args:
            values: List of allowed set values (must have at least one value)
            charset: Optional character set specification
            collation: Optional collation specification

        Raises:
            ValueError: If values list is empty
        """
        if not values:
            raise ValueError("SET must have at least one value")
        self.values = values
        self.charset = charset
        self.collation = collation

    def to_sql(self) -> str:
        """
        Generate the SQL type definition string.

        Returns:
            SQL type definition for use in CREATE TABLE statements
        """
        values_str = ','.join(f"'{v}'" for v in self.values)
        result = f"SET({values_str})"

        if self.charset:
            result += f" CHARACTER SET {self.charset}"
        if self.collation:
            result += f" COLLATE {self.collation}"

        return result

    def __str__(self) -> str:
        return self.to_sql()

    def __repr__(self) -> str:
        return f"MySQLSetType(values={self.values!r}, charset={self.charset!r}, collation={self.collation!r})"
