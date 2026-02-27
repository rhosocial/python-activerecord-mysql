# 本地 MySQL 测试

## 概述

介绍如何在本地搭建 MySQL 测试环境。

## 使用 Docker 运行 MySQL

```bash
# 运行 MySQL 容器
docker run -d \
  --name mysql-test \
  -e MYSQL_ROOT_PASSWORD=test \
  -e MYSQL_DATABASE=test \
  -p 3306:3306 \
  mysql:8.0

# 等待 MySQL 启动
docker exec mysql-test wait-for-it.sh localhost:3306 --timeout=30
```

## 使用 Docker Compose

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

## 运行测试

```bash
# 设置环境变量
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=test
export MYSQL_USER=root
export MYSQL_PASSWORD=test

# 运行测试
pytest tests/
```

💡 *AI 提示词：* "Docker 和 Docker Compose 有什么区别？"
