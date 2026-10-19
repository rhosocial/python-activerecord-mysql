# src/rhosocial/activerecord/backend/impl/mysql/expression/__init__.py
"""
MySQL-specific expression classes.

This module provides expression classes that are specific to MySQL, such as
LOAD DATA INFILE, JSON_TABLE, JSON functions, spatial functions, vector
functions, MATCH...AGAINST expressions, row-level locking expressions,
and JSON Duality View expressions.

Directory structure:
- load_data.py      - LOAD DATA INFILE expression
- json_table.py    - JSON_TABLE expression
- json.py           - JSON function expressions
- spatial.py         - Spatial function expressions
- vector.py          - Vector function expressions (MySQL 9.0+)
- match_against.py - MATCH...AGAINST expression
- locking.py        - Row-level locking expressions (FOR UPDATE, FOR SHARE)
- json_duality_view.py - JSON Duality View expressions (MySQL 9.7+)
- types.py          - MySQL-specific DataType subclasses for DDL
"""

from .table_options import MySQLRowFormat, MySQLCreateTableOptions
from .dml import MySQLInsertExpression
from .alter_column import MySQLAddColumn
from .column import (
    MySQLColumnFormat,
    MySQLColumnStorage,
    MySQLColumnDefinition,
    MySQLColumnOptions,
)
from .load_data import MySQLLoadDataExpression, LoadDataOptions
from .json_table import MySQLJSONTableExpression, JSONTableColumn, NestedPath
from .json import (
    MySQLJSONExtractExpression,
    MySQLJSONObjectExpression,
    MySQLJSONArrayExpression,
    MySQLJSONContainsExpression,
    MySQLJSONUnquoteExpression,
    MySQLJSONSetExpression,
    MySQLJSONRemoveExpression,
    MySQLJSONTypeExpression,
    MySQLJSONValidExpression,
    MySQLJSONSearchExpression,
)
from .spatial import (
    MySQLSTGeomFromTextExpression,
    MySQLSTDistanceExpression,
    MySQLSTWithinExpression,
    MySQLSTContainsExpression,
    MySQLSpatialLiteralExpression,
    MySQLSTGeomFromWKBExpression,
    MySQLSTAsTextExpression,
    MySQLSTAsGeoJSONExpression,
    MySQLCreateSpatialIndexExpression,
)
from .vector import (
    MySQLVectorExpression,
    MySQLDistanceEuclideanExpression,
    MySQLDistanceCosineExpression,
    MySQLDistanceDotExpression,
    MySQLStringToVectorExpression,
    MySQLVectorToStringExpression,
    MySQLVectorDimExpression,
    MySQLCreateVectorIndexExpression,
)
from .set_type import (
    MySQLSetLiteralExpression,
    MySQLFindInSetExpression,
    MySQLSetContainsExpression,
)
from .fulltext import MySQLFulltextIndexOptionsExpression
from .table_expr import MySQLInlineIndexExpression, MySQLStorageOptionsExpression
from .match_against import MySQLMatchAgainstExpression, MatchAgainstMode
from .json_duality_view import (
    CreateJsonDualityViewExpression,
    DropJsonDualityViewExpression,
    DualityObjectSpec,
    DualityColumnMapping,
    DualityNestedMapping,
    DualityViewDMLTag,
    MySQLDualityObjectSelectExpression,
    MySQLDualityObjectBodyExpression,
    MySQLNestedDualityExpression,
)
from .optimizer_hint import (
    MySQLOptimizerHintExpression,
    SetVarHint,
    OptimizerHintType,
)
from .partition import (
    MySQLPartitionStrategy,
    MySQLPartitionClause,
    MySQLPartitionMaxValue,
    MySQLPartitionValue,
    MySQLPartitionDefinition,
    MySQLPartitionByRange,
    MySQLPartitionByRangeColumns,
    MySQLPartitionByList,
    MySQLPartitionByListColumns,
    MySQLPartitionByHash,
    MySQLPartitionByKey,
    MySQLPartitionOptions,
    MySQLPartitionTableExpression,
    MySQLAddPartitionExpression,
    MySQLDropPartitionExpression,
    MySQLTruncatePartitionExpression,
    MySQLReorganizePartitionExpression,
    MySQLExchangePartitionExpression,
    MySQLRemovePartitioningExpression,
    MySQLCoalescePartitionExpression,
    MySQLAnalyzePartitionExpression,
    MySQLCheckPartitionExpression,
    MySQLOptimizePartitionExpression,
    MySQLRebuildPartitionExpression,
    MySQLRepairPartitionExpression,
    MySQLGetPartitionsExpression,
    MySQLSubpartitionStrategy,
    MySQLSubpartitionDefinition,
    MySQLSubpartitionClause,
)
from .partition_lifecycle import (
    MySQLAddPartitionHelper,
    MySQLAddSubpartitionHelper,
    MySQLCoalescePartitionHelper,
    MySQLDropOldestPartitionHelper,
    MySQLReorganizePartitionHelper,
)
from .rename_table import MySQLRenameTableExpression
from .table_statement import MySQLTableStatement, MySQLValuesExpression
from .maintenance import (
    MySQLAnalyzeTableExpression,
    MySQLCheckTableExpression,
    MySQLChecksumTableExpression,
    MySQLOptimizeTableExpression,
    MySQLRepairTableExpression,
    CheckTableOption,
    ChecksumTableOption,
    RepairTableOption,
    NoWriteToBinlogOption,
)
from .routine import (
    MySQLCallExpression,
    MySQLCreateProcedureExpression,
    MySQLDropProcedureExpression,
    MySQLCreateFunctionExpression,
    MySQLDropFunctionExpression,
)
from .load_xml import MySQLLoadXMLStatement, LoadXMLPriority, LoadXMLConflictMode
from .admin import (
    MySQLCacheIndexExpression,
    MySQLLoadIndexIntoCacheExpression,
    MySQLFlushExpression,
    FlushOption,
    MySQLResetExpression,
    ResetOption,
    MySQLInstallComponentExpression,
    MySQLUninstallComponentExpression,
    MySQLInstallPluginExpression,
    MySQLUninstallPluginExpression,
    MySQLCloneExpression,
    MySQLRestartExpression,
    MySQLBinlogExpression,
    MySQLHandlerOpenExpression,
    MySQLHandlerReadExpression,
    MySQLHandlerCloseExpression,
    HandlerReadMode,
    MySQLDoExpression,
    MySQLKillExpression,
    KillTarget,
    MySQLShutdownExpression,
    MySQLHelpExpression,
    AccountSpec,
    GrantPrivilege,
    MySQLCreateUserExpression,
    MySQLDropUserExpression,
    MySQLGrantExpression,
    MySQLRevokeExpression,
)

