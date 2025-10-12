"""
Test the namespace behavior after removing src/rhosocial/__init__.py
This test verifies that the namespace package functionality still works correctly
without the init file in this extension package.
"""

import pytest
import sys
from pathlib import Path

# Add src and tests to Python path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))


def test_can_import_main_activerecord():
    """Test that we can import the main activerecord package"""
    import rhosocial.activerecord
    assert rhosocial.activerecord is not None
    assert hasattr(rhosocial.activerecord, '__file__')


def test_can_import_mysql_backend():
    """Test that we can import the MySQL backend from this package"""
    import rhosocial.activerecord.backend.impl.mysql.backend
    assert rhosocial.activerecord.backend.impl.mysql.backend is not None
    assert hasattr(rhosocial.activerecord.backend.impl.mysql.backend, '__file__')


def test_mysql_backend_is_in_same_namespace():
    """Test that MySQL backend is accessible under the same namespace as main package"""
    import rhosocial.activerecord
    import rhosocial.activerecord.backend.impl.mysql
    
    # Verify that mysql is available in the backend implementation namespace
    assert hasattr(rhosocial.activerecord.backend.impl, 'mysql')
    assert rhosocial.activerecord.backend.impl.mysql is not None


def test_can_access_mysql_classes():
    """Test that we can access specific MySQL classes"""
    from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
    from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
    
    # Test that classes exist and are of correct type
    assert MySQLBackend is not None
    assert MySQLConnectionConfig is not None
    assert isinstance(MySQLBackend, type)
    assert isinstance(MySQLConnectionConfig, type)


def test_namespace_path_extension_not_needed():
    """Test that removing the __init__.py with namespace path extension doesn't break imports"""
    import rhosocial.activerecord
    import rhosocial.activerecord.backend.impl.mysql.backend
    
    # Both packages should be importable and functional
    main_module_file = rhosocial.activerecord.__file__
    mysql_module_file = rhosocial.activerecord.backend.impl.mysql.backend.__file__
    
    # Verify both modules have valid file paths
    assert main_module_file is not None
    assert mysql_module_file is not None
    assert main_module_file.endswith('__init__.py')
    assert mysql_module_file.endswith('backend.py')


def test_version_attributes():
    """Test that version attributes are accessible from both packages"""
    import rhosocial.activerecord
    import rhosocial.activerecord.backend.impl.mysql
    
    # Check main package version
    assert hasattr(rhosocial.activerecord, '__version__')
    main_version = rhosocial.activerecord.__version__
    print(f"Main package version: {main_version}")
    
    # Check MySQL backend version
    assert hasattr(rhosocial.activerecord.backend.impl.mysql, '__version__')
    mysql_version = rhosocial.activerecord.backend.impl.mysql.__version__
    print(f"MySQL backend version: {mysql_version}")
    
    # Verify they are valid version strings
    assert isinstance(main_version, str)
    assert isinstance(mysql_version, str)
    assert len(main_version) > 0
    assert len(mysql_version) > 0


if __name__ == "__main__":
    # Run the tests directly if executed as a script
    test_can_import_main_activerecord()
    print("SUCCESS: Main ActiveRecord import test passed")
    
    test_can_import_mysql_backend()
    print("SUCCESS: MySQL backend import test passed")
    
    test_mysql_backend_is_in_same_namespace()
    print("SUCCESS: Namespace functionality test passed")
    
    test_can_access_mysql_classes()
    print("SUCCESS: MySQL classes access test passed")
    
    test_namespace_path_extension_not_needed()
    print("SUCCESS: Namespace path extension removal test passed")
    
    test_version_attributes()
    print("SUCCESS: Version attributes test passed")
    
    print("\nAll namespace behavior tests passed!")