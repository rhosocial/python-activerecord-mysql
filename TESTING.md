# Testing Guide for rhosocial-activerecord-mysql

This guide explains how to test the MySQL backend implementation using both MySQL-specific tests and the shared test suite from rhosocial-activerecord.

## Overview

The MySQL backend testing includes:
1. **Shared Test Suite**: Inherited from `rhosocial.activerecord_test` to ensure compatibility
2. **MySQL-Specific Tests**: Tests for MySQL-specific features and optimizations

## Prerequisites

### 1. Install Dependencies

```bash
# Install with test dependencies
pip install -e ".[test]"

# This installs:
# - rhosocial-activerecord[test] (includes shared test suite)
# - pytest and related tools
# - mysql-connector-python
```

### 2. MySQL Server Setup

Set up MySQL server for testing:

```bash
# Using Docker (recommended)
docker run -d \
  --name mysql-test \
  -e MYSQL_ROOT_PASSWORD=test_password \
  -e MYSQL_DATABASE=test_db \
  -p 3306:3306 \
  mysql:8.0

# Or use existing MySQL installation
mysql -u root -p -e "CREATE DATABASE test_db;"
```

### 3. Test Configuration

Create `tests/config.yml`:

```yaml
mysql:
  host: localhost
  port: 3306
  user: root
  password: test_password
  database: test_db
  charset: utf8mb4
  
test_settings:
  cleanup_after_test: true
  verbose: false
```

## Test Structure

The MySQL backend tests should follow this structure:

```
tests/
├── __init__.py
├── config.yml                           # MySQL connection config
├── conftest.py                         # Pytest configuration
├── test_mysql_backend.py               # MySQL-specific backend tests
├── test_mysql_types.py                 # MySQL data type tests
├── test_mysql_features.py              # MySQL-specific features
├── shared/                             # Shared test suite runners
│   ├── __init__.py
│   ├── test_basic.py                   # Run basic tests
│   ├── test_query.py                   # Run query tests
│   ├── test_relations.py               # Run relation tests
│   └── test_mixins.py                  # Run mixin tests
└── fixtures/                           # Test fixtures
    ├── __init__.py
    └── models.py
```

## Using the Shared Test Suite

### 1. Import and Run Basic Tests

```python
# tests/shared/test_basic.py
import pytest
from rhosocial.activerecord_test.basic.test_crud import TestCRUD
from rhosocial.activerecord_test.basic.test_fields import TestFields
from rhosocial.activerecord_test.basic.test_validation import TestValidation
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLCRUD(TestCRUD):
    """Run shared CRUD tests with MySQL backend."""
    
    @pytest.fixture(scope='class')
    def backend(self, mysql_config):
        """Provide MySQL backend for tests."""
        backend = MySQLBackend(**mysql_config)
        yield backend
        backend.close()
    
    @pytest.fixture(autouse=True)
    def setup_schema(self, backend):
        """Load test schema before each test."""
        # The shared tests expect certain tables
        # Load the appropriate schema based on test requirements
        schema_path = 'tests/rhosocial/activerecord_test/basic/fixtures/schema/sqlite/users.sql'
        
        # Convert SQLite schema to MySQL if needed
        with open(schema_path) as f:
            sql = f.read()
            # Replace SQLite-specific syntax with MySQL
            sql = sql.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
            sql = sql.replace('INTEGER PRIMARY KEY', 'INT PRIMARY KEY')
            
        backend.execute(sql)
        yield
        backend.execute("DROP TABLE IF EXISTS users")


class TestMySQLFields(TestFields):
    """Run shared field tests with MySQL backend."""
    
    @pytest.fixture(scope='class')
    def backend(self, mysql_config):
        backend = MySQLBackend(**mysql_config)
        yield backend
        backend.close()


class TestMySQLValidation(TestValidation):
    """Run shared validation tests with MySQL backend."""
    
    @pytest.fixture(scope='class')
    def backend(self, mysql_config):
        backend = MySQLBackend(**mysql_config)
        yield backend
        backend.close()
```

