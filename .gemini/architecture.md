# MySQL Backend Architecture for RhoSocial ActiveRecord

## System Overview

The MySQL backend for RhoSocial ActiveRecord is designed as a pluggable component that extends the core ActiveRecord functionality with MySQL-specific features and optimizations. It follows a modular architecture that separates core ActiveRecord patterns from database-specific implementations.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Application Code<br/>ActiveRecord Models]
    end
    
    subgraph "Core ActiveRecord Layer"
        CORE[Core ActiveRecord<br/>Abstract Backend Interface<br/>Model Base Classes]
    end
    
    subgraph "Database Backend Layer" 
        MYSQL[MySQL Backend<br/>Implementation]
        OTHER[Other Backends<br/>SQLite, PostgreSQL, etc.]
    end
    
    subgraph "Database Drivers"
        DRIVER[mysql-connector-python]
        DRIVER_OTHER[Other Drivers]
    end
    
    subgraph "Database Server"
        DB[(MySQL Server<br/>8.0+)]
        DB_OTHER[(Other Databases)]
    end
    
    APP --> CORE
    CORE --> MYSQL
    CORE --> OTHER
    MYSQL --> DRIVER
    OTHER --> DRIVER_OTHER
    DRIVER --> DB
    DRIVER_OTHER --> DB_OTHER
```

## Component Architecture

### 1. Core Backend Interface

The core ActiveRecord defines an abstract interface that all backends must implement:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class StorageBackend(ABC):
    """Abstract interface for storage backends."""
    
    @abstractmethod
    def execute(self, sql: str, params: Optional[Tuple] = None) -> Any:
        """Execute SQL query."""
        pass
    
    @abstractmethod
    def execute_many(self, sql: str, params_list: List[Tuple]) -> None:
        """Execute SQL query multiple times with different parameters."""
        pass
    
    @abstractmethod
    def get_connection(self) -> Any:
        """Get a database connection."""
        pass
    
    @abstractmethod
    def transaction(self) -> Any:
        """Get a transaction context manager."""
        pass
    
    @abstractmethod
    def get_server_version(self) -> Tuple[int, ...]:
        """Get database server version."""
        pass
```

### 2. MySQL Backend Implementation

The MySQL backend implements the storage interface with MySQL-specific functionality:

```mermaid
classDiagram
    class StorageBackend {
        <<abstract>>
        +execute(sql, params)
        +execute_many(sql, params_list)
        +get_connection()
        +transaction()
        +get_server_version()
    }
    
    class MySQLBackend {
        -connection_config: Dict
        -connection_pool: Any
        +execute(sql, params)
        +execute_many(sql, params_list)
        +get_connection()
        +transaction()
        +get_server_version()
        +_initialize_capabilities()
    }
    
    class MySQLConfig {
        +host: str
        +port: int
        +database: str
        +username: str
        +password: str
        +charset: str
        +pool_size: int
    }
    
    class MySQLDialect {
        +escape_identifier(name)
        +last_insert_id_query(table_name)
        +convert_sql(sql)
    }
    
    StorageBackend <|-- MySQLBackend
    MySQLBackend --> MySQLConfig
    MySQLBackend --> MySQLDialect
```

### 3. MySQL Backend Components

#### Backend Core (`backend.py`)
- Implements the `StorageBackend` abstract interface
- Manages MySQL connections and connection pooling
- Handles query execution and results
- Manages transaction handling

#### Configuration (`config.py`)
- Handles MySQL-specific configuration loading
- Supports multiple configuration sources (file, environment, direct)
- Manages connection string construction

#### SQL Dialect (`dialect.py`)
- MySQL-specific SQL syntax handling
- Query generation for MySQL compatibility
- Identifier escaping for MySQL
- MySQL-specific functions and syntax

#### Type System (`types.py`, `type_converters.py`)
- MySQL-specific data type mappings
- Type conversion between Python and MySQL types
- Custom type support (JSON, ENUM, SET, etc.)

#### Transaction Management (`transaction.py`)
- MySQL-specific transaction handling
- Savepoint support
- Transaction isolation levels

## Data Flow Architecture

### Query Execution Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Model as ActiveRecord Model
    participant Backend as MySQL Backend
    participant Driver as mysql-connector
    participant DB as MySQL Server
    
    App->>Model: model.save() / Model.find(1) / Model.where(...).all()
    Model->>Backend: Execute SQL statement
    Backend->>Driver: Execute query with params
    Driver->>DB: Send SQL to MySQL
    DB-->>Driver: Return results
    Driver-->>Backend: Process results
    Backend-->>Model: Return processed data
    Model-->>App: Return ActiveRecord objects
