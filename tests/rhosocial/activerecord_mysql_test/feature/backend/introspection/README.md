# introspection tests

The MySQL introspection stack: tables, columns, indexes (incl. FULLTEXT), foreign keys, triggers, views and database info, cache management, SHOW command parsing and the status introspector (server status/variables/replication).

## Key files

- `test_introspection_cache.py` — cache invalidation, expiration, thread safety
- `test_introspection_columns.py` — list_columns / get_column_info / column_exists
- `test_introspection_database.py` — get_database_info and capabilities
- `test_introspection_foreign_keys.py` — foreign key metadata
- `test_introspection_indexes.py` — index metadata incl. primary key
- `test_introspection_tables.py` — table metadata
- `test_introspection_triggers.py` — trigger metadata
- `test_introspection_views.py` — view metadata
- `test_show_functionality.py` — SHOW ... parsing
- `test_status_introspector.py` — status introspector categories and replication info
