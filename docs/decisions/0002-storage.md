# ADR 0002: 分层版本、元数据与制品存储

Status: accepted architectural direction; storage implementation deferred to P1/P5.
Task: A0-04.

## Context

发布必须可复现，源系统记录和高频遥测不应全部复制进 RDF。工作区内容、审核和部署活动状态不能混为一份可变图。

## Decision

SQLite 为开发元数据基线，PostgreSQL 为交付演练配置，通过 Repository 隔离；迁移和集成测试覆盖两者。TBox/ABox/SHACL/rules/vocabulary/mapping/suite 分层不可变 revision，以 workspace_revision 引用一致快照。

本地内容哈希目录保存原文、解析结果、报告与发布包；提供兼容 S3 的接口，不承诺首版已实现 S3。图数据保留经过治理的事实、推导事件与来源关系，原始高频数据留源系统。源秘密仅持 credential_ref，不保存密码 JSON。

## Alternatives

- 全部数据 RDF 化：查询语义统一，但高频数据膨胀且与双查询路线冲突。
- 图数据库保存全部项目状态：削弱事务/迁移和对象生命周期管理，增加存储耦合。
- 首版只支持云制品存储：不满足本地/内网演示与离线交付。

## Consequences

变更需要创建新内容 revision，哈希不能被当作数字签名。查询必须记录实际图版本与源快照，跨源 best_effort 一致性不得宣称全局原子时点。备份需要覆盖元数据、制品、活动发布和远端图版本。

## Evidence

[原生实测](../../spikes/semantica/reports/0.7.0-ontologyworkspace.3/README.md)：SQLite只读接入、三元组保真与制品hash通过。此证据不覆盖元数据Repository/PostgreSQL迁移或S3实现。

[批准设计](../superpowers/specs/2026-11-10-ontology-workspace-design.md) 和 [总体计划](../superpowers/plans/2026-11-10-ontology-workspace-roadmap.md)。本 ADR 未进行数据库迁移或部署验证。
