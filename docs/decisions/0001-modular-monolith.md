# ADR 0001: 模块化单体与自建前端

Status: accepted architectural direction; implementation not yet verified.
Task: A0-04.

## Context

工作台需要跨接入、模型、映射、认证、验证、发布和部署的一致审计。V1 没有多租户计费或超大规模分布式调度目标。用户确认语义后端 Semantica、自建 React 前端，只做工具。

## Decision

采用 domain/application/infrastructure/api 模块化单体。FastAPI 是交付治理和编排边界，不重写语义引擎；React/TypeScript 前端只读真实 API 和任务记录。Semantica 仅在 infrastructure/semantica_adapter 内接入，稳定 DTO/Protocol 隔离上游。

## Alternatives

- 扩展 Semantica Explorer：减少部分界面投入，但不满足自建前端要求且增加内部状态耦合。
- 微服务：独立部署能力强，但增加事务、认证、部署和运维复杂度，不符合 V1 范围。
- CLI only：利于技术探针，但不能满足交付人员独立操作；CLI 保留为测试/运维入口。

## Consequences

初版可共享元数据事务和版本快照，但每个模块需稳定接口；后续 Worker/存储可替换。不得把内部 Semantica 对象传给业务或前端。首批没有 UI，不能造截图或运行轨迹。

## Evidence

[原生探针通过与边界](../../spikes/semantica/reports/0.7.0-ontologyworkspace.3/README.md)：真实 Semantica .3 的17原生能力通过；这不证明FastAPI/React模块化单体已交付。

[批准设计](../superpowers/specs/2026-11-10-ontology-workspace-design.md)。Semantica 可调用能力以 A0-02 真实探针为准，本 ADR 不宣称已经通过。
