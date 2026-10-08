# tests/rhosocial/activerecord_mysql_test/feature/backend/test_expression_roundtrip_all.py
"""Serialization and rendering coverage for every expression class MySQL sees.

Two halves, and the second one used to be missing.

**Serialization.** Every class the matrix knows must round-trip losslessly
through the dict / JSON / XML channels.

**Rendering.** ``to_sql()`` has exactly four legal answers, and the matrix says
which one each class gives:

* it renders, and the rendered SQL is byte-identical after all three
  round-trips;
* it refuses with ``UnsupportedFeatureError`` -- the dialect does not have the
  feature;
* it refuses with ``NotImplementedError`` -- the class is an abstract base with
  no dialect contract of its own;
* it refuses with anything else, because the instance the harness built is not
  one the dialect will render.

The first three need no row: nothing is wrong with them. The fourth is a defect
or a harness limitation and each one is named in :data:`_NOT_RENDERED` with the
exception type it raises and a reason.

A missing formatter used to be spelled with that fourth answer. ``to_sql()``
raised ``AttributeError`` for a dialect that simply has no method of that name,
which is the one exception type the tree does not use for a capability gap, so
these 25 classes read as "silently wrong" when in fact the dialect was stating a
gap. Core now spells it ``UnsupportedFeatureError``, so they are no longer the
fourth answer at all and :data:`_DECLARED_GAP` records them where they belong:
a class that does not render, is accounted for, and is accounted for as a
*declared* gap rather than as an accident.

The previous version of this file had no third case.
``sql_consistent`` in the shared testsuite ends in
``except Exception: return``, so a class whose ``to_sql()`` blew up for an
uninteresting reason reported as a pass, and this file turned an unbuildable
class into ``pytest.skip``, which shares a green tick with "correctly
unsupported". Every one of those is now a named row in one of the tables below,
and all three tables are asserted exactly, in both directions: a new class
nobody listed is a failure, and so is a row left behind after the class started
working.

Discovery is ``collect_expression_classes``, never
``ExpressionRegistry._registry``. The registry is process-global and grows as
sibling modules import other backends, so three runs of this file measured
three different denominators.

Coverage spans two packages. ``backend.expression`` is core's own class
library, collected here as well as this backend's, because outside the single
hand-written predicate at the bottom of this file it had no matrix at all, and
a backend is the only place that knows what its own dialect does with those
classes.
"""

import collections.abc
import inspect
import typing

import pytest

