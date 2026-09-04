# ddl tests

MySQL-specific DDL coverage: storage options, comments, auto-increment and inline indexes, CREATE TABLE ... LIKE, RENAME/TRUNCATE/ALTER statement coverage, administrative statement branch coverage, auto-increment regressions, MySQL 9.7 GIPK regression execution, and expression-level CreateTableExpression.diff() for the MySQL dialect.

## Key files

- `test_admin_statement_coverage.py` — admin/maintenance/routine statement branches
- `test_auto_increment_ddl.py` — auto-increment / defaults / timestamp DDL regressions
- `test_create_table_expression_diff.py` — CreateTableExpression.diff() with MySQL overrides (in-place MODIFY COLUMN)
- `test_create_table_like.py` — CREATE TABLE ... LIKE rendering
- `test_ddl_features.py` — ENGINE/CHARSET/COMMENT/SET/ENUM and friends
- `test_mysql97_ddl_regression_execution.py` — MySQL 9.7 GIPK / function regressions
- `test_statement_coverage.py` — RENAME TABLE, TRUNCATE, LOAD XML, routines, maintenance
