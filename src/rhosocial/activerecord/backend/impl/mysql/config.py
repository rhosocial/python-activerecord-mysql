# src/rhosocial/activerecord/backend/impl/mysql/config.py
"""MySQL-specific connection configuration

This module provides MySQL-specific connection configuration classes that extend
the base ConnectionConfig with MySQL-specific parameters and functionality.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple

from rhosocial.activerecord.backend.config import (
    ConnectionConfig,
    ConnectionPoolMixin,
    SSLMixin,
    CharsetMixin,
    TimezoneMixin,
    VersionMixin,
    LoggingMixin
)


@dataclass
class MySQLConnectionConfig(
    ConnectionConfig,
    ConnectionPoolMixin,
    SSLMixin,
    CharsetMixin,
    TimezoneMixin,
    VersionMixin,
    LoggingMixin
):
    """MySQL connection configuration with MySQL-specific parameters.

    This class extends the base ConnectionConfig with MySQL-specific
    parameters and functionality including connection pooling, SSL,
    character sets, timezone handling, and logging options.
    """

    # MySQL-specific authentication
    auth_plugin: Optional[str] = None

    # MySQL-specific connection options
    autocommit: bool = True
    init_command: Optional[str] = "SET sql_mode='STRICT_TRANS_TABLES'"
    # connect_timeout: int = 10
    # Not all versions of mysql-connector-python support these parameters.
    # read_timeout: int = 30
    # write_timeout: int = 30

    # MySQL-specific flags
    use_pure: bool = True
    get_warnings: bool = True
    ssl_disabled: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary, including MySQL-specific parameters."""
        # Get base config
        config_dict = super().to_dict()

        # Add MySQL-specific parameters
        mysql_params = {
            'auth_plugin': self.auth_plugin,
            'autocommit': self.autocommit,
            'init_command': self.init_command,
            # 'connect_timeout': self.connect_timeout,
            # 'read_timeout': self.read_timeout,
            # 'write_timeout': self.write_timeout,
            'use_pure': self.use_pure,
            'get_warnings': self.get_warnings,
            'ssl_disabled': self.ssl_disabled,
        }

        # Only include non-None values
        for key, value in mysql_params.items():
            if value is not None:
                config_dict[key] = value

        return config_dict