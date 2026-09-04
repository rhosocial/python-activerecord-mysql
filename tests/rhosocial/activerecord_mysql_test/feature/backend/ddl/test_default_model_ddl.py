# tests/rhosocial/activerecord_mysql_test/feature/backend/ddl/test_default_model_ddl.py
"""Default-type model rendering — MySQL.

``DefaultUser`` declares plain Python types with no ``UseSqlType``; MySQL
derives the column types via its own suggestion mapping. Dialect
instantiation needs no DB server; only ``to_sql()`` is exercised here.
"""

from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.examples.ddl_default_types import DefaultUser


def _render() -> str:
    sql, _ = DefaultUser.generate_create_table(dialect=MySQLDialect()).to_sql()
    return sql


def test_default_user_has_no_explicit_sql_types():
    assert DefaultUser.__table_field_sql_types__ == {}


def test_mysql_default_user_ddl_columns():
    sql = _render()
    assert "CREATE TABLE `default_users`" in sql
    assert "`id` INT PRIMARY KEY AUTO_INCREMENT" in sql
    assert "`username` TEXT NOT NULL" in sql
    assert "`email` TEXT NOT NULL" in sql
    assert "`is_active` TINYINT NOT NULL" in sql
    assert "`balance` DOUBLE NOT NULL" in sql
    assert "`created_at` DATETIME NOT NULL" in sql
    assert "`metadata` TEXT NOT NULL" in sql
    assert "`avatar` BLOB NOT NULL" in sql
    assert "`birthday` DATE" in sql