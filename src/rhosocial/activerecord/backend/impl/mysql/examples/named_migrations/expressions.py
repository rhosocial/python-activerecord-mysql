# src/rhosocial/activerecord/backend/impl/mysql/examples/named_migrations/expressions.py
"""
DDL named expression functions for MySQL migration examples.

Each function receives a *dialect* and returns a DDL expression object.
These are the building blocks used by NamedMigration up()/down() methods.
"""

from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    DropTableExpression,
)
from rhosocial.activerecord.backend.impl.mysql.expression.types import (
    MySQLIntType,
    MySQLTextType,
)


def create_users_table(dialect):
    """CREATE TABLE users (id INT PRIMARY KEY AUTO_INCREMENT, name TEXT, email TEXT)."""
    return CreateTableExpression(
        dialect,
        table="users",
        columns=[
            ColumnDefinition(
                "id",
                MySQLIntType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.AUTO_INCREMENT),
                ],
            ),
            ColumnDefinition("name", MySQLTextType()),
            ColumnDefinition("email", MySQLTextType()),
        ],
    )


def drop_users_table(dialect):
    """DROP TABLE IF EXISTS users."""
    return DropTableExpression(dialect, table="users", if_exists=True)


def create_posts_table(dialect):
    """CREATE TABLE posts (id INT PRIMARY KEY AUTO_INCREMENT, title TEXT, user_id INT)."""
    return CreateTableExpression(
        dialect,
        table="posts",
        columns=[
            ColumnDefinition(
                "id",
                MySQLIntType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.AUTO_INCREMENT),
                ],
            ),
            ColumnDefinition("title", MySQLTextType()),
            ColumnDefinition("user_id", MySQLIntType()),
        ],
    )


def drop_posts_table(dialect):
    """DROP TABLE IF EXISTS posts."""
    return DropTableExpression(dialect, table="posts", if_exists=True)