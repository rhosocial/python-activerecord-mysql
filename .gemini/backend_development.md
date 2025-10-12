# MySQL Backend Development Guide for RhoSocial ActiveRecord

## Introduction

This guide provides instructions for developing and extending the MySQL backend implementation for RhoSocial ActiveRecord. It covers the architecture, development patterns, testing approach, and best practices for adding new MySQL-specific features.

## Development Environment Setup

### Prerequisites

1. **Python Versions**: Support for Python 3.8+ (with special considerations for 3.14+ free-threading)
2. **MySQL Server**: Version 8.0 or higher (for full feature support)
3. **Development Tools**: Git, virtual environment manager (venv, conda, etc.)

### Initial Setup

```bash
# Clone all related repositories
git clone https://github.com/rhosocial/python-activerecord.git
git clone https://github.com/rhosocial/python-activerecord-mysql.git
git clone https://github.com/rhosocial/python-activerecord-testsuite.git

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install the MySQL backend in editable mode
cd python-activerecord-mysql
pip install -e ".[dev,test]"
```

### MySQL Server Setup

For development and testing, you can set up MySQL using Docker:

```bash
# Start MySQL server for development
docker run -d \
  --name mysql-dev-activerecord \
  -e MYSQL_ROOT_PASSWORD=test_password \
  -e MYSQL_DATABASE=test_activerecord_mysql \
  -p 3306:3306 \
  mysql:8.0
```

## Architecture Overview

### Core Components

The MySQL backend consists of several key components:

```
src/rhosocial/activerecord/backend/impl/mysql/
├── __init__.py              # Package exports
├── backend.py              # Main backend implementation
├── config.py               # Configuration handling
├── dialect.py              # MySQL-specific SQL dialect
├── transaction.py          # Transaction management
├── types.py                # MySQL-specific data types
└── type_converters.py      # Type conversion utilities
```

### Extension Points

The backend provides several extension points for MySQL-specific functionality:

1. **Capability Declaration**: Declare supported MySQL features
2. **Type Conversions**: Add MySQL-specific type handling
3. **SQL Dialect**: Extend MySQL-specific syntax support
4. **Connection Management**: Customize connection pooling and handling

## Developing New MySQL Features

### 1. Determine Feature Category

First, determine which category your MySQL-specific feature belongs to:

- **Data Types**: New data type support (JSON, ENUM, SET, etc.)
- **Query Functions**: MySQL-specific SQL functions
- **Schema Features**: Table options, indexes, constraints
- **Connection Features**: Pooling, SSL, authentication methods
- **Performance**: Optimizations for specific use cases

### 2. Implement the Feature

#### Example: Adding JSON Path Operations Support

```python
# src/rhosocial/activerecord/backend/impl/mysql/dialect.py
class MySQLDialect:
    def json_path_extract(self, column: str, path: str) -> str:
        """Generate MySQL-specific JSON path extraction."""
        return f"JSON_EXTRACT({column}, '{path}')"
    
    def json_contains(self, column: str, value: str) -> str:
        """Generate MySQL-specific JSON contains check."""
        return f"JSON_CONTAINS({column}, {value})"
```

```python
# Update the backend to use the new dialect features
# src/rhosocial/activerecord/backend/impl/mysql/backend.py
class MySQLBackend(StorageBackend):
    def __init__(self, **config):
        super().__init__()
        self.dialect = MySQLDialect()
    
    def execute_json_path_query(self, table: str, column: str, path: str, value: any):
        """Execute a JSON path query using MySQL-specific syntax."""
        query = f"SELECT * FROM {table} WHERE {self.dialect.json_path_extract(column, path)} = %s"
        return self.execute(query, (value,))
```

### 3. Declare Capabilities

Add the new feature to the capability system:

