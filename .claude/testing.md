# Testing Guide - python-activerecord-mysql

> AI Assistant Note: This document covers MySQL backend-specific testing requirements.

## Project-Specific Information

| Item | Value |
|------|-------|
| **Python Version** | 3.8+ |
| **Database Driver** | mysql-connector-python |
| **Free-Threading Support** | ✅ Yes |

## Dependencies

```toml
dependencies = [
    "rhosocial-activerecord>=0.9.0,<2.0.0",
    "mysql-connector-python>=9.0.0"
]
```

## Quick Test Commands

```bash
# Activate virtual environment and set PYTHONPATH
cd /mnt/i/GitHubRepositories/rhosocial/python-activerecord-mysql
source .venv/bin/activate
export PYTHONPATH=src

# Run tests
pytest

# Run specific test directory
pytest tests/rhosocial/activerecord_mysql_test/feature/basic/
```

## Backend-Specific Test Markers

```python
markers = [
    "mysql_json: MySQL-specific JSON tests",
]
```

## Key Differences from Core

- Uses MySQL-specific dialect in `src/rhosocial/activerecord/backend/impl/mysql/dialect.py`
- Schema files in `tests/rhosocial/activerecord_mysql_test/feature/basic/schema/`
- Provider implementation in `tests/providers/`

## Reference

- [Core testing guide](../python-activerecord/.claude/testing.md)
- [MySQL backend development](../python-activerecord/.claude/backend_development.md)