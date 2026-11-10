# Semantica Native Document Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐用户已批准的 Semantica 无损 RDF 文档与有限人工编辑能力，恢复实际原生 G0。

**Architecture:** 原始 Semantica 0.7.0 源码不可变，扩展源码受控并构建明确本地版本 `0.7.0+ontologyworkspace.1`。业务仅经 Adapter 调用 Semantica 原生模块；RDFLib 仍为 Semantica 内部底层库，不在平台替代引擎。之前失败基线保留不改。

**Tech Stack:** Python 3.12、Semantica 0.7.0 base、RDFLib、pytest、uv。

**Spec:** [授权裁决](<docs/superpowers/specs/2026-11-10-semantica-native-document-extension-design.md>)。

## Global Constraints

- 固定源码基线、补丁 SHA256 与真实安装分发版本，保留上游 MIT 许可。
- 不直接修改 site-packages，不伪造 native metadata，不以 Fake/monkeypatch/平台 RDFLib 编辑补出成功。
- 完整三元组、BNodes、复杂 OWL、imports 声明保留；不自动网络 fetch。
- 不实施全 OWL DL、业务模拟、训练或自动大模型下载。生成/修改仍由平台创建新 DRAFT revision。
- 现有 native 失败证据字节与哈希不得更新；绿色单位测试不等于 G0/G-P0。

## Review Focus

- JSON-LD 远程 @context/@import 必须拒绝，普通内联 namespace URI 不应误拒绝（Task 1）。
- RDF/XML DTD/实体/外部引用不得读取文件或发网络请求（Task 1）。
- 标签多语言/匿名 restriction 不能因有限编辑而丢失（Task 1）。
- 未授权路径、无穷大输入、无效 URI/不存在类必须在变更前拒绝（Task 1、2）。
- wheel 内容版本/RECORD 哈希必须对应实际补丁代码，不能只改版本字样（Task 2）。

## File Structure

- `patches/semantica/ontology_document.py`: 发布到 Semantica namespace 的原生模块源码。
- `patches/semantica/manifest.json`: base/version/代码哈希/许可与接口身份。
- `scripts/build_semantica_patch.py`: 从校验过的固定 base 构建带扩展的候选 wheel，不修改安装环境。
- `tests/spikes/test_native_document.py`: 实際安装候选后直接调用 Semantica namespace 验收，无 Fake。
- `tests/spikes/test_patch_build.py`: 可重现构建、版本/RECORD/包路径安全。
- `spikes/semantica/cases.py`: 原生往返/编辑改为候选文档 API。

### Task 1: A0-02E1 无损原生文档

**Consumes:** 已验证 base 0.7.0 的 RDFLib 底层库与严格技术夹具。
**Produces:** `semantica.ontology.document.OntologyDocument.from_rdf(data: str, *, format: str='turtle', base_uri: str|None=None) -> OntologyDocument`；`serialize(*, format: str='turtle') -> str`；`with_label(subject_uri: str, label: str, *, language: str|None=None) -> OntologyDocument`。

- [ ] RED：`test_complex_roundtrip_isomorphic` 输入已归档复杂 TTL，输出 isomorphic=True、imports/BNodes 原样保留。
- [ ] RED：`test_label_edit_is_immutable_and_scoped` 在新文档只替换目标 subject 指定 language 的 rdfs:label；旧文档同构未改、其他语言标签/所有未知三元组保持。
- [ ] RED：`test_remote_context_dtd_invalid_uri_and_oversize_rejected` 远程 context/@import、XML DTD、非法 subject/非 URI/缺少 owl:Class、超过 1 MiB 输入拒绝且无变化。普通内联 namespace URI 允许。
- [ ] Run：`.venv-probe/bin/python -m pytest tests/spikes/test_native_document.py -v`，初始缺原生模块为 RED。
- [ ] Implement 原生模块；内部图私有，返回新文档，不暴露在平台 APIs。Turtle/NT/XML/JSON-LD 只有通过安全预检的格式才开放；未知格式拒绝，禁止任意路径与 URL 读取接口。
- [ ] GREEN：运行相同测试（Task 2 正式构建/安装后）；不动态注入模块取得通过。
- [ ] Commit `feat(A0-02E1): add Semantica native immutable ontology document`。

### Task 2: A0-02E2 可审计候选构建

**Consumes:** fixed base archive/source inventory、Task1 原生源码。
**Produces:** `build_patch(base_dir: Path, output_dir: Path) -> Path` 候选 wheel 与 manifest；真实 distribution version 为 `0.7.0+ontologyworkspace.1`。

- [ ] RED：`test_patch_wheel_version_record_and_module` 确认新增 native module、__version__/METADATA 一致、RECORD 所有实际内容 SHA256 正确；基线内容不得悄然改变。
- [ ] RED：`test_build_is_deterministic_and_rejects_bad_inventory` 相同输入两次 wheel SHA256 一致；不合法 archive/inventory/path traversal/hash mismatch 拒绝。
- [ ] Run：`.venv-probe/bin/python -m pytest tests/spikes/test_patch_build.py -v`。
- [ ] Implement 构建脚本，校验来源/文件哈希，生成正确 wheel metadata/RECORD 与固定时间戳；保留许可。来源不完整时只诊断，不伪造完整性。
- [ ] GREEN：同测试；在隔离候选 venv 使用 uv 安装真实 wheel，确认 `importlib.metadata.version('semantica')` 与原生 module.__file__ 来自候选包。
- [ ] Commit `build(A0-02E2): package audited Semantica document extension`。

### Task 3: A0-02E3 恢复真实 G0 与模型配置

**Consumes:** 已安装候选 wheel 与 Task1 的原生 API。
**Produces:** 新版本真实 G0 evidence（原 0.7.0 evidence 不变），正确小型本地 NLP 配置。

- [ ] RED：现有 native roundtrip/edit 仍失败；将期望版本明确改为候选，不 mock metadata。
- [ ] Implement cases：直接 native `OntologyDocument.from_rdf/serialize/with_label`，同构与有限差分断言；版本测试验证实际分发版本与安装代码。
- [ ] 原生 NER/dependency 未配置模型时继续 fail closed。核实必要最小 spaCy/model 版本、下载体积/许可/来源/哈希，再按已授权项目依赖方式配置本地小模型；绝不自动安装大模型或将 pattern 当 ML。
- [ ] Run `.venv-candidate/bin/python -m pytest tests/spikes/test_native.py tests/spikes/test_native_document.py -v`，必须全真实 GREEN，无 skip/xfail。
- [ ] Run `.venv-candidate/bin/python -m spikes.semantica.runner --output .runtime/a0-candidate`，17 项 native 全通过方可 exit0。
- [ ] Commit `test(A0-02E3): verify candidate native document and complete G0`，若仍有失败，保留并诊断，不写 DONE。

## Return to Approved A0 Plan

E3/G0 成功才返回 A0-03 干净锁安装、A0-05 contracts、A0-06 完整 Adapter、A0-07 共享 Fake/真实契约及产品工厂拒 Fake、A0-08 升级隔离；阶段结束独立全分支 review。保持原 inline 执行方式，用户只在新的必要范围/权限决策处确认。