```

### Connection Management Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Backend as MySQL Backend
    participant Pool as Connection Pool
    participant MySQL as MySQL Driver
    
    Note over App, MySQL: Initial Connection Request
    App->>Backend: get_connection()
    Backend->>Pool: Request connection
    alt Pool has available connection
        Pool-->>Backend: Return existing connection
    else Pool needs new connection
        Pool->>MySQL: Create new connection
        MySQL-->>Pool: New connection
        Pool-->>Backend: Return new connection
    end
    Backend-->>App: Connection object
    
    Note over App, MySQL: After use
    App->>Backend: return_connection(conn)
    Backend->>Pool: Return connection to pool
    Pool->>Pool: Validate and store connection
```

## Capability System Architecture

The MySQL backend reports its capabilities to enable selective test execution and feature detection:

```mermaid
graph LR
    subgraph "Capability System"
        DETECT[Capability Detection]
        DECL[Capability Declaration]
        REQ[Test Requirements]
        EXEC[Test Execution]
    end
    
    subgraph "MySQL Backend"
        VERSION[Version Detection]
        FEAT[Feature Detection]
        CAP_OBJ[DatabaseCapabilities]
    end
    
    VERSION --> FEAT
    FEAT --> CAP_OBJ
    CAP_OBJ --> DETECT
    REQ --> DETECT
    DETECT --> EXEC
```

### Capability Categories

The MySQL backend declares support for these capability categories:

1. **CTE (Common Table Expressions)**: Basic, recursive, and materialized CTEs
2. **JSON Operations**: JSON_EXTRACT, JSON_SEARCH, JSON_TABLE, etc.
3. **Window Functions**: ROW_NUMBER, RANK, LAG, LEAD, etc.
4. **Full-Text Search**: MATCH...AGAINST operations
5. **Advanced Grouping**: CUBE, ROLLUP operations
6. **Connection Features**: Pooling, SSL, etc.

## Testing Architecture Integration

The MySQL backend seamlessly integrates with the shared test suite:

```mermaid
graph TB
    subgraph "Testsuite Package"
        CORE_TESTS[Core Test Functions<br/>Backend-agnostic logic]
        PROVIDER_IFACE[Provider Interfaces<br/>Contract definitions]
        FIXTURES[Standard Fixtures<br/>Model definitions]
    end
    
    subgraph "MySQL Backend Tests"
        MYSQL_PROVIDER[MySQL Provider<br/>Implementation]
        MYSQL_FIXTURES[MySQL-specific<br/>Schema conversion]
        MYSQL_TESTS[MySQL-specific<br/>Functionality tests]
    end
    
    subgraph "Test Execution"
        PYTEST[Pytest Runner<br/>With capability plugins]
        EXECUTION[Test Execution<br/>Using MySQL backend]
    end
    
    PROVIDER_IFACE --> MYSQL_PROVIDER
    FIXTURES --> MYSQL_FIXTURES
    CORE_TESTS --> MYSQL_TESTS
    MYSQL_PROVIDER --> PYTEST
    MYSQL_FIXTURES --> PYTEST
    MYSQL_TESTS --> PYTEST
    PYTEST --> EXECUTION
```

### Provider Pattern Implementation

The MySQL backend implements the provider pattern to work with shared tests:

```python
class MySQLTestProvider(ITestProvider):
    """Provider implementation for MySQL backend tests."""
    
    def setup_basic_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Setup basic models with MySQL backend."""
        # Configure models with MySQL backend
        # Convert SQLite schemas to MySQL syntax
        # Return tuple of configured models
        pass
    
    def setup_query_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Setup query models with MySQL backend."""
        pass

    def get_backend_capabilities(self) -> DatabaseCapabilities:
        """Get MySQL backend capabilities for test selection."""
        pass
```

## Deployment Architecture

### Package Distribution

The MySQL backend is distributed as a separate package to maintain modularity:

```
rhosocial-activerecord (core) - Required
├── rhosocial-activerecord-mysql (this package) - Optional
├── rhosocial-activerecord-pgsql - Optional
├── rhosocial-activerecord-testsuite - Optional (for testing)
└── Application - Uses chosen backend
```

### Environment Setup

The architecture supports multiple deployment environments:

1. **Development**: Direct source code with editable installation
2. **Testing**: MySQL server with test database and schema
3. **Production**: Connection pooling and optimized settings
4. **CI/CD**: Automated testing with MySQL service containers

## Security Architecture

### Connection Security
- SSL/TLS support for encrypted connections
- Connection pooling with secure credential handling
- SQL injection prevention through parameterization

### Data Security
- Type-safe data handling through converter system
- Proper escaping of identifiers and data
- Isolation of database operations from application logic

## Performance Architecture

### Connection Pooling
- Configurable pool sizes based on application needs
- Automatic connection validation and reconnection
- Efficient resource utilization under load

### Query Optimization
- Prepared statement support
- Batch operation capabilities
- MySQL-specific query optimizations
- Index utilization awareness

This architecture enables the MySQL backend to provide robust, secure, and performant database access while maintaining compatibility with the core ActiveRecord patterns and supporting the shared test suite ecosystem.