### 2. Import and Run Query Tests

```python
# tests/shared/test_query.py
import pytest
from rhosocial.activerecord_test.query.test_basic import TestBasicQueries
from rhosocial.activerecord_test.query.test_conditions import TestConditions
from rhosocial.activerecord_test.query.test_joins import TestJoins
from rhosocial.activerecord_test.query.test_window_functions import TestWindowFunctions
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLQueries(TestBasicQueries):
    """Run shared query tests with MySQL backend."""
    
    @pytest.fixture(scope='class')
    def backend(self, mysql_config):
        backend = MySQLBackend(**mysql_config)
        yield backend
        backend.close()
    
    @pytest.fixture(autouse=True)
    def load_query_fixtures(self, backend):
        """Load query test fixtures."""
        # Load schemas from shared test suite
        schemas = [
            'users.sql',
            'posts.sql', 
            'comments.sql'
        ]
        
        for schema in schemas:
            path = f'tests/rhosocial/activerecord_test/query/fixtures/schema/sqlite/{schema}'
            with open(path) as f:
                sql = self.convert_sqlite_to_mysql(f.read())
                backend.execute(sql)
        
        yield
        
        # Cleanup
        for table in ['comments', 'posts', 'users']:
            backend.execute(f"DROP TABLE IF EXISTS {table}")
    
    def convert_sqlite_to_mysql(self, sql):
        """Convert SQLite SQL to MySQL syntax."""
        conversions = {
            'AUTOINCREMENT': 'AUTO_INCREMENT',
            'INTEGER PRIMARY KEY': 'INT PRIMARY KEY',
            'BOOLEAN': 'TINYINT(1)',
            'TIMESTAMP DEFAULT CURRENT_TIMESTAMP': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for sqlite_syntax, mysql_syntax in conversions.items():
            sql = sql.replace(sqlite_syntax, mysql_syntax)
        
        return sql
```

### 3. Import and Run Relation Tests

```python
# tests/shared/test_relations.py
import pytest
from rhosocial.activerecord_test.relation.test_base import TestRelationBase
from rhosocial.activerecord_test.relation.test_cache import TestRelationCache
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLRelations(TestRelationBase):
    """Run shared relation tests with MySQL backend."""
    
    @pytest.fixture(scope='class')
    def backend(self, mysql_config):
        backend = MySQLBackend(**mysql_config)
        yield backend
        backend.close()
```

### 4. Import and Run Mixin Tests

```python
# tests/shared/test_mixins.py
import pytest
from rhosocial.activerecord_test.mixins.test_timestamps import TestTimestamps
from rhosocial.activerecord_test.mixins.test_soft_delete import TestSoftDelete
from rhosocial.activerecord_test.mixins.test_optimistic_lock import TestOptimisticLock
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLTimestamps(TestTimestamps):
    """Run timestamp mixin tests with MySQL backend."""
    
    @pytest.fixture(scope='class')
    def backend(self, mysql_config):
        backend = MySQLBackend(**mysql_config)
        yield backend
        backend.close()
```

## MySQL-Specific Tests

### 1. MySQL Backend Tests

