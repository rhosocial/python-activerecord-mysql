# tests/rhosocial/activerecord_mysql_test/feature/backend/construct/suggestion/test_change_point_suggestions.py
"""MySQL's four migration decision-point suggestion protocols, offline.

The plan hands a backend *frozen projections* of declarations. These tests
exercise both those real plan shapes and hand-built points carrying live nodes,
then render every supported chain one action per statement through the dialect's
own formatter -- so the asserted SQL proves the chain is made of existing nodes
and not a hand-written string.
"""

import dataclasses

import pytest
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    AddIndexAction,
    AddTableConstraintAction,
    AlterTableStatement,
    DropIndexAction,
    DropTableConstraintAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
    TableCheckConstraint,
    TableConstraint,
    TableExcludeConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.suggestion import (
    ColumnReorderSuggestion,
    PartitionSchemeChangeSuggestion,
    TableConstraintChangeSuggestion,
    TableIndexChangeSuggestion,
)
from rhosocial.activerecord.backend.suggestion.protocols import (
    ColumnReorderSuggestionSupport,
    PartitionSchemeChangeSuggestionSupport,
    TableConstraintChangeSuggestionSupport,
    TableIndexChangeSuggestionSupport,
)
from rhosocial.activerecord.migration.schema_change import _freeze

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
    MySQLRemovePartitioningExpression,
)

PROTOCOLS = (
    (ColumnReorderSuggestionSupport, "suggest_column_reorder"),
    (TableConstraintChangeSuggestionSupport, "suggest_table_constraint_change"),
    (TableIndexChangeSuggestionSupport, "suggest_table_index_change"),
    (PartitionSchemeChangeSuggestionSupport, "suggest_partition_scheme_change"),
)


@pytest.fixture
def dialect():
    return MySQLDialect((8, 0, 0))


def _alter(dialect, action):
    """One action in one statement: no multi-action SQL strings."""
    return AlterTableStatement(dialect, Table(dialect, "events"), [action]).to_sql()[0]


def _assert_frozen_answer(answer, point, state):
    assert type(answer) is type(point)
    assert answer.state == state
    with pytest.raises(dataclasses.FrozenInstanceError):
        answer.operations = False


def test_dialect_advertises_all_four_protocols(dialect):
    for protocol, method in PROTOCOLS:
        assert isinstance(dialect, protocol)
        assert callable(getattr(dialect, method))


class TestColumnReorder:
    def test_chain_is_absent_for_empty_point_and_unaddressable_for_a_real_reorder(self, dialect):
        empty = dialect.suggest_column_reorder(
            ColumnReorderSuggestion(
                table_name="events",
                old_order=("id", "created_at"),
                new_order=("id", "created_at"),
            )
        )
        _assert_frozen_answer(empty, empty, "absent")
        assert empty.operations is None

        point = ColumnReorderSuggestion(
            table_name="events",
            old_order=("id", "created_at"),
            new_order=("created_at", "id"),
            reordered_columns=("id", "created_at"),
        )
        answer = dialect.suggest_column_reorder(point)
        assert answer.state == "unaddressable"
        assert answer.operations is False
        assert answer.table_name == point.table_name
        assert answer.new_order == point.new_order
        # The incoming point is untouched: the answer is a new frozen value.
        assert point.operations is None

    def test_docstring_names_available_and_missing_mechanisms(self):
        doc = MySQLDialect.suggest_column_reorder.__doc__
        assert "MySQLAddColumn" in doc and "FIRST" in doc
        assert "ModifyColumnAction" in doc and "after_column" in doc
        assert "ColumnDefinition" in doc and "DataType" in doc
        assert "drop+add" in doc


