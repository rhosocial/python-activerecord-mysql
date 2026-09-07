# DDL 特征 Spec

MySQL 实现了核心 DDL 特征认领协议（`dialect.build_spec`）。本章说明 MySQL 方言
认领哪些 Spec、如何翻译，以及它新增的 MySQL 特定 Spec。

## 认领机制

`Model.generate_create_table(dialect)` 时，生成器把每个声明的 Spec 交给
`dialect.build_spec(spec)`：

- **接受** → 方言构造并返回表达式层实例（`TableConstraint` / `IndexDefinition` /
  `ColumnConstraint` / `MySQLPartitionBy*`），进入 `CreateTableExpression`；
- **不接受** → 返回 `None`，该 Spec 被静默忽略。

接受范围由 MySQL 方言自行决定。认为忽略会丢约束时，可在 `build_spec` 内抛错。

## 通用 Spec

全部通用 Spec 由核心默认翻译认领：

| Spec | MySQL 翻译 |
|------|------------|
| `CheckSpec` | `TableConstraint(CHECK)`，惰性谓词生成时求值 |
| `UniqueSpec` | `TableConstraint(UNIQUE)` |
| `NotNullSpec` | `ColumnConstraint(NOT NULL)` |
| `PrimaryKeySpec` | 单列→列级 PK / 复合→表级 PK |
| `DefaultSpec` | `ColumnConstraint(DEFAULT)`，参数化 `Literal` |
| `ForeignKeySpec` | `ForeignKeyConstraint`（含参照动作） |
| `IndexSpec` | `IndexDefinition`；部分索引条件受部分索引能力门控 |
| `JsonColumnSpec` | 列类型补丁 → `JsonType`，渲染为原生 `JSON` |

## MySQL 特定 Spec

定义于 `rhosocial.activerecord.backend.impl.mysql.ddl_spec`；以 `isinstance`
认领、由 `MySQLDDLSpecMixin` 翻译。仅 MySQL 方言认领——其他后端全部忽略。

### 分区 Spec

```python
from rhosocial.activerecord.backend.impl.mysql.ddl_spec import (
    MySQLRangePartition, MySQLListPartition, MySQLHashPartition,
    MySQLPartitionDefinitionSpec, MySQLPartitionBound,
)

class Orders(ActiveRecord):
    __table_partition__ = [
        MySQLRangePartition("created_at", [
            MySQLPartitionDefinitionSpec("p2026", less_than=[MySQLPartitionBound(2027)]),
            MySQLPartitionDefinitionSpec("p_max", less_than=[MySQLPartitionBound("MAXVALUE")]),
        ]),
        # MySQLListPartition("region", [
        #     MySQLPartitionDefinitionSpec("p_east", in_values=[MySQLPartitionBound("EAST")]),
        # ]),
        # MySQLHashPartition("id", 4),
    ]
```

翻译为 MySQL 分区表达式层（`MySQLPartitionByRange` / `ByList` / `ByHash`）并挂到
`CreateTableExpression.partition`；渲染 DDL 与分区生命周期管理见
[分区](partition.md)。

### 原生类型列 Spec

```python
from rhosocial.activerecord.backend.impl.mysql.ddl_spec import (
    MySQLVectorColumnSpec,   # VECTOR(dim)，MySQL 9.0+
    MySQLSpatialColumnSpec,  # GEOMETRY/POINT/... 可选 SRID
    MySQLSetColumnSpec,      # SET('a','b',...)
)

class T(ActiveRecord):
    __table_constraints__ = [
        MySQLVectorColumnSpec("embedding", dim=384),
        MySQLSpatialColumnSpec("location", kind="POINT", srid=4326),
        MySQLSetColumnSpec("tags", ["a", "b", "c"]),
    ]
```

渲染为 `VECTOR(384)`、`POINT SRID 4326`、`SET('a','b','c')`。
`MySQLVectorColumnSpec` 仅在方言报告支持向量类型时认领，否则忽略。
