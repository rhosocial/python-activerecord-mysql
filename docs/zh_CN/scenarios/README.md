# 应用场景

本节介绍 MySQL 后端的特定使用场景。

## 内容

- [并行工作器](parallel_workers.md)：多进程和异步并发模式

## 概述

并行工作器场景演示了在多进程和异步并发环境中正确使用 MySQL 后端的方法。关键的 MySQL 特有特性包括：

- **行级锁**: InnoDB 支持对不同行的并发写入（不同于 SQLite 的文件级锁）
- **原生异步 I/O**: `mysql-connector-python` 提供真正的网络 I/O 异步（不同于 SQLite 的线程池模拟）
- **死锁自动检测**: InnoDB 检测死锁并回滚开销较低的事务
- **单连接模型**: 每个 ActiveRecord 类绑定到一个连接；多进程是正确的并发方式

## 与核心库场景的关系

本节是[核心库场景](https://github.com/Rhosocial/python-activerecord/tree/main/docs/zh_CN/scenarios)的 MySQL 特定补充，重点关注：

- MySQL 特定的并发行为（行级锁、死锁检测）
- 异步 I/O 的真正优势（网络延迟场景）
- 与 SQLite 的关键区别

核心库场景中介绍的通用 ActiveRecord 使用模式（关系、查询构建、工作池）也适用于 MySQL 后端。

AI 提示: "对于 MySQL 并发，多进程和多线程有什么区别？"
