# tests/rhosocial/activerecord_mysql_test/feature/query/worker/conftest.py
"""
Pytest configuration for query worker tests.

This file re-exports fixtures from the corresponding testsuite.
"""
# Use pytest_plugins to avoid ImportPathMismatchError when multiple
# worker/conftest.py files exist in different directories
pytest_plugins = ["rhosocial.activerecord.testsuite.feature.query.worker.conftest"]
