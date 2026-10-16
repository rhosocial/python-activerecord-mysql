"""
Aggregate queries with GROUP BY and HAVING.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = MySQLConnectionConfig(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE", "test"),
    username=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    charset="utf8mb4",
)
backend = MySQLBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.core import Literal  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)

drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, "sales"), if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, "sales"),
    columns=[
        ColumnDefinition(
            "id",
            "INT",
            constraints=[
                ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None, is_auto_increment=True)),
                ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
            ],
        ),
        ColumnDefinition("product", "VARCHAR(100)"),
        ColumnDefinition("quantity", "INT"),
        ColumnDefinition("price", "DECIMAL(10,2)"),
        ColumnDefinition("region", "VARCHAR(50)"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, "sales"),
    columns=["product", "quantity", "price", "region"],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, "Widget"), Literal(dialect, 10), Literal(dialect, 5.00), Literal(dialect, "North")],
            [Literal(dialect, "Widget"), Literal(dialect, 5), Literal(dialect, 5.00), Literal(dialect, "South")],
            [Literal(dialect, "Gadget"), Literal(dialect, 8), Literal(dialect, 10.00), Literal(dialect, "North")],
            [Literal(dialect, "Gadget"), Literal(dialect, 3), Literal(dialect, 10.00), Literal(dialect, "South")],
            [Literal(dialect, "Widget"), Literal(dialect, 7), Literal(dialect, 5.00), Literal(dialect, "East")],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    QueryStatement,
    Column,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.expression.functions import (  # noqa: E402
    avg,
    sum_,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate  # noqa: E402
from rhosocial.activerecord.backend.expression.objects import Table

# SUM and AVG are classed nodes, not a generic call carrying a name string:
# the identity of the aggregate travels on the node.
query = QueryStatement(
    dialect=dialect,
    select=[
        Column(dialect, "product"),
        sum_(dialect, Column(dialect, "quantity"), alias="total_qty"),
        avg(dialect, Column(dialect, "price"), alias="avg_price"),
    ],
    from_=Table(dialect, "sales"),
    group_by_having=GroupByHavingClause(
        dialect,
        group_by=[Column(dialect, "product")],
        having=ComparisonPredicate(
            dialect,
            ">",
            sum_(dialect, Column(dialect, "quantity")),
            Literal(dialect, 10),
        ),
    ),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f" {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