```python
# src/rhosocial/activerecord/backend/impl/mysql/backend.py
from rhosocial.activerecord.backend.capabilities import (
    DatabaseCapabilities,
    JSONCapability
)

class MySQLBackend(StorageBackend):
    def _initialize_capabilities(self):
        capabilities = DatabaseCapabilities()
        version = self.get_server_version()
        
        # JSON operations support from MySQL 5.7+
        if version >= (5, 7, 0):
            capabilities.add_json_operation([
                JSONCapability.BASIC_JSON,
                JSONCapability.JSON_EXTRACT,
                JSONCapability.JSON_SEARCH,
                JSONCapability.JSON_PATH_OPERATIONS  # Add new capability
            ])
        
        return capabilities
```

### 4. Add Type Handling

If your feature adds new type support, update the type conversion system:

```python
# src/rhosocial/activerecord/backend/impl/mysql/type_converters.py
class MySQLTypeConverter:
    def __init__(self):
        self.type_mappings = {
            # Existing mappings...
            'json': self.convert_json,
            'json_path': self.convert_json_path
        }
    
    def convert_json(self, value):
        """Convert Python object to MySQL JSON."""
        import json
        return json.dumps(value) if not isinstance(value, str) else value
    
    def convert_json_path(self, value):
        """Convert to valid MySQL JSON path."""
        # Ensure proper JSON path format
        if isinstance(value, str):
            return value if value.startswith('$') else f'${value}'
        return str(value)
```

## Testing New Features

### 1. Unit Tests for the Feature

Create tests that verify your new feature works correctly:

```python
# tests/test_mysql_json_paths.py
import pytest
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

def test_mysql_json_path_extraction(mysql_backend):
    """Test MySQL-specific JSON path extraction."""
    mysql_backend.execute("""
        CREATE TABLE json_test (
            id INT PRIMARY KEY AUTO_INCREMENT,
            data JSON
        )
    """)
    
    class JSONTest(ActiveRecord):
        __backend__ = mysql_backend
        __tablename__ = 'json_test'
        id: int
        data: dict
    
    # Insert JSON data
    test_data = {'user': {'name': 'John', 'age': 30, 'tags': ['dev', 'python']}}
    record = JSONTest(data=test_data)
    record.save()
    
    # Test path extraction
    result = JSONTest.where(
        "JSON_EXTRACT(data, '$.user.name') = %s",
        ['John']
    ).first()
    
    assert result is not None
    assert result.data['user']['name'] == 'John'
    
    # Test nested array access
    result = JSONTest.where(
        "JSON_CONTAINS(data->'$.user.tags', %s)",
        ['"python"']
    ).first()
    
    assert result is not None
    assert 'python' in result.data['user']['tags']
```

### 2. Integration Tests with Shared Test Suite

If appropriate, add hooks to make your feature work with the shared test suite:

```python
# tests/providers/mysql_provider.py
class MySQLTestProvider(ITestProvider):
    def setup_json_fixtures(self, scenario):
        """Setup models with JSON capabilities."""
        config = self._get_mysql_config(scenario)
        backend = MySQLBackend(**config)
        
        class JSONModel(ActiveRecord):
            __backend__ = backend
            __tablename__ = 'mysql_json_test'
            id: int
            json_data: dict
        
        # Create table with JSON column
        backend.execute("""
            CREATE TABLE mysql_json_test (
                id INT PRIMARY KEY AUTO_INCREMENT,
                json_data JSON
            )
        """)
        
        return (JSONModel,)
```

### 3. Capability-Based Tests

Ensure your tests properly declare capability requirements:

```python
# tests/test_mysql_json_paths.py
from rhosocial.activerecord.backend.capabilities import (
    CapabilityCategory,
    JSONCapability
)
from rhosocial.activerecord.testsuite.utils import requires_capabilities

@requires_capabilities(
    (CapabilityCategory.JSON_OPERATIONS, JSONCapability.JSON_PATH_OPERATIONS)
)
def test_mysql_json_path_operations(json_model_class):
    """Test JSON path operations that require specific MySQL capabilities."""
    # Test implementation here
    pass
```

## MySQL-Specific Optimizations

### Query Optimization

When implementing new features, consider MySQL-specific optimizations:

