# tests/rhosocial/activerecord_mysql_test/feature/backend/test_mysql_ddl_features.py
"""
MySQL DDL features tests.

This module tests MySQL-specific DDL features including:
- Storage options (ENGINE, CHARSET, COLLATE)
- Table-level COMMENT
- Column-level COMMENT
- AUTO_INCREMENT
- Inline index definitions
- ENUM type helper
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
from rhosocial.activerecord.backend.impl.mysql.types import MySQLEnumType, MySQLSetType


class TestMySQLStorageOptions:
    """Tests for MySQL storage options (ENGINE, CHARSET, COLLATE)."""

    def test_engine_option(self):
        """Test ENGINE storage option."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test_table',
            columns=columns,
            storage_options={'ENGINE': 'InnoDB'}
        )
        sql, params = expr.to_sql()
        assert 'ENGINE=InnoDB' in sql

    def test_charset_option(self):
        """Test DEFAULT CHARSET storage option."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test_table',
            columns=columns,
            storage_options={'DEFAULT CHARSET': 'utf8mb4'}
        )
        sql, params = expr.to_sql()
        assert 'DEFAULT CHARSET=utf8mb4' in sql

    def test_collate_option(self):
        """Test COLLATE storage option."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test_table',
            columns=columns,
            storage_options={'COLLATE': 'utf8mb4_unicode_ci'}
        )
        sql, params = expr.to_sql()
        assert 'COLLATE=utf8mb4_unicode_ci' in sql

    def test_multiple_storage_options(self):
        """Test multiple storage options combined."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test_table',
            columns=columns,
            storage_options={
                'ENGINE': 'InnoDB',
                'DEFAULT CHARSET': 'utf8mb4',
                'COLLATE': 'utf8mb4_unicode_ci'
            }
        )
        sql, params = expr.to_sql()
        assert 'ENGINE=InnoDB' in sql
        assert 'DEFAULT CHARSET=utf8mb4' in sql
        assert 'COLLATE=utf8mb4_unicode_ci' in sql

    def test_storage_options_with_if_not_exists(self):
        """Test storage options with IF NOT EXISTS."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test_table',
            columns=columns,
            if_not_exists=True,
            storage_options={'ENGINE': 'InnoDB'}
        )
        sql, params = expr.to_sql()
        assert 'IF NOT EXISTS' in sql
        assert 'ENGINE=InnoDB' in sql


class TestMySQLTableComment:
    """Tests for MySQL table-level COMMENT."""

    def test_table_comment(self):
        """Test table-level COMMENT."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            dialect_options={'comment': '用户信息表'}
        )
        sql, params = expr.to_sql()
        assert "COMMENT '用户信息表'" in sql

    def test_table_comment_with_storage_options(self):
        """Test table COMMENT with storage options."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            storage_options={
                'ENGINE': 'InnoDB',
                'DEFAULT CHARSET': 'utf8mb4'
            },
            dialect_options={'comment': '用户信息表'}
        )
        sql, params = expr.to_sql()
        assert 'ENGINE=InnoDB' in sql
        assert 'DEFAULT CHARSET=utf8mb4' in sql
        assert "COMMENT '用户信息表'" in sql

    def test_table_comment_special_characters(self):
        """Test table COMMENT with special characters."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test',
            columns=columns,
            dialect_options={'comment': "测试's表"}
        )
        sql, params = expr.to_sql()
        assert "COMMENT" in sql


class TestMySQLColumnComment:
    """Tests for MySQL column-level COMMENT."""

    def test_column_comment(self):
        """Test column-level COMMENT."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ], comment='主键ID'),
            ColumnDefinition('name', 'VARCHAR(100)', comment='用户名')
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns
        )
        sql, params = expr.to_sql()
        assert "COMMENT '主键ID'" in sql
        assert "COMMENT '用户名'" in sql

    def test_column_comment_with_table_comment(self):
        """Test column COMMENT with table COMMENT."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ], comment='主键'),
            ColumnDefinition('name', 'VARCHAR(100)', comment='名称')
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            dialect_options={'comment': '用户表'}
        )
        sql, params = expr.to_sql()
        assert "COMMENT '主键'" in sql
        assert "COMMENT '名称'" in sql
        assert "COMMENT '用户表'" in sql


class TestMySQLAutoIncrement:
    """Tests for MySQL AUTO_INCREMENT."""

    def test_auto_increment_primary_key(self):
        """Test AUTO_INCREMENT with PRIMARY KEY."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'BIGINT', constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns
        )
        sql, params = expr.to_sql()
        assert 'AUTO_INCREMENT' in sql
        assert 'PRIMARY KEY' in sql

    def test_auto_increment_with_comment(self):
        """Test AUTO_INCREMENT with column COMMENT."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'BIGINT', constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ], comment='自增主键')
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns
        )
        sql, params = expr.to_sql()
        assert 'AUTO_INCREMENT' in sql
        assert "COMMENT '自增主键'" in sql

    def test_auto_increment_not_null(self):
        """Test that AUTO_INCREMENT requires NOT NULL."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'BIGINT', constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='test',
            columns=columns
        )
        sql, params = expr.to_sql()
        assert 'NOT NULL' in sql
        assert 'AUTO_INCREMENT' in sql