```python
# tests/test_mysql_backend.py
import pytest
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLBackend:
    """Test MySQL-specific backend functionality."""
    
    def test_connection_pooling(self, mysql_config):
        """Test MySQL connection pooling."""
        backend = MySQLBackend(**mysql_config, pool_size=5)
        
        # Test multiple concurrent connections
        connections = []
        for _ in range(5):
            conn = backend.get_connection()
            connections.append(conn)
        
        # All connections should be from pool
        assert len(set(id(c) for c in connections)) <= 5
        
        # Return connections to pool
        for conn in connections:
            backend.return_connection(conn)
        
        backend.close()
    
    def test_mysql_specific_types(self, mysql_backend):
        """Test MySQL-specific data types."""
        # Test JSON type
        mysql_backend.execute("""
            CREATE TABLE json_test (
                id INT PRIMARY KEY AUTO_INCREMENT,
                data JSON
            )
        """)
        
        # Insert JSON data
        mysql_backend.execute(
            "INSERT INTO json_test (data) VALUES (%s)",
            ('{"key": "value"}',)
        )
        
        # Query JSON data
        result = mysql_backend.execute(
            "SELECT data->>'$.key' FROM json_test"
        ).fetchone()
        
        assert result[0] == 'value'
        
        mysql_backend.execute("DROP TABLE json_test")
```

### 2. MySQL Type Tests

```python
# tests/test_mysql_types.py
import pytest
from datetime import datetime, date, time
from decimal import Decimal
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLTypes:
    """Test MySQL data type handling."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mysql_backend):
        """Create test table with various MySQL types."""
        mysql_backend.execute("""
            CREATE TABLE type_test (
                id INT PRIMARY KEY AUTO_INCREMENT,
                varchar_col VARCHAR(255),
                text_col TEXT,
                json_col JSON,
                datetime_col DATETIME,
                date_col DATE,
                time_col TIME,
                decimal_col DECIMAL(10,2),
                enum_col ENUM('option1', 'option2', 'option3'),
                set_col SET('tag1', 'tag2', 'tag3')
            )
        """)
        yield
        mysql_backend.execute("DROP TABLE IF EXISTS type_test")
    
    def test_json_type(self, mysql_backend):
        """Test JSON column type."""
        class TypeTest(ActiveRecord):
            __backend__ = mysql_backend
            __tablename__ = 'type_test'
            
            id: int
            json_col: dict
        
        # Save JSON data
        test = TypeTest(json_col={'nested': {'key': 'value'}})
        test.save()
        
        # Retrieve and verify
        loaded = TypeTest.find(test.id)
        assert loaded.json_col == {'nested': {'key': 'value'}}
    
    def test_enum_type(self, mysql_backend):
        """Test ENUM column type."""
        class TypeTest(ActiveRecord):
            __backend__ = mysql_backend
            __tablename__ = 'type_test'
            
            id: int
            enum_col: str
        
        # Test valid enum value
        test = TypeTest(enum_col='option1')
        test.save()
        assert test.enum_col == 'option1'
        
        # Test invalid enum value
        with pytest.raises(ValueError):
            invalid = TypeTest(enum_col='invalid_option')
            invalid.save()
```

### 3. MySQL Feature Tests

```python
# tests/test_mysql_features.py
import pytest
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


class TestMySQLFeatures:
    """Test MySQL-specific features."""
    
    def test_fulltext_search(self, mysql_backend):
        """Test MySQL FULLTEXT search."""
        mysql_backend.execute("""
            CREATE TABLE articles (
                id INT PRIMARY KEY AUTO_INCREMENT,
                title VARCHAR(200),
                content TEXT,
                FULLTEXT KEY (title, content)
            )
        """)
        
        class Article(ActiveRecord):
            __backend__ = mysql_backend
            __tablename__ = 'articles'
            
            id: int
            title: str
            content: str
        
        # Insert test articles
        Article(title="Python Programming", 
                content="Learn Python programming language").save()
        Article(title="MySQL Database", 
                content="MySQL is a relational database").save()
        
        # Perform fulltext search
        results = Article.where(
            "MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)",
            "Python"
        ).all()
        
        assert len(results) == 1
        assert results[0].title == "Python Programming"
        
        mysql_backend.execute("DROP TABLE articles")
    
    def test_insert_on_duplicate_key(self, mysql_backend):
        """Test INSERT ... ON DUPLICATE KEY UPDATE."""
        mysql_backend.execute("""
            CREATE TABLE counters (
                name VARCHAR(50) PRIMARY KEY,
                count INT DEFAULT 0
            )
        """)
        
        # Insert or update
        mysql_backend.execute("""
            INSERT INTO counters (name, count) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE count = count + VALUES(count)
        """, ('visits', 1))
        
        # Insert again (should update)
        mysql_backend.execute("""
            INSERT INTO counters (name, count) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE count = count + VALUES(count)
        """, ('visits', 1))
        
        result = mysql_backend.execute(
            "SELECT count FROM counters WHERE name = %s",
            ('visits',)
        ).fetchone()
        
        assert result[0] == 2
        
        mysql_backend.execute("DROP TABLE counters")
```