```python
# Example: Optimized batch insert using MySQL's VALUES syntax
def optimized_batch_insert(self, table_name: str, columns: List[str], values: List[Tuple]):
    """Optimized batch insert using MySQL's ON DUPLICATE KEY UPDATE."""
    if not values:
        return
    
    # Use MySQL's VALUES syntax for efficient batch operations
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    
    query = f"""
        INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
    """
    
    # Add update clauses for conflicts
    update_clauses = [f"{col} = VALUES({col})" for col in columns if col != 'id']
    query += ', '.join(update_clauses)
    
    # Execute with all values
    flattened_values = [val for row in values for val in row]
    return self.execute(query, flattened_values)
```

### Connection Pooling

Implement efficient connection pooling for high-concurrency scenarios:

```python
# Example: Enhanced connection pooling
class MySQLBackend(StorageBackend):
    def __init__(self, **config):
        super().__init__()
        self.pool_config = {
            'pool_name': config.get('pool_name', 'activerecord_pool'),
            'pool_size': config.get('pool_size', 10),
            'pool_reset_session': config.get('pool_reset_session', True),
            'autocommit': config.get('autocommit', False)
        }
        
        self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            **{**config, **self.pool_config}
        )
    
    def get_connection(self):
        """Get connection from pool."""
        return self.connection_pool.get_connection()
    
    def return_connection(self, connection):
        """Return connection to pool."""
        if connection.is_connected():
            connection.close()  # Connection pool handles reuse internally
```

## Best Practices for Feature Development

### 1. Version Compatibility

Always check MySQL version before using version-specific features:

```python
def supports_window_functions(self) -> bool:
    """Check if MySQL version supports window functions."""
    version = self.get_server_version()
    return version >= (8, 0, 0)  # Window functions available from 8.0+

def execute_with_window_function(self, query: str):
    """Execute query with window function if supported."""
    if not self.supports_window_functions():
        raise NotImplementedError(
            f"Window functions require MySQL 8.0+, current version: {self.get_server_version()}"
        )
    return self.execute(query)
```

### 2. Error Handling

Implement proper error handling for MySQL-specific errors:

```python
import mysql.connector.errors

def execute_with_retry(self, sql: str, params: Tuple = None, max_retries: int = 3):
    """Execute with retry logic for transient MySQL errors."""
    for attempt in range(max_retries):
        try:
            return self.execute(sql, params)
        except mysql.connector.errors.OperationalError as e:
            # Retry on connection errors
            if "Lost connection" in str(e) or "server has gone away" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                    continue
            raise
        except Exception as e:
            raise e
```

### 3. Resource Management

Properly manage database resources:

```python
def __enter__(self):
    """Context manager entry."""
    self._connection = self.get_connection()
    self._cursor = self._connection.cursor()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit."""
    if self._cursor:
        self._cursor.close()
    if self._connection:
        self.return_connection(self._connection)
```

### 4. Type Consistency

Maintain type consistency across the codebase:

```python
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from rhosocial.activerecord.types import ActiveRecordProtocol

def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """Execute query and return consistent result format."""
    cursor = self.get_cursor()
    try:
        cursor.execute(sql, params or ())
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()
```

## Adding New Test Patterns

### 1. Backend-Specific Test Structure

When adding new functionality, follow the established test structure:

```
tests/
├── rhosocial/
│   └── activerecord_mysql_test/
│       ├── feature/          # Core functionality tests
│       │   ├── backend/      # Backend interface tests
│       │   ├── basic/        # Basic CRUD tests
│       │   ├── query/        # Query functionality
│       │   ├── relation/     # Relationship tests  
│       │   ├── events/       # Event system tests
│       │   └── mixins/       # Mixin functionality
│       └── realworld/        # Business scenario tests
├── test_mysql_*.py          # MySQL-specific tests
└── providers/               # Test provider implementations
```

### 2. Provider Pattern Implementation

For new features that should work with the shared test suite, implement the provider pattern:

