# Local MySQL Testing

## Overview

This section describes how to set up a local MySQL testing environment.

## Running MySQL with Docker

```bash
# Run MySQL container
docker run -d \
  --name mysql-test \
  -e MYSQL_ROOT_PASSWORD=test \
  -e MYSQL_DATABASE=test \
  -p 3306:3306 \
  mysql:8.0

# Wait for MySQL to start
docker exec mysql-test wait-for-it.sh localhost:3306 --timeout=30
```

## Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: test
      MYSQL_DATABASE: test
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

```bash
docker-compose up -d
```

## Running Tests

```bash
# Set environment variables
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=test
export MYSQL_USER=root
export MYSQL_PASSWORD=test

# Run tests
pytest tests/
```

💡 *AI Prompt:* "What is the difference between Docker and Docker Compose?"