# DataType subclasses for DDL
from .types import (
    MySQLBigIntType,
    MySQLBinaryType,
    MySQLBitType,
    MySQLBlobType,
    MySQLEnumType,
    MySQLGeometryCollectionType,
    MySQLGeometryType,
    MySQLIntType,
    MySQLLineStringType,
    MySQLLongBlobType,
    MySQLLongTextType,
    MySQLMediumBlobType,
    MySQLMediumTextType,
    MySQLMultiLineStringType,
    MySQLMultiPointType,
    MySQLMultiPolygonType,
    MySQLPointType,
    MySQLPolygonType,
    MySQLSetType,
    MySQLSmallIntType,
    MySQLTextType,
    MySQLTinyBlobType,
    MySQLTinyIntType,
    MySQLTinyTextType,
    MySQLUUIDType,
    MySQLVarBinaryType,
    MySQLVectorType,
    MySQLYearType,
)

__all__ = [
    "MySQLLoadDataExpression",
    "LoadDataOptions",
    "MySQLCreateTableOptions",
    "MySQLRowFormat",
    "MySQLInsertExpression",
    "MySQLAddColumn",
    "MySQLColumnFormat",
    "MySQLColumnStorage",
    "MySQLColumnDefinition",
    "MySQLColumnOptions",
    "MySQLJSONTableExpression",
    "JSONTableColumn",
    "NestedPath",
    "MySQLJSONExtractExpression",
    "MySQLJSONObjectExpression",
    "MySQLJSONArrayExpression",
    "MySQLJSONContainsExpression",
    "MySQLJSONUnquoteExpression",
    "MySQLJSONSetExpression",
    "MySQLJSONRemoveExpression",
    "MySQLJSONTypeExpression",
    "MySQLJSONValidExpression",
    "MySQLJSONSearchExpression",
    "MySQLSTGeomFromTextExpression",
    "MySQLSTDistanceExpression",
    "MySQLSTWithinExpression",
    "MySQLSTContainsExpression",
    "MySQLSpatialLiteralExpression",
    "MySQLSTGeomFromWKBExpression",
    "MySQLSTAsTextExpression",
    "MySQLSTAsGeoJSONExpression",
    "MySQLCreateSpatialIndexExpression",
    "MySQLVectorExpression",
    "MySQLDistanceEuclideanExpression",
    "MySQLDistanceCosineExpression",
    "MySQLDistanceDotExpression",
    "MySQLStringToVectorExpression",
    "MySQLVectorToStringExpression",
    "MySQLVectorDimExpression",
    "MySQLCreateVectorIndexExpression",
    "MySQLSetLiteralExpression",
    "MySQLFindInSetExpression",
    "MySQLSetContainsExpression",
    "MySQLFulltextIndexOptionsExpression",
    "MySQLInlineIndexExpression",
    "MySQLStorageOptionsExpression",
    "MySQLMatchAgainstExpression",
    "MatchAgainstMode",
    "CreateJsonDualityViewExpression",
    "DropJsonDualityViewExpression",
    "DualityObjectSpec",
    "DualityColumnMapping",
    "DualityNestedMapping",
    "DualityViewDMLTag",
    "MySQLDualityObjectSelectExpression",
    "MySQLDualityObjectBodyExpression",
    "MySQLNestedDualityExpression",
    "MySQLOptimizerHintExpression",
    "SetVarHint",
    "OptimizerHintType",
    "MySQLPartitionStrategy",
    "MySQLPartitionClause",
    "MySQLPartitionMaxValue",
    "MySQLPartitionValue",
    "MySQLPartitionDefinition",
    "MySQLPartitionByRange",
    "MySQLPartitionByRangeColumns",
    "MySQLPartitionByList",
    "MySQLPartitionByListColumns",
    "MySQLPartitionByHash",
    "MySQLPartitionByKey",
    "MySQLPartitionOptions",
    "MySQLPartitionTableExpression",
    "MySQLAddPartitionExpression",
    "MySQLDropPartitionExpression",
    "MySQLTruncatePartitionExpression",
    "MySQLReorganizePartitionExpression",
    "MySQLExchangePartitionExpression",
    "MySQLRemovePartitioningExpression",
    "MySQLCoalescePartitionExpression",
    "MySQLAnalyzePartitionExpression",
    "MySQLCheckPartitionExpression",
    "MySQLOptimizePartitionExpression",
    "MySQLRebuildPartitionExpression",
    "MySQLRepairPartitionExpression",
    "MySQLSubpartitionStrategy",
    "MySQLSubpartitionDefinition",
    "MySQLSubpartitionClause",
    "MySQLRenameTableExpression",
    "MySQLTableStatement",
    "MySQLValuesExpression",
    "MySQLAnalyzeTableExpression",
    "MySQLCheckTableExpression",
    "MySQLChecksumTableExpression",
    "MySQLOptimizeTableExpression",
    "MySQLRepairTableExpression",
    "CheckTableOption",
    "ChecksumTableOption",
    "RepairTableOption",
    "NoWriteToBinlogOption",
    "MySQLCallExpression",
    "MySQLCreateProcedureExpression",
    "MySQLDropProcedureExpression",
    "MySQLCreateFunctionExpression",
    "MySQLDropFunctionExpression",
    "MySQLLoadXMLStatement",
    "LoadXMLPriority",
    "LoadXMLConflictMode",
    "MySQLCacheIndexExpression",
    "MySQLLoadIndexIntoCacheExpression",
    "MySQLFlushExpression",
    "FlushOption",
    "MySQLResetExpression",
    "ResetOption",
    "MySQLInstallComponentExpression",
    "MySQLUninstallComponentExpression",
    "MySQLInstallPluginExpression",
    "MySQLUninstallPluginExpression",
    "MySQLCloneExpression",
    "MySQLRestartExpression",
    "MySQLBinlogExpression",
    "MySQLHandlerOpenExpression",
    "MySQLHandlerReadExpression",
    "MySQLHandlerCloseExpression",
    "HandlerReadMode",
    "MySQLDoExpression",
    "MySQLKillExpression",
    "KillTarget",
    "MySQLShutdownExpression",
    "MySQLHelpExpression",
    "AccountSpec",
    "GrantPrivilege",
    "MySQLCreateUserExpression",
    "MySQLDropUserExpression",
    "MySQLGrantExpression",
    "MySQLRevokeExpression",
    # DataType subclasses for DDL
    "MySQLBigIntType",
    "MySQLBinaryType",
    "MySQLBitType",
    "MySQLBlobType",
    "MySQLEnumType",
    "MySQLGeometryCollectionType",
    "MySQLGeometryType",
    "MySQLIntType",
    "MySQLLineStringType",
    "MySQLLongBlobType",
    "MySQLLongTextType",
    "MySQLMediumBlobType",
    "MySQLMediumTextType",
    "MySQLMultiLineStringType",
    "MySQLMultiPointType",
    "MySQLMultiPolygonType",
    "MySQLPointType",
    "MySQLPolygonType",
    "MySQLSetType",
    "MySQLSmallIntType",
    "MySQLTextType",
    "MySQLTinyBlobType",
    "MySQLTinyIntType",
    "MySQLTinyTextType",
    "MySQLUUIDType",
    "MySQLVarBinaryType",
    "MySQLVectorType",
    "MySQLYearType",
]

