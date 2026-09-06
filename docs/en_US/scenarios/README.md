# Scenarios

This section covers specific usage scenarios for the MySQL backend.

## Contents

- [Parallel Workers](parallel_workers.md): Multi-process and async concurrency patterns

## Overview

The parallel worker scenario demonstrates correct usage of the MySQL backend in multi-process and async concurrent environments. Key MySQL-specific characteristics include:

- **Row-level locking**: InnoDB supports concurrent writes to different rows (unlike SQLite's file-level lock)
- **Native async I/O**: `mysql-connector-python` provides genuine network I/O async (unlike SQLite's thread-pool simulation)
- **Deadlock auto-detection**: InnoDB detects deadlocks and rolls back the cheaper transaction
- **Single-connection model**: Each ActiveRecord class binds to one connection; multi-process is the correct approach for concurrency

## Relationship with Core Library Scenarios

This section is a MySQL-specific supplement to the [Core Library Scenarios](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios), focusing on:

- MySQL-specific concurrent behavior (row-level locking, deadlock detection)
- True advantages of async I/O (network latency scenarios)
- Key differences compared to SQLite

The general ActiveRecord usage patterns introduced in the core library scenarios (relationships, query building, worker pools) also apply to the MySQL backend.

AI Prompt: "What is the difference between multiprocessing and multithreading for MySQL concurrency?"
