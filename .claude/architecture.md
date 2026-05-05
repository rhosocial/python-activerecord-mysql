# Architecture Guide - python-activerecord-mysql

> MySQL backend implementation for rhosocial-activerecord

## Project Overview

| Item | Value |
|------|-------|
| **Database** | MySQL |
| **Python Driver** | mysql-connector-python |
| **Python Version** | 3.8+ |
| **Package** | rhosocial-activerecord-mysql |

## Directory Structure

```
python-activerecord-mysql/
├── src/rhosocial/activerecord/backend/impl/mysql/
│   ├── __init__.py           # Backend initialization
│   ├── __main__.py           # CLI entry point
│   ├── backend.py            # Sync backend implementation
│   ├── async_backend.py      # Async backend implementation
│   ├── config.py             # Configuration
│   ├── dialect.py            # MySQL dialect
│   ├── protocols.py          # Protocol definitions
│   ├── transaction.py        # Transaction management
│   ├── adapters.py           # Type adapters
│   ├── mixins.py             # MySQL-specific mixins
│   ├── types.py              # MySQL-specific types
│   ├── cli/                  # CLI commands
│   ├── expression/           # MySQL-specific expressions
│   │   ├── json.py           # JSON functions
│   │   ├── match_against.py  # FULLTEXT search
│   │   ├── locking.py        # Locking expressions
│   │   └── spatial.py        # Spatial functions
│   ├── functions/            # MySQL-specific functions
│   ├── introspection/        # Schema introspection
│   └── show/                 # SHOW statements
├── tests/
│   └── rhosocial/activerecord_mysql_test/
└── pyproject.toml
```

## MySQL-Specific Features

- **JSON functions**: JSON_ARRAY, JSON_OBJECT, JSON_CONTAINS, etc.
- **FULLTEXT search**: MATCH AGAINST for full-text queries
- **Spatial types**: GEOMETRY, POINT, POLYGON, etc.
- **Locking**: FOR UPDATE, LOCK IN SHARE MODE
- **INSERT ... ON DUPLICATE KEY UPDATE**: Upsert support

## Expression-Dialect System

All backends use Expression-Dialect separation:
- Expression classes define query structure
- Dialect classes handle SQL generation
- MySQL-specific expressions in `expression/` directory

## Namespace Package

Backend implementations use Python namespace packages (no `__init__.py` in impl subdirectories):
- Core: `rhosocial.activerecord`
- Backend: `rhosocial.activerecord.backend.impl.mysql`

## Reference

- [Core architecture](../python-activerecord/.claude/architecture.md)
- [Backend development guide](../python-activerecord/.claude/backend_development.md)