# ``MySQL`` is one word. The general derivation -- a run of capitals counts as
# a single word -- disagrees with this backend's identifier and yields
# ``my_sql_flush_expression``, ``my_sqljson_object_expression``,
# ``my_sqlst_as_text_expression`` and ``my_sqluuid_type``. The kind is a wire
# contract (§3), so the identifier is declared whole and the kind is derived
# from that declaration: ``KIND_RESERVED`` is data, not behaviour, so no class
# overrides ``kind()`` and class name, kind and formatter entry keep one source.
#
# The loop walks this package's own modules rather than an exported name list,
# for the reason the sqlite package's note gives: a hand-maintained list can
# only ever be out of date, and a node that is defined but not re-exported here
# (the SHOW family) would silently keep the split spelling.
import importlib as _importlib
import pkgutil as _pkgutil

from rhosocial.activerecord.backend.expression.core import BaseExpression as _BaseExpression

for _module_info in _pkgutil.walk_packages(__path__, prefix=__name__ + ".", onerror=lambda _error: None):
    _module = _importlib.import_module(_module_info.name)
    for _value in vars(_module).values():
        if (
            isinstance(_value, type)
            and issubclass(_value, _BaseExpression)
            and _value.__name__.startswith("MySQL")
            and _value.__module__ == _module_info.name
        ):
            _value.KIND_RESERVED = ("MySQL",)
del _module_info, _module, _value, _importlib, _pkgutil, _BaseExpression
