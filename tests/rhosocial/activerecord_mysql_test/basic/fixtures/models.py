# tests/rhosocial/activerecord_mysql_test/basic/fixtures/models.py
"""MySQL-specific test model fixtures for basic functionality

This module provides MySQL-specific test models that inherit from core test models
and are configured to work specifically with MySQL backends.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from rhosocial.activerecord_test.basic.fixtures.models import (
    User as BaseUser,
    TypeCase as BaseTypeCase,
    ValidatedUser as BaseValidatedUser,
    ValidatedFieldUser as BaseValidatedFieldUser,
    TypeTestModel as BaseTypeTest,
)
from rhosocial.activerecord_test.utils import create_active_record_fixture


class MySQLUser(BaseUser):
    """MySQL-specific user model for CRUD testing

    Inherits from the base User model and adds MySQL-specific configuration.
    Uses the schema defined in mysql56/mysql80 users.sql files.
    """
    __supported_backends__ = ["mysql"]
    __table_name__ = "users"

    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


class MySQLTypeCase(BaseTypeCase):
    """MySQL-specific type case model for field type testing

    Inherits from the base TypeCase model and adds MySQL-specific configuration.
    Can be extended with additional MySQL-specific field types if needed.
    """
    __supported_backends__ = ["mysql"]
    __table_name__ = "type_cases"

    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


class MySQLValidatedUser(BaseValidatedUser):
    """MySQL-specific validated user model for validation testing

    Inherits from the base ValidatedUser model and uses MySQL-specific
    validation features like CHECK constraints (MySQL 8.0+).
    """
    __supported_backends__ = ["mysql"]
    __table_name__ = "validated_users"

    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


class MySQLValidatedFieldUser(BaseValidatedFieldUser):
    """MySQL-specific validated field user model

    Uses the validated_field_users table schema with MySQL-specific
    data types like ENUM and DECIMAL.
    """
    __supported_backends__ = ["mysql"]
    __table_name__ = "validated_field_users"

    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


class MySQLTypeTest(BaseTypeTest):
    """MySQL-specific type test model for comprehensive data type testing

    Tests MySQL-specific data types including JSON (MySQL 8.0+) vs TEXT (MySQL 5.6),
    BOOLEAN vs TINYINT(1), and other MySQL-specific type handling.
    """
    __supported_backends__ = ["mysql"]
    __table_name__ = "type_tests"

    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


# Create MySQL-specific fixtures using the utility function
# These fixtures will automatically use MySQL backend configuration
user_class = create_active_record_fixture(MySQLUser)
type_case_class = create_active_record_fixture(MySQLTypeCase)
validated_user_class = create_active_record_fixture(MySQLValidatedUser)
validated_field_user_class = create_active_record_fixture(MySQLValidatedFieldUser)
type_test_class = create_active_record_fixture(MySQLTypeTest)