class TestMySQLInlineIndex:
    """Tests for MySQL inline index definitions."""

    def test_simple_index(self):
        """Test simple INDEX definition."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('name', 'VARCHAR(100)')
        ]
        indexes = [
            IndexDefinition('idx_name', ['name'])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            indexes=indexes
        )
        sql, params = expr.to_sql()
        assert 'INDEX `idx_name`' in sql
        assert '(`name`)' in sql

    def test_unique_index(self):
        """Test UNIQUE INDEX definition."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('email', 'VARCHAR(100)')
        ]
        indexes = [
            IndexDefinition('idx_email', ['email'], unique=True)
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            indexes=indexes
        )
        sql, params = expr.to_sql()
        assert 'UNIQUE INDEX' in sql
        assert 'idx_email' in sql

    def test_composite_index(self):
        """Test composite index on multiple columns."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('user_id', 'INT'),
            ColumnDefinition('created_at', 'DATETIME')
        ]
        indexes = [
            IndexDefinition('idx_user_created', ['user_id', 'created_at'])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='orders',
            columns=columns,
            indexes=indexes
        )
        sql, params = expr.to_sql()
        assert '`user_id`, `created_at`' in sql or '`user_id`,`created_at`' in sql

    def test_index_with_type(self):
        """Test INDEX with USING clause."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('name', 'VARCHAR(100)')
        ]
        indexes = [
            IndexDefinition('idx_name', ['name'], type='BTREE')
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            indexes=indexes
        )
        sql, params = expr.to_sql()
        assert 'USING BTREE' in sql

    def test_hash_index(self):
        """Test HASH index type."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('key', 'VARCHAR(100)')
        ]
        indexes = [
            IndexDefinition('idx_key', ['key'], type='HASH')
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='cache',
            columns=columns,
            indexes=indexes
        )
        sql, params = expr.to_sql()
        assert 'USING HASH' in sql

    def test_multiple_indexes(self):
        """Test multiple inline indexes."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('email', 'VARCHAR(100)'),
            ColumnDefinition('username', 'VARCHAR(50)')
        ]
        indexes = [
            IndexDefinition('idx_email', ['email'], unique=True),
            IndexDefinition('idx_username', ['username'])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            indexes=indexes
        )
        sql, params = expr.to_sql()
        assert 'UNIQUE INDEX `idx_email`' in sql
        assert 'INDEX `idx_username`' in sql