class TestTableConstraintChange:
    def test_drop_chain_from_frozen_projection_renders(self, dialect):
        # A foreign-key branch is identified by its ``references`` parameter,
        # so the projection unambiguously names a kind MySQL drops by name.
        constraint = TableConstraint(
            dialect,
            branch=TableForeignKeyConstraint(dialect, ["b"], (Table(dialect, "parents"), ["id"])),
            name="fk_b",
        )
        point = TableConstraintChangeSuggestion(
            table_name="events", old_constraints=(_freeze(constraint),), new_constraints=()
        )
        answer = dialect.suggest_table_constraint_change(point)
        _assert_frozen_answer(answer, point, "actions")
        assert len(answer.operations) == 1
        assert isinstance(answer.operations[0], DropTableConstraintAction)
        assert _alter(dialect, answer.operations[0]) == (
            "ALTER TABLE `events` DROP CONSTRAINT `fk_b`"
        )

    def test_ambiguous_frozen_columns_branch_is_false(self, dialect):
        """PRIMARY KEY and UNIQUE freeze to the same ``{columns}`` branch."""
        unique = TableConstraint(
            dialect, branch=TableUniqueConstraint(dialect, ["created_at"]), name="uq_created"
        )
        point = TableConstraintChangeSuggestion(
            table_name="events", old_constraints=(_freeze(unique),), new_constraints=()
        )
        answer = dialect.suggest_table_constraint_change(point)
        _assert_frozen_answer(answer, point, "unaddressable")
        assert answer.operations is False

    def test_add_chain_from_live_node_renders(self, dialect):
        constraint = TableConstraint(
            dialect, branch=TableUniqueConstraint(dialect, ["created_at"]), name="uq_created"
        )
        point = TableConstraintChangeSuggestion(
            table_name="events", old_constraints=(), new_constraints=(constraint,)
        )
        answer = dialect.suggest_table_constraint_change(point)
        _assert_frozen_answer(answer, point, "actions")
        assert len(answer.operations) == 1
        assert isinstance(answer.operations[0], AddTableConstraintAction)
        assert _alter(dialect, answer.operations[0]) == (
            "ALTER TABLE `events` ADD CONSTRAINT `uq_created` UNIQUE (`created_at`)"
        )

    def test_drop_then_add_is_two_actions(self, dialect):
        old = TableConstraint(dialect, branch=TableUniqueConstraint(dialect, ["a"]), name="uq_a")
        new = TableConstraint(
            dialect,
            branch=TableForeignKeyConstraint(dialect, ["b"], (Table(dialect, "parents"), ["id"])),
            name="fk_b",
        )
        point = TableConstraintChangeSuggestion(
            table_name="events", old_constraints=(old,), new_constraints=(new,)
        )
        answer = dialect.suggest_table_constraint_change(point)
        assert [type(op) for op in answer.operations] == [
            DropTableConstraintAction,
            AddTableConstraintAction,
        ]
        assert _alter(dialect, answer.operations[0]) == (
            "ALTER TABLE `events` DROP CONSTRAINT `uq_a`"
        )
        assert _alter(dialect, answer.operations[1]) == (
            "ALTER TABLE `events` ADD CONSTRAINT `fk_b` "
            "FOREIGN KEY (`b`) REFERENCES `parents` (`id`)"
        )

    def test_unaddressable_kinds_and_ambiguous_projections_are_false(self, dialect):
        primary_key = TableConstraint(
            dialect, branch=TablePrimaryKeyConstraint(dialect, ["id"]), name="pk_events"
        )
        excluded = TableConstraint(
            dialect, branch=TableExcludeConstraint(dialect, ["a"]), name="ex_a"
        )
        cases = (
            TableConstraintChangeSuggestion(table_name="events", old_constraints=(primary_key,)),
            TableConstraintChangeSuggestion(table_name="events", new_constraints=(excluded,)),
            TableConstraintChangeSuggestion(
                table_name="events", new_constraints=(_freeze(primary_key),)
            ),
            TableConstraintChangeSuggestion(
                table_name="events",
                old_constraints=(_freeze(primary_key),),
                new_constraints=(primary_key,),
            ),
        )
        for point in cases:
            answer = dialect.suggest_table_constraint_change(point)
            _assert_frozen_answer(answer, point, "unaddressable")
            assert answer.operations is False

    def test_unchanged_point_is_absent(self, dialect):
        point = TableConstraintChangeSuggestion(table_name="events")
        answer = dialect.suggest_table_constraint_change(point)
        _assert_frozen_answer(answer, point, "absent")
        assert answer.operations is None