from rhosocial.activerecord.testsuite.utils.expression import (
    collect_expression_classes,
    make_instance,
    register_all,
    register_special_constructor,
    roundtrip_expression,
    sql_consistent,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Table

MYSQL_EXPR_PKG = "rhosocial.activerecord.backend.impl.mysql.expression"
CORE_EXPR_PKG = "rhosocial.activerecord.backend.expression"

CLASSES = collect_expression_classes(MYSQL_EXPR_PKG)
CORE_CLASSES = collect_expression_classes(CORE_EXPR_PKG)
ALL_CLASSES = {**CORE_CLASSES, **CLASSES}
register_all(ALL_CLASSES)


def _table(d, name="t"):
    return Table(d, name)


# ---------------------------------------------------------------------------
# Dedicated constructors
# ---------------------------------------------------------------------------
#
# The generic constructor reads ``__init__``'s annotations and invents a value
# for each required parameter. It cannot build every shape, so the classes it
# cannot build get an explicit factory. The tables below say *which* reason
# applies, because the two reasons are not the same kind of thing:
#
# ``harness-defect``
#     The annotation is a parameterised generic -- ``partitions:
#     Sequence[str]`` -- and the harness reads the ``Sequence`` inside it as
#     the catalogue object ``Sequence``, so the constructor is handed an object
#     it cannot iterate and says ``'Sequence' object is not iterable``. That is
#     a defect in the harness, not in the expression: the parameter really is a
#     list of strings. Fixing it means changing
#     ``rhosocial-activerecord-testsuite``, which CI installs from that
#     repository's own branch, so it cannot be made from here.
#     ``test_constructor_tables_are_exact`` checks that these seven are exactly
#     the rows whose annotation is a parameterised Sequence, which is what will
#     say to delete them once the fix lands.
#
# ``misread-and-contract``
#     Reached by the same misreading, but the factory stays afterwards: once the
#     harness supplies a list the expression still refuses an empty one, so the
#     reason here is the non-empty requirement, not the misreading.
#
# ``expression-contract``
#     Nothing to do with the misreading -- the annotation is ``Any``, ``str``
#     or an enum. The expression needs something the generic constructor cannot
#     know: a DataType, a non-empty pair of values, an enum member, a positive
#     integer, a row source. These factories are permanent.
#
# All three tables are asserted against the registrations actually installed,
# and the first two are also asserted against each other's annotation shape, so
# a row cannot quietly change which kind of problem it describes.

_HARNESS_DEFECT_CONSTRUCTORS = {
    "partition.MySQLAnalyzePartitionExpression": "``partitions: Sequence[str]`` "
    "is read as the catalogue object Sequence, so the constructor gets "
    "'Sequence' object is not iterable.",
    "partition.MySQLCheckPartitionExpression": "``partitions: Sequence[str]`` "
    "is read as the catalogue object Sequence.",
    "partition.MySQLDropPartitionExpression": "``partitions: Sequence[str]`` "
    "is read as the catalogue object Sequence.",
    "partition.MySQLOptimizePartitionExpression": "``partitions: "
    "Sequence[str]`` is read as the catalogue object Sequence.",
    "partition.MySQLRebuildPartitionExpression": "``partitions: Sequence[str]`` "
    "is read as the catalogue object Sequence.",
    "partition.MySQLRepairPartitionExpression": "``partitions: Sequence[str]`` "
    "is read as the catalogue object Sequence.",
    "partition.MySQLTruncatePartitionExpression": "``partitions: "
    "Sequence[str]`` is read as the catalogue object Sequence.",
}

_MISREAD_AND_CONTRACT_CONSTRUCTORS = {
    "partition.MySQLPartitionByHash": "``keys: Sequence[BaseExpression]`` is "
    "read as the catalogue object Sequence, and keys must be non-empty "
    "afterwards.",
    "partition.MySQLPartitionByList": "``keys: Sequence[BaseExpression]`` is "
    "read as the catalogue object Sequence, and keys must be non-empty "
    "afterwards.",
    "partition.MySQLPartitionByListColumns": "``keys: "
    "Sequence[BaseExpression]`` is read as the catalogue object Sequence, and "
    "keys must be non-empty afterwards.",
    "partition.MySQLPartitionByRange": "``keys: Sequence[BaseExpression]`` is "
    "read as the catalogue object Sequence, and keys must be non-empty "
    "afterwards.",
    "partition.MySQLPartitionByRangeColumns": "``keys: "
    "Sequence[BaseExpression]`` is read as the catalogue object Sequence, and "
    "keys must be non-empty afterwards.",
    "partition.MySQLPartitionClause": "``keys: Sequence[BaseExpression]`` is "
    "read as the catalogue object Sequence, and method must additionally be a "
    "MySQLPartitionStrategy member or its string value.",
    "partition_lifecycle.MySQLAddPartitionHelper": "``partition_values: "
    "Sequence[...]`` is read as the catalogue object Sequence, and "
    "partition_values must be non-empty afterwards.",
    "partition_lifecycle.MySQLDropOldestPartitionHelper": "``partition_names: "
    "Sequence[str]`` is read as the catalogue object Sequence, and "
    "partition_names must be non-empty afterwards.",
    "partition.MySQLSubpartitionClause": "``subpartition_definitions: "
    "Sequence[...]`` is read as the catalogue object Sequence, and strategy "
    "must additionally be a MySQLSubpartitionStrategy member.",
}

_EXPRESSION_CONTRACT_CONSTRUCTORS = {
    "column.MySQLColumnDefinition": "data_type must be a DataType instance; the "
    "generic constructor supplies a string.",
    "dml.MySQLInsertExpression": "into and source are unannotated, so the "
    "generic constructor supplies a string for each and validate() refuses.",
    "json.MySQLJSONArrayExpression": "values and args are annotated Any with a "
    "None default, so the generic constructor supplies neither and the "
    "instance renders JSON_ARRAY().",
    "json.MySQLJSONContainsExpression": "path is optional, so an instance built "
    "from the two required strings renders JSON_CONTAINS(x, %s) with no JSON "
    "path; the factory supplies one.",
    "json.MySQLJSONExtractExpression": "both required parameters are annotated "
    "str, so the generic constructor turns the JSON path into the value "
    "placeholder; the factory separates them.",
    "json.MySQLJSONObjectExpression": "data is Any with a None default, so the "
    "generic constructor produces JSON_OBJECT() with no members.",
    "match_against.MySQLMatchAgainstExpression": "columns is a List[str], so the "
    "generic constructor supplies an empty list and the instance renders "
    "MATCH() AGAINST(...), which MySQL will not parse.",
    "partition.MySQLCoalescePartitionExpression": "count must be a positive "
    "integer; the generic constructor supplies \"x\".",
    "spatial.MySQLSTDistanceExpression": "the two geometries are annotated str, "
    "so the generic constructor renders ST_Distance(x, x) with the placeholder "
    "identifier in both positions.",
    "types.MySQLEnumType": "values must be a non-empty list of labels.",
    "types.MySQLSetType": "values must be a non-empty list of labels.",
    "types.MySQLVectorType": "dim must be a positive integer.",
}

#: Every class with a dedicated constructor, in one mapping, so
#: ``test_constructor_tables_are_exact`` has one thing to compare against.
DEDICATED_CONSTRUCTORS = {
    **_HARNESS_DEFECT_CONSTRUCTORS,
    **_MISREAD_AND_CONTRACT_CONSTRUCTORS,
    **_EXPRESSION_CONTRACT_CONSTRUCTORS,
}


def _register_mysql_specials():
    """Install one dedicated constructor per row of the two tables above."""
    from rhosocial.activerecord.backend.expression.core import Column, Literal
    from rhosocial.activerecord.backend.expression.statements.dml import ValuesSource
    from rhosocial.activerecord.backend.expression.types import IntegerType
    from rhosocial.activerecord.backend.impl.mysql.expression.column import (
        MySQLColumnDefinition,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.dml import (
        MySQLInsertExpression,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.json import (
        MySQLJSONArrayExpression,
        MySQLJSONContainsExpression,
        MySQLJSONExtractExpression,
        MySQLJSONObjectExpression,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.match_against import (
        MySQLMatchAgainstExpression,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.partition import (
        MySQLCoalescePartitionExpression,
        MySQLPartitionByHash,
        MySQLPartitionByList,
        MySQLPartitionByListColumns,
        MySQLPartitionByRange,
        MySQLPartitionByRangeColumns,
        MySQLPartitionClause,
        MySQLSubpartitionClause,
        MySQLSubpartitionStrategy,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.partition_lifecycle import (
        MySQLAddPartitionHelper,
        MySQLDropOldestPartitionHelper,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.spatial import (
        MySQLSTDistanceExpression,
    )
    from rhosocial.activerecord.backend.impl.mysql.expression.types import (
        MySQLEnumType,
        MySQLSetType,
        MySQLVectorType,
    )

    def partition_maintenance(d, cls_name):
        import rhosocial.activerecord.backend.impl.mysql.expression.partition as mod

        return getattr(mod, cls_name)(d, table=Table(d, "t"), partitions=["p0"])

    factories = {
        "match_against.MySQLMatchAgainstExpression":
            lambda d: MySQLMatchAgainstExpression(d, columns=["title"], search_string="x"),
        "json.MySQLJSONObjectExpression":
            lambda d: MySQLJSONObjectExpression(d, {"a": 1}),
        "json.MySQLJSONArrayExpression":
            lambda d: MySQLJSONArrayExpression(d, 1, 2, alias="arr"),
        "json.MySQLJSONExtractExpression":
            lambda d: MySQLJSONExtractExpression(d, "data", "$.a", alias="n"),
        "json.MySQLJSONContainsExpression":
            lambda d: MySQLJSONContainsExpression(d, "data", "x", "$.a"),
        "spatial.MySQLSTDistanceExpression":
            lambda d: MySQLSTDistanceExpression(d, "g1", "g2"),
        "partition.MySQLPartitionClause":
            lambda d: MySQLPartitionClause(d, "RANGE", [Column(d, "id")]),
        "partition.MySQLPartitionByRange":
            lambda d: MySQLPartitionByRange(d, [Column(d, "id")]),
        "partition.MySQLPartitionByRangeColumns":
            lambda d: MySQLPartitionByRangeColumns(d, [Column(d, "a"), Column(d, "b")]),
        "partition.MySQLPartitionByList":
            lambda d: MySQLPartitionByList(d, [Column(d, "id")]),
        "partition.MySQLPartitionByListColumns":
            lambda d: MySQLPartitionByListColumns(d, [Column(d, "a"), Column(d, "b")]),
        "partition.MySQLPartitionByHash":
            lambda d: MySQLPartitionByHash(d, [Column(d, "id")], partitions_count=4),
        "partition.MySQLSubpartitionClause":
            lambda d: MySQLSubpartitionClause(d, MySQLSubpartitionStrategy.HASH, count=4),
        "partition.MySQLCoalescePartitionExpression":
            lambda d: MySQLCoalescePartitionExpression(d, table=Table(d, "t"), count=2),
        "column.MySQLColumnDefinition":
            lambda d: MySQLColumnDefinition(d, "id", IntegerType(d)),
        "dml.MySQLInsertExpression":
            lambda d: MySQLInsertExpression(
                d, into=Table(d, "t"), source=ValuesSource(d, [[Literal(d, 1)]])
            ),
        "types.MySQLEnumType": lambda d: MySQLEnumType(d, values=["a", "b"]),
        "types.MySQLSetType": lambda d: MySQLSetType(d, values=["a", "b"]),
        "types.MySQLVectorType": lambda d: MySQLVectorType(d, dim=3),
        "partition_lifecycle.MySQLAddPartitionHelper":
            lambda d: MySQLAddPartitionHelper(
                d, table=Table(d, "t"), partition_values=[1]
            ),
        "partition_lifecycle.MySQLDropOldestPartitionHelper":
            lambda d: MySQLDropOldestPartitionHelper(
                d, table=Table(d, "t"), partition_names=["p0"]
            ),
    }
    for _name in (
        "MySQLAnalyzePartitionExpression",
        "MySQLCheckPartitionExpression",
        "MySQLDropPartitionExpression",
        "MySQLOptimizePartitionExpression",
        "MySQLRebuildPartitionExpression",
        "MySQLRepairPartitionExpression",
        "MySQLTruncatePartitionExpression",
    ):
        factories[f"partition.{_name}"] = (
            lambda d, _n=_name: partition_maintenance(d, _n)
        )

    assert set(factories) == set(DEDICATED_CONSTRUCTORS), (
        "the factory table and the reason table disagree; each factory is "
        "written out in full and each reason is written out in full, and this "
        f"is what keeps them aligned. missing={sorted(set(factories) - set(DEDICATED_CONSTRUCTORS))} "
        f"extra={sorted(set(DEDICATED_CONSTRUCTORS) - set(factories))}"
    )
    for _tail, _factory in factories.items():
        register_special_constructor(_tail, _factory)


_register_mysql_specials()


# ---------------------------------------------------------------------------
# Exemption tables
# ---------------------------------------------------------------------------

# Classes the generic constructor cannot build, so there is no instance to
# assert on. Keyed by fqn suffix; the value is why.
#
# The six ddl_alter rows are the generic constructor skipping a defaulted
# positional parameter, which shifts every later positional argument.
#
# This table used to hold four XML rows as well, for the ``Sequence[X]``
# misreading the constructor tables above document. Those are gone because
# testsuite fixed it: a parameterised alias now yields an empty container before
# the relation-name test runs, so the constructor gets ``[]`` and builds the
# class. The rows named a gap that no longer exists, and retiring them is what
# the exactness test below demands. The four are not lost -- they are XML
# functions this dialect has no formatter for, so they moved to
# :data:`_DECLARED_GAP`, which is where a class that constructs but does not
# render belongs.
_UNBUILDABLE = {
    "statements.ddl_alter.AlterConstraint":
        "constraint_name defaults to None and the constructor rejects it, so "
        "the generic placeholder is never reached.",
    "statements.ddl_alter.AlterConstraintAction":
        "same shape as AlterConstraint: an abstract constraint action with no "
        "constructible default.",
    "statements.ddl_alter.AlterTableConstraint":
        "same shape as AlterConstraint.",
    "statements.ddl_alter.ValidateConstraint":
        "constraint_name defaults to None and the constructor rejects it.",
    "statements.ddl_alter.ValidateConstraintAction":
        "same shape as ValidateConstraint.",
    "statements.ddl_alter.ValidateTableConstraint":
        "same shape as ValidateConstraint.",
    "statements.ddl_domain.AddDomainCheckAction":
        "check must be a DomainCheckConstraint instance; the generic "
        "constructor supplies a string.",
    "types.enum_.EnumType":
        "values defaults to None and EnumType requires a non-empty list.",
}

# Classes that build, whose ``to_sql()`` refuses because MySQL's base list names
# no formatter for them. Keyed by fqn suffix; the value is
# ``(formatter name, reason)``. The formatter name is the load-bearing half and
# is asserted against the class's own ``format_method``, so a row cannot quietly
# start describing a different gap.
#
# These 25 used to sit in ``_NOT_RENDERED`` as ``AttributeError``, which said
# "the dialect's base list is missing a name" through the one exception type the
# tree does not use for capability gaps. Core's ``to_sql`` now spells that same
# fact as ``UnsupportedFeatureError``, the way every other gap in the tree is
# spelled, so they are a third kind of row rather than a second one. Deleting
# them would lose the accounting -- "this class does not render" would stop being
# written down -- so they are re-classified, and
# ``test_declared_gap_table_is_exact`` asserts the new table exactly, in both
# directions, the same way ``test_not_rendered_table_is_exact`` asserts the other.
#
# Two of the three reasons below are not "MySQL lacks the feature" but "MySQL
# claims the feature and then has nothing to render it with", which is a defect
# in the source rather than a gap in coverage, so they are called out as their
# own kind rather than filed with the SQL-standard features MySQL genuinely does
# not have.
_DECLARED_GAP = {
    # --- MySQL claims support and has no renderer for it. -----------------
    # Each of these has a ``supports_*`` method answering True while the
    # formatter the expression dispatches to does not exist, so a caller that
    # asks whether the feature is available is told yes and is then refused.
    "statements.ddl_schema.CreateSchemaExpression": (
        "format_create_schema_statement",
        "DECLARED BUT NOT RENDERED. MySQLSchemaMixin.supports_create_schema() "
        "answers True -- MySQL takes SCHEMA as a synonym for DATABASE -- yet "
        "MySQLDialect defines no format_create_schema_statement. The dialect "
        "claims the capability and refuses the statement.",
    ),
    "statements.ddl_schema.DropSchemaExpression": (
        "format_drop_schema_statement",
        "DECLARED BUT NOT RENDERED. Same shape as CreateSchemaExpression: "
        "MySQLSchemaMixin.supports_drop_schema() answers True and "
        "format_drop_schema_statement is absent.",
    ),
    "table_expr.MySQLInlineIndexExpression": (
        "format_inline_index",
        "DECLARED BUT NOT RENDERED. MySQLDDLTableMixin."
        "supports_inline_index() answers True, and the expression dispatches "
        "to format_inline_index, which MySQLDialect does not define. CREATE "
        "TABLE renders its inline indexes through format_index_definition, so "
        "the class is unreachable from any rendering path in this backend -- "
        "nothing in src or tests constructs it.",
    ),
    # --- SQL/PGQ: property graphs are not a MySQL feature. ----------------
    "graph.AlterPropertyGraphExpression": (
        "format_alter_property_graph_statement",
        "SQL/PGQ: MySQL has no property graphs, so no "
        "format_alter_property_graph_statement exists.",
    ),
    "graph.ColumnsClause": (
        "format_graph_columns_clause",
        "SQL/PGQ graph column list; no format_graph_columns_clause.",
    ),
    "graph.CreatePropertyGraphExpression": (
        "format_create_property_graph_statement",
        "SQL/PGQ: no format_create_property_graph_statement.",
    ),
    "graph.DropPropertyGraphExpression": (
        "format_drop_property_graph_statement",
        "SQL/PGQ: no format_drop_property_graph_statement.",
    ),
    "graph.EdgeTable": (
        "format_edge_table",
        "SQL/PGQ edge table; no format_edge_table.",
    ),
    "graph.GraphTableExpression": (
        "format_graph_table_expression",
        "SQL/PGQ: no format_graph_table_expression.",
    ),
    "graph.TablePropertiesClause": (
        "format_table_properties_clause",
        "SQL/PGQ table properties; no format_table_properties_clause.",
    ),
    "graph.VertexTable": (
        "format_vertex_table",
        "SQL/PGQ vertex table; no format_vertex_table.",
    ),
    # --- PIVOT / UNPIVOT are T-SQL and Oracle, not MySQL. -----------------
    "pivot.PivotExpression": (
        "format_pivot_expression",
        "PIVOT is T-SQL/Oracle; MySQL spells it as GROUP BY with conditional "
        "aggregates and declares no formatter.",
    ),
    "pivot.UnpivotExpression": (
        "format_unpivot_expression",
        "UNPIVOT is T-SQL/Oracle; MySQL declares no formatter.",
    ),
    # --- Case-insensitive matching is written LOWER() = LOWER() here. -----
    "predicates.ILIKEExpression": (
        "format_ilike_expression",
        "MySQL has no ILIKE operator; case-insensitive matching is written "
        "LOWER(a) = LOWER(b), and no formatter exists.",
    ),
    # --- The abstract row-source base names a contract nothing implements. --
    "sources.base.TableSource": (
        "format_table_source",
        "The base row-source class names format_table_source as its contract; "
        "MySQL reads named tables through NamedRelationRef and mixes in no "
        "base that implements it.",
    ),
    # --- COMMENT ON is SQL-standard/PostgreSQL. ---------------------------
    "statements.ddl_comment.CommentOnExpression": (
        "format_comment_statement",
        "COMMENT ON is SQL-standard/PostgreSQL. MySQL spells a table comment "
        "as a CREATE TABLE option and a column comment inline, which "
        "format_column_definition already renders.",
    ),
    # --- SEQUENCE is not a MySQL object. -----------------------------------
    # These three rendered before this branch dropped SequenceMixin from the
    # base list, and what they rendered was the defect: MySQL has no sequence
    # object -- it numbers rows with AUTO_INCREMENT columns -- while the
    # inherited formatters never consult supports_sequence() and only checked
    # the option-level probes, which also answer False. So
    # ``CREATE SEQUENCE `s` NO CYCLE`` came back out of a dialect whose own
    # supports_sequence() said the feature was absent. They now refuse through
    # the dispatch, which is the same declared gap as the property-graph rows
    # above and stated for the same reason. Naming a sequence is untouched:
    # SequenceNameMixin stays, so Sequence(dialect, "s").to_sql() renders.
    "statements.ddl_sequence.CreateSequenceExpression": (
        "format_create_sequence_statement",
        "MySQL has no sequence object; AUTO_INCREMENT columns are how rows are "
        "numbered. MySQLDialect mixes in no base providing this formatter.",
    ),
    "statements.ddl_sequence.DropSequenceExpression": (
        "format_drop_sequence_statement",
        "MySQL has no sequence object; no format_drop_sequence_statement.",
    ),
    "statements.ddl_sequence.AlterSequenceExpression": (
        "format_alter_sequence_statement",
        "MySQL has no sequence object; no format_alter_sequence_statement.",
    ),
    # --- XML functions are not in MySQL. -----------------------------------
    "xml.XMLAggExpression": (
        "format_xmlagg_expression",
        "XML functions are not in MySQL; no format_xmlagg_expression.",
    ),
    # The four that used to be pinned in _UNBUILDABLE, because the harness read
    # their ``Sequence[X]`` parameter as the catalogue object Sequence and could
    # not construct them at all. testsuite fixed that, so they construct now, and
    # the gap they have is the ordinary one: XML is not in MySQL and no formatter
    # exists. They were unreachable from the matrix before and are accounted for
    # here now, which is the outcome the _UNBUILDABLE rows asked for.
    "xml.XMLAttributesExpression": (
        "format_xmlattributes_expression",
        "XML functions are not in MySQL; no format_xmlattributes_expression. "
        "This row was in _UNBUILDABLE until testsuite stopped reading "
        "attributes: Sequence[XMLAttribute] as the catalogue object Sequence.",
    ),
    "xml.XMLConcatExpression": (
        "format_xmlconcat_expression",
        "XML functions are not in MySQL; no format_xmlconcat_expression. This "
        "row was in _UNBUILDABLE until testsuite stopped reading parts: "
        "Sequence[BaseExpression] as the catalogue object Sequence.",
    ),
    "xml.XMLForestExpression": (
        "format_xmlforest_expression",
        "XML functions are not in MySQL; no format_xmlforest_expression. This "
        "row was in _UNBUILDABLE until testsuite stopped reading items: "
        "Sequence[XMLForestItem] as the catalogue object Sequence.",
    ),
    "xml.XMLTableExpression": (
        "format_xmltable_expression",
        "XML functions are not in MySQL; no format_xmltable_expression. This "
        "row was in _UNBUILDABLE until testsuite stopped reading columns: "
        "Sequence[XMLTableColumn] as the catalogue object Sequence.",
    ),
    "xml.XMLCommentExpression": (
        "format_xmlcomment_expression",
        "XML functions are not in MySQL; no format_xmlcomment_expression.",
    ),
    "xml.XMLElementExpression": (
        "format_xmlelement_expression",
        "XML functions are not in MySQL; no format_xmlelement_expression.",
    ),
    "xml.XMLExistsExpression": (
        "format_xmlexists_expression",
        "XML functions are not in MySQL; no format_xmlexists_expression.",
    ),
    "xml.XMLPIExpression": (
        "format_xmlpi_expression",
        "XML functions are not in MySQL; no format_xmlpi_expression.",
    ),
    "xml.XMLParseExpression": (
        "format_xmlparse_expression",
        "XML functions are not in MySQL; no format_xmlparse_expression.",
    ),
    "xml.XMLQueryExpression": (
        "format_xmlquery_expression",
        "XML functions are not in MySQL; no format_xmlquery_expression.",
    ),
    "xml.XMLRootExpression": (
        "format_xmlroot_expression",
        "XML functions are not in MySQL; no format_xmlroot_expression.",
    ),
    "xml.XMLSerializeExpression": (
        "format_xmlserialize_expression",
        "XML functions are not in MySQL; no format_xmlserialize_expression.",
    ),
}

# Classes that build but whose ``to_sql()`` raises something outside the legal
# answers -- neither the two refusals nor a rendered (sql, params) pair. Keyed by
# fqn suffix; the value is ``(exception type name, reason)``. The type is
# asserted, so a row cannot quietly change what it raises.
#
# None of these is a missing formatter any more: a missing formatter raises
# ``UnsupportedFeatureError``, and the 25 that used to be listed here for that
# reason now have their own table above. What is left is the dialect refusing
# the *instance* the generic constructor happened to build, and that is the
# interesting half -- every row below is a refusal that is the right answer to
# a wrong value.
_NOT_RENDERED = {
    # --- A MySQL formatter shadows the core one and reads other slots. ----
    "statements.ddl_function.CreateFunctionExpression": (
        "AttributeError",
        "MySQLRoutineMixin.format_create_function_statement reads expr.name; "
        "core's CreateFunctionExpression carries expr.function, so the MySQL "
        "routine formatter shadows the core one for an expression it cannot "
        "render.",
    ),
    "statements.ddl_function.DropFunctionExpression": (
        "AttributeError",
        "Same shadowing as CreateFunctionExpression.",
    ),
    "query_sources.JSONTableExpression": (
        "AttributeError",
        "MySQLJSONFunctionMixin.format_json_table_expression reads json_doc / "
        "path / columns; core's JSONTableExpression exposes a different "
        "shape, so the MySQL formatter cannot read it.",
    ),
    # --- The dialect correctly refuses what the harness invented. ---------
    "collation.CollateExpression": (
        "ValueError",
        "The generic constructor supplies \"x\" for collation_name and MySQL's "
        "validate_collation_name refuses a collation it does not know. The "
        "refusal is the right answer to a wrong value.",
    ),
    "routine.MySQLCallExpression": (
        "TypeError",
        "name must be a Procedure or Function object; the generic constructor "
        "supplies a string. Refusing is the object-kind guard working.",
    ),
    "routine.MySQLCreateFunctionExpression": (
        "TypeError",
        "name must be a routine object; the generic constructor supplies a "
        "string.",
    ),
    "routine.MySQLCreateProcedureExpression": (
        "TypeError",
        "name must be a routine object; the generic constructor supplies a "
        "string.",
    ),
    "routine.MySQLDropFunctionExpression": (
        "TypeError",
        "name must be a routine object; the generic constructor supplies a "
        "string.",
    ),
    "routine.MySQLDropProcedureExpression": (
        "TypeError",
        "name must be a routine object; the generic constructor supplies a "
        "string.",
    ),
    "types._base.DataType": (
        "TypeError",
        "Abstract base whose name is None, so format_data_type cannot "
        "dispatch. No dialect implements a base without a concrete name.",
    ),
    "types.array.ArrayType": (
        "TypeError",
        "MySQL has no array type, so there is no format_data_type_array.",
    ),
    "types.binary.BinaryType": (
        "TypeError",
        "MySQL spells fixed-width binary data VARBINARY/BLOB; there is no "
        "format_data_type_binary.",
    ),
    "types.binary.VarBinaryType": (
        "TypeError",
        "MySQL spells fixed-width binary data VARBINARY/BLOB; there is no "
        "format_data_type_varbinary.",
    ),
    "types.datetime_.IntervalType": (
        "TypeError",
        "MySQL spells intervals with INTERVAL n unit inside a date expression, "
        "not as a column type; no format_data_type_interval.",
    ),
    "types.uuid_.UUIDType": (
        "TypeError",
        "MySQL 8.0 stores a UUID as CHAR(36) or BINARY(16); no "
        "format_data_type_uuid.",
    ),
    # --- The instance the generic constructor builds is not a valid one. ---
    "advanced_functions.CaseExpression": (
        "ValueError",
        "CASE needs at least one WHEN/THEN pair; the generic constructor "
        "supplies an empty list.",
    ),
    "advanced_functions.WindowClause": (
        "ValueError",
        "A window clause needs at least one window definition; the generic "
        "constructor supplies an empty list.",
    ),
    "advanced_functions.WindowDefinition": (
        "AttributeError",
        "base / partition_by / order_by must be expressions; the generic "
        "constructor supplies strings.",
    ),
    "advanced_functions.WindowSpecification": (
        "ValueError",
        "A window specification needs at least one of PARTITION BY / ORDER BY "
        "/ FRAME; the generic constructor supplies none.",
    ),
    "admin.MySQLFlushExpression": (
        "ValueError",
        "FLUSH needs at least one option; the generic constructor supplies an "
        "empty list.",
    ),
    "admin.MySQLHandlerCloseExpression": (
        "TypeError",
        "table must be a Table object; the generic constructor supplies a "
        "string, and the dialect's object-kind guard refuses it.",
    ),
    "admin.MySQLHandlerOpenExpression": (
        "TypeError",
        "table must be a Table object; the generic constructor supplies a "
        "string, and the dialect's object-kind guard refuses it.",
    ),
    "admin.MySQLHandlerReadExpression": (
        "TypeError",
        "table must be a Table object; the generic constructor supplies a "
        "string, and the dialect's object-kind guard refuses it.",
    ),
    "admin.MySQLResetExpression": (
        "AttributeError",
        "option must be a ResetOption member; the generic constructor supplies "
        "a string.",
    ),
    "alter_column.MySQLAddColumn": (
        "AttributeError",
        "column must be a ColumnDefinition; the generic constructor supplies a "
        "string.",
    ),
    "datetime.TemporalOptionsExpression": (
        "ValueError",
        "Temporal options cannot be empty, and the generic constructor cannot "
        "know which one to pick.",
    ),
    "json_duality_view.CreateJsonDualityViewExpression": (
        "AttributeError",
        "The JSON duality view takes duality object specs; the generic "
        "constructor supplies strings.",
    ),
    "json_duality_view.MySQLDualityObjectBodyExpression": (
        "AttributeError",
        "Built without the tags / columns mapping its formatter reads.",
    ),
    "json_duality_view.MySQLDualityObjectSelectExpression": (
        "AttributeError",
        "Built without the from_table / from_alias its formatter reads.",
    ),
    "json_duality_view.MySQLNestedDualityExpression": (
        "AttributeError",
        "subquery must be a duality object select spec; the generic "
        "constructor supplies a string.",
    ),
    "maintenance.MySQLAnalyzeTableExpression": (
        "ValueError",
        "ANALYZE TABLE needs at least one table; the generic constructor "
        "supplies an empty list.",
    ),
    "maintenance.MySQLCheckTableExpression": (
        "ValueError",
        "CHECK TABLE needs at least one table; the generic constructor supplies "
        "an empty list.",
    ),
    "maintenance.MySQLChecksumTableExpression": (
        "ValueError",
        "CHECKSUM TABLE needs at least one table; the generic constructor "
        "supplies an empty list.",
    ),
    "maintenance.MySQLOptimizeTableExpression": (
        "ValueError",
        "OPTIMIZE TABLE needs at least one table; the generic constructor "
        "supplies an empty list.",
    ),
    "maintenance.MySQLRepairTableExpression": (
        "ValueError",
        "REPAIR TABLE needs at least one table; the generic constructor "
        "supplies an empty list.",
    ),
    "maintenance.MySQLTableMaintenanceExpression": (
        "ValueError",
        "A whole-table maintenance statement needs at least one table; the "
        "generic constructor supplies an empty list.",
    ),
    "optimizer_hint.MySQLOptimizerHintExpression": (
        "AttributeError",
        "hints must be objects carrying variable / value; the generic "
        "constructor supplies strings.",
    ),
    "partition.MySQLAddPartitionExpression": (
        "AttributeError",
        "partitions must be partition definitions; the generic constructor "
        "supplies strings.",
    ),
    "partition.MySQLReorganizePartitionExpression": (
        "AttributeError",
        "into must be partition definitions; the generic constructor supplies "
        "strings.",
    ),
    "partition_lifecycle.MySQLAddSubpartitionHelper": (
        "ValueError",
        "A partition definition needs less_than or in_values; the generic "
        "constructor supplies neither.",
    ),
    "partition_lifecycle.MySQLCoalescePartitionHelper": (
        "ValueError",
        "target_count must be below current_count; the generic constructor "
        "supplies 1 for both.",
    ),
    "rename_table.MySQLRenameTableExpression": (
        "ValueError",
        "renames must be a non-empty list of (old, new) Table pairs; the "
        "generic constructor supplies an empty list.",
    ),
    "statements.ddl_alter.AddColumn": (
        "AttributeError",
        "column must be a ColumnDefinition; the generic constructor supplies a "
        "string.",
    ),
    "statements.ddl_alter.AddTableConstraint": (
        "AttributeError",
        "constraint must be a TableConstraint; the generic constructor supplies "
        "a string.",
    ),
    "statements.ddl_alter.ChangeColumn": (
        "AttributeError",
        "column must be a ColumnDefinition; the generic constructor supplies a "
        "string.",
    ),
    "statements.ddl_alter.ModifyColumn": (
        "AttributeError",
        "column must be a ColumnDefinition; the generic constructor supplies a "
        "string.",
    ),
    "statements.ddl_trigger.CreateTriggerExpression": (
        "AttributeError",
        "timing must be a TriggerTiming member; the generic constructor "
        "supplies a string.",
    ),
    "statements.ddl_table.ColumnConstraint": (
        "ValueError",
        "constraint_type must be a ColumnConstraintType member or its string "
        "value; the generic constructor supplies \"x\".",
    ),
    "statements.ddl_table.ReferencesClause": (
        "ValueError",
        "REFERENCES needs at least one referenced column; the generic "
        "constructor supplies an empty list.",
    ),
    "statements.dml.MergeAction": (
        "TypeError",
        "core's format_merge_action joins a None part when the action is "
        "unset, and the generic constructor supplies None. MySQL declares no "
        "MERGE at all -- upsert is ON DUPLICATE KEY UPDATE -- so this row is "
        "core's shape rather than MySQL's.",
    ),
    "statements.dml.MergeExpression": (
        "AttributeError",
        "source must be a row source; the generic constructor supplies a "
        "string. MySQL has no MERGE.",
    ),
    "table_expr.MySQLStorageOptionsExpression": (
        "AttributeError",
        "Built without the options mapping its formatter reads.",
    ),
    "table_statement.MySQLValuesExpression": (
        "ValueError",
        "VALUES needs at least one ROW(...); the generic constructor supplies "
        "an empty list.",
    ),
}


def _suffix(fqn):
    """The fqn suffix the exemption tables are keyed by."""
    for pkg in (MYSQL_EXPR_PKG, CORE_EXPR_PKG):
        if fqn.startswith(pkg + "."):
            return fqn[len(pkg) + 1:]
    raise AssertionError(f"unexpected class origin: {fqn}")


_SUFFIXES = {_suffix(fqn): fqn for fqn in ALL_CLASSES}
assert len(_SUFFIXES) == len(ALL_CLASSES), (
    "two collected classes share an fqn suffix, so the exemption tables could "
    "not tell them apart"
)


def _uses_parameterised_sequence(cls):
    """Whether ``__init__`` declares a parameterised ``Sequence[...]``.

    The harness's defect is exactly this shape: it reads the ``Sequence`` of a
    subscripted generic as the catalogue object. Detecting it is what lets the
    rows that depend on it be told apart from rows that do not.
    """
    for param in inspect.signature(cls.__init__).parameters.values():
        annotation = param.annotation
        if isinstance(annotation, str):
            # PEP 563 stores the annotation unevaluated. A subscript is the
            # tell that survives without importing the module's globals.
            if "[" in annotation and "Sequence" in annotation:
                return True
            continue
        if typing.get_origin(annotation) is collections.abc.Sequence:
            if getattr(annotation, "__args__", ()):
                return True
    return False


# ---------------------------------------------------------------------------
# The matrix
# ---------------------------------------------------------------------------


#: The classes the matrix actually parametrizes over: everything collected
#: except the ones pinned in ``_UNBUILDABLE``. Those get no case at all rather
#: than a skipped one, because a skip here is indistinguishable from "the
#: dialect correctly refuses this" and that is the confusion this file exists to
#: remove. ``test_unbuildable_table_is_exact`` proves the exclusion is exactly
#: the set that cannot be built.
_MATRIX_FQNS = sorted(
    (fqn for fqn in ALL_CLASSES if _suffix(fqn) not in _UNBUILDABLE), key=_suffix
)

#: The same set as :data:`_MATRIX_FQNS`, by suffix, which is how every table in
#: this file is keyed.
_MATRIX_IDS = {_suffix(fqn) for fqn in _MATRIX_FQNS}


@pytest.fixture(params=_MATRIX_FQNS, ids=[_suffix(f) for f in _MATRIX_FQNS])
def expr_case(request, mysql_dialect):
    """One collected class, built against the MySQL dialect."""
    fqn = request.param
    instance, _source = make_instance(ALL_CLASSES[fqn], mysql_dialect)
    assert instance is not None, (
        f"{_suffix(fqn)} cannot be constructed by the generic constructor and "
        f"is not listed in _UNBUILDABLE; either give it a dedicated "
        f"constructor or pin it there with a reason"
    )
    return _suffix(fqn), instance


class TestExpressionSerialization:
    """Every class the matrix knows survives all three encoding channels."""

    def test_get_params_roundtrip(self, expr_case, mysql_dialect):
        suffix, instance = expr_case
        roundtrip_expression(suffix, instance, mysql_dialect)


class TestExpressionRendering:
    """``to_sql()`` has four legal answers and the matrix says which."""

    def test_to_sql_is_classified(self, expr_case, mysql_dialect):
        suffix, instance = expr_case
        try:
            rendered = instance.to_sql()
        except UnsupportedFeatureError:
            # Refused because the dialect lacks the feature. Expected, and the
            # exception type is the assertion.
            #
            # Not every refusal of this kind is written down, and that is the
            # point of the split. Most are a formatter calling a `supports_*`
            # probe that declines, which is the dialect answering "no" to the
            # feature it was asked to render. Only the refusals that come from
            # the *dispatch* -- the base list naming no formatter at all -- are a
            # wiring fact about this backend, and those are in _DECLARED_GAP.
            # A class there is checked in test_declared_gap_table_is_exact.
            return
        except NotImplementedError:
            # An abstract base with no dialect contract of its own.
            return
        except Exception as exc:
            row = _NOT_RENDERED.get(suffix)
            assert row is not None, (
                f"{suffix}: to_sql() raised {type(exc).__name__}, which is neither "
                f"UnsupportedFeatureError nor NotImplementedError and is not listed "
                f"in _NOT_RENDERED: {exc}"
            )
            assert type(exc).__name__ == row[0], (
                f"{suffix}: _NOT_RENDERED says {row[0]} but it raised "
                f"{type(exc).__name__}: {exc}"
            )
            return
        # It rendered, so the SQL must be byte-identical after all three
        # round-trips. This is the assertion the shared `except Exception:
        # return` made unreachable.
        assert isinstance(rendered, tuple) and len(rendered) == 2, (
            f"{suffix}: to_sql() returned {rendered!r}, expected a (sql, params) tuple"
        )
        sql_consistent(suffix, instance, mysql_dialect)


# ---------------------------------------------------------------------------
# The tables are constraints, not documentation
# ---------------------------------------------------------------------------


def _verdicts(mysql_dialect):
    """What every collected class actually does when asked to render.

    Four buckets, and the split between the two refusals is the one the tables
    care about. ``UnsupportedFeatureError`` reaches ``to_sql`` by two different
    routes and they mean different things:

    ``no_formatter``
        The dispatch itself found nothing. ``getattr(dialect, format_method)``
        is absent, so ``to_sql()`` never called anything. This is a fact about
        this backend's base list and it is what :data:`_DECLARED_GAP` records.

    ``probe``
        A formatter *was* found and it called a ``supports_*`` method that
        raised. The dialect answered "I do not have this feature", which is the
        ordinary capability gap and needs no row.

    Telling them apart by re-doing the lookup is the only honest way, because
    ``to_sql()`` raises the same type for both and the exception message does not
    say which happened. Getting this wrong would put 37 classes in a table that
    is about wiring, so it is done against the live dialect rather than by
    matching on strings.
    """
    out = {
        "renders": set(),
        "abstract": set(),
        "no_formatter": {},
        "probe": set(),
        "other": {},
    }
    # Iterates the matrix, not ALL_CLASSES: a class in _UNBUILDABLE is not this
    # table's business, and whether _UNBUILDABLE itself is still exact is
    # test_unbuildable_table_is_exact's claim to make. Walking ALL_CLASSES here
    # would report an unbuildable class as a missing row in both tables, which
    # says nothing true about either.
    for fqn in _MATRIX_FQNS:
        instance, _source = make_instance(ALL_CLASSES[fqn], mysql_dialect)
        if instance is None:
            continue
        suffix = _suffix(fqn)
        try:
            instance.to_sql()
            out["renders"].add(suffix)
            continue
        except NotImplementedError:
            out["abstract"].add(suffix)
            continue
        except UnsupportedFeatureError:
            pass
        except Exception as exc:
            out["other"][suffix] = type(exc).__name__
            continue

        # It refused with UnsupportedFeatureError. Which route?
        formatter = getattr(mysql_dialect, instance.format_method, None)
        if formatter is None or not callable(formatter):
            out["no_formatter"][suffix] = instance.format_method
        else:
            out["probe"].add(suffix)
    return out


def test_unbuildable_table_is_exact(mysql_dialect):
    """_UNBUILDABLE lists every unbuildable class, and nothing else."""
    observed = {
        _suffix(fqn)
        for fqn, cls in ALL_CLASSES.items()
        if make_instance(cls, mysql_dialect)[0] is None
    }
    missing = sorted(observed - set(_UNBUILDABLE))
    stale = sorted(set(_UNBUILDABLE) - observed)
    assert not missing, (
        "these classes cannot be constructed and are not pinned in "
        f"_UNBUILDABLE: {missing}"
    )
    assert not stale, (
        f"these rows in _UNBUILDABLE are stale -- the classes now construct: {stale}"
    )
    for suffix, reason in _UNBUILDABLE.items():
        assert reason.strip(), f"_UNBUILDABLE[{suffix!r}] has no reason"


def test_not_rendered_table_is_exact(mysql_dialect):
    """_NOT_RENDERED lists every class whose to_sql() fails unexpectedly."""
    observed = _verdicts(mysql_dialect)["other"]

    missing = sorted(set(observed) - set(_NOT_RENDERED))
    stale = sorted(set(_NOT_RENDERED) - set(observed))
    assert not missing, (
        "these classes raise something the matrix does not understand and are "
        f"not pinned in _NOT_RENDERED: {missing}"
    )
    assert not stale, (
        f"these rows in _NOT_RENDERED are stale -- the classes now render or "
        f"refuse properly: {stale}"
    )
    for suffix, (exc_name, reason) in _NOT_RENDERED.items():
        assert exc_name == observed[suffix], (
            f"_NOT_RENDERED[{suffix!r}] says {exc_name} but it raises "
            f"{observed[suffix]}"
        )
        assert reason.strip(), f"_NOT_RENDERED[{suffix!r}] has no reason"


def test_declared_gap_table_is_exact(mysql_dialect):
    """_DECLARED_GAP lists every class the dispatch cannot find a formatter for.

    Exact in both directions, which is the property that makes the table worth
    keeping:

    * a class that grows a formatter leaves ``no_formatter``, so a row left
      behind is a failure -- the table cannot outlive the gap it describes;
    * a class that starts refusing *through the dispatch* rather than through a
      probe enters ``no_formatter``, so an unlisted one is a failure -- the table
      cannot fall behind a gap that appears.

    The formatter name is asserted too, so a row cannot quietly start describing
    a different gap than the one it was written for. That is the difference
    between a table and a comment: renaming ``format_vertex_table`` to something
    else in the dialect leaves this red.
    """
    observed = _verdicts(mysql_dialect)["no_formatter"]

    missing = sorted(set(observed) - set(_DECLARED_GAP))
    stale = sorted(set(_DECLARED_GAP) - set(observed))
    assert not missing, (
        "these classes refuse because MySQLDialect names no formatter for "
        f"them, and they are not pinned in _DECLARED_GAP: {missing}"
    )
    assert not stale, (
        "these rows in _DECLARED_GAP are stale -- the classes now render, or "
        f"refuse through a probe rather than the dispatch: {stale}"
    )
    for suffix, (formatter_name, reason) in _DECLARED_GAP.items():
        assert formatter_name == observed[suffix], (
            f"_DECLARED_GAP[{suffix!r}] names {formatter_name} but the class "
            f"dispatches to {observed[suffix]}"
        )
        assert reason.strip(), f"_DECLARED_GAP[{suffix!r}] has no reason"


def test_the_three_render_verdicts_partition_the_matrix(mysql_dialect):
    """No class is unaccounted for, and the two tables do not overlap.

    Each table is exact against its own bucket, which does not by itself stop a
    class from being in both, nor from a class having no verdict at all. This
    closes both: every matrix class lands in exactly one bucket, the two
    bookkeeping tables are the two that need rows, and the two legal verdicts
    need none.
    """
    verdicts = _verdicts(mysql_dialect)
    buckets = set(verdicts["renders"]) | set(verdicts["abstract"])
    buckets |= set(verdicts["no_formatter"]) | set(verdicts["probe"])
    buckets |= set(verdicts["other"])

    assert buckets == set(_MATRIX_IDS), (
        "these matrix classes took no verdict at all: "
        f"{sorted(set(_MATRIX_IDS) - buckets)}"
    )
    overlap = set(_DECLARED_GAP) & set(_NOT_RENDERED)
    assert not overlap, (
        "these classes are pinned as both a declared gap and an unexplained "
        f"failure; they are the same fact stated twice: {sorted(overlap)}"
    )


def test_constructor_tables_are_exact():
    """Every row has a registered factory, and every factory has a row."""
    from rhosocial.activerecord.testsuite.utils import expression as harness

    installed = set(harness._SPECIAL_REGISTRY) - set(harness.special_constructors())
    listed = set(DEDICATED_CONSTRUCTORS)
    assert not (listed - installed), (
        "these classes have a documented reason but no registered constructor: "
        f"{sorted(listed - installed)}"
    )
    assert not (installed - listed), (
        "these constructors are registered without a row in the reason tables: "
        f"{sorted(installed - listed)}"
    )
    for suffix, reason in DEDICATED_CONSTRUCTORS.items():
        assert reason.strip(), f"DEDICATED_CONSTRUCTORS[{suffix!r}] has no reason"


def test_harness_defect_rows_match_the_misreading():
    """The misreading rows are exactly the rows whose annotation triggers it.

    The claim in the table comment -- that these seven factories exist only
    because the harness reads ``Sequence[str]`` as the catalogue object -- is
    checkable, so it is checked. This is the test that says to delete them once
    ``rhosocial-activerecord-testsuite`` stops doing it, and it fails now, which
    is the point: it names the seven rather than letting the exemption grow.
    """
    reaches = {
        _suffix(fqn)
        for fqn, cls in ALL_CLASSES.items()
        if _uses_parameterised_sequence(cls)
    }
    misread = set(_HARNESS_DEFECT_CONSTRUCTORS) | set(
        _MISREAD_AND_CONTRACT_CONSTRUCTORS
    )
    observed = reaches & set(DEDICATED_CONSTRUCTORS)
    assert misread == observed, (
        "the rows that say the Sequence misreading is why a dedicated "
        "constructor is needed, and the rows that actually declare a "
        "parameterised Sequence, disagree. "
        f"claimed-but-not-misread={sorted(misread - observed)} "
        f"misread-but-not-claimed={sorted(observed - misread)}"
    )


def test_both_packages_are_collected():
    """The matrix covers core's own class library, not just this backend's."""
    assert len(CORE_CLASSES) > 100, (
        f"core's class library yielded only {len(CORE_CLASSES)} classes, so the "
        f"matrix would not be covering it"
    )
    assert len(CLASSES) > 100, (
        f"the MySQL package yielded only {len(CLASSES)} classes"
    )


def test_core_expressions_also_roundtrip(mysql_dialect):
    """Core expression classes usable with MySQL dialect also round-trip."""
    from rhosocial.activerecord.backend.expression.core import Column, Literal
    from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

    expr = ComparisonPredicate(
        mysql_dialect, "=", Column(mysql_dialect, "a"), Literal(mysql_dialect, 1)
    )
    roundtrip_expression("core", expr, mysql_dialect)
    sql_consistent("core", expr, mysql_dialect)