class TestMySQLEnumType:
    """Tests for MySQL ENUM type helper."""

    def test_simple_enum(self):
        """Test simple ENUM definition."""
        enum_type = MySQLEnumType(['pending', 'processing', 'completed'])
        sql = enum_type.to_sql()
        assert sql == "ENUM('pending','processing','completed')"

    def test_enum_with_charset(self):
        """Test ENUM with CHARACTER SET."""
        enum_type = MySQLEnumType(['active', 'inactive'], charset='utf8mb4')
        sql = enum_type.to_sql()
        assert 'CHARACTER SET utf8mb4' in sql

    def test_enum_with_collation(self):
        """Test ENUM with COLLATE."""
        enum_type = MySQLEnumType(['a', 'b'], collation='utf8mb4_bin')
        sql = enum_type.to_sql()
        assert 'COLLATE utf8mb4_bin' in sql

    def test_enum_with_charset_and_collation(self):
        """Test ENUM with both CHARACTER SET and COLLATE."""
        enum_type = MySQLEnumType(
            ['pending', 'done'],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        sql = enum_type.to_sql()
        assert 'CHARACTER SET utf8mb4' in sql
        assert 'COLLATE utf8mb4_unicode_ci' in sql

    def test_enum_str_representation(self):
        """Test ENUM string representation."""
        enum_type = MySQLEnumType(['yes', 'no'])
        assert str(enum_type) == "ENUM('yes','no')"

    def test_enum_repr(self):
        """Test ENUM repr."""
        enum_type = MySQLEnumType(['a', 'b'])
        repr_str = repr(enum_type)
        assert 'MySQLEnumType' in repr_str
        assert 'a' in repr_str

    def test_enum_empty_values_raises_error(self):
        """Test that empty values list raises ValueError."""
        with pytest.raises(ValueError, match="ENUM must have at least one value"):
            MySQLEnumType([])

    def test_enum_in_column_definition(self):
        """Test ENUM type used in column definition."""
        dialect = MySQLDialect()
        status_enum = MySQLEnumType(['draft', 'published', 'archived'])
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('status', status_enum.to_sql(), constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL)
            ])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='articles',
            columns=columns
        )
        sql, params = expr.to_sql()
        assert "ENUM('draft','published','archived')" in sql


class TestMySQLSetType:
    """Tests for MySQL SET type helper."""

    def test_simple_set(self):
        """Test simple SET definition."""
        set_type = MySQLSetType(['read', 'write', 'execute'])
        sql = set_type.to_sql()
        assert sql == "SET('read','write','execute')"

    def test_set_with_charset(self):
        """Test SET with CHARACTER SET."""
        set_type = MySQLSetType(['tag1', 'tag2'], charset='utf8mb4')
        sql = set_type.to_sql()
        assert 'CHARACTER SET utf8mb4' in sql

    def test_set_with_collation(self):
        """Test SET with COLLATE."""
        set_type = MySQLSetType(['a', 'b'], collation='utf8mb4_bin')
        sql = set_type.to_sql()
        assert 'COLLATE utf8mb4_bin' in sql

    def test_set_str_representation(self):
        """Test SET string representation."""
        set_type = MySQLSetType(['x', 'y'])
        assert str(set_type) == "SET('x','y')"

    def test_set_repr(self):
        """Test SET repr."""
        set_type = MySQLSetType(['a', 'b'])
        repr_str = repr(set_type)
        assert 'MySQLSetType' in repr_str

    def test_set_empty_values_raises_error(self):
        """Test that empty values list raises ValueError."""
        with pytest.raises(ValueError, match="SET must have at least one value"):
            MySQLSetType([])


class TestMySQLTableConstraints:
    """Tests for MySQL table-level constraints."""

    def test_primary_key_constraint(self):
        """Test PRIMARY KEY table constraint."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT'),
            ColumnDefinition('name', 'VARCHAR(100)')
        ]
        table_constraints = [
            TableConstraint(TableConstraintType.PRIMARY_KEY, columns=['id'])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            table_constraints=table_constraints
        )
        sql, params = expr.to_sql()
        assert 'PRIMARY KEY (`id`)' in sql

    def test_unique_constraint(self):
        """Test UNIQUE table constraint."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('id', 'INT', constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
            ]),
            ColumnDefinition('email', 'VARCHAR(100)')
        ]
        table_constraints = [
            TableConstraint(TableConstraintType.UNIQUE, columns=['email'])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            table_constraints=table_constraints
        )
        sql, params = expr.to_sql()
        assert 'UNIQUE (`email`)' in sql

    def test_composite_primary_key(self):
        """Test composite PRIMARY KEY."""
        dialect = MySQLDialect()
        columns = [
            ColumnDefinition('user_id', 'INT'),
            ColumnDefinition('role_id', 'INT')
        ]
        table_constraints = [
            TableConstraint(TableConstraintType.PRIMARY_KEY, columns=['user_id', 'role_id'])
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='user_roles',
            columns=columns,
            table_constraints=table_constraints
        )
        sql, params = expr.to_sql()
        assert 'PRIMARY KEY' in sql
        assert '`user_id`' in sql
        assert '`role_id`' in sql


