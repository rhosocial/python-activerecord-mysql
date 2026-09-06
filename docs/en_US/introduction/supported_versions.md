# Supported Versions

## MySQL Version Support

| MySQL Version | Support Status | Notes |
|--------------|----------------|-------|
| 5.6.x | ❌ End of Life | No longer supported by Oracle |
| 5.7.x | ❌ End of Life | No longer supported by Oracle |
| 8.0.x | ⚠️ Extended Support | Extended support ends April 2026; recommend upgrading to 8.4 LTS |
| 8.4.x | ✅ Recommended | Current LTS version, active premier support |
| 9.0.x | ✅ Supported | Innovation release, adds VECTOR type support |
| 9.6.x | ✅ Supported | Innovation release |
| 9.7.x | ✅ Supported | Latest LTS version, adds JSON Duality Views |

> **Important**: This backend is designed exclusively for MySQL databases. The dialect behavior is tightly coupled with MySQL version-specific features. **Do not use this backend with other MySQL-compatible databases**, including but not limited to MariaDB, TiDB, CockroachDB, PlanetScale, or any other MySQL protocol-compatible systems. Using it with non-MySQL databases may result in incorrect SQL generation, unexpected behavior, or data corruption.

⚠️ **Note**:

- MySQL 5.6 and 5.7 have reached End of Life; using them is not recommended
- MySQL 8.0 is in Extended Support phase; consider upgrading to 8.4 LTS for new deployments
- Some features may have subtle differences between versions, refer to specific feature documentation

## Python Version Requirements

| Python Version | Support Status | Notes |
|---------------|----------------|-------|
| 3.8 | ✅ Supported | |
| 3.9 | ✅ Supported | |
| 3.10 | ✅ Supported | |
| 3.11 | ✅ Supported | |
| 3.12 | ✅ Supported | |
| 3.13 | ✅ Supported | Supports free-threaded build (3.13t) |
| 3.14 | ✅ Supported | Supports free-threaded build (3.14t) |
| 3.15 | ✅ Tested | Pre-release; supports free-threaded build (3.15t) |

**Free-Threaded Python**: Starting from Python 3.13, a free-threaded (no-GIL) build is available as `python3.13t`, `python3.14t`, etc. This backend is compatible with free-threaded Python, though some threading-specific features may behave differently. See documentation for details.

## Dependency Requirements

| Dependency | Version | Notes |
|-----------|---------|-------|
| rhosocial-activerecord | >=1.0.0 | Core library |
| mysql-connector-python | >=8.0.0 | MySQL driver (only supported) |

⚠️ **Important**: This backend only supports mysql-connector-python driver. Other drivers like mysqlclient, PyMySQL are not supported.

💡 *AI Prompt:* "How to use MySQL 8.0's JSON_TABLE function?"
