# src/rhosocial/activerecord/backend/impl/mysql/introspection/status_types.py
"""MySQL's own server status families.

These six dataclasses used to live in core's
``rhosocial.activerecord.backend.introspection.status.types``. They named
questions only MySQL answers -- InnoDB's buffer pool, the binary log, the slow
query log, replication as master and as slave -- so every other backend
carried a permanently ``None`` slot that asserted it had something it does
not have. They now live here, on the engine that answers them, and core keeps
the public slots only (``.claude/rules/introspection.md`` §5: ownership is
decided by divergence, and ``extra`` is not a place for another family's
fields).

They are carried over unchanged: same fields, same defaults, same docstrings,
so a caller that read them from core reads the same objects here.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.status import ServerOverview


@dataclass
class InnoDBInfo:
    """InnoDB storage engine information (MySQL specific).

    Attributes:
        buffer_pool_size: Buffer pool size in bytes
        buffer_pool_instances: Number of buffer pool instances
        buffer_pool_pages_total: Total pages in buffer pool
        buffer_pool_pages_data: Data pages in buffer pool
        buffer_pool_pages_dirty: Dirty pages in buffer pool
        buffer_pool_pages_free: Free pages in buffer pool
        buffer_pool_read_requests: Number of read requests
        buffer_pool_reads: Number of reads from disk
        buffer_pool_wait_free: Number of times had to wait for free page
        log_waits: Number of log waits
        log_write_requests: Number of log write requests
        log_writes: Number of log writes
        os_file_reads: Number of OS file reads
        os_file_writes: Number of OS file writes
        os_fsyncs: Number of OS fsyncs
        row_lock_current_waits: Current row lock waits
        row_lock_time: Total row lock time in ms
        row_lock_time_avg: Average row lock time in ms
        row_lock_waits: Number of row lock waits
        rows_read: Rows read
        rows_inserted: Rows inserted
        rows_updated: Rows updated
        rows_deleted: Rows deleted
        data_reads: Data reads
        data_writes: Data writes
        data_read: Data read in bytes
        data_written: Data written in bytes
        extra: Additional backend-specific information
    """

    buffer_pool_size: Optional[int] = None
    buffer_pool_instances: Optional[int] = None
    buffer_pool_pages_total: Optional[int] = None
    buffer_pool_pages_data: Optional[int] = None
    buffer_pool_pages_dirty: Optional[int] = None
    buffer_pool_pages_free: Optional[int] = None
    buffer_pool_read_requests: Optional[int] = None
    buffer_pool_reads: Optional[int] = None
    buffer_pool_wait_free: Optional[int] = None
    log_waits: Optional[int] = None
    log_write_requests: Optional[int] = None
    log_writes: Optional[int] = None
    os_file_reads: Optional[int] = None
    os_file_writes: Optional[int] = None
    os_fsyncs: Optional[int] = None
    row_lock_current_waits: Optional[int] = None
    row_lock_time: Optional[int] = None
    row_lock_time_avg: Optional[float] = None
    row_lock_waits: Optional[int] = None
    rows_read: Optional[int] = None
    rows_inserted: Optional[int] = None
    rows_updated: Optional[int] = None
    rows_deleted: Optional[int] = None
    data_reads: Optional[int] = None
    data_writes: Optional[int] = None
    data_read: Optional[int] = None
    data_written: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BinaryLogInfo:
    """Binary log information (MySQL specific).

    Attributes:
        log_enabled: Whether binary logging is enabled
        log_format: Binary log format (ROW, STATEMENT, MIXED)
        log_files: List of binary log files
        current_log_file: Current binary log file name
        current_log_position: Current position in binary log
        log_size_bytes: Total size of binary logs
        gtid_mode: GTID mode (ON, OFF, ON_PERMISSIVE, OFF_PERMISSIVE)
        gtid_executed: Executed GTID set
        gtid_purged: Purged GTID set
        binlog_rows_query_log_events: Whether rows query log events are enabled
        binlog_checksum: Checksum algorithm used
        extra: Additional backend-specific information
    """

    log_enabled: Optional[bool] = None
    log_format: Optional[str] = None
    log_files: List[str] = field(default_factory=list)
    current_log_file: Optional[str] = None
    current_log_position: Optional[int] = None
    log_size_bytes: Optional[int] = None
    gtid_mode: Optional[str] = None
    gtid_executed: Optional[str] = None
    gtid_purged: Optional[str] = None
    binlog_rows_query_log_events: Optional[bool] = None
    binlog_checksum: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SlowQueryInfo:
    """Slow query log configuration information (MySQL specific).

    Attributes:
        slow_query_log: Whether slow query log is enabled
        slow_query_log_file: Slow query log file path
        long_query_time: Threshold for slow queries in seconds
        log_queries_not_using_indexes: Whether to log queries not using indexes
        log_slow_admin_statements: Whether to log slow admin statements
        log_slow_slave_statements: Whether to log slow slave statements
        min_examined_row_limit: Minimum rows examined to be logged
        slow_queries_count: Number of slow queries recorded
        extra: Additional backend-specific information
    """

    slow_query_log: Optional[bool] = None
    slow_query_log_file: Optional[str] = None
    long_query_time: Optional[float] = None
    log_queries_not_using_indexes: Optional[bool] = None
    log_slow_admin_statements: Optional[bool] = None
    log_slow_slave_statements: Optional[bool] = None
    min_examined_row_limit: Optional[int] = None
    slow_queries_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationSlaveInfo:
    """MySQL slave replication status information.

    Attributes:
        master_host: Master host
        master_port: Master port
        master_user: Master user
        slave_io_running: Whether IO thread is running
        slave_sql_running: Whether SQL thread is running
        seconds_behind_master: Seconds behind master
        master_log_file: Current master log file
        read_master_log_pos: Position read from master log
        relay_master_log_file: Relay master log file
        slave_io_state: IO thread state
        last_io_errno: Last IO error number
        last_io_error: Last IO error message
        last_sql_errno: Last SQL error number
        last_sql_error: Last SQL error message
        relay_log_file: Current relay log file
        relay_log_pos: Position in relay log
        exec_master_log_pos: Executed position in master log
        extra: Additional backend-specific information
    """

    master_host: Optional[str] = None
    master_port: Optional[int] = None
    master_user: Optional[str] = None
    slave_io_running: Optional[str] = None
    slave_sql_running: Optional[str] = None
    seconds_behind_master: Optional[int] = None
    master_log_file: Optional[str] = None
    read_master_log_pos: Optional[int] = None
    relay_master_log_file: Optional[str] = None
    slave_io_state: Optional[str] = None
    last_io_errno: Optional[int] = None
    last_io_error: Optional[str] = None
    last_sql_errno: Optional[int] = None
    last_sql_error: Optional[str] = None
    relay_log_file: Optional[str] = None
    relay_log_pos: Optional[int] = None
    exec_master_log_pos: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationMasterInfo:
    """MySQL master replication status information.

    Attributes:
        binary_log_file: Current binary log file
        binary_log_position: Current binary log position
        binlog_do_db: Databases to replicate
        binlog_ignore_db: Databases to ignore
        gtid_executed: Executed GTID set
        gtid_purged: Purged GTID set
        extra: Additional backend-specific information
    """

    binary_log_file: Optional[str] = None
    binary_log_position: Optional[int] = None
    binlog_do_db: List[str] = field(default_factory=list)
    binlog_ignore_db: List[str] = field(default_factory=list)
    gtid_executed: Optional[str] = None
    gtid_purged: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MySQLReplicationInfo:
    """MySQL replication status information (combines master and slave info).

    Attributes:
        is_master: Whether this server is a master
        is_slave: Whether this server is a slave
        server_id: Server ID
        master_info: Master replication info (if this is a master)
        slave_info: Slave replication info (if this is a slave)
        extra: Additional backend-specific information
    """

    is_master: Optional[bool] = None
    is_slave: Optional[bool] = None
    server_id: Optional[int] = None
    master_info: Optional[ReplicationMasterInfo] = None
    slave_info: Optional[ReplicationSlaveInfo] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MySQLServerOverview(ServerOverview):
    """MySQL's complete status overview: the core shape plus its own families.

    An LSP subclass of :class:`ServerOverview`, so ``get_overview()``'s core
    signature does not change -- the subclass is a legal covariant return --
    and ``to_dict()`` iterates the instance's fields rather than naming them,
    so the four MySQL families below serialize without being re-declared.

    The slots are the engine's own typed answers, each ``None`` until the
    introspector asked for it: a server with binary logging off reports
    ``binary_log.log_enabled is False`` rather than a missing object, and one
    that is not replicating reports ``mysql_replication`` with no master and
    no slave detail.
    """

    innodb: Optional[InnoDBInfo] = None
    binary_log: Optional[BinaryLogInfo] = None
    slow_query: Optional[SlowQueryInfo] = None
    mysql_replication: Optional[MySQLReplicationInfo] = None