```python
# tests/providers/mysql_json_provider.py
from typing import Tuple, Type
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.testsuite.core.provider import ITestProvider

class MySQLJSONProvider(ITestProvider):
    def setup_json_fixtures(self, scenario: str) -> Tuple[Type[ActiveRecord], ...]:
        """Setup JSON-specific test fixtures with MySQL backend."""
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
        
        config = self._get_config(scenario)
        backend = MySQLBackend(**config)
        
        class JSONTestModel(ActiveRecord):
            __backend__ = backend
            __tablename__ = f'json_test_{scenario}'
            id: int
            json_data: dict
        
        # Create table with JSON column
        backend.execute(f"""
            CREATE TABLE json_test_{scenario} (
                id INT PRIMARY KEY AUTO_INCREMENT,
                json_data JSON
            )
        """)
        
        return (JSONTestModel,)
```

### 3. Schema Conversion

When reusing shared test schemas, provide MySQL-specific conversions:

```python
class MySQLTestProvider(ITestProvider):
    def _convert_sqlite_to_mysql_schema(self, sqlite_schema: str) -> str:
        """Convert SQLite schema to MySQL syntax."""
        conversions = [
            ('AUTOINCREMENT', 'AUTO_INCREMENT'),
            ('INTEGER PRIMARY KEY', 'INT PRIMARY KEY'),
            ('BOOLEAN', 'TINYINT(1)'),
            ('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('TEXT', 'LONGTEXT'),  # MySQL TEXT has different limits
        ]
        
        result = sqlite_schema
        for sqlite_syntax, mysql_syntax in conversions:
            result = result.replace(sqlite_syntax, mysql_syntax)
        
        return result
```

## Performance Testing

### 1. Benchmark Setup

Create performance tests for your new features:

```python
# tests/benchmark/mysql_json_performance.py
import time
import pytest
from rhosocial.activerecord import ActiveRecord

def test_mysql_json_performance(mysql_backend):
    """Benchmark JSON operations performance."""
    mysql_backend.execute("""
        CREATE TABLE perf_json_test (
            id INT PRIMARY KEY AUTO_INCREMENT,
            data JSON
        )
    """)
    
    class PerfJSONTest(ActiveRecord):
        __backend__ = mysql_backend
        __tablename__ = 'perf_json_test'
        id: int
        data: dict
    
    # Insert test data
    test_data = {'nested': {'key': f'value_{i}', 'arr': list(range(10))} for i in range(100)}
    
    start_time = time.time()
    for data in test_data:
        record = PerfJSONTest(data={'content': data})
        record.save()
    insert_duration = time.time() - start_time
    
    # Query test
    start_time = time.time()
    results = PerfJSONTest.where(
        "JSON_EXTRACT(data, '$.content.key') LIKE %s",
        ['value_%']
    ).limit(10).all()
    query_duration = time.time() - start_time
    
    # Assertions
    assert len(results) == 10
    assert insert_duration < 5.0  # Should complete in under 5 seconds
    assert query_duration < 1.0   # Should query quickly
```

### 2. Load Testing

Test your feature under load conditions:

```python
# tests/load/mysql_json_load.py
import concurrent.futures
import threading
from rhosocial.activerecord import ActiveRecord

def test_mysql_json_concurrent_load(mysql_backend):
    """Test JSON operations under concurrent load."""
    mysql_backend.execute("""
        CREATE TABLE load_json_test (
            id INT PRIMARY KEY AUTO_INCREMENT,
            data JSON
        )
    """)
    
    class LoadJSONTest(ActiveRecord):
        __backend__ = mysql_backend
        __tablename__ = 'load_json_test'
        id: int
        data: dict
    
    def worker(worker_id: int):
        """Worker function for concurrent testing."""
        for i in range(10):
            test_data = {'worker': worker_id, 'item': i, 'payload': f'data_{worker_id}_{i}'}
            record = LoadJSONTest(data=test_data)
            record.save()
            
            # Query back with JSON operations
            result = LoadJSONTest.where(
                "JSON_EXTRACT(data, '$.payload') = %s",
                [f'data_{worker_id}_{i}']
            ).first()
            
            assert result is not None
            assert result.data['worker'] == worker_id
    
    # Run concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, i) for i in range(5)]
        concurrent.futures.wait(futures)
    
    # Verify all records were created
    all_records = LoadJSONTest.all()
    assert len(all_records) == 50  # 5 workers * 10 items each
```

