# ADR 0005: 固定 Semantica 与 fail-closed 企业适配

Status: accepted boundary; candidate 0.7.0 under installation/probe, not yet certified compatible.
Task: A0-04; depends on A0-02/03/06/07/08.

## Context

主分支配置版本与发布版不同，不能仅依据文档选 API。用户要求以 Semantica 执行语义逻辑并控制快速变化风险。

## Decision

通过平台 SemanticBackend Protocol、稳定 DTO 与 BackendError 调用固定 Semantica。Ingest/Parse/Extract/KG/Ontology/SHACL/Reasoning 共享真实/Fake 契约。产品代码仅 Adapter 导入 Semantica，递归检查结果类型和来源，不能原样传 native 对象/异常/traceback。

Fake 仅单元/契约测试，产品工厂拒绝 Fake。不支持/依赖缺失/验证失败必须带明确错误，不静默切换替代语义引擎。原始生成结果为 DRAFT，未知 confidence 用 null。

升级在隔离环境执行相同契约、确定性图同构、推理/来源/错误行为对比，并人工审查差异后更新锁；当前版本自对比或 Fake 用例不能证明未来真实版本兼容。

## Alternatives

- 业务层直接使用 native 类：开发快，但污染版本边界，增加升级与异常泄露风险。
- 宽泛依赖 main/latest：无法可靠复现已发布结果。
- 上游出错回退 Fake/RDFLib 自建语义引擎：表面连续可用，但违反真实运行与后端选择。

## Consequences

必要能力缺失会阻断对应门禁；项目与制品浏览可继续，语义操作显示不可用。若上游不足，必须提供实测证据和扩展 Adapter/上游贡献方案，经必要确认后实施。框架版本与完整传递依赖来自已验证锁。

## Evidence

[固定版本探针计划](../superpowers/plans/2026-11-10-ontology-workspace-a0.md)。实际证据将在 A0-02 输出；当前没有“已兼容”声明。
