# schema tests

SchemaSupport capability semantics on the MySQL dialect: under strict semantics `SCHEMA` is only an alias for `DATABASE`, so the umbrella flag is False while the granular CREATE/DROP SCHEMA DDL flags stay True.

## Key files

- `test_schema_support.py` — SchemaSupport capability semantics
