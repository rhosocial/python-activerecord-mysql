# tests/rhosocial/activerecord_mysql_test/basic/test_crud.py
"""Basic CRUD Test Module for MySQL Backend

This module reuses core CRUD tests from rhosocial.activerecord_test.basic.test_crud
and adds MySQL-specific CRUD functionality tests.

All core test functions are imported and executed with MySQL-specific models
to ensure backend compatibility.
"""

import time
from decimal import Decimal
from datetime import datetime

import pytest

# Import core test functions for reuse
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user,
    test_create_user_with_invalid_data,
    test_find_user,
    test_find_nonexistent_user,
    test_update_user,
    test_update_with_invalid_data,
    test_delete_user,
    test_delete_nonexistent_user,
    test_create_user_with_defaults,
    test_user_state_tracking,
    test_user_dirty_tracking,
    test_user_refresh,
    test_user_timestamps,
)

# Import MySQL-specific test fixtures - needed as fixture, do not remove
from .fixtures.models import (
    user_class,
    type_case_class,
    validated_user_class,
    validated_field_user_class,
    type_test_class
)


# Core test functions are automatically executed by pytest when imported
# The imported functions will use the MySQL-specific fixtures defined above

# Additional MySQL-specific CRUD tests


def test_mysql_decimal_precision(user_class):
    """Test MySQL DECIMAL type precision handling"""
    user = user_class(
        username="decimal_test",
        email="decimal@test.com",
        age=30,
        balance=Decimal("99999.99")
    )
    user.save()

    retrieved = user_class.find_one(user.id)
    assert retrieved.balance == Decimal("99999.99")
    assert isinstance(retrieved.balance, Decimal)


def test_mysql_boolean_handling(validated_field_user_class):
    """Test MySQL boolean field handling (TINYINT vs BOOLEAN)"""
    user = validated_field_user_class(
        username="booltest",
        email="bool@test.com",
        age=25,
        balance=Decimal("100.00"),
        is_active=True
    )
    user.save()

    retrieved = validated_field_user_class.find_one(user.id)
    assert retrieved.is_active is True
    assert isinstance(retrieved.is_active, bool)

    # Test boolean update
    retrieved.is_active = False
    retrieved.save()

    updated = validated_field_user_class.find_one(user.id)
    assert updated.is_active is False


def test_mysql_enum_field_handling(validated_field_user_class):
    """Test MySQL ENUM field type handling"""
    user = validated_field_user_class(
        username="enumtest",
        email="enum@test.com",
        age=30,
        balance=Decimal("200.00"),
        status="active"
    )
    user.save()

    retrieved = validated_field_user_class.find_one(user.id)
    assert retrieved.status == "active"

    # Test enum value change
    retrieved.status = "inactive"
    retrieved.save()

    updated = validated_field_user_class.find_one(user.id)
    assert updated.status == "inactive"

    # Test invalid enum value handling should be done in validation tests


def test_mysql_auto_increment_behavior(user_class):
    """Test MySQL AUTO_INCREMENT behavior"""
    # Create multiple users and verify ID assignment
    user1 = user_class(
        username="autoincr1",
        email="auto1@test.com",
        age=25,
        balance=Decimal("100.00")
    )
    user1.save()
    first_id = user1.id

    user2 = user_class(
        username="autoincr2",
        email="auto2@test.com",
        age=26,
        balance=Decimal("200.00")
    )
    user2.save()
    second_id = user2.id

    assert second_id > first_id
    assert first_id is not None
    assert second_id is not None


def test_mysql_datetime_precision(user_class):
    """Test MySQL DATETIME field precision"""
    current_time = datetime.now()

    user = user_class(
        username="timetest",
        email="time@test.com",
        age=30,
        balance=Decimal("150.00")
    )
    user.save()

    # Check that created_at and updated_at are set
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.created_at <= user.updated_at

    # Update and check timestamp changes
    original_created = user.created_at
    original_updated = user.updated_at

    time.sleep(0.1)  # Ensure time difference
    user.username = "timetest_updated"
    user.save()

    assert user.created_at == original_created  # Should not change
    assert user.updated_at > original_updated  # Should be updated


def test_mysql_large_text_handling(user_class):
    """Test handling of large text values in MySQL"""
    # Create a user with a long email (testing VARCHAR limits)
    long_email = "a" * 200 + "@test.com"  # 208 chars, should fit in VARCHAR(255)

    user = user_class(
        username="largetext",
        email=long_email,
        age=30,
        balance=Decimal("100.00")
    )
    user.save()

    retrieved = user_class.find_one(user.id)
    assert retrieved.email == long_email
    assert len(retrieved.email) == 208


def test_mysql_null_handling(user_class):
    """Test MySQL NULL value handling"""
    user = user_class(
        username="nulltest",
        email="null@test.com",
        age=None,  # Optional field, should allow NULL
        balance=Decimal("100.00")
    )
    user.save()

    retrieved = user_class.find_one(user.id)
    assert retrieved.age is None
    assert retrieved.username == "nulltest"
    assert retrieved.email == "null@test.com"


def test_mysql_transaction_behavior(user_class):
    """Test MySQL transaction behavior during CRUD operations"""
    # This test verifies that each operation commits properly
    initial_count = len(user_class.find_all())

    # Create user
    user = user_class(
        username="transaction_test",
        email="trans@test.com",
        age=30,
        balance=Decimal("100.00")
    )
    user.save()

    # Verify immediately visible (auto-commit behavior)
    current_count = len(user_class.find_all())
    assert current_count == initial_count + 1

    # Delete user
    user.delete()

    # Verify deletion committed
    final_count = len(user_class.find_all())
    assert final_count == initial_count