## Documentation and Examples

### 1. Feature Documentation

Document your new feature in the appropriate places:

```python
# In your new method
def json_path_query(self, table: str, column: str, path: str, value: any):
    """Execute a JSON path query using MySQL-specific syntax.
    
    This feature requires MySQL 5.7+ and is optimized for performance with
    large JSON documents.
    
    Args:
        table: Name of the table containing JSON data
        column: Name of the JSON column
        path: JSON path expression (e.g., '$.user.name')
        value: Value to compare against the extracted path
        
    Returns:
        List of matching records
        
    Raises:
        NotImplementedError: If MySQL version is < 5.7
        ValueError: If path is not a valid JSON path
        
    Example:
        ```python
        results = backend.json_path_query(
            'users', 'profile', '$.preferences.theme', 'dark'
        )
        ```
    """
    # Implementation here
```

### 2. Example Usage

Create example files demonstrating your new feature:

```python
# examples/mysql_json_features.py
"""
Example: MySQL JSON Feature Usage
=================================

This example demonstrates how to use MySQL-specific JSON features
with the ActiveRecord pattern.
"""

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

# Configure MySQL backend
mysql_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'test_password',
    'database': 'test_activerecord_mysql'
}

mysql_backend = MySQLBackend(**mysql_config)

class User(ActiveRecord):
    __backend__ = mysql_backend
    __tablename__ = 'examples_users'
    
    id: int
    name: str
    profile: dict  # Will be stored as JSON in MySQL

# Create table with JSON column
mysql_backend.execute("""
    CREATE TABLE IF NOT EXISTS examples_users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255),
        profile JSON
    )
""")

# Create user with JSON profile
user = User(
    name="John Doe",
    profile={
        "preferences": {
            "theme": "dark",
            "notifications": True,
            "language": "en"
        },
        "settings": {
            "timezone": "UTC",
            "date_format": "YYYY-MM-DD"
        }
    }
)
user.save()

# Query using JSON path extraction
dark_theme_users = User.where(
    "JSON_EXTRACT(profile, '$.preferences.theme') = %s",
    ['dark']
).all()

print(f"Users with dark theme: {len(dark_theme_users)}")

# Query using JSON contains
users_with_notifications = User.where(
    "JSON_EXTRACT(profile, '$.preferences.notifications') = %s",
    [True]
).all()

print(f"Users with notifications enabled: {len(users_with_notifications)}")
```

## Common Development Scenarios

### 1. Adding New Data Type Support

To add support for a new MySQL data type:

1. Update type converters
2. Add dialect support for the type
3. Update capability declarations
4. Add tests for the new type
5. Update documentation

### 2. Implementing MySQL-Specific Functionality

For MySQL-specific functions like full-text search:

1. Add method to backend class
2. Update dialect to generate correct SQL
3. Declare capability for the feature
4. Add comprehensive tests
5. Consider version compatibility

### 3. Performance Optimization

When optimizing for performance:

1. Profile the current implementation
2. Identify bottlenecks
3. Consider MySQL-specific optimizations (indexes, query syntax)
4. Test with realistic data volumes
5. Verify concurrent access works properly

## Troubleshooting Development Issues

### Common Issues

1. **MySQL Version Compatibility**: Always verify MySQL version before using new features
2. **Connection Issues**: Check connection pooling and timeout settings
3. **Type Conversion Problems**: Ensure proper type handling between Python and MySQL
4. **SQL Syntax Errors**: Validate MySQL-specific syntax in queries
5. **Test Failures**: Verify PYTHONPATH is set correctly for test execution

### Debugging Tips

1. Enable MySQL query logging to see generated SQL
2. Use connection pooling statistics to monitor performance
3. Test with different MySQL versions to ensure compatibility
4. Verify character encoding settings for text data
5. Check MySQL server error logs for issues

This guide provides the foundation for developing new MySQL-specific features while maintaining compatibility with the broader RhoSocial ActiveRecord ecosystem.