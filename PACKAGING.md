# Packaging Guide for rhosocial-activerecord-mysql

This guide describes how to build, test, and package the MySQL backend for rhosocial-activerecord.

## Overview

The `rhosocial-activerecord-mysql` package provides MySQL database backend support for the rhosocial-activerecord ORM. It integrates seamlessly with the core activerecord package through Python namespace packages.

## Package Structure

```
rhosocial-activerecord-mysql/
├── src/
│   └── rhosocial/
│       └── activerecord/
│           └── backend/
│               └── impl/
│                   └── mysql/          # MySQL backend implementation
│                       ├── __init__.py
│                       ├── backend.py
│                       ├── connection.py
│                       ├── query_builder.py
│                       └── ...
├── tests/
│   └── rhosocial/
│       └── activerecord_test/
│           └── backend/
│               └── impl/
│                   └── mysql/          # MySQL-specific tests
│                       ├── __init__.py
│                       ├── test_backend.py
│                       ├── test_connection.py
│                       └── ...
├── docs/                              # Documentation
├── examples/                          # Usage examples
├── pyproject.toml
├── README.md
├── LICENSE
├── MANIFEST.in
└── build_hooks.py                     # Custom build hooks
```

## Dependencies

### Core Dependencies
- `rhosocial-activerecord>=1.0.0,<2.0.0` - Core ActiveRecord package
- `mysql-connector-python>=9.3.0` - Official MySQL driver

### Optional Dependencies
- `PyMySQL>=1.1.0` - Alternative pure Python MySQL driver (via `[pymysql]` extra)
- `DBUtils>=3.0.0` - Connection pooling support (via `[pooling]` extra)

## Installation

### Production Installation
```bash
# Basic installation with mysql-connector-python
pip install rhosocial-activerecord-mysql

# With PyMySQL driver
pip install rhosocial-activerecord-mysql[pymysql]

# With connection pooling
pip install rhosocial-activerecord-mysql[pooling]

# All features
pip install rhosocial-activerecord-mysql[all]
```

### Development Installation
```bash
# Clone the repository
git clone https://github.com/rhosocial/python-activerecord-mysql.git
cd python-activerecord-mysql

# Install in editable mode with test dependencies
pip install -e ".[test]"

# Or with all development dependencies
pip install -e ".[dev,test]"
```

## Packaging Modes

### 1. Default Mode
**Purpose**: Production distribution  
**Content**: Only MySQL backend implementation files

```bash
python -m build
```

### 2. Test Mode
**Purpose**: Include tests for verification  
**Content**: Default + test files

```bash
HATCH_BUILD_MODE=test python -m build
```

### 3. Documentation Mode
**Purpose**: Include documentation  
**Content**: Default + documentation files

```bash
HATCH_BUILD_MODE=docs python -m build
```

### 4. Development Mode
**Purpose**: Complete development package  
**Content**: Everything (source + tests + docs + examples)

```bash
HATCH_BUILD_MODE=dev python -m build
```

## Usage

### Basic Usage
```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

# Configure MySQL backend
backend = MySQLBackend(
    host='localhost',
    port=3306,
    user='root',
    password='password',
    database='myapp'
)

# Use with ActiveRecord
class User(ActiveRecord):
    __backend__ = backend
    __tablename__ = 'users'
    
    id: int
    name: str
    email: str

# Create and query records
user = User(name="John Doe", email="john@example.com")
user.save()

users = User.where(name="John Doe").all()
```

### Connection Pooling
```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, PooledMySQLBackend

# Use pooled backend for better performance
backend = PooledMySQLBackend(
    host='localhost',
    port=3306,
    user='root',
    password='password',
    database='myapp',
    pool_size=10,
    max_overflow=20
)
```

## Version Management

The package version is defined in `src/rhosocial/activerecord/backend/impl/mysql/__init__.py`:

```python
__version__ = "1.0.0.dev1"
```

Version format follows [PEP 440](https://packaging.python.org/en/latest/specifications/version-specifiers/).

## Building the Package

### Prerequisites
```bash
pip install build hatchling
```

### Build Commands
```bash
# Build default package
python -m build

# Build with specific mode
HATCH_BUILD_MODE=test python -m build
HATCH_BUILD_MODE=docs python -m build
HATCH_BUILD_MODE=dev python -m build

# Clean previous builds
rm -rf dist/ build/ *.egg-info/
```

## Environment Management

### Using Hatch Environments

#### Test Environment
```bash
# Create test environment
hatch env create test

# Run tests
hatch run test:test

# Run tests with coverage
hatch run test:cov
```

#### Development Environment
```bash
# Create development environment
hatch env create dev

# Format code
hatch run dev:format

# Lint code
hatch run dev:lint

# Run all checks
hatch run dev:all
```

#### Documentation Environment
```bash
# Create docs environment
hatch env create docs

# Build documentation
hatch run docs:build

# Serve documentation locally
hatch run docs:serve
```

## Release Process

1. **Update Version**: Edit `__version__` in `src/rhosocial/activerecord/backend/impl/mysql/__init__.py`

2. **Run Tests**: Ensure all tests pass
   ```bash
   hatch run test:test
   ```

3. **Build Package**: Create distribution files
   ```bash
   python -m build
   ```

4. **Check Package**: Verify the package
   ```bash
   twine check dist/*
   ```

5. **Upload to PyPI**: Publish the package
   ```bash
   twine upload dist/*
   ```

## Troubleshooting

### Import Errors
```python
# Error: ImportError: cannot import name 'MySQLBackend'
# Solution: Ensure rhosocial-activerecord-mysql is installed
pip install rhosocial-activerecord-mysql
```

### Connection Issues
```python
# Error: Can't connect to MySQL server
# Solution: Check MySQL server is running and credentials are correct
# Also ensure the MySQL driver is installed
pip install mysql-connector-python
# or
pip install PyMySQL
```

### Namespace Package Conflicts
```bash
# If encountering namespace issues, reinstall in correct order
pip uninstall rhosocial-activerecord rhosocial-activerecord-mysql
pip install rhosocial-activerecord
pip install rhosocial-activerecord-mysql
```

## Contributing

See CONTRIBUTING.md for guidelines on contributing to this project.