class TestMySQLDropTable:
    """Tests for MySQL DROP TABLE."""

    def test_drop_table_if_exists(self):
        """Test DROP TABLE IF EXISTS."""
        dialect = MySQLDialect()
        expr = DropTableExpression(
            dialect=dialect,
            table_name='test_table',
            if_exists=True
        )
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS `test_table`'
        assert params == ()

    def test_drop_table_without_if_exists(self):
        """Test DROP TABLE without IF EXISTS."""
        dialect = MySQLDialect()
        expr = DropTableExpression(
            dialect=dialect,
            table_name='test_table',
            if_exists=False
        )
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE `test_table`'
        assert params == ()


class TestMySQLCompleteTableCreation:
    """Tests for complete MySQL table creation with all features."""

    def test_complete_table_creation(self):
        """Test complete table creation with all MySQL features."""
        dialect = MySQLDialect()
        status_enum = MySQLEnumType(['active', 'inactive', 'deleted'])
        
        columns = [
            ColumnDefinition(
                'id',
                'BIGINT',
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
                ],
                comment='Primary key'
            ),
            ColumnDefinition(
                'name',
                'VARCHAR(100)',
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
                comment='User name'
            ),
            ColumnDefinition(
                'email',
                'VARCHAR(255)',
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
                comment='Email address'
            ),
            ColumnDefinition(
                'status',
                status_enum.to_sql(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
                comment='User status'
            ),
            ColumnDefinition('created_at', 'DATETIME', comment='Creation timestamp')
        ]
        
        indexes = [
            IndexDefinition('idx_email', ['email'], unique=True),
            IndexDefinition('idx_status', ['status'])
        ]
        
        expr = CreateTableExpression(
            dialect=dialect,
            table_name='users',
            columns=columns,
            indexes=indexes,
            if_not_exists=True,
            storage_options={
                'ENGINE': 'InnoDB',
                'DEFAULT CHARSET': 'utf8mb4',
                'COLLATE': 'utf8mb4_unicode_ci'
            },
            dialect_options={'comment': 'User information table'}
        )
        
        sql, params = expr.to_sql()
        
        # Verify all components are present
        assert 'CREATE TABLE IF NOT EXISTS' in sql
        assert '`users`' in sql
        assert 'BIGINT' in sql
        assert 'NOT NULL' in sql
        assert 'PRIMARY KEY' in sql
        assert 'AUTO_INCREMENT' in sql
        assert 'VARCHAR(100)' in sql
        assert 'VARCHAR(255)' in sql
        assert "ENUM('active','inactive','deleted')" in sql
        assert 'DATETIME' in sql
        assert 'UNIQUE INDEX `idx_email`' in sql
        assert 'INDEX `idx_status`' in sql
        assert 'ENGINE=InnoDB' in sql
        assert 'DEFAULT CHARSET=utf8mb4' in sql
        assert 'COLLATE=utf8mb4_unicode_ci' in sql
        assert "COMMENT 'User information table'" in sql
        # Column comments
        assert "COMMENT 'Primary key'" in sql
        assert "COMMENT 'User name'" in sql
        assert "COMMENT 'Email address'" in sql
        assert "COMMENT 'User status'" in sql
        assert "COMMENT 'Creation timestamp'" in sql
