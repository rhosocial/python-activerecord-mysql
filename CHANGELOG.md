## [1.0.0.dev5] - 2025-12-11

### Added

- Added full support for mapped column models and implemented support for annotated adapter query tests and type adapter tests in the MySQL backend. Enhanced test coverage for field and column mapping. ([#6](https://github.com/rhosocial/python-activerecord-mysql/issues/6))



### Fixed

- Resolved schema errors and test cleanup issues in the MySQL backend tests. ([#6](https://github.com/rhosocial/python-activerecord-mysql/issues/6))


## [1.0.0.dev4] - 2025-11-29

### Added

- Refactor type conversion system in MySQL backend with adapters (See [rhosocial/python-activerecord#20](https://github.com/rhosocial/python-activerecord/issues/20)) ([#3](https://github.com/rhosocial/python-activerecord-mysql/issues/3))
- Add backend CLI tool functionality for database operations ([#4](https://github.com/rhosocial/python-activerecord-mysql/issues/4))


## [1.0.0.dev3] - 2025-11-07

### Added

- Added new MySQL backend test infrastructure, including schema definitions, comprehensive query feature tests, extensive CTE support tests, detailed relation management tests, asynchronous backend adaptation, and backend-specific tests. ([#2](https://github.com/rhosocial/python-activerecord-mysql/issues/2))