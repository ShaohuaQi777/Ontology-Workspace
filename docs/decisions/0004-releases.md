# ADR 0004: 不可变联合发布与版本化部署

Status: accepted architectural direction; deployment verification deferred to P5.
Task: A0-04.

## Context

交付不能只导出一份 TTL。审核、认证、规则、Shapes、映射、验证结果和版本依赖共同决定发布有效性。

## Decision

Release Manifest 固定 workspace_revision、backend/adapter 版本、制品 hash、验证运行和人工审批/认证引用。临时目录生成并校验后原子封存，release_id 不覆盖。治理对象须 CERTIFIED，参与断言须审核，失效认证/失败验证阻断正式发布。

本地文件部署用版本目录与活动指针。首远端 Oxigraph 独立服务，asserted/inferred 为版本 named graph，工作台显式选择版本数据集。dry-run、健康/核心查询 smoke test 与失败恢复必要；回滚选择上一已验证版本，再检查健康和核心查询。旧图不无条件删除。

## Alternatives

- 原地覆盖默认图：操作简单，但无法可靠回滚和重现实验。
- 同时实现所有图数据库：分散测试与部署责任，违背 V1 边界。
- 自动生成后直接发布：违反人工治理要求。

## Consequences

工作台活动指针不代表第三方默认图查询自动切换。GraphDB/Neo4j 属后续 Adapter；Neo4j 属性图转换需声明 RDF/OWL 语义差异。制品 hash 保证完整性，不是签名。离线包不包含源秘密。

## Evidence

[批准设计](../superpowers/specs/2026-11-10-ontology-workspace-design.md)。Oxigraph 未在 A0 部署，不宣称健康/回滚已验证。
