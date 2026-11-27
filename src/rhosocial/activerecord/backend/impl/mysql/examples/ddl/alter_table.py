"""
Alter table statements - ADD_COLUMN.

Note: MySQL supports multiple actions in a single ALTER TABLE statement,
but for simplicity we demonstrate individual operations.

Note: MODIFY COLUMN is a MySQL-specific feature. The MySQL dialect's
format_modify_column_action is not yet implemented, so this example
only demonstrates ADD_COLUMN.
"""
from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)

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

drop_orders = DropTableStatement(dialect=dialect, table=Table(dialect, "orders"), if_exists=True)
sql, params = drop_orders.to_sql()
backend.execute(sql, params)

drop_table = DropTableStatement(dialect=dialect, table=Table(dialect, "users"), if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    columns=[
        ColumnDefinition(
            "id",
            integer_auto_increment_parts(None, "INT")[0],
            constraints=[
                ColumnConstraint(None, branch=ColumnPrimaryKeyConstraint(None)),
                ColumnConstraint(None, branch=ColumnNotNullConstraint(None)),
            ],
         attributes=integer_auto_increment_parts(None, "INT")[1]),
        ColumnDefinition("name", "VARCHAR(100)"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, "users"),
    columns=["name"],
    source=ValuesSource(
        dialect,
        [[Literal(dialect, "Alice")]],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, "users"),
    columns=["name"],
    source=ValuesSource(
        dialect,
        [[Literal(dialect, "Alice")]],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import AlterTableStatement  # noqa: E402
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddColumnAction  # noqa: E402
from rhosocial.activerecord.backend.expression.objects import Table

add_col_action = AddColumnAction(
    dialect=dialect,
    column=ColumnDefinition(
        name="email",
        data_type="VARCHAR(100)",
    ),
)

add_col_expr = AlterTableStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    action=add_col_action,
)

sql, params = add_col_expr.to_sql()
print(f"SQL (Add Column email): {sql}")
print(f"Params: {params}")

backend.execute(sql, params)
print("Column email added successfully")

add_age_action = AddColumnAction(
    dialect=dialect,
    column=ColumnDefinition(
        "age",
        "INT",
        constraints=[
            ColumnConstraint(
                None,
                branch=ColumnDefaultConstraint(None, Literal(dialect, 0))
                ),
                ],
                ),
            )

add_age_expr = AlterTableStatement(
    dialect=dialect,
    table=Table(dialect, "users"),
    action=add_age_action,
)

sql, params = add_age_expr.to_sql()
print(f"SQL (Add Column age): {sql}")
print(f"Params: {params}")

backend.execute(sql, params)
print("Column age added successfully")

# ============================================================
# SECTION: Execution (verify alterations)
# ============================================================

# Verify using introspector
columns = backend.introspector.list_columns("users")
print("Table structure after alterations:")
for col in columns:
    print(f"  {col}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
