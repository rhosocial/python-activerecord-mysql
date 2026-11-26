# tests/rhosocial/activerecord_mysql_test/feature/backend/execute/introspection/test_introspection_state.py
"""Live tests for the neutral object-state families MySQL can answer.

These cover the families beside partitioning: indexes, constraints, derived
backing indexes, schema names and item existence. The answers are core's
neutral dataclasses, not this backend's own records.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import ProtocolNotImplementedError
from rhosocial.activerecord.backend.introspection.types import (
    ConstraintState,
    DerivedObjectState,
    IndexState,
    ItemKind,
)

from mysql_live_server import mysql_server_available

pytestmark = pytest.mark.skipif(
    not mysql_server_available(),
    reason="No MySQL server reachable from the configured scenarios",
)


class TestListIndexStates:
    def test_reports_neutral_index_states(self, backend_with_tables):
        states = backend_with_tables.introspector.list_index_states("users")

        assert states
        assert all(isinstance(state, IndexState) for state in states)
        assert {"PRIMARY", "idx_users_email", "idx_users_name_age"} <= {
            state.name for state in states
        }
        assert all(state.usable and state.visible for state in states)
        email = next(state for state in states if state.name == "idx_users_email")
        assert email.unique
        assert email.method == "btree"
        assert email.backs_constraint == "idx_users_email"


class TestListConstraintStates:
    def test_reports_neutral_constraint_states(self, backend_with_tables):
        states = backend_with_tables.introspector.list_constraint_states("users")

        assert states
        assert all(isinstance(state, ConstraintState) for state in states)
        kinds = {state.kind for state in states}
        assert "primary_key" in kinds
        assert "unique" in kinds
        primary = next(state for state in states if state.kind == "primary_key")
        assert primary.name == "PRIMARY"
        assert primary.backing_index == "PRIMARY"
        assert primary.validated and primary.enforced
        assert not primary.deferred and not primary.disabled


class TestListDerivedObjects:
    def test_reports_the_backing_indexes(self, backend_with_tables):
        states = backend_with_tables.introspector.list_derived_objects("users")

        assert all(isinstance(state, DerivedObjectState) for state in states)
        assert all(state.kind == "backing_index" for state in states)
        assert {"PRIMARY", "idx_users_email"} <= {state.name for state in states}


class TestListSchemas:
    def test_includes_the_connected_database(self, backend_with_tables):
        names = backend_with_tables.introspector.list_schemas()

        assert backend_with_tables.config.database in names


class TestItemExists:
    def test_tables_and_missing_tables(self, backend_with_tables):
        assert backend_with_tables.introspector.item_exists(ItemKind.TABLE, "users")
        assert not backend_with_tables.introspector.item_exists(
            ItemKind.TABLE, "state_does_not_exist"
        )

    def test_the_connected_schema(self, backend_with_tables):
        assert backend_with_tables.introspector.item_exists(
            ItemKind.SCHEMA, backend_with_tables.config.database
        )

    def test_a_sequence_does_not_exist_in_mysql(self, backend_with_tables):
        assert not backend_with_tables.introspector.item_exists(
            ItemKind.SEQUENCE, "state_does_not_exist"
        )

    def test_an_index_name_alone_is_refused(self, backend_with_tables):
        with pytest.raises(ProtocolNotImplementedError):
            backend_with_tables.introspector.item_exists(ItemKind.INDEX, "idx_users_email")
