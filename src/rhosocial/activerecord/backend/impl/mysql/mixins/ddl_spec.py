# src/rhosocial/activerecord/backend/impl/mysql/mixins/ddl_spec.py
"""MySQL ``build_spec`` implementation (DDL feature-spec claiming).

Composed into ``MySQLDialect``. Claims the MySQL-specific Specs defined in
``..ddl_spec`` via ``isinstance`` and translates them into the MySQL partition
expression layer. All other Specs fall through to the generic
``DDLSpecBuildingMixin`` base translation.
"""

from typing import Any, Optional

from rhosocial.activerecord.backend.dialect.mixins.ddl_spec import DDLSpecBuildingMixin
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements.ddl_spec import (
    ColumnPatchSpec,
    DDLSpec,
    PartitionSpec,
)

from ..ddl_spec import (
    MySQLHashPartition,
    MySQLListPartition,
    MySQLPartitionBound,
    MySQLPartitionDefinitionSpec,
    MySQLRangePartition,
    MySQLSetColumnSpec,
    MySQLSpatialColumnSpec,
    MySQLVectorColumnSpec,
)
from ..expression import (
    MySQLPartitionByHash,
    MySQLPartitionByList,
    MySQLPartitionByRange,
    MySQLPartitionDefinition,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
    MySQLGeometryType,
    MySQLPointType,
    MySQLLineStringType,
    MySQLPolygonType,
    MySQLMultiPointType,
    MySQLMultiLineStringType,
    MySQLMultiPolygonType,
    MySQLGeometryCollectionType,
    MySQLSetType,
    MySQLVectorType,
)


def _bound_expression(dialect, bound: "MySQLPartitionBound"):
    """Translate a plain boundary to the MySQL partition value expression."""
    if bound.value == "MAXVALUE":
        return MySQLPartitionMaxValue(dialect)
    return MySQLPartitionValue(dialect, bound.value)


def _definition_expression(dialect, spec: "MySQLPartitionDefinitionSpec"):
    """Translate a plain partition definition to ``MySQLPartitionDefinition``."""
    less_than = None
    in_values = None
    if spec.less_than is not None:
        less_than = [_bound_expression(dialect, b) for b in spec.less_than]
    elif spec.in_values is not None:
        in_values = [_bound_expression(dialect, b) for b in spec.in_values]
    return MySQLPartitionDefinition(
        name=spec.name,
        less_than=less_than,
        in_values=in_values,
    )


class MySQLDDLSpecMixin(DDLSpecBuildingMixin):
    """MySQL-specific ``build_spec`` claiming and translation."""

    def build_spec(self, spec: "DDLSpec") -> Optional[Any]:
        """Claim MySQL partition Specs; otherwise defer to the generic build."""
        if isinstance(spec, MySQLRangePartition):
            return self._build_mysql_range_partition(spec)
        if isinstance(spec, MySQLListPartition):
            return self._build_mysql_list_partition(spec)
        if isinstance(spec, MySQLHashPartition):
            return self._build_mysql_hash_partition(spec)
        if isinstance(spec, MySQLVectorColumnSpec):
            return self._build_mysql_vector_column(spec)
        if isinstance(spec, MySQLSpatialColumnSpec):
            return self._build_mysql_spatial_column(spec)
        if isinstance(spec, MySQLSetColumnSpec):
            return self._build_mysql_set_column(spec)
        return super().build_spec(spec)

    def _build_mysql_range_partition(self, spec: "MySQLRangePartition"):
        return MySQLPartitionByRange(
            self,
            keys=[Column(self, spec.column)],
            partitions=[_definition_expression(self, d) for d in spec.partitions],
        )

    def _build_mysql_list_partition(self, spec: "MySQLListPartition"):
        return MySQLPartitionByList(
            self,
            keys=[Column(self, spec.column)],
            partitions=[_definition_expression(self, d) for d in spec.partitions],
        )

    def _build_mysql_hash_partition(self, spec: "MySQLHashPartition"):
        return MySQLPartitionByHash(
            self,
            keys=[Column(self, spec.column)],
            partitions_count=spec.partitions,
        )

    def _build_mysql_vector_column(self, spec: "MySQLVectorColumnSpec"):
        """VECTOR(dim) column — MySQL 9.0+; unclaimed (None) if unsupported."""
        supports = getattr(self, "supports_vector_type", None)
        if supports is not None:
            try:
                supported = bool(supports())
            except Exception:
                supported = True
            if not supported:
                return None
        return ColumnPatchSpec(
            column=spec.column,
            patched_data_type=MySQLVectorType(self, dim=spec.dim),
        )

    def _build_mysql_spatial_column(self, spec: "MySQLSpatialColumnSpec"):
        """Spatial column (GEOMETRY / POINT / ... ) with optional SRID."""
        kinds = {
            "GEOMETRY": MySQLGeometryType,
            "POINT": MySQLPointType,
            "LINESTRING": MySQLLineStringType,
            "POLYGON": MySQLPolygonType,
            "MULTIPOINT": MySQLMultiPointType,
            "MULTILINESTRING": MySQLMultiLineStringType,
            "MULTIPOLYGON": MySQLMultiPolygonType,
            "GEOMETRYCOLLECTION": MySQLGeometryCollectionType,
        }
        type_cls = kinds[spec.kind]
        return ColumnPatchSpec(
            column=spec.column,
            patched_data_type=type_cls(self, srid=spec.srid),
        )

    def _build_mysql_set_column(self, spec: "MySQLSetColumnSpec"):
        """SET('a','b',...) column."""
        return ColumnPatchSpec(
            column=spec.column,
            patched_data_type=MySQLSetType(self, values=spec.values),
        )

    def _build_partition_spec(self, spec: "PartitionSpec"):
        """Unclaimed partition Specs silently return ``None``."""
        return None