## Configuration and Fixtures

### Main conftest.py

```python
# tests/conftest.py
import pytest
import yaml
from pathlib import Path
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend


@pytest.fixture(scope='session')
def mysql_config():
    """Load MySQL configuration."""
    config_path = Path(__file__).parent / 'config.yml'
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config['mysql']


@pytest.fixture(scope='function')
def mysql_backend(mysql_config):
    """Provide MySQL backend for tests."""
    backend = MySQLBackend(**mysql_config)
    yield backend
    
    # Cleanup: drop all tables
    tables = backend.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
    ).fetchall()
    
    for table in tables:
        backend.execute(f"DROP TABLE IF EXISTS {table[0]}")
    
    backend.close()
```

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=rhosocial.activerecord.backend.impl.mysql

# Verbose mode
pytest -v
```

### Run Specific Test Categories

```bash
# Run only shared test suite
pytest tests/shared/

# Run only MySQL-specific tests
pytest tests/test_mysql_*.py

# Run specific test file
pytest tests/test_mysql_backend.py
```

### Run with Markers

```python
# Mark MySQL version specific tests
@pytest.mark.mysql80
def test_window_functions():
    pass

# Run tests for specific MySQL version
pytest -m mysql80
```

## Best Practices

1. **Inherit Shared Tests**: Always run the shared test suite to ensure compatibility
2. **Schema Conversion**: Convert SQLite schemas to MySQL syntax when using shared fixtures
3. **Clean State**: Ensure database is clean between tests
4. **Connection Management**: Properly close connections in fixtures
5. **Version Compatibility**: Test against multiple MySQL versions when possible
6. **Error Testing**: Include tests for MySQL-specific error conditions
7. **Performance**: Test MySQL-specific optimizations

## Continuous Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_password
          MYSQL_DATABASE: test_db
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -e ".[test]"
    
    - name: Wait for MySQL
      run: |
        until mysqladmin ping -h 127.0.0.1 --silent; do
          echo 'waiting for mysql...'
          sleep 1
        done
    
    - name: Run tests
      run: |
        pytest --cov=rhosocial.activerecord.backend.impl.mysql
```

## Troubleshooting

### Connection Issues

```bash
# Test MySQL connection
mysql -h localhost -P 3306 -u root -ptest_password -e "SELECT 1"

# Check Docker container
docker ps | grep mysql
docker logs mysql-test
```

### Import Errors

```python
# Ensure rhosocial-activerecord[test] is installed
pip install rhosocial-activerecord[test]

# Check imports
python -c "from rhosocial.activerecord_test.basic import TestCRUD"
```

### Schema Compatibility

When using shared test schemas, you may need to convert SQLite syntax:

```python
def convert_sqlite_to_mysql(sql):
    """Convert SQLite schema to MySQL."""
    conversions = {
        'AUTOINCREMENT': 'AUTO_INCREMENT',
        'INTEGER': 'INT',
        'REAL': 'DOUBLE',
        'BLOB': 'LONGBLOB',
        'INTEGER PRIMARY KEY': 'INT PRIMARY KEY',
        'WITHOUT ROWID': '',  # Remove SQLite specific
    }
    
    for old, new in conversions.items():
        sql = sql.replace(old, new)
    
    return sql
```