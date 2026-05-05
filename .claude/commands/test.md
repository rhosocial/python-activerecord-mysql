Run the full test suite for python-activerecord-mysql.

**Prerequisites:**
```bash
cd /mnt/i/GitHubRepositories/rhosocial/python-activerecord-mysql
source .venv/bin/activate
export PYTHONPATH=src
```

**Run tests:**
```bash
pytest tests/ -v
```

**Test directories:**
- `tests/rhosocial/activerecord_mysql_test/feature/basic/` - Basic CRUD tests
- `tests/rhosocial/activerecord_mysql_test/feature/query/` - Query tests
- `tests/rhosocial/activerecord_mysql_test/feature/backend/` - Backend-specific tests

Show test results and any failures. Focus on failing tests and suggest fixes.