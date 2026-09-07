# tests/rhosocial/activerecord_mysql_test/feature/backend/ddl/test_ddl_spec_protocol.py
"""MySQL DDL feature-spec claiming tests (``build_spec``).

Covers the MySQL-specific Specs (partition) and the generic Specs on the
MySQL dialect:

- MySQL partition Specs (RANGE / LIST / HASH) translate to the MySQL
  partition expression layer with correct DDL.
- Generic Specs still translate via the core ``DDLSpecBuildingMixin``.
- Foreign Specs (``PartitionSpec`` marker, unknown objects) return ``None``
  (silently ignored).
"""

import pytest

from rhosocial.activerecord.base import (
    CheckSpec,
    PartitionSpec,
    PrimaryKeySpec,
    UniqueSpec,
)
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.ddl_spec import (
    MySQLHashPartition,
    MySQLListPartition,
    MySQLPartitionBound,
    MySQLPartitionDefinitionSpec,
    MySQLRangePartition,
    MySQLSetColumnSpec,
    MySQLSpatialColumnSpec,
    MySQLVectorColumnSpec,
)


@pytest.fixture
def dialect():
    return MySQLDialect()


class TestProtocolConformance:
    def test_build_spec_returns_none_for_unknown(self, dialect):
        assert dialect.build_spec(object()) is None

    def test_build_spec_returns_none_for_base_partition_marker(self, dialect):
        # The core PartitionSpec marker is claimed by nobody; MySQL only
        # claims its own MySQL*Partition subclasses.
        assert dialect.build_spec(PartitionSpec()) is None


class TestGenericSpecTranslation:
    """Generic Specs keep working on the MySQL dialect."""

    def test_unique_spec(self, dialect):
        result = dialect.build_spec(UniqueSpec(["a", "b"], name="uq_ab"))
        assert result.columns == ["a", "b"]

    def test_check_spec_lazy(self, dialect):
        result = dialect.build_spec(
            CheckSpec(lambda d: Column(d, "age") >= 18, name="ck_age")
        )
        assert result.check_condition is not None

    def test_primary_key_single(self, dialect):
        result = dialect.build_spec(PrimaryKeySpec(["id"]))
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraint,
            ColumnConstraintType,
        )
        assert isinstance(result, ColumnConstraint)
        assert result.constraint_type == ColumnConstraintType.PRIMARY_KEY


class TestMySQLPartitionSpecs:
    def test_range_partition(self, dialect):
        spec = MySQLRangePartition(
            "created_at",
            [
                MySQLPartitionDefinitionSpec(
                    "p2026", less_than=[MySQLPartitionBound(2027)]
                ),
                MySQLPartitionDefinitionSpec(
                    "p_max", less_than=[MySQLPartitionBound("MAXVALUE")]
                ),
            ],
        )
        expr = dialect.build_spec(spec)
        assert type(expr).__name__ == "MySQLPartitionByRange"
        sql, _ = expr.to_sql()
        assert "PARTITION BY RANGE" in sql
        assert "VALUES LESS THAN (2027)" in sql
        assert "MAXVALUE" in sql

    def test_list_partition(self, dialect):
        spec = MySQLListPartition(
            "region",
            [
                MySQLPartitionDefinitionSpec(
                    "p_east", in_values=[MySQLPartitionBound("EAST")]
                )
            ],
        )
        expr = dialect.build_spec(spec)
        assert type(expr).__name__ == "MySQLPartitionByList"
        sql, _ = expr.to_sql()
        assert "PARTITION BY LIST" in sql
        assert "VALUES IN ('EAST')" in sql

    def test_hash_partition(self, dialect):
        spec = MySQLHashPartition("id", 4)
        expr = dialect.build_spec(spec)
        assert type(expr).__name__ == "MySQLPartitionByHash"
        sql, _ = expr.to_sql()
        assert "PARTITION BY HASH" in sql
        assert "PARTITIONS 4" in sql

    def test_range_requires_partitions(self):
        with pytest.raises(ValueError):
            MySQLRangePartition("id", [])

    def test_definition_requires_bound(self):
        with pytest.raises(ValueError):
            MySQLPartitionDefinitionSpec("p1")


class TestBuildSpecFeedsCreateTable:
    def test_partition_spec_feeds_create_table(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnDefinition,
            CreateTableExpression,
        )
        from rhosocial.activerecord.backend.expression.types import IntegerType

        part = dialect.build_spec(
            MySQLRangePartition(
                "id",
                [MySQLPartitionDefinitionSpec("p1", less_than=[MySQLPartitionBound(100)])],
            )
        )
        pk = dialect.build_spec(PrimaryKeySpec(["id"]))
        cols = [
            ColumnDefinition("id", IntegerType(), constraints=[pk]),
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table="t_orders",
            columns=cols,
            partition=part,
        )
        sql, _ = expr.to_sql()
        assert "PARTITION BY RANGE" in sql


class TestMySQLTypeSpecs:
    """MySQL column-type Specs (vector / spatial / SET)."""

    def test_vector_column(self, dialect):
        dialect.version = (9, 0, 0)
        result = dialect.build_spec(MySQLVectorColumnSpec("embedding", dim=384))
        assert result.patched_data_type is not None
        sql, _ = result.patched_data_type.to_sql(dialect)
        assert sql == "VECTOR(384)"

    def test_spatial_column(self, dialect):
        result = dialect.build_spec(
            MySQLSpatialColumnSpec("location", kind="POINT", srid=4326)
        )
        sql, _ = result.patched_data_type.to_sql(dialect)
        assert "POINT" in sql
        assert "SRID 4326" in sql

    def test_set_column(self, dialect):
        result = dialect.build_spec(MySQLSetColumnSpec("tags", ["a", "b"]))
        sql, _ = result.patched_data_type.to_sql(dialect)
        assert "SET" in sql
        assert "'a'" in sql

    def test_vector_invalid_dim(self):
        with pytest.raises(ValueError):
            MySQLVectorColumnSpec("v", 0)

    def test_spatial_invalid_kind(self):
        with pytest.raises(ValueError):
            MySQLSpatialColumnSpec("g", kind="BOGUS")

    def test_model_type_specs_render(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        dialect.version = (9, 0, 0)

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [
                MySQLVectorColumnSpec("embedding", dim=384),
                MySQLSpatialColumnSpec("location", kind="POINT", srid=4326),
                MySQLSetColumnSpec("tags", ["a", "b", "c"]),
            ]
            embedding: object
            location: object
            tags: str

        expr = T.generate_create_table(dialect)
        sql, _ = expr.to_sql()
        assert "VECTOR(384)" in sql
        assert "POINT SRID 4326" in sql
        assert "SET('a','b','c')" in sql