class TestTableIndexChange:
    def test_add_and_drop_chains_from_frozen_projections_render(self, dialect):
        old = IndexDefinition(dialect, "idx_old", ["a"])
        new = IndexDefinition(dialect, "idx_new", ["b"])
        point = TableIndexChangeSuggestion(
            table_name="events", old_indexes=(_freeze(old),), new_indexes=(_freeze(new),)
        )
        answer = dialect.suggest_table_index_change(point)
        _assert_frozen_answer(answer, point, "actions")
        assert [type(op) for op in answer.operations] == [
            DropIndexAction,
            AddIndexAction,
        ]
        assert _alter(dialect, answer.operations[0]) == (
            "ALTER TABLE `events` DROP INDEX `idx_old`"
        )
        assert _alter(dialect, answer.operations[1]) == (
            "ALTER TABLE `events` ADD INDEX `idx_new` (`b`)"
        )

    def test_redefined_index_is_drop_then_add(self, dialect):
        old = IndexDefinition(dialect, "idx", ["a"])
        new = IndexDefinition(dialect, "idx", ["b"])
        point = TableIndexChangeSuggestion(
            table_name="events", old_indexes=(_freeze(old),), new_indexes=(_freeze(new),)
        )
        answer = dialect.suggest_table_index_change(point)
        assert _alter(dialect, answer.operations[0]) == ("ALTER TABLE `events` DROP INDEX `idx`")
        assert _alter(dialect, answer.operations[1]) == (
            "ALTER TABLE `events` ADD INDEX `idx` (`b`)"
        )

    def test_live_index_instances_are_used_as_is(self, dialect):
        index = IndexDefinition(dialect, "idx", ["a"])
        point = TableIndexChangeSuggestion(table_name="events", new_indexes=(index,))
        answer = dialect.suggest_table_index_change(point)
        assert answer.operations[0].index is index
        assert _alter(dialect, answer.operations[0]) == (
            "ALTER TABLE `events` ADD INDEX `idx` (`a`)"
        )
        dropped = TableIndexChangeSuggestion(
            table_name="events", old_indexes=(Index(dialect, "idx"),)
        )
        answer = dialect.suggest_table_index_change(dropped)
        assert _alter(dialect, answer.operations[0]) == ("ALTER TABLE `events` DROP INDEX `idx`")

    def test_options_the_alter_path_cannot_spell_are_false(self, dialect):
        typed = _freeze(IndexDefinition(dialect, "idx", ["a"], type="HASH"))
        partial = _freeze(IndexDefinition(dialect, "idx", ["a"], if_not_exists=True))
        for point in (
            TableIndexChangeSuggestion(table_name="events", new_indexes=(typed,)),
            TableIndexChangeSuggestion(table_name="events", new_indexes=(partial,)),
        ):
            answer = dialect.suggest_table_index_change(point)
            _assert_frozen_answer(answer, point, "unaddressable")
            assert answer.operations is False

    def test_unchanged_point_is_absent(self, dialect):
        point = TableIndexChangeSuggestion(table_name="events")
        answer = dialect.suggest_table_index_change(point)
        _assert_frozen_answer(answer, point, "absent")
        assert answer.operations is None


class TestPartitionSchemeChange:
    def test_removing_partitioning_reuses_existing_suggestion(self, dialect):
        strategy = PartitionClause(dialect, "HASH", [Column(dialect, "id")])
        for old in (strategy, _freeze(strategy)):
            point = PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=old, new_partition=None
            )
            answer = dialect.suggest_partition_scheme_change(point)
            _assert_frozen_answer(answer, point, "actions")
            assert len(answer.operations) == 1
            assert isinstance(answer.operations[0], MySQLRemovePartitioningExpression)
            assert answer.operations[0].to_sql()[0] == ("ALTER TABLE `events` REMOVE PARTITIONING")

    def test_adding_or_changing_a_scheme_is_false(self, dialect):
        old = PartitionClause(dialect, "HASH", [Column(dialect, "id")])
        other = PartitionClause(dialect, "RANGE", [Column(dialect, "created_at")])
        for point in (
            PartitionSchemeChangeSuggestion(table_name="events", new_partition=_freeze(old)),
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=_freeze(old), new_partition=_freeze(other)
            ),
            PartitionSchemeChangeSuggestion(
                table_name="events", old_partition=(("not", "a", "clause"),)
            ),
        ):
            answer = dialect.suggest_partition_scheme_change(point)
            _assert_frozen_answer(answer, point, "unaddressable")
            assert answer.operations is False

    def test_unchanged_scheme_is_absent(self, dialect):
        strategy = PartitionClause(dialect, "HASH", [Column(dialect, "id")])
        point = PartitionSchemeChangeSuggestion(
            table_name="events", old_partition=strategy, new_partition=strategy
        )
        answer = dialect.suggest_partition_scheme_change(point)
        _assert_frozen_answer(answer, point, "absent")
        assert answer.operations is None

    def test_check_constraint_is_drop_addressable(self, dialect):
        """The per-kind probe distinguishes DROP CONSTRAINT (3940) from DROP CHECK (3821)."""
        check = TableConstraint(
            dialect,
            branch=TableCheckConstraint(
                dialect, ComparisonPredicate(dialect, ">", Column(dialect, "a"), 0)
            ),
            name="ck_a",
        )
        point = TableConstraintChangeSuggestion(
            table_name="events", old_constraints=(check,), new_constraints=()
        )
        answer = dialect.suggest_table_constraint_change(point)
        assert answer.operations is not False
        assert _alter(dialect, answer.operations[0]) == (
            "ALTER TABLE `events` DROP CONSTRAINT `ck_a`"
        )
