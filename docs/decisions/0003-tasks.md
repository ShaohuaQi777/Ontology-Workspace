# ADR 0003: 持久化任务表与单 Worker

Status: accepted architectural direction; Worker implementation deferred to P1/P2.
Task: A0-04.

## Context

Pipeline 必须显示真实执行状态、错误、来源、参数版本和运行制品。进程中断不能丢失任务，也不能无条件重试部署副作用。

## Decision

V1 单应用/单 Worker，元数据持久化任务表记录 input revision、run_id、parent_run_id、幂等键、步骤状态、心跳和输出。原子领取任务，支持检查点、interrupted 与有界重放，保留旧失败。

取消为 cancellation_requested，步骤边界处理；阻塞 Semantica 调用未实际终止前不能写 cancelled。仅无外部副作用或有幂等保证的步骤自动恢复。部署不得盲目重试；结果提交前校验快照与取消状态。

## Alternatives

- 纯进程内队列：最简单但重启丢任务和证据。
- 直接引入 Celery/Kafka：可扩展，但增加离线交付和运维依赖，超出初版需要。
- 每条任务启动一个 Agent：扩大成本/权限面，不属于本体工具目标。

## Consequences

不承诺分布式队列安全或即时硬取消；前端轮询持久化真实日志。队列替换保留接口，所有步骤继承可信上下文但不继承客户端自称的权限。重放产生新的 run_id/replay_of，不覆盖旧运行。

## Evidence

[批准设计](../superpowers/specs/2026-11-10-ontology-workspace-design.md)。探针 CLI 与产品 Worker 是不同范围，A0 不宣称任务恢复已实现。
