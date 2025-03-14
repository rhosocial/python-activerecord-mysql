# Contributing to MySQL Backend for Python ActiveRecord

Thank you for your interest in contributing to `rhosocial-activerecord-mysql`! This document provides guidelines for contributing to this MySQL backend extension for the main ActiveRecord package.

## Getting Started

As `rhosocial-activerecord-mysql` is an extension of the main [`rhosocial-activerecord`](https://github.com/rhosocial/python-activerecord) package, we recommend first familiarizing yourself with the main project's contribution guidelines. Much of the information there applies here as well.

**Please refer to the main project's [CONTRIBUTING.md](https://github.com/rhosocial/python-activerecord/blob/main/CONTRIBUTING.md) for general guidelines on:**

- Where to get help or report issues
- Issue reporting guidelines
- Code style and conventions
- Testing requirements
- Documentation standards
- Ways to support the project
- Donation channels

## Development Setup for Joint Development

Since `rhosocial-activerecord-mysql` depends on [`rhosocial-activerecord`](https://github.com/rhosocial/python-activerecord), there are specific considerations for development setups.

### Option 1: Developing the MySQL Backend

If you're working on enhancing or fixing the MySQL backend itself:

1. Clone both repositories:
   ```bash
   git clone https://github.com/rhosocial/python-activerecord.git
   git clone https://github.com/rhosocial/python-activerecord-mysql.git
   ```

2. Set up symbolic links from the MySQL backend to the main package:
   ```bash
   # On Linux/macOS
   ln -s "$(pwd)/python-activerecord-mysql/src/rhosocial/activerecord/backend/impl/mysql" "$(pwd)/python-activerecord/src/rhosocial/activerecord/backend/impl/"
   
   # On Windows (Command Prompt with admin privileges)
   mklink /D "path\to\python-activerecord\src\rhosocial\activerecord\backend\impl\mysql" "path\to\python-activerecord-mysql\src\rhosocial\activerecord\backend\impl\mysql"
   ```

3. Create a virtual environment and install development dependencies:
   ```bash
   cd python-activerecord
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install main package in development mode
   pip install -e .
   pip install -r requirements-dev.txt
   
   # Install MySQL-specific dependencies
   pip install mysql-connector-python
   ```

4. Run tests that involve the MySQL backend:
   ```bash
   # From the main package directory
   pytest tests/rhosocial/activerecord/backend/mysql80
   ```

### Option 2: Developing Applications Using the MySQL Backend

If you're developing an application that uses `rhosocial-activerecord-mysql`:

1. Clone both repositories:
   ```bash
   git clone https://github.com/rhosocial/python-activerecord.git
   git clone https://github.com/rhosocial/python-activerecord-mysql.git
   ```

2. Install both packages in development mode:
   ```bash
   # Create a virtual environment for your application
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install packages in development mode
   pip install -e ./python-activerecord
   pip install -e ./python-activerecord-mysql
   
   # Now install your application's dependencies
   pip install -r requirements.txt
   ```

3. This setup allows you to modify both packages and immediately see the effects in your application.

## Pull Request Process

1. Ensure your changes work properly with the main [`rhosocial-activerecord`](https://github.com/rhosocial/python-activerecord) package.
2. Update documentation if necessary.
3. Add or update tests to cover your changes.
4. Ensure all tests pass.
5. Submit your pull request to our repository.

## Communication

For issues specific to the MySQL backend, please use the [issues page](https://github.com/rhosocial/python-activerecord-mysql/issues) of this repository.
For broader questions about the ActiveRecord implementation, refer to the main project's communication channels.

Thank you for contributing to `rhosocial-activerecord-mysql`!