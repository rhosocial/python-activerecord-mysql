# rhosocial-activerecord MySQL Backend Documentation

> **AI Learning Assistant**: Key concepts in this documentation are marked with AI Prompt. When you encounter concepts you don't understand, you can ask the AI assistant directly.
>
> **Example:** "How does the MySQL backend handle transactions? How does it differ from SQLite?"

## Table of Contents

1. **[Introduction](introduction/README.md)**
    *   **[MySQL Backend Overview](introduction/README.md)**: Architecture, sync/async parity, and quick example
    *   **[Relationship with Core Library](introduction/relationship.md)**: How the backend integrates with rhosocial-activerecord
    *   **[Supported Versions](introduction/supported_versions.md)**: MySQL, Python, and dependency version matrix

2. **[Installation & Configuration](installation_and_configuration/README.md)**
    *   **[Installation Guide](installation_and_configuration/installation.md)**: pip installation and driver setup
    *   **[Connection Configuration](installation_and_configuration/configuration.md)**: Host, port, database, credentials, and advanced options
    *   **[SSL/TLS Configuration](installation_and_configuration/ssl.md)**: Secure connection settings
    *   **[Connection Management](installation_and_configuration/pool.md)**: Connect-on-use lifecycle and async pool roadmap
    *   **[Character Set / Encoding](installation_and_configuration/charset.md)**: utf8mb4 configuration and best practices

3. **[MySQL Specific Features](backend_specific_features/README.md)**
    *   **[Field Types](backend_specific_features/field_types.md)**: SET, ENUM, JSON, TEXT vs VARCHAR
    *   **[Dialect Expressions](backend_specific_features/dialect.md)**: MySQL-specific SQL syntax and functions
    *   **[Storage Engines](backend_specific_features/storage_engine.md)**: InnoDB, MyISAM selection
    *   **[Indexing](backend_specific_features/indexing.md)**: Index types and optimization strategies
    *   **[EXPLAIN](backend_specific_features/explain.md)**: Query execution plan analysis
    *   **[Introspection](backend_specific_features/introspection.md)**: Database metadata queries
    *   **[Partitioning](backend_specific_features/partition.md)**: Table partitioning strategies

4. **[DDL Operations](ddl/README.md)**
    *   **[DDL Overview](ddl/README.md)**: CREATE TABLE, ALTER TABLE, DROP TABLE

5. **[Transaction Support](transaction_support/README.md)**
    *   **[Isolation Levels](transaction_support/isolation_level.md)**: READ COMMITTED, REPEATABLE READ, etc.
    *   **[Savepoint](transaction_support/savepoint.md)**: Nested transactions
    *   **[Deadlock Handling](transaction_support/deadlock.md)**: Auto-detection and retry strategies

6. **[Type Adapters](type_adapters/README.md)**
    *   **[Type Mapping](type_adapters/mapping.md)**: MySQL to Python type conversion
    *   **[Custom Adapters](type_adapters/custom.md)**: Extending type support
    *   **[Timezone Handling](type_adapters/timezone.md)**: UTC and local timezone

7. **[Testing](testing/README.md)**
    *   **[Test Configuration](testing/configuration.md)**: MySQL-specific test setup
    *   **[Local Testing](testing/local.md)**: Docker-based local test environment

8. **[Troubleshooting](troubleshooting/README.md)**
    *   **[Connection Errors](troubleshooting/connection.md)**: Error codes and diagnostics
    *   **[Performance Issues](troubleshooting/performance.md)**: Slow query analysis

9. **[Scenarios](scenarios/README.md)**
    *   **[Parallel Workers](scenarios/parallel_workers.md)**: Multi-process and async concurrency patterns

10. **[Customization](customization/README.md)**
    *   **[Custom Expressions](customization/custom_expressions.md)**: MySQL-specific SQL extension classes
    *   **[Custom Data Types](customization/custom_types.md)**: Custom DataType subclasses
    *   **[Custom Type Adapters](customization/custom_adapters.md)**: Custom Python-to-MySQL converters

11. **[Command-Line Interface](cli/README.md)**
    *   **[CLI Overview](cli/README.md)**: Commands for querying, introspecting, and managing MySQL

> **Core Library Documentation**: For the complete ActiveRecord framework (modeling, querying, relationships, performance, worker pools), refer to [rhosocial-activerecord documentation](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US).
