# Testing

This section covers testing for the MySQL backend.

## Contents

- [Test Configuration](configuration.md): test environment setup
- [Local MySQL Testing](local.md): local database testing

## Provider Responsibilities

For provider implementation guidelines, see the [Core Testsuite Provider Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/testing/provider_guide.md).

### MySQL-Specific Notes

- **Async cursor cleanup**: Failing to close cursors before disconnecting can cause `RuntimeError: Set changed size during iteration`
- **Table conflicts**: Not dropping tables can cause "table already exists" errors

### Implementation Reference

See the test suite documentation for detailed implementation guidelines:
- `python-activerecord-testsuite/docs/en_US/README.md`
- [Core Backend Testing Guide](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/testing/backend_testing.md)
