## [v1.0.0.dev10] - 2026-03-28

### Added

- Added comprehensive introspection support for MySQL backend, including database schema discovery, metadata retrieval via SHOW commands, CLI introspection subcommand, and batch SQL execution via executescript method. ([#18](https://github.com/rhosocial/python-activerecord-mysql/issues/18))


## [v1.0.0.dev9] - 2026-03-22

### Added

- Added MySQL SET and VECTOR type support, and refactored backend code to extract common functionality into mixin classes for better code reuse between sync and async implementations. ([#16](https://github.com/rhosocial/python-activerecord-mysql/issues/16))


## [v1.0.0.dev8] - 2026-03-20

### Added

- Added MySQL CLI protocol support display with database introspection for version detection, enabling users to view detailed feature availability based on actual server version. ([#12](https://github.com/rhosocial/python-activerecord-mysql/issues/12))
- Added Python version-aware fixture selection for MySQL backend testing, enabling Python 3.10+ UnionType syntax support. ([#13](https://github.com/rhosocial/python-activerecord-mysql/issues/13))



### Fixed

- Reduced cognitive complexity in CLI display_info functions to comply with SonarCloud quality standards. ([#14](https://github.com/rhosocial/python-activerecord-mysql/issues/14))


## [v1.0.0.dev7] - 2026-03-13

### Added

- Added MySQL-specific DDL support including trigger DDL, enhanced CREATE TABLE with LIKE syntax, FULLTEXT/SPATIAL indexes, ENUM/SET type adapters, and spatial type functions. ([#10](https://github.com/rhosocial/python-activerecord-mysql/issues/10))


## [v1.0.0.dev6] - 2026-02-27

### Added

- Adapted MySQL backend to new expression-dialect architecture, rewritten backend tests, and added GROUP BY non-standard SQL behavior tests. ([#8](https://github.com/rhosocial/python-activerecord-mysql/issues/8))


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