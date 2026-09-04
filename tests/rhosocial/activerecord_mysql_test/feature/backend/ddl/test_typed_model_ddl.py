# tests/rhosocial/activerecord_mysql_test/feature/backend/ddl/test_typed_model_ddl.py
"""Cross-backend UseSqlType demonstration — MySQL rendering.

The shared ``TypedUser`` model (core generic types) renders MySQL-native SQL
without any per-dialect string mappings. Dialect instantiation needs no DB
server; only ``to_sql()`` is exercised here.
"""

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.examples.ddl_types import TypedUser


def _render() -> str:
    sql, _ = TypedUser.generate_create_table(dialect=MySQLDialect()).to_sql()
    return sql


def test_mysql_typed_user_ddl_columns():
    sql = _render()
    assert "CREATE TABLE `typed_users`" in sql
    assert "`id` INT PRIMARY KEY AUTO_INCREMENT" in sql
    assert "`username` VARCHAR(100) NOT NULL" in sql
    assert "`email` VARCHAR(255) NOT NULL" in sql
    assert "`is_active` TINYINT(1) NOT NULL" in sql
    assert "`balance` DECIMAL(10, 2)" in sql
    assert "`birthday` DATE" in sql
    assert "`created_at` DATETIME NOT NULL" in sql
    assert "`bio` TEXT" in sql
    assert "`metadata` JSON" in sql
    assert "`big_counter` BIGINT" in sql
    assert "`avatar` BLOB" in sql
    assert "`wake_up_time` TIME" in sql


def test_mysql_typed_user_no_per_dialect_string_keys():
    for _field_name, marker in TypedUser.__table_field_sql_types__.items():
        assert not hasattr(marker, "dialect_types")
        assert marker.data_type is not None