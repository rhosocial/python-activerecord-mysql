"""
FOR UPDATE Row Locking - MySQL.

This example demonstrates:
1. SELECT ... FOR UPDATE to lock rows
2. Preventing dirty reads in concurrent scenarios
3. Using SKIP LOCKED for non-blocking locks
4. NOWAIT for immediate failure on lock
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import os
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig

config = MySQLConnectionConfig(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    database=os.getenv('MYSQL_DATABASE', 'test'),
    username=os.getenv('MYSQL_USERNAME', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
)
backend = MySQLBackend(connection_config=config)
backend.connect()
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
    QueryExpression,
    TableExpression,
    UpdateExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
dml_options = ExecutionOptions(stmt_type=StatementType.DML)

drop_table = DropTableExpression(dialect=dialect, table_name='accounts', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='accounts',
    columns=[
        ColumnDefinition('id', 'INT', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'VARCHAR(100)', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('balance', 'DECIMAL(10,2)', constraints=[
            ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0),
        ]),
    ],
    if_not_exists=True,
    dialect_options={'engine': 'InnoDB'},
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert_expr = InsertExpression(
    dialect=dialect,
    into='accounts',
    columns=['name', 'balance'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Alice'), Literal(dialect, 1000)],
        [Literal(dialect, 'Bob'), Literal(dialect, 500)],
    ]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: SELECT FOR UPDATE
# ============================================================
# Lock rows to prevent concurrent modifications

# In a transaction, select with FOR UPDATE
with backend.transaction():
    # Lock Alice's row using ForUpdateClause
    lock_query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'balance')],
        from_=TableExpression(dialect, 'accounts'),
        where=ComparisonPredicate(dialect, '=', Column(dialect, 'name'), Literal(dialect, 'Alice')),
        for_update=ForUpdateClause(dialect),
    )
    sql, params = lock_query.to_sql()
    result = backend.execute(sql, params, options=dql_options)
    print(f"Locked row: {result.data}")

    # Update the balance
    update_expr = UpdateExpression(
        dialect=dialect,
        table='accounts',
        assignments={'balance': Literal(dialect, 900)},
        where=ComparisonPredicate(dialect, '=', Column(dialect, 'name'), Literal(dialect, 'Alice')),
    )
    sql, params = update_expr.to_sql()
    backend.execute(sql, params, options=dml_options)

# The lock is released after commit

# ============================================================
# SECTION: FOR UPDATE with WHERE Conditions
# ============================================================
# Lock specific rows based on conditions

with backend.transaction():
    lock_query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'balance')],
        from_=TableExpression(dialect, 'accounts'),
        where=ComparisonPredicate(dialect, '>', Column(dialect, 'balance'), Literal(dialect, 500)),
        for_update=ForUpdateClause(dialect),
    )
    sql, params = lock_query.to_sql()
    result = backend.execute(sql, params, options=dql_options)
    print(f"Locked high balance accounts: {len(result.data)} rows")

# ============================================================
# SECTION: SKIP LOCKED (MySQL 8.0+)
# ============================================================
# Skip locked rows instead of waiting

skip_query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'balance')],
    from_=TableExpression(dialect, 'accounts'),
    for_update=ForUpdateClause(dialect, skip_locked=True),
)
sql, params = skip_query.to_sql()
print(f"SKIP LOCKED SQL: {sql}")
result = backend.execute(sql, params, options=dql_options)
print(f"SKIP LOCKED result: {result.data}")

# ============================================================
# SECTION: NOWAIT (MySQL 8.0+)
# ============================================================
# Fail immediately if rows are locked

try:
    nowait_query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'balance')],
        from_=TableExpression(dialect, 'accounts'),
        where=ComparisonPredicate(dialect, '=', Column(dialect, 'name'), Literal(dialect, 'Alice')),
        for_update=ForUpdateClause(dialect, nowait=True),
    )
    sql, params = nowait_query.to_sql()
    result = backend.execute(sql, params, options=dql_options)
    print(f"NOWAIT result: {result.data}")
except Exception as e:
    print(f"NOWAIT failed (expected if locked): {e}")

# ============================================================
# SECTION: Lock Modes
# ============================================================
# FOR UPDATE - exclusive lock (write lock)
# FOR SHARE - shared lock (read lock)

# Use MySQLForUpdateClause with MySQLLockStrength.SHARE for FOR SHARE
from rhosocial.activerecord.backend.impl.mysql.expression import (
    MySQLForUpdateClause,
    MySQLLockStrength,
)

with backend.transaction():
    share_query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'id'), Column(dialect, 'name'), Column(dialect, 'balance')],
        from_=TableExpression(dialect, 'accounts'),
        for_update=MySQLForUpdateClause(dialect, strength=MySQLLockStrength.SHARE),
    )
    sql, params = share_query.to_sql()
    result = backend.execute(sql, params, options=dql_options)
    print(f"FOR SHARE result: {len(result.data)} rows")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table_name='accounts', if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use ForUpdateClause with QueryExpression for SELECT ... FOR UPDATE
# 2. ForUpdateClause(dialect, skip_locked=True) for SKIP LOCKED (MySQL 8.0+)
# 3. ForUpdateClause(dialect, nowait=True) for NOWAIT (MySQL 8.0+)
# 4. Use MySQLForUpdateClause with MySQLLockStrength.SHARE for FOR SHARE (MySQL 8.0+)
# 5. Requires InnoDB engine
# 6. Locks released on COMMIT/ROLLBACK
