#!/usr/bin/env python3
"""
Example: MySQL Connection Pool Stress Test (Synchronous)

This example demonstrates a stress test for the connection pool by having multiple
threads repeatedly acquire and release connections from the same pool.
It verifies the reliability of PooledBackend under concurrent usage.

Run with: .venv_mysql\Scripts\python connection_pool_stress_test_sync.py
Or in MySQL virtual environment

Requirements:
    pip install mysql-connector-python
    pip install -e ..\\..\\python-activerecord\\src
    pip install -e ..\\..\\python-activerecord-testsuite\\src
    # Or use the virtual environment: .venv3.10*
"""

import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("MYSQL_HOST", "")
os.environ.setdefault("MYSQL_PORT", "")
os.environ.setdefault("MYSQL_USER", "")
os.environ.setdefault("MYSQL_PASSWORD", "")
os.environ.setdefault("MYSQL_DATABASE", "")
os.environ.setdefault("MYSQL_CHARSET", "")
os.environ.setdefault("MYSQL_AUTOCOMMIT", "")

# Add the project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", 
                             "python-activerecord", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", 
                             "python-activerecord-testsuite", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", 
                             "python-activerecord-mysql", "src"))

from rhosocial.activerecord.connection.pool import PoolConfig, BackendPool
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


def worker_thread(pool: BackendPool, worker_id: int, iterations: int, lock: threading.Lock):
    """Worker function that repeatedly acquires and releases connections."""
    success_count = 0
    error_count = 0
    
    for i in range(iterations):
        backend = None
        try:
            # Acquire connection from pool
            backend = pool.acquire(timeout=30.0)
            
            # Output backend info for verification
            with lock:
                print(f"  [Worker {worker_id}] Iteration {i + 1}/{iterations}")
                print(f"    threadsafety: {backend.threadsafety}")
                print(f"    mode: {pool.connection_mode}")
            
            # Execute a simple query to verify connection works
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT 1 AS test", [], options=options)
            
            if result.data and result.data[0]["test"] == 1:
                success_count += 1
                with lock:
                    print(f"    [Worker {worker_id}] Query OK")
            else:
                error_count += 1
                with lock:
                    print(f"    [Worker {worker_id}] Query failed: unexpected result")
            
            # Small delay to simulate work
            time.sleep(0.01)
            
        except Exception as e:
            error_count += 1
            with lock:
                print(f"    [Worker {worker_id}] Error: {e}")
        finally:
            if backend is not None:
                pool.release(backend)
    
    return worker_id, success_count, error_count


def main():
    # Pre-set environment defaults to empty strings to prevent accidental leakage
    os.environ.setdefault("MYSQL_HOST", "")
    os.environ.setdefault("MYSQL_PORT", "")
    os.environ.setdefault("MYSQL_USER", "")
    os.environ.setdefault("MYSQL_PASSWORD", "")
    os.environ.setdefault("MYSQL_DATABASE", "")
    os.environ.setdefault("MYSQL_CHARSET", "")
    os.environ.setdefault("MYSQL_AUTOCOMMIT", "")
    
    print("=" * 70)
    print("MySQL Connection Pool Stress Test (Synchronous)")
    print("=" * 70)
    
    # MySQL connection parameters - use environment variables
    mysql_host = (os.environ.get("MYSQL_HOST") or "").strip()
    mysql_port = int((os.environ.get("MYSQL_PORT") or "0").strip() or 0)
    mysql_user = (os.environ.get("MYSQL_USER") or "").strip()
    mysql_password = (os.environ.get("MYSQL_PASSWORD") or "").strip()
    mysql_database = (os.environ.get("MYSQL_DATABASE") or "").strip()
    mysql_charset = (os.environ.get("MYSQL_CHARSET") or "").strip()
    mysql_autocommit = (os.environ.get("MYSQL_AUTOCOMMIT") or "").strip()
    
    mysql_config = {
        "host": mysql_host,
        "username": mysql_user,
        "password": mysql_password,
        "database": mysql_database,
    }
    if mysql_port > 0:
        mysql_config["port"] = mysql_port
    if mysql_charset:
        mysql_config["charset"] = mysql_charset
    if mysql_autocommit:
        mysql_config["autocommit"] = mysql_autocommit.lower() == "true"
    
    print("Environment variables:")
    for key in ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_DATABASE"]:
        print(f"  {key}={os.environ.get(key, 'NOT SET')}")
    print()

    try:
        # Create backend to get threadsafety info
        test_backend = MySQLBackend(**mysql_config)
        test_backend.connect()
        print(f"Backend threadsafety: {test_backend.threadsafety}")
        print(f"  0 = None (not thread-safe)")
        print(f"  1 = mysql-connector (only supports SQL)")
        print(f"  2 = Full thread-safe")
        test_backend.disconnect()
        
        # Create connection pool with higher load
        config = PoolConfig(
            min_size=10,
            max_size=50,
            connection_mode="auto",  # auto-detect based on threadsafety
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: MySQLBackend(**mysql_config)
        )
        
        print(f"\nPool configuration:")
        print(f"  min_size: {config.min_size}")
        print(f"  max_size: {config.max_size}")
        print(f"  connection_mode: {config.connection_mode}")
        print(f"  validate_on_borrow: {config.validate_on_borrow}")
        print(f"  validation_query: {config.validation_query}")
        
        pool = BackendPool.create(config)
        
        print(f"\nEffective connection mode: {pool.connection_mode}")
        
        print(f"\nPool initial stats: {pool.get_stats()}")
        
        # -----------------------------------------------------------
        # Stress test with multiple threads
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Starting stress test with 20 workers, 50 iterations each")
        print("-" * 50)
        
        num_workers = 20
        iterations = 50
        lock = threading.Lock()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_thread, pool, i, iterations, lock)
                for i in range(num_workers)
            ]
            
            for future in as_completed(futures):
                worker_id, success, errors = future.result()
                print(f"Worker {worker_id} completed: {success} success, {errors} errors")
        
        elapsed = time.time() - start_time
        
        # -----------------------------------------------------------
        # Results
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Stress test results")
        print("-" * 50)
        
        stats = pool.get_stats()
        print(f"Total connections created: {stats.total_created}")
        print(f"Total acquired: {stats.total_acquired}")
        print(f"Total released: {stats.total_released}")
        print(f"Current available: {stats.current_available}")
        print(f"Current in use: {stats.current_in_use}")
        print(f"Elapsed time: {elapsed:.2f}s")
        
        # -----------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------
        print("\n" + "-" * 50)
        print("Cleanup")
        print("-" * 50)
        
        pool.close()
        print(f"Pool closed: {pool.is_closed}")
        
        print("\n" + "=" * 70)
        print("Stress test completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure MySQL server is running and credentials are correct.")


if __name__ == "__main__":
    main()