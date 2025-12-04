> **Important**: This document is a supplement to the main **Testing Architecture and Execution Guide** ([local](../../python-activerecord/.gemini/testing.md) | [github](https://github.com/Rhosocial/python-activerecord/blob/main/.gemini/testing.md)). Please read the core documentation first to understand the overall testing architecture, provider patterns, and capability negotiation. This guide focuses only on details specific to the MySQL backend.

# MySQL Backend Testing Guide

## 1. Overview

This guide provides instructions for setting up and running tests for the `rhosocial-activerecord-mysql` backend, covering MySQL-specific configuration, testing patterns, and troubleshooting.

## 2. MySQL Test Environment Setup

### 2.1. Dependencies

In addition to core testing dependencies, the MySQL backend requires `mysql-connector-python`.

```toml
# pyproject.toml
[project.optional-dependencies]
test = [
    # ... other dependencies
    "mysql-connector-python>=9.3.0",
    "rhosocial-activerecord-testsuite",
]
```

### 2.2. Test Scenario Configuration

All database configurations for testing are managed through **test scenarios**. The primary method for defining these scenarios is the `tests/config/mysql_scenarios.yaml` file. This file is git-ignored, so you must create it locally.

The test framework, specifically `config_manager.py` and `providers/scenarios.py`, reads this file to understand which database environments are available for testing.

**Example `tests/config/mysql_scenarios.yaml`:**

This example shows how to configure connections for different versions of MySQL. You should adapt the host, port, and credential details to your local environment.

```yaml
scenarios:
  # Example for a MySQL 8.0 server
  mysql_80:
    host: localhost
    port: 3308
    database: test_activerecord_80
    username: test_user
    password: "your_password"
    charset: utf8mb4
    autocommit: true
    ssl_verify_cert: false

  # Example for a MySQL 5.7 server (commented out by default)
  # mysql_57:
  #   host: localhost
  #   port: 3307
  #   database: test_activerecord_57
  #   username: test_user
  #   password: "your_password"
  #   charset: utf8mb4
  #   autocommit: true
```

Alternatively, for CI/CD environments, you can configure scenarios using environment variables, but the YAML file is recommended for local development.

### 2.3. Setting Up Test Databases with Docker

For a consistent and isolated testing environment, you can use Docker to run MySQL instances.

```bash
# Start a MySQL 8.0 container for the 'mysql_80' scenario
docker run -d \
  --name mysql-test-80 \
  -e MYSQL_ROOT_PASSWORD=your_password \
  -e MYSQL_DATABASE=test_activerecord_80 \
  -p 3308:3306 \
  mysql:8.0
```

## 3. Testing Against the Shared Test Suite

Integrating the MySQL backend with `rhosocial-activerecord-testsuite` involves implementing a set of provider classes that adapt the generic tests to the MySQL environment.

### 3.1. Implement Provider Interfaces by Feature

Instead of a single monolithic provider, the integration is organized by feature. For each feature category defined in the test suite (e.g., `basic`, `query`), a corresponding provider must be implemented in the `tests/providers/` directory.

Each provider (`tests/providers/basic.py`, `tests/providers/query.py`, etc.) is responsible for:
1.  **Setting up the database connection** for its specific test scenario.
2.  **Creating the necessary schema**. This often involves reading a generic SQLite schema file from the test suite and converting it to MySQL-compatible SQL on the fly.
3.  **Configuring and returning the ActiveRecord models** required for the tests in that feature category.
4.  **Handling cleanup** (teardown) after tests are complete.

The `providers/registry.py` file is then used to discover and register all these individual provider implementations, making them available to the test runner.

### 3.2. Import and Execute Shared Tests

With the providers in place, the actual test execution is triggered by files within the `tests/rhosocial/activerecord_mysql_test/feature/` directory.

To ensure maximum compatibility and to prove the backend's adherence to the `testsuite` contract, **it is strongly recommended to import and run the entire suite of tests without omissions.** This approach provides a comprehensive validation of the backend's implementation against the expected behavior.

These test files typically import the test classes directly from the `rhosocial-activerecord-testsuite` package. Pytest fixtures then invoke the appropriate registered provider to set up the environment, allowing the generic tests to run against the MySQL backend.

To enable this, the `rhosocial-activerecord-testsuite` package must be installed and accessible.

```bash
# Ensure the test suite is installed
pip install rhosocial-activerecord-testsuite
```

## 4. Capability Declaration

A critical part of the integration is declaring the backend's supported features. This process is fundamentally separate from the test execution phase.

### Declaration at Backend Instantiation

Capabilities are declared once, during the **backend's instantiation phase**, not during the testing phase. Each backend class, such as `MySQLBackend`, has an `_initialize_capabilities` method that is called upon its creation. This method inspects the database version and other properties to build a `DatabaseCapabilities` object.

**Example: Declaring Capabilities in `MySQLBackend`:**
```python
# src/rhosocial/activerecord/backend/impl/mysql/backend.py
from rhosocial.activerecord.backend.capabilities import (
    DatabaseCapabilities,
    CTECapability,
    JSONCapability
)

class MySQLBackend(StorageBackend):
    def _initialize_capabilities(self):
        """Initializes and returns the backend's capability descriptor."""
        capabilities = DatabaseCapabilities()
        version = self.get_server_version()

        # JSON operations supported from MySQL 5.7+
        if version >= (5, 7, 0):
            capabilities.add_json_operation([
                JSONCapability.BASIC_JSON,
                JSONCapability.JSON_EXTRACT,
            ])

        # CTEs supported from MySQL 8.0+
        if version >= (8, 0, 0):
            capabilities.add_cte(...) # Add specific CTE capabilities

        return capabilities
```

Because this declaration is done upfront, the test suite can automatically read the capabilities from the instantiated backend and skip tests that are not supported, without any additional logic in the test files themselves. This is why the testing phase simply needs to import the test suite.

### Capabilities in Backend-Specific Tests

For backend-specific tests that you write yourself, you are responsible for managing capability checks. If a test relies on a feature that may not be present in all versions of MySQL (e.g., a function only available in MySQL 8.0+), you should use your own mechanism, such as a pytest marker, to skip the test when run against an older version.

## 5. Writing MySQL-Specific Tests

While the shared test suite covers common ActiveRecord functionalities, dedicated tests are often needed for MySQL-specific features or optimizations.

These backend-specific tests can be organized in a separate dedicated directory within `tests/` (e.g., `tests/mysql_specific_tests/`) or, more commonly, interspersed within the feature-based directories under `tests/rhosocial/activerecord_mysql_test/feature/` (e.g., `tests/rhosocial/activerecord_mysql_test/feature/query/test_mysql_window_functions.py`) to align with the `testsuite`'s conventions.

### Example: Testing Full-Text Search

```python
# tests/test_mysql_fulltext.py
def test_mysql_fulltext_search(mysql_backend):
    """Tests MySQL's FULLTEXT search capability."""
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
        # ... fields
    
    Article(title="Python Programming", content="...").save()
    
    # Perform full-text search using MATCH...AGAINST
    results = Article.where(
        "MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)",
        ["Python"]
    ).all()
    
    assert len(results) == 1
```

## 6. Troubleshooting

*   **Issue**: `mysql.connector.errors.DatabaseError: 2003 - Can't connect to MySQL server`
    *   **Solution**:
        1.  Check if your MySQL service is running (e.g., via `docker ps`).
        2.  Confirm that the details in your `mysql_scenarios.yaml` file match your running database instance.
        3.  Try connecting to the database manually to verify credentials.

*   **Issue**: MySQL syntax error, especially when running shared tests.
    *   **Solution**: Check the schema conversion logic in your providers. It may need to be updated to handle more SQLite-to-MySQL syntax differences.

*   **Issue**: Tests skipped due to unsupported capabilities.
    *   **Solution**: Check the `_initialize_capabilities` method in `src/rhosocial/activerecord/backend/impl/mysql/backend.py`. Ensure it correctly declares all supported features based on your MySQL version.

## 7. Quick Command Reference

**Crucial Prerequisite**: Before running any tests, `PYTHONPATH` **must** be set.

```bash
# Set PYTHONPATH (Linux/macOS)
export PYTHONPATH=src

# Set PYTHONPATH (Windows PowerShell)
$env:PYTHONPATH="src"

# ---
# Test Execution
# ---

# Run all MySQL backend tests
pytest tests/

# Run tests for a specific feature
pytest tests/rhosocial/activerecord_mysql_test/feature/basic/

# Run specific tests by name
pytest -k "fulltext"

# View coverage
pytest --cov=rhosocial.activerecord.backend.impl.mysql tests/
```