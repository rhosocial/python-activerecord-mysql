# Common Connection Errors

## Overview

This section covers common MySQL connection errors and their solutions.

## Connection Refused

### Error Message
```
ERROR 2003 (HY000): Can't connect to MySQL server
```

### Causes
- MySQL service is not running
- Incorrect port
- Firewall blocking

### Solutions
```bash
# Check if MySQL is running
sudo systemctl status mysql

# Check port
telnet localhost 3306
```

## Authentication Failed

### Error Message
```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

### Causes
- Incorrect username or password
- User does not have remote access permissions

### Solutions
```sql
-- Execute on MySQL server
CREATE USER 'user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON database.* TO 'user'@'%';
FLUSH PRIVILEGES;
```

## Connection Timeout

### Error Message
```
ERROR 2003: Can't connect to MySQL server (110)
```

### Causes
- Network issues
- connect_timeout setting is too short

### Solutions
```python
config = MySQLConnectionConfig(
    host='remote.host.com',
    connect_timeout=30,  # Increase timeout
)
```

## SSL Connection Error

### Error Message
```
ERROR 2026 (HY000): SSL connection error
```

### Causes
- SSL certificate issues
- Incorrect SSL configuration

### Solutions
```python
config = MySQLConnectionConfig(
    host='remote.host.com',
    ssl_verify_cert=False,  # Disable certificate verification (testing only)
)
```

💡 *AI Prompt:* "How to troubleshoot MySQL connection errors?"
