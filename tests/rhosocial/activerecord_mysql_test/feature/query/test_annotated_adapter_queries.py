# tests/rhosocial/activerecord_mysql_test/feature/query/test_annotated_adapter_queries.py
"""
This is a "bridge" file for the query features test group, specifically for
tests related to Annotated type adapters.

Its purpose is to import the generic tests from the `rhosocial-activerecord-testsuite`
package and make them discoverable by `pytest` within this project's test run.
"""

from rhosocial.activerecord.testsuite.feature.query.conftest import (
    annotated_query_fixtures,
)

from rhosocial.activerecord.testsuite.feature.query.test_annotated_adapter_queries import *
