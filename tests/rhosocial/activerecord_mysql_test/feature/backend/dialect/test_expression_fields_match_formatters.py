# tests/rhosocial/activerecord_mysql_test/feature/backend/dialect/test_expression_fields_match_formatters.py
"""A formatter may not read a field its statement does not carry.

A statement formatter that reads ``expr.schema_name`` needs the expression to
have that attribute. When the formatter was changed to qualify names and the
expression was not given the field, the result is not wrong SQL -- it is an
``AttributeError`` on a statement that can never be built, which is how
SQLServerColumnstoreIndexExpression reached CI.

These were source scans rather than runtime tests. A scan does not work here:
whether the field exists depends on inheritance reaching core, which lives in
another repository, and on **core_kwargs forwarding. Reading the source of this
repository can see neither, so a scan reported defects that were not there --
two were chased down and both were false alarms -- while a field genuinely
removed still passed. Building the statement answers the question the defect
actually asks: does this statement build, and does the schema reach the SQL?
"""
import importlib
import inspect

import pytest

#: Statement fields a formatter may read that some expression classes carry
#: under a different name. Reading these by their own name is the defect.
#: TruncateExpression and the PostgreSQL vacuum/statistics expressions name the
#: field `schema`; the DDL statements name it `schema_name`.
KNOWN_ALIASES = {
    "schema": {"TruncateExpression"},
}


class TestQualifiedStatementsRender:
    """A statement whose formatter qualifies names must build with a schema.

    Checked by building each statement and rendering it, not by scanning
    source. Each case names the statement and how to build it, so adding
    coverage for a newly qualified object type is one entry rather than a new
    mechanism.

    MySQL quotes with backticks, so the expected SQL below carries
    ```app```.`table` where ``app`` was passed in.
    """

    @pytest.fixture
    def dialect(self):
        from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect

        return MySQLDialect(version=(8, 0, 0))

    def test_create_spatial_index(self, dialect):
        """Both the index and the table it sits on are qualified.

        ``format_create_spatial_index`` is annotated ``expr`` with no type and
        type-checks at runtime instead, which is exactly the shape a source
        scan could not attribute to a class.
        """
        from rhosocial.activerecord.backend.impl.mysql.expression.spatial import (
            MySQLCreateSpatialIndexExpression,
        )

        expr = MySQLCreateSpatialIndexExpression(
            dialect, index_name="idx_places_geom", table_name="places", column="geom"
        )
        assert expr.to_sql()[0] == (
            "CREATE SPATIAL INDEX `idx_places_geom` ON `places` (`geom`)"
        ), expr.to_sql()[0]
        qualified = MySQLCreateSpatialIndexExpression(
            dialect,
            index_name="idx_places_geom",
            table_name="places",
            column="geom",
            schema_name="app",
        )
        assert qualified.to_sql()[0] == (
            "CREATE SPATIAL INDEX `app`.`idx_places_geom` ON `app`.`places` (`geom`)"
        ), qualified.to_sql()[0]

    def test_fulltext_index_options(self, dialect):
        from rhosocial.activerecord.backend.impl.mysql.expression.fulltext import (
            MySQLFulltextIndexOptionsExpression,
        )

        expr = MySQLFulltextIndexOptionsExpression(
            dialect, index_name="ft_orders", columns=["body"]
        )
        assert expr.to_sql()[0] == "FULLTEXT `ft_orders` (`body`)", expr.to_sql()[0]
        qualified = MySQLFulltextIndexOptionsExpression(
            dialect, index_name="ft_orders", columns=["body"], schema_name="app"
        )
        assert qualified.to_sql()[0] == "FULLTEXT `app`.`ft_orders` (`body`)", (
            qualified.to_sql()[0]
        )

    def test_table_statement(self, dialect):
        from rhosocial.activerecord.backend.impl.mysql.expression.table_statement import (
            MySQLTableExpression,
        )

        expr = MySQLTableExpression(dialect, table_name="orders")
        assert expr.to_sql()[0] == "TABLE `orders`", expr.to_sql()[0]
        qualified = MySQLTableExpression(
            dialect, table_name="orders", schema_name="app"
        )
        assert qualified.to_sql()[0] == "TABLE `app`.`orders`", qualified.to_sql()[0]

    def test_drop_view_inherits_the_field_from_core(self, dialect):
        """The case a source scan got wrong in both directions.

        DropViewExpression lives in core and assigns schema_name there. A scan
        of this repository sees the formatter reading the field and no
        assignment at all, so it either misses a field that is there or reports
        one that is not, depending on how it resolves the base. Building it
        settles the question.
        """
        from rhosocial.activerecord.backend.expression import DropViewExpression

        expr = DropViewExpression(dialect, view_name="v_orders")
        assert expr.to_sql()[0] == "DROP VIEW `v_orders`", expr.to_sql()[0]
        qualified = DropViewExpression(
            dialect, view_name="v_orders", schema_name="app"
        )
        assert qualified.to_sql()[0] == "DROP VIEW `app`.`v_orders`", (
            qualified.to_sql()[0]
        )

    def test_create_trigger(self, dialect):
        """The trigger, its table and the routine it calls are all qualified."""
        from rhosocial.activerecord.backend.expression import CreateTriggerExpression
        from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
            TriggerEvent,
            TriggerLevel,
            TriggerTiming,
        )

        def build(schema_name=None):
            return CreateTriggerExpression(
                dialect,
                trigger_name="trg_audit",
                table_name="orders",
                timing=TriggerTiming.BEFORE,
                events=[TriggerEvent.INSERT],
                function_name="audit_fn",
                level=TriggerLevel.ROW,
                schema_name=schema_name,
            )

        assert build().to_sql()[0] == (
            "CREATE TRIGGER `trg_audit` BEFORE INSERT ON `orders` FOR EACH ROW "
            "CALL `audit_fn`"
        )
        assert build(schema_name="app").to_sql()[0] == (
            "CREATE TRIGGER `app`.`trg_audit` BEFORE INSERT ON `app`.`orders` "
            "FOR EACH ROW CALL `app`.`audit_fn`"
        )


class TestExpressionSignatures:
    """The expressions this backend's formatters qualify must take the field."""

    @pytest.mark.parametrize(
        "import_path,class_name",
        [
            (
                "rhosocial.activerecord.backend.impl.mysql.expression.spatial",
                "MySQLCreateSpatialIndexExpression",
            ),
            (
                "rhosocial.activerecord.backend.impl.mysql.expression.fulltext",
                "MySQLFulltextIndexOptionsExpression",
            ),
            (
                "rhosocial.activerecord.backend.impl.mysql.expression.table_statement",
                "MySQLTableExpression",
            ),
            (
                "rhosocial.activerecord.backend.expression.statements.ddl_view",
                "DropViewExpression",
            ),
            (
                "rhosocial.activerecord.backend.expression.statements.ddl_trigger",
                "CreateTriggerExpression",
            ),
        ],
    )
    def test_qualified_expression_accepts_schema_name(self, import_path, class_name):
        module = importlib.import_module(import_path)
        cls = getattr(module, class_name)
        params = inspect.signature(cls.__init__).parameters
        assert "schema_name" in params, (
            f"{class_name} is qualified by its formatter, so it needs the "
            f"field; got {list(params)}"
        )
        assert params["schema_name"].default is None, (
            f"{class_name} must default schema_name to None -- None is what "
            f"means unqualified"
        )
