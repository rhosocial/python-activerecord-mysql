"""
MySQL-specific full-text search using MATCH...AGAINST.
"""
from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

if __name__ == "__main__":
    config = MySQLConnectionConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "test"),
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
    )
    backend = MySQLBackend(connection_config=config)
    backend.connect()
    dialect = backend.dialect

    from rhosocial.activerecord.backend.expression import (  # noqa: E402
        CreateTableStatement,
        InsertStatement,
        ValuesSource,
        DropTableStatement,
    )
    from rhosocial.activerecord.backend.expression.core import Parameter  # noqa: E402
    from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
        ColumnConstraint,
        ColumnDefinition,
        ColumnNotNullConstraint,
        ColumnPrimaryKeyConstraint,
    )

    drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, "articles"), if_exists=True)
    sql, params = drop_table.to_sql()
    backend.execute(sql, params)

    create_table = CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, "articles"),
        columns=[
            ColumnDefinition(
                "id",
                integer_auto_increment_parts(None, "INT")[0],
                constraints=[
                    ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
                    ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
                ],
             attributes=integer_auto_increment_parts(None, "INT")[1]),
            ColumnDefinition("title", "VARCHAR(200)"),
            ColumnDefinition("content", "TEXT"),
        ],
        if_not_exists=True,
    )
    sql, params = create_table.to_sql()
    backend.execute(sql, params)

    insert = InsertStatement(
        dialect=dialect,
        into=Table(dialect, "articles"),
        columns=["title", "content"],
        source=ValuesSource(
            dialect,
            [
                [
                    Parameter(dialect, "MySQL Tutorial"),
                    Parameter(dialect, "This tutorial covers MySQL database basics and advanced features."),
                ],
                [
                    Parameter(dialect, "PostgreSQL Guide"),
                    Parameter(dialect, "Learn PostgreSQL from beginner to advanced level."),
                ],
                [
                    Parameter(dialect, "Database Design"),
                    Parameter(dialect, "Best practices for designing relational databases including MySQL and PostgreSQL."),
                ],
            ],
        ),
    )
    sql, params = insert.to_sql()
    backend.execute(sql, params)

    sql = "CREATE FULLTEXT INDEX ft_idx ON articles (title, content)"
    backend.execute(sql)

    # ============================================================
    # SECTION: Business Logic (the pattern to learn)
    # ============================================================
    from rhosocial.activerecord.backend.expression import QueryStatement, Column  # noqa: E402
    from rhosocial.activerecord.backend.impl.mysql.expression import MySQLMatchAgainstExpression, MatchAgainstMode  # noqa: E402
    from rhosocial.activerecord.backend.expression.objects import Table

    # Use MySQLMatchAgainstExpression for full-text search
    match_expr = MySQLMatchAgainstExpression(
        dialect=dialect,
        columns=["title", "content"],
        search_string="MySQL",
        mode=MatchAgainstMode.NATURAL_LANGUAGE,
    )

    # Create separate instances - one for SELECT with alias, one for WHERE without alias
    match_with_alias = MySQLMatchAgainstExpression(
        dialect=dialect,
        columns=["title", "content"],
        search_string="MySQL",
        mode=MatchAgainstMode.NATURAL_LANGUAGE,
    )
    match_with_alias = match_with_alias.as_("relevance")

    match_for_where = MySQLMatchAgainstExpression(
        dialect=dialect,
        columns=["title", "content"],
        search_string="MySQL",
        mode=MatchAgainstMode.NATURAL_LANGUAGE,
    )

    # Build query using expression (supports alias via as_)
    query = QueryStatement(
        dialect=dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "title"),
            match_with_alias,
        ],
        from_=Table(dialect, "articles"),
        where=(match_for_where > 0),
    )

    sql, params = query.to_sql()
    print(f"SQL: {sql}")
    print(f"Params: {params}")

    # ============================================================
    # SECTION: Execution (run the expression)
    # ============================================================
    result = backend.execute(sql, params)
    print(f"Rows returned: {len(result.data) if result.data else 0}")
    for row in result.data or []:
        print(f" {row}")

    # ============================================================
    # SECTION: Teardown (necessary for execution, reference only)
    # ============================================================
    backend.disconnect()
