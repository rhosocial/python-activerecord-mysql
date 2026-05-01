"""
MySQL Full-Text Search example - MATCH...AGAINST.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

config = MySQLConnectionConfig(
    host='localhost',
    port=3306,
    database='test',
    username='test',
    password='test',
)
backend = MySQLBackend(connection_config=config)
dialect = backend.dialect

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.impl.mysql.expression import MySQLMatchAgainstExpression, MatchAgainstMode
from rhosocial.activerecord.backend.expression.core import TableExpression

# Create a full-text search expression
# MySQL 5.6+ supports FULLTEXT indexes on InnoDB
articles = TableExpression(dialect, 'articles')

# Natural language search (default)
match_expr = MySQLMatchAgainstExpression(
    dialect=dialect,
    columns=['title', 'content'],
    search_string='database',
    mode=MatchAgainstMode.NATURAL_LANGUAGE,
)

sql, params = match_expr.to_sql()
print(f"Natural Language: {sql}")
print(f"Params: {params}")

# Boolean mode (allows wildcards, operators)
match_boolean = MySQLMatchAgainstExpression(
    dialect=dialect,
    columns=['title', 'content'],
    search_string='+mysql -oracle',
    mode=MatchAgainstMode.BOOLEAN,
)

sql, params = match_boolean.to_sql()
print(f"Boolean: {sql}")

# With query expansion
match_expanded = MySQLMatchAgainstExpression(
    dialect=dialect,
    columns=['title', 'content'],
    search_string='database',
    mode=MatchAgainstMode.NATURAL_LANGUAGE_WITH_QUERY_EXPANSION,
)

sql, params = match_expanded.to_sql()
print(f"With Query Expansion: {sql}")

# ============================================================
# SECTION: Output (reference)
# ============================================================
# Expected outputs:
# NATURAL LANGUAGE: MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)
# BOOLEAN: MATCH(title, content) AGAINST(%s IN BOOLEAN MODE)
# WITH QUERY EXPANSION: MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION)
