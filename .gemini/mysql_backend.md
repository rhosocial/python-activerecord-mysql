# MySQL Backend Knowledge Base for RhoSocial ActiveRecord

## Repository Overview

The `rhosocial-activerecord-mysql` repository provides a MySQL-specific backend implementation for the RhoSocial ActiveRecord package. It extends the core functionality of `rhosocial-activerecord` by adding MySQL-specific features and optimizations while maintaining compatibility with the shared test suite.

## Architecture and Dependencies

### Package Dependencies
- **Core Package**: `rhosocial-activerecord` - Provides the base ActiveRecord pattern implementation
- **Testsuite Package**: `rhosocial-activerecord-testsuite` - Provides standardized test contracts
- **MySQL Driver**: `mysql-connector-python` - Official MySQL connector for Python

### Repository Structure
- `src/rhosocial/activerecord/backend/impl/mysql/` - Core MySQL backend implementation
- `tests/` - MySQL-specific tests and shared test suite adapters
- `.gemini/` - Knowledge base and AI assistant guidance

## Core Components

### Backend Implementation
The MySQL backend is implemented in several key files:

- `backend.py` - Core MySQL backend class implementation
- `config.py` - MySQL-specific configuration handling
- `dialect.py` - MySQL-specific SQL dialect and syntax
- `types.py` - MySQL-specific data type handling
- `type_converters.py` - Type conversion utilities for MySQL
- `transaction.py` - MySQL-specific transaction handling

### Key Features

#### MySQL-Specific Capabilities
1. **JSON Type Support**: Full support for MySQL's native JSON data type
2. **Full-Text Search**: Integration with MySQL's MATCH...AGAINST functionality
3. **Window Functions**: Support for MySQL 8.0+ window functions
4. **Common Table Expressions**: Support for recursive and materialized CTEs
5. **Connection Pooling**: Built-in support for MySQL connection pooling
6. **Enum/Set Types**: Support for MySQL-specific ENUM and SET data types

#### Performance Optimizations
1. **Prepared Statements**: Efficient prepared statement handling
2. **Batch Operations**: Optimized batch insert/update/delete operations
3. **Connection Management**: Efficient connection reuse and pooling
4. **Index Utilization**: Optimized index usage for better query performance

## Testing Strategy

### Two-Tier Testing Approach
1. **Shared Test Suite**: Reuses tests from `rhosocial-activerecord-testsuite`
2. **MySQL-Specific Tests**: Validates MySQL-specific functionality

### Test Configuration
- Tests require a MySQL server (version 8.0+ recommended)
- Configuration via `tests/config.yml` or environment variables
- Schema conversion from shared SQLite schemas to MySQL syntax

## Configuration and Setup

### MySQL Server Requirements
- MySQL version 8.0 or higher (for full feature support)
- Required plugins: JSON, Full-text search (if using those features)

### Configuration Options
The MySQL backend supports various configuration options:

```python
config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'password',
    'database': 'test_db',
    'charset': 'utf8mb4',
    'autocommit': True,
    'pool_size': 10,
    'pool_name': 'activerecord_pool',
    'connection_timeout': 10,
    'read_timeout': 10,
    'write_timeout': 10
}
```

## Development Guidelines

### Implementing New MySQL Features
1. **Capability Declaration**: Declare new capabilities in the backend class
2. **Version Checking**: Check MySQL server version before using new features
3. **Schema Conversion**: Update schema conversion utilities if needed
4. **Test Coverage**: Add tests for new functionality

### Schema Management
- Convert SQLite schemas to MySQL syntax when reusing shared tests
- Use MySQL-specific data types where appropriate
- Consider MySQL storage engines (InnoDB by default)

## MySQL-Specific Optimizations

### Query Optimizations
1. **Prepared Statements**: Use prepared statements for repeated queries
2. **Batch Operations**: Use batch operations for multiple insertions/updates
3. **Connection Pooling**: Utilize connection pooling for better performance
4. **Indexing**: Proper indexing for optimal query performance

### Data Type Handling
1. **JSON Support**: Utilize MySQL's native JSON type for JSON data
2. **Temporal Types**: Support for DATE, TIME, DATETIME, TIMESTAMP
3. **Numeric Types**: Support for INT, BIGINT, DECIMAL, FLOAT, DOUBLE
4. **Text Types**: Support for VARCHAR, TEXT, MEDIUMTEXT, LONGTEXT

## Common Patterns

### MySQL-Specific Model Configuration
```python
class MySQLModel(ActiveRecord):
    __backend__ = mysql_backend
    
    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }
```

### JSON Field Operations
```python
# Using MySQL's JSON functions
result = Model.where(
    "JSON_EXTRACT(json_column, '$.key') = %s",
    ['value']
).all()
```

### Full-Text Search
```python
# Using MySQL's full-text search
results = Article.where(
    "MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)",
    ['search term']
).all()
```

## Version Compatibility

### MySQL 8.0+ Features
- Window Functions (ROW_NUMBER, RANK, etc.)
- Common Table Expressions (CTEs)
- JSON_TABLE function
- Descending indexes

### MySQL 5.7+ Features
- Native JSON data type
- JSON functions (JSON_EXTRACT, JSON_SEARCH, etc.)

### Legacy Support
- Maintain compatibility with older MySQL versions where possible
- Use version detection to enable features conditionally

## Troubleshooting

### Common Issues
1. **Connection Issues**: Verify MySQL server is running and credentials are correct
2. **Charset Issues**: Ensure proper character set configuration (utf8mb4 recommended)
3. **Feature Availability**: Check MySQL version before using version-specific features
4. **Schema Conversion**: Ensure proper conversion from SQLite to MySQL syntax

### Debugging Tools
- MySQL Workbench or command-line client for direct database access
- Query logging to analyze generated SQL statements
- Connection pooling statistics to monitor performance

## Best Practices

### Performance
1. **Connection Pooling**: Always use connection pooling in production
2. **Prepared Statements**: Use prepared statements for repeated queries
3. **Batch Operations**: Use batch operations for multiple records
4. **Indexing**: Properly index frequently queried columns

### Security
1. **Parameterized Queries**: Always use parameterized queries to prevent SQL injection
2. **Connection Security**: Use SSL connections when possible
3. **User Permissions**: Grant minimal required permissions to database users

### Maintainability
1. **Version Detection**: Use MySQL version detection to conditionally enable features
2. **Error Handling**: Properly handle MySQL-specific error conditions
3. **Testing**: Maintain comprehensive test coverage for all MySQL-specific features
4. **Documentation**: Document MySQL-specific behaviors and configurations