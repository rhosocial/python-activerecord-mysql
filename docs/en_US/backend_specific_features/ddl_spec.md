# DDL Feature Specs

MySQL implements the core DDL feature-spec claiming protocol
(`dialect.build_spec`). This chapter documents which Specs the MySQL dialect
claims, how it translates them, and the MySQL-specific Specs it adds.

## How claiming works

At `Model.generate_create_table(dialect)` time the generator hands each
declared Spec to `dialect.build_spec(spec)`:

- **Accepted** → the dialect builds and returns an expression-layer instance
  (`TableConstraint` / `IndexDefinition` / `ColumnConstraint` /
  `MySQLPartitionBy*`), which lands in the `CreateTableExpression`;
- **Not accepted** → returns `None`, and the Spec is silently ignored.

Acceptance scope is the MySQL dialect's own decision. A backend that
considers ignoring unsafe may raise inside `build_spec`.

## Generic Specs

All generic Specs are claimed and translated by the core default:

| Spec | MySQL translation |
|------|-------------------|
| `CheckSpec` | `TableConstraint(CHECK)`, lazy predicates evaluated at build time |
| `UniqueSpec` | `TableConstraint(UNIQUE)` |
| `NotNullSpec` | `ColumnConstraint(NOT NULL)` |
| `PrimaryKeySpec` | column-level PK (single) / table-level composite PK |
| `DefaultSpec` | `ColumnConstraint(DEFAULT)` with a parameterized `Literal` |
| `ForeignKeySpec` | `ForeignKeyConstraint` with referential actions |
| `IndexSpec` | `IndexDefinition`; partial conditions require partial-index support |
| `JsonColumnSpec` | column type patch → `JsonType`, rendered as native `JSON` |

## MySQL-specific Specs

Defined in `rhosocial.activerecord.backend.impl.mysql.ddl_spec`; claimed via
`isinstance` and translated by `MySQLDDLSpecMixin`. Only the MySQL dialect
claims these — every other backend ignores them.

### Partition Specs

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

Translated to the MySQL partition expression layer (`MySQLPartitionByRange` /
`ByList` / `ByHash`) and attached to `CreateTableExpression.partition`; see
[Partitioning](partition.md) for the rendered DDL and lifecycle management.

### Native-type Column Specs

```python
from rhosocial.activerecord.backend.impl.mysql.ddl_spec import (
    MySQLVectorColumnSpec,   # VECTOR(dim), MySQL 9.0+
    MySQLSpatialColumnSpec,  # GEOMETRY/POINT/... with optional SRID
    MySQLSetColumnSpec,      # SET('a','b',...)
)

class T(ActiveRecord):
    __table_constraints__ = [
        MySQLVectorColumnSpec("embedding", dim=384),
        MySQLSpatialColumnSpec("location", kind="POINT", srid=4326),
        MySQLSetColumnSpec("tags", ["a", "b", "c"]),
    ]
```

Rendered as `VECTOR(384)`, `POINT SRID 4326`, `SET('a','b','c')`.
`MySQLVectorColumnSpec` is claimed only when the dialect reports vector-type
support; otherwise it is ignored.
