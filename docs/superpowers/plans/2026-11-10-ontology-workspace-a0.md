# Ontology Workspace A0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立从零开发的工具仓库，优先交付 P0 Semantica 企业适配层：固定版本、统一接口、对象与异常隔离、真实/Fake 契约及升级兼容性，并交付 ADR、共享契约与可复现 G0/G-P0 证据。

**Architecture:** 自建平台仅实现交付治理与薄适配，语义功能委托 Semantica。A0 先交付可执行技术探针及边界契约，不开发页面、制造业案例或产品业务流程。

**Tech Stack:** Python 3.12、uv、pytest、Pydantic、JSON Schema 2020-12、PyYAML、RDFLib 技术比较；Semantica 发布候选 0.7.0。平台后续使用 FastAPI + React/TypeScript。

**Spec:** ../specs/2026-11-10-ontology-workspace-design.md （用户已批准）。

## Global Constraints

- 从零构建，不读取旧 PoC 或其数据。
- 语义后端逻辑使用 Semantica；React 前端完全自建，不复用 Semantica Explorer。
- 只开发工具，不开发场景模拟、制造业案例、故障规则或业务金标。
- Fake Backend 只用于单元/契约测试，绝不用于产品页面或正式验收。
- 不自建推理引擎；缺少必要 Semantica 能力须报告，不静默降级或把探针失败改成成功。
- A0 必须显式选用 Python 3.12，不能使用默认 python3（本机为 3.9.6）。
- 无大型模型自动下载，不安装 semantica[all]，不通过聊天索取密钥。
- GitHub 目标 https://github.com/ShaohuaQi777/Ontology-Workspace.git；不强推、不改全局 Git 设置、不上传秘密/运行数据/第三方仓库。
- 每任务单一职责提交，提交含任务 ID；状态 TODO/IN_PROGRESS/REVIEW/DONE/BLOCKED。

## Review Focus

1. 发布版本与 main 不一致：测试已安装元数据必须对应选定发布版本，不允许证据混用（Task 2/3）。
2. 可选依赖缺失或模块导入失败：有界错误和失败证据，不伪报 unsupported 为通过（Task 2）。
3. TTL 空白节点、复杂 OWL 公理：往返比较图同构，不因简化 DTO 丢失三元组（Task 2）。
4. 恶意包路径/符号链接及清单完整性：安全验证拒绝逃逸/重复路径/坏哈希；Schema 不能被误称为运行时防护（Task 5）。
5. 推导事实缺少规则/前提或日志含秘密：契约拒绝缺失来源，探针只输出白名单参数与异常摘要（Task 2/5）。

---

## P0–P8 优先级与本批边界

总路线见 [P0–P8 总体开发计划](2026-11-10-ontology-workspace-roadmap.md)。本批不再止于技术探针与文档：新增 A0-06/07/08，实际交付可调用企业 Adapter、Fake Backend 和兼容性执行器。P0 先完成，再进入需要该接口的项目/映射/验证流程。

| 产品优先级 | 纳入的开发内容 | 当前任务/后续门禁 |
|---|---|---|
| P0 | 固定版本、SemanticBackend、对象异常隔离、七类契约、Fake、升级测试 | A0-02/03/06/07/08；G-P0 |
| P1 | 模板/命名空间、五层制品、草稿与分支差异合并、可视化编辑、zh-en 术语、外部本体复用对齐 | 后续 P1-01–06；G-P1 |
| P2 | 字段/值/枚举映射、主数据对齐、实体关系事件抽取、候选批量审核与失败重放 | 后续 P2-01–06；G-P2 |
| P3 | 六状态人工认证，覆盖概念/关系/规则/映射/抽取/冲突策略 | 认证引用在 A0 DTO 预留；状态机/服务在 P3-01–04 |
| P4 | RDF/OWL/SHACL、用户 CQ/金标、规则覆盖率/无答案、五类冲突、回归与定位跳转 | 后续 P4-01–06；G-P4 |
| P5 | 联合发布、Manifest/哈希/依赖/审批、dry-run/健康/smoke/回滚/报告 | A0-05 清单基础；后续 P5-01–05，首远端仍 Oxigraph |
| P6 | ISA-95 风格/系统映射模板、时序窗口、假设与证据、维修/订单关联、多模态派生映射 | 后续 P6-01–07，只有工具扩展，无场景模拟 |
| P7 | SQL/SPARQL/遍历/混合查询、answerability、查询验证执行、来源与推理路径 | 后续独立 P7-01–06；不能越过字段权限门禁 |
| P8 | RBAC/SecretProvider/行列权限、持久队列/run_id、日志审计、离线备份、插件签名 | P0 契约安全前置，P1/P2 起持续实现；G-P8 |

P8 编号靠后不等于安全延后。P3 的认证对象类型/revision/引用预留在 A0，正式发布不能只看 REVIEWED；P7 不在 A0 增加另一套语义引擎；P6 不添加制造业案例、数据或金标。GraphDB/Neo4j 作为追加目标路线，不未经确认覆盖已选 Oxigraph。

## 事实与范围

2026-11-10 查证：PyPI JSON 返回 info.version=0.7.0；Git v0.7.0 标签对象 13108ff0df67be052dd6e60313049370bea5205c，解引用 commit 2a9afec685fe6f4a18350834caed3d6a9affb27a。v0.8.0/0.8.0 标签查询无结果。主分支 pyproject 声明 0.8.0，不代表已发布包。

证据 URL：
- https://pypi.org/pypi/semantica/json
- https://github.com/semantica-agi/semantica/tree/v0.7.0
- https://github.com/semantica-agi/semantica/blob/v0.7.0/semantica/ontology/__init__.py
- https://github.com/semantica-agi/semantica/blob/v0.7.0/semantica/ingest/__init__.py

A0 探针同时建立完整 capability 清单和最低运行证据。必要能力不能实测时，保留成功项目和失败原因，G0 标记未通过；ADR/契约工作可继续，但不进入依赖缺失能力的产品实现。下一波项目/权限、前端、发布、部署均不在本计划实现范围，原设计相关需求明确延期至后续计划。

## 文件结构与责任

执行目录：/Users/shaohua/DeepSeek Harness/Ontology-Workspace（新仓库）；首次建立 main 基线后使用 using-git-worktrees 创建隔离工作区/分支。下列路径相对实际工作树根目录。

- README.md、AGENTS.md、.gitignore、.python-version：工具定位、执行规范、排除运行制品、Python 版本。
- docs/superpowers/specs/2026-11-10-ontology-workspace-design.md：已批准设计副本，保留当前工作区原件，不移动或删除。
- docs/superpowers/plans/2026-11-10-ontology-workspace-a0.md：本计划副本。
- docs/progress/a0.md：任务状态、提交、命令与门禁。
- pyproject.toml、uv.lock：最终环境与依赖锁；探针环境早期独立安装。
- spikes/semantica/{__init__.py,models.py,runner.py,cases.py,fixtures.py,README.md}：证据 DTO、命令行、真实 API 用例、最小技术数据、运行说明。
- spikes/semantica/capability-matrix.md：实测 API、安装 extras、输入输出、版本、失败与限制。
- src/ontology_platform/semantic/{__init__.py,backend.py,dto.py,errors.py}：P0 稳定 Protocol/DTO/错误，不导入 Semantica。
- src/ontology_platform/infrastructure/semantica_adapter/{__init__.py,backend.py,translation.py}：唯一产品级 Semantica 边界。
- src/ontology_platform/infrastructure/backend_factory.py：产品入口只允许真实 Adapter，拒绝 Fake。
- tests/fakes/semantic_backend.py、tests/contract/{semantic_cases.py,test_semantic_backend.py,test_semantic_boundary.py}：Fake、共享契约与对象/异常/导入边界测试。
- scripts/compare_semantic_versions.py、tests/compatibility/test_semantica_upgrade.py、docs/operations/semantica-upgrades.md：隔离版本对比、升级安全测试与说明。
- tests/bootstrap/test_repository.py：仓库基线检查（stdlib unittest）。
- tests/spikes/{test_evidence.py,test_runner.py,test_real_semantica.py}：证据记录、失败行为与真实运行。
- docs/decisions/0001-modular-monolith.md、0002-storage.md、0003-tasks.md、0004-releases.md、0005-semantic-boundary.md：架构决策。
- contracts/{scenario-pack.schema.json,semantic-backend.openapi.yaml,validation-result.schema.json,release-manifest.schema.json}：四项 0.1.0 契约。
- contract_tools/{__init__.py,validate.py}：独立契约/路径校验工具，不是场景生成器。
- tests/contract/test_contracts.py：正反例、路径逃逸、引用解析、清单验证。
- scripts/verify_a0.py：汇总证据、运行契约测试、输出 G0 结果与非零失败码。
- docs/operations/a0-environment.md、docs/reports/a0-report.md：可复现安装与波次报告。

探针生成运行文件放 .runtime/a0/（ignored）。经人工检查的脱敏证据摘要保存 docs/reports/a0-evidence.json；不提交缓存、原始标准错误或整份第三方源码。

### Task 1 / A0-01：可测试的新仓库基线

**Files:** Create README.md、AGENTS.md、.gitignore、.python-version、docs/progress/a0.md、tests/bootstrap/test_repository.py；复制已批准设计与本计划。

**Interfaces:** Produces 测试可运行仓库、main 初始提交、origin、隔离功能工作树；基线 SHA 写入 docs/progress/a0.md。不产生产品 API。

- [ ] 1. 核实新目录尚不存在、目标 remote 引用和现有 Git 用户配置；存在意外文件或 remote 不再为空则先检查，不覆盖。使用 using-git-worktrees 执行指南安排新仓库基线后隔离，不在 Harness 本身初始化 Git。
- [ ] 2. 先创建测试 `test_repository_has_explicit_python`（.python-version == '3.12'）、`test_repository_excludes_runtime_and_secrets`（git check-ignore --no-index 接受 .venv/、.venv-probe/、.venv-repro/、.runtime/、.cache/、.env、*.pem，不排除普通源码或文档）、`test_readme_identifies_tool_only_scope`（README 含“只开发工具”及 Semantica）。
  最低测试断言（stdlib unittest 的方法体）：
  ```python
  def test_repository_has_explicit_python(self):
      self.assertEqual((ROOT / '.python-version').read_text().strip(), '3.12')
  ```
- [ ] 3. `python3.12 -m unittest discover -s tests/bootstrap -v`，预期缺少配置/README 的失败；记录输出，不把 Git 未初始化导致的 unrelated error 当成目标失败。初始化空仓库属于此任务准备，运行前完成。
- [ ] 4. 写最小配置和文档，.gitignore 同时排除 .worktrees/、模型缓存、node_modules/、dist/、SQLite 运行库，允许 .env.example 仅含空占位值。AGENTS 写入 TDD、任务 ID、Semantica 边界、禁止场景数据及安全规范。
- [ ] 5. 重跑同一测试，预期全部通过；`git diff --check` 返回 0；精确 git add 上述文件并 `git commit -m 'chore(A0-01): establish tool-only repository baseline'`。设置 main 和 origin 后记录 SHA，创建隔离功能分支/工作树，再验证测试。

### Task 2 / A0-02：真实 Semantica 技术探针

**Files:** Create spikes/semantica/*、tests/spikes/*、spikes/semantica/capability-matrix.md。

**Interfaces:**
- `ProbeEvidence`：case_id、status（passed/failed/unavailable）、backend_version、api_symbol、run_id、source_refs、parameters（白名单）、artifact_hashes、checks、error_code；不含 secrets 或完整任意异常正文。
- `run_case(case_id: str, output_dir: Path) -> ProbeEvidence`：真实 Semantica 调用或失败记录，无 Fake 回退。
- `run_all(output_dir: Path) -> list[ProbeEvidence]`。
- CLI `python -m spikes.semantica.runner --output .runtime/a0`：每项证据 JSON + 汇总；必要项不通过退出 1。

- [ ] 1. 在隔离工作树用 `uv venv --python python3.12 .venv-probe` 建独立环境；安装候选 `uv pip install --python .venv-probe/bin/python 'semantica[documents,parse-pdf,shacl]==0.7.0' pytest pydantic jsonschema pyyaml`。只安装计划 extras。任何解析/安装失败先记录精确包名和版本，暂停该环境验证，不换 latest 或加 --no-deps 掩盖。核心 import 缺少可选包只能在确认 API 所需后添加最小依赖并记入报告。
- [ ] 2. 写证据与失败测试：`test_version_is_installed_distribution_version`、`test_missing_dependency_records_unavailable`、`test_runtime_failure_records_failed`、`test_exception_does_not_leak_secret`（异常含模拟 token，输出不能出现）、`test_no_fallback_when_semantica_fails`。mock 仅用于这些失败分支；核心成功验证必须真实调用。失败测试 monkeypatch cases 的真实调用入口抛 ImportError 后断言如下，不改变 run_case 签名：
  ```python
  evidence = run_case('parse_pdf', tmp_path)
  assert evidence.status == 'unavailable'
  assert evidence.backend_version == importlib.metadata.version('semantica')
  assert evidence.error_code == 'DEPENDENCY_UNAVAILABLE'
  ```
- [ ] 3. `.venv-probe/bin/python -m pytest tests/spikes/test_evidence.py tests/spikes/test_runner.py -v`，预期未实现模块失败；实现 models.py/runner.py 的证据白名单与 CLI。所有状态均保留 backend_version，未安装时明确 null 并 unavailable，不伪造版本。
- [ ] 4. fixtures.py 在 tmp_path 构造领域无关 CSV/JSON/只读 SQLite、最小文本 PDF 和 DOCX、含空白节点 restriction 的 TTL、SHACL 正反例、两条可推导规则和冲突值。PDF 用最小合法 PDF 字节夹具，不安装另一个语义解析器；DOCX 用已安装 python-docx，仅生成测试文件。所有数据标记技术测试。
- [ ] 5. 写真实参数化测试 `test_native_case[case_id]`。参数覆盖 ingest_csv、ingest_json、ingest_sqlite、parse_pdf、parse_docx、extract_entities_relations_events、build_graph、ontology_generate、ontology_roundtrip、ontology_edit、shacl_pass、shacl_fail、reason_forward、conflict_evidence、provenance_export、query_select_ask、normalize_align。每例断言 native API 实际调用、预期输出/错误、来源与版本；不存在的真实符号作为能力失败证据，不用 monkeypatch 造成功。
- [ ] 6. 运行真实测试，预期未实现 case registry 失败。逐例读取安装包实际源码及签名后实现 cases.py 的最小真实调用；将精确 symbol、source file、signature、输入/输出形态、extras、验证断言写入 capability-matrix.md。已核实的入口候选包括 semantica.ingest.FileIngestor/DBIngestor/OntologyIngestor、semantica.ontology.OntologyEngine/OntologyGenerator/run_shacl_validation。候选不能替代实际调用；其余模块以安装包为准。
- [ ] 7. 特别验证 `test_ontology_roundtrip_retains_blank_nodes` 按 RDFLib isomorphic 比较所有三元组；`test_inference_records_rule_and_premises` 验证源/推导分离及规则/前提可追踪；`test_shacl_negative_case_is_violation` 检查不合格确实 reported；`test_owl_import_not_fetched` 通过阻止外部网络证明 imports 不自动拉取。不要求完整 OWL DL 推理。
- [ ] 8. `.venv-probe/bin/python -m pytest tests/spikes -v` 和 `.venv-probe/bin/python -m spikes.semantica.runner --output .runtime/a0`。预期必要例全部 passed 且错误敏感信息不泄露；若缺口，提交代码/失败证据并标记 A0-02 BLOCKED、G0 未通过，报告扩展 Adapter/上游方案等待确认，不提高成功率或跳过用例。
- [ ] 9. 检查摘要安全、`git diff --check`；精确 add 探针与测试，`git commit -m 'test(A0-02): probe native Semantica capabilities and evidence'`。

### Task 3 / A0-03：环境锁定与全新安装

**Files:** Create pyproject.toml、uv.lock、docs/operations/a0-environment.md；Modify tests/spikes/test_evidence.py。

**Interfaces:** `uv sync --locked --python python3.12` 创建相同依赖图；`uv run --locked python -m spikes.semantica.runner --output .runtime/a0` 用锁定环境重放。

- [ ] 1. 写 `test_runtime_matches_dependency_lock`：解析 uv.lock 与 importlib.metadata，semantica == 0.7.0（仅 Task 2 此候选实测通过时）；Python minor == (3,12)；全部直接运行依赖与锁中版本一致。先在探针环境运行，预期缺少锁失败。
  ```python
  lock = tomllib.loads(Path('uv.lock').read_text())
  semantica = next(p for p in lock['package'] if p['name'] == 'semantica')
  assert semantica['version'] == importlib.metadata.version('semantica') == '0.7.0'
  assert sys.version_info[:2] == (3, 12)
  ```
- [ ] 2. pyproject requires-python='>=3.12,<3.13'，运行依赖为 Task 2 已证实需要的 Semantica extras 与最小 DTO/Schema 库；dev group pytest。项目先只包含 spikes、contract_tools、scripts，不凭空创建产品模块。`uv lock --python python3.12` 固定全部传递依赖，`uv sync --locked --python python3.12`，禁止手工编辑锁来消除冲突。
- [ ] 3. `uv run --locked pytest tests/bootstrap tests/spikes -v`，预期通过；在新且不存在的 .venv-repro 使用 `UV_PROJECT_ENVIRONMENT=.venv-repro uv sync --locked --python python3.12` 和同一环境 `uv run --locked pytest tests/spikes -v`。不删除现有环境；若该路径存在用新命名并记录。
- [ ] 4. 记录实际 Python、Semantica、uv 版本、来源、extras、平台限制、包哈希锁、正常/失败命令与离线可复现边界；本机通过不能代表 Linux/Docker 通过。静态记录主分支与发布差异。
- [ ] 5. `git diff --check`；`git commit -m 'build(A0-03): lock verified Python and Semantica dependencies'`。Task 2 尚未通过时不得将版本写成“已验证”，只锁候选并保留门禁未通过说明。

### Task 4 / A0-04：ADR 与门禁证据

**Files:** Create docs/decisions/0001–0005、scripts/verify_a0.py；Test tests/spikes/test_gate.py。

**Interfaces:** `evaluate_gate(evidence: list[ProbeEvidence]) -> dict`：缺失、重复、失败必要 case 或 backend 版本混用时 passed=false。CLI `uv run --locked python scripts/verify_a0.py --evidence .runtime/a0/summary.json` 输出摘要并退出 0/1；Task 5 完成后加入契约测试结果。

- [ ] 1. 写 `test_missing_case_fails_gate`、`test_unavailable_fails_gate`、`test_duplicate_case_fails_gate`、`test_mixed_backend_versions_fail_gate`、`test_all_required_cases_pass`；先运行 `uv run --locked pytest tests/spikes/test_gate.py -v`，预期导入缺失失败。
  最小失败断言：
  ```python
  def test_missing_case_fails_gate():
      result = evaluate_gate([])
      assert result['passed'] is False
      assert 'build_graph' in result['missing_cases']
  ```
- [ ] 2. 实现只读 evaluate_gate，必要 cases 与 Task 2 参数完全一致。不吞掉异常、不把空 evidence 视作通过、不允许运行后改必要例名单。脚本从 __file__ 定位仓库根并加载 spikes，不能依赖未配置的 src 路径或偶然 PYTHONPATH。
- [ ] 3. ADR 每篇包含 context、accepted decision、alternatives、consequences 和基于 Task 2 的实测链接。覆盖模块化单体、SQLite/PostgreSQL + 内容哈希制品、单 Worker 持久化/重启/取消边界、不可变快照/审批/版本 named graph、Semantica-only 语义逻辑与缺口处理。远端部署未实测则明确后续验证，不能宣称 Oxigraph 已可部署。
- [ ] 4. 同一 gate 测试通过；使用真实 evidence 运行 CLI，实际退出状态决定 G0。测试 PASS 只证明 gate 逻辑，不证明真实 G0 通过。
- [ ] 5. `git diff --check`；`git commit -m 'docs(A0-04): record architecture decisions and evidence gate'`。

### Task 5 / A0-05：四项共享契约与正反例

**Files:** Create contracts/*、contract_tools/validate.py、tests/contract/test_contracts.py；Modify pyproject.toml、scripts/verify_a0.py、docs/progress/a0.md；必要时更新 uv.lock。

**Interfaces:**
- `validate_document(kind: str, document: dict) -> list[dict]`：支持 scenario-pack、validation-result、release-manifest 与 backend-operation，对象错误返回 JSON Pointer + code + message；无错误返回 []。
- `validate_pack_paths(root: Path, manifest: dict) -> list[dict]`：解析 containment、存在性、符号链接、源/入口路径；不执行查询、脚本或解析源内容。
- `verify_release_files(root: Path, manifest: dict) -> list[dict]`：拒绝重复相对路径、逃逸、不存在文件和 SHA256 不匹配。
- CLI `uv run --locked python -m contract_tools.validate --kind KIND --file PATH`，无错误退出 0，有错误退出 1。

- [ ] 1. 写 `test_each_schema_has_positive_and_negative_examples` 参数化四类；`test_pack_major_version_is_supported`、`test_absolute_and_parent_paths_rejected`、`test_symlink_escape_rejected`、`test_missing_pack_entrypoint_rejected`、`test_duplicate_release_path_rejected`、`test_bad_hash_rejected`、`test_inferred_finding_requires_rule_and_premises`、`test_backend_error_is_platform_dto`。先 `uv run --locked pytest tests/contract -v`，预期缺少 Schema/validator 失败。
  最低失败断言；合法例在测试文件中显式构造，不能读产品演示数据：
  ```python
  def test_empty_pack_rejected():
      errors = validate_document('scenario-pack', {})
      assert any(e['code'] == 'SCHEMA_REQUIRED' for e in errors)
  ```
- [ ] 2. JSON Schema 使用 2020-12，schema_version='0.1.0'。Pack 必需 pack_id、version（三段 semver，pack major 支持 1）、domain、ontology_entrypoint、sources；constraints_entrypoint 可选；mappings/rules/competency_questions/expected/evaluation 是可选相对路径。sources 至少一项，每项 id/kind/path；id 不重复需要运行时检查，并补 `test_duplicate_source_ids_rejected`。开放扩展字段不允许伪造核心 required 字段。
- [ ] 3. ValidationResult 必需 run_id、workspace_revision、graph_build_id、backend_version、suite_revision、status、findings、evidence；finding 有 severity、code、resource、message、source_refs，推导 finding 必需 rule_version 与 premise_refs。失败/不可用不能 status=passed。
- [ ] 4. ReleaseManifest 必需 release_id、version、workspace_revision、created_at、backend_version、artifacts、validation_run_ids、approval_id；artifacts 每项 path、sha256（64 位小写 hex）、size（非负）、kind、revision；至少一项。这里只校验清单结构与文件完整性，不实现发布审批或宣称“已发布”。
- [ ] 5. semantic-backend.openapi.yaml 用 OpenAPI 3.1，定义 operationId（ingest/parse/extract/normalize/align/build_graph/import_ontology/edit_ontology/generate_ontology/validate/reason/detect_conflicts/export/capabilities）、版本化 JSON 请求/结果 envelope 和 BackendError。每个 operation 明确所需 source/graph/schema/suite/ruleset/release ID；success 带 run_id/backend_version/source_refs/artifact_refs/parameters；error 带 code/run_id/retryable/message，无第三方 traceback。A0 提供文档契约而非运行 HTTP 服务；测试解析全部 $ref 与 request/response 实例，不拿 YAML 语法成功当作契约通过。
- [ ] 6. 实现 validate.py：Draft202012Validator、受限 YAML safe_load、根目录相对路径检查、resolved containment 与符号链接逃逸检测、流式 SHA256、大小及重复路径检查。仅 Schema 测试不能替代真实临时目录安全测试。不加入场景生成器或执行源包脚本。
- [ ] 6a. 为 P3/P7/P8 预留 object_refs（kind/id/revision）、certification_refs、scope_ref、adapter_version；Extract 候选标记 DRAFT，confidence 可 null，不能输出“已认证”。Release 认证引用与部署依赖记录必须版本绑定。完整认证/查询/插件 Schema 在对应波次实现；预留字段不能被当成已实现鉴权。测试 `test_generated_candidate_is_draft`、`test_null_confidence_is_not_perfect_score`、`test_secret_reference_never_contains_plaintext`。
- [ ] 7. `uv run --locked pytest tests/contract -v`、`uv run --locked pytest tests -v`、`git diff --check`。全部通过后 scripts/verify_a0.py 同时要求 contract pytest 退出 0 和真实 capability gate 通过；缺口继续报告 G0 未通过。
- [ ] 8. 精确 add，`git commit -m 'feat(A0-05): define shared contracts and executable validation'`。契约状态为本工具 0.1.0 提案，不称双方已冻结。

### Task 6 / A0-06 / P0-02–03：统一 SemanticBackend 与企业 Adapter

**Files:** Create src/ontology_platform/semantic/{backend.py,dto.py,errors.py}、infrastructure/semantica_adapter/{backend.py,translation.py}、tests/contract/test_semantic_boundary.py；Modify pyproject.toml/uv.lock 包发现配置，包含 src 包。测试工厂与源码边界以实际根目录定位。

**Interfaces:**
- `SemanticBackend` Protocol：`ingest(IngestRequest) -> IngestResult`、`parse(ParseRequest) -> ParseResult`、`extract(ExtractRequest) -> ExtractionResult`、`build_graph(GraphBuildRequest) -> GraphResult`、`ontology(OntologyRequest) -> OntologyResult`、`validate_shacl(SHACLRequest) -> ValidationResult`、`reason(ReasoningRequest) -> ReasoningResult`、`capabilities() -> list[Capability]`。ontology action 限定 import/edit/generate/export；扩展 normalize/align/conflicts/export 与原 OpenAPI operationId 通过显式映射，不用重命名掩盖操作。
- DTO 位于 dto.py，使用 Pydantic，仅接受平台值类型与 artifact refs。所有请求包含 run_id、workspace_revision、source_refs、scope_ref；每种请求定义对应来源、schema、graph、shape 或 ruleset revision。所有结果包含 run_id、backend_version、adapter_version、source_refs、artifact_refs、object_refs。
- `BackendError(code: str, message: str, run_id: str, retryable: bool)`：业务层唯一语义执行异常，code 枚举依赖不可用/输入不合法/能力未支持/超时/后端失败；不嵌入原生异常对象或 traceback。
- `SemanticaBackend(artifact_root: Path)`：调用 A0-02 已实测 API，读取输出制品并转换 DTO，无法转换时失败，不原样返回任意 native 对象。

- [ ] 1. 写 `test_native_objects_do_not_escape`（返回含 native 对象嵌套列表/字典，必须转换或 BackendError）、`test_native_exceptions_are_wrapped`、`test_business_modules_do_not_import_semantica`（AST 检查，仅 Adapter 和 spikes 例外）、`test_request_result_are_json_serializable`、`test_secret_is_absent_from_result_and_error`；`uv run --locked pytest tests/contract/test_semantic_boundary.py -v`，预期不存在平台模块失败。
- [ ] 2. 实现 Protocol/DTO/BackendError 与上述 Adapter；版本取安装元数据、参数只取允许项。语义行为使用已实测 API，不复制 cases.py 的语义实现；spike 可复用 Adapter 后保持独立真实证据。安全检查先于 native 调用，scope_ref 只绑定运行上下文，不冒称 A0 已实现 RBAC。
- [ ] 3. `uv sync --locked --python python3.12` 与同一测试、真实探针回归。七类调用成功与失败均能输出稳定结果/错误；原生能力缺口仍阻断对应 case。
- [ ] 4. `git diff --check`；`git commit -m 'feat(A0-06): isolate Semantica behind enterprise backend contract'`。

### Task 7 / A0-07 / P0-04：Fake Backend 与七类共享契约

**Files:** Create tests/fakes/semantic_backend.py、tests/contract/{semantic_cases.py,test_semantic_backend.py}、src/ontology_platform/infrastructure/backend_factory.py。

**Interfaces:** `FakeBackend(artifact_root: Path)` 实现 Task 6 同一 Protocol，固定领域无关技术响应、可配置失败，backend_version 明确 fake；`create_backend(kind: str, artifact_root: Path) -> SemanticBackend` 产品工厂只接受 semantica，kind=fake 必须抛配置错误。Fake 只能从测试 fixture 引用，不随产品工厂注册。

- [ ] 1. 写 `test_shared_contract[backend_kind,operation,case]`，同一套七类正反例参数化 Fake/真实 Adapter；`test_factory_rejects_fake`、`test_fake_requires_no_semantica_import_or_network`、`test_fake_does_not_mark_candidates_certified`。先 `uv run --locked pytest tests/contract/test_semantic_backend.py -v`，预期 Fake/工厂未实现失败。
- [ ] 2. 实现 Fake 和共享 cases：输入不合法、缺少来源、语义失败、候选置信度、SHACL violation、规则与前提来源、RDF 空白节点/JSON DTO 等契约相同；不要求 Fake 的复杂语义等价于真实引擎。Fake 支持注入失败只为测试异常路径。
- [ ] 3. `uv run --locked pytest tests/contract/test_semantic_backend.py -v`，真实 Adapter 成功例不能用 Fake 结果替代或 skip 后计入通过。外部模型缺失时真实 Extract 显示 unavailable，并阻断 G-P0，而 Fake 通过仅证明上层可替换。
- [ ] 4. `git diff --check`；`git commit -m 'test(A0-07): share semantic contracts across fake and real backends'`。

### Task 8 / A0-08 / P0-05：版本升级兼容性

**Files:** Create scripts/compare_semantic_versions.py、tests/compatibility/test_semantica_upgrade.py、docs/operations/semantica-upgrades.md；Modify scripts/verify_a0.py、docs/progress/a0.md。

**Interfaces:** `compare_reports(baseline: dict, candidate: dict) -> dict` 输出 compatible、schema_diffs、capability_diffs、semantic_diffs、error_diffs；CLI `uv run --locked python scripts/compare_semantic_versions.py --baseline REPORT --candidate REPORT --output PATH`，不兼容返回 1。报告必须声明真实/Fake、backend/adapter/contract 版本与数据 hash，禁止以 Fake 报告宣称真实版本兼容。

- [ ] 1. 写 `test_removed_field_breaks_compatibility`、`test_exception_mapping_change_breaks_compatibility`、`test_inferred_fact_change_breaks_compatibility`、`test_rdf_blank_node_labels_do_not_break_compatibility`、`test_missing_required_case_breaks_compatibility`、`test_fake_report_not_accepted_as_real_upgrade`；先执行 `uv run --locked pytest tests/compatibility -v`，预期比较器不存在失败。
- [ ] 2. 实现比较器：Schema required/类型/枚举、case 输入版本、能力缺失、稳定错误码、确定性图同构/规则输出和 provenance 结构比较；不比较时戳、run_id 或随机空白节点标签。LLM 输出比较字段与审核状态契约，不假设同提示重采样完全一致。
- [ ] 3. 文档固定升级流程：当前 lock 的真实基线报告 → 独立不存在环境安装显式 candidate 版本/commit → 同一 Adapter/共享用例执行 → 比较差异 → 人工审查 → 新 lock/回归 → 可回退旧环境。禁止测试时改生产 lock 或安装 latest。无新候选时运行当前版本两个隔离环境的自对比与受控破坏报告测试；明确“升级执行器可用，未验证未提供的未来版本”。
- [ ] 4. `uv run --locked pytest tests/compatibility tests/contract tests/spikes -v`。更新 verify_a0：G0=原生探针/锁/基础 Schema，G-P0=G0 + 统一真实/Fake 契约 + 隔离 + 升级执行器验证；任一未满足不得进入依赖 P0 的波次。测试报告不能替代真实 native evidence。
- [ ] 5. `git diff --check`；`git commit -m 'test(A0-08): gate Semantica upgrades on compatibility evidence'`。

## 波次收尾与交付

- [ ] 新 reviewer 审查整个 A0 差异及安全边界，缺陷修复也必须先失败测试；尚未开发的产品能力不得出现在“已完成”清单。
- [ ] 最新 `uv run --locked pytest tests -v`、`uv run --locked python -m spikes.semantica.runner --output .runtime/a0`、`uv run --locked python scripts/verify_a0.py --evidence .runtime/a0/summary.json`、`git diff --check`、`git status --short`，保留实际输出与退出码。不存在失败时才标记 DONE。
- [ ] docs/reports/a0-report.md 写任务/提交/命令/结果/实测限制/运行 CLI/G0/G-P0，并区分原生、Fake 与升级测试证据。无前端因此不制造截图。涉及安装/API/规则能力缺口时回报用户需要决定的选项；G-P0 未通过不进入依赖该接口的项目波次。
- [ ] 审查 git diff --cached 和 tracked files，确认不含 .env、模型、原始运行数据/第三方代码；普通 push 当前 A0 功能分支到 origin。不强推 main，不自动合并；依 finishing-a-development-branch 流程决定集成。认证失败保留本地提交并报告，禁止索取 token。

## 计划自查与明确延期

A0 各项都有可复现入口与待实施状态：Task 1 基线，Task 2 原生 API 能力（含 Extract），Task 3 锁/干净安装，Task 4 ADR/G0，Task 5 基础契约安全，Task 6 统一 Adapter 与隔离，Task 7 Fake/真实共享契约，Task 8 升级兼容性/G-P0。Review Focus 五类及新增对象递归泄漏、Fake 工厂拒绝、升级破坏分别有指定失败测试。run_id/backend_version/source_refs 在探针和契约中保持相同命名；虚拟环境仅早期隔离，最终命令全部使用 uv.lock。

项目 CRUD/RBAC、持久化任务 Worker、产品本体工作室、全对象认证/审批、图部署/回滚、备份恢复、React E2E、制造业工具扩展、SQL/图谱双查询和插件验签在总体计划 P1–P8 的后续波次细化，不在 A0 声称完成；P8 必要安全从对应首个 API/接入前置。Semantica 真实依赖/能力不能安装运行时，此计划交付失败证据而不是替代实现。性能规模等待用户真实数据，A0 不构造业务模拟数据。

## 执行方式建议

建议 Native：在本会话依次实现 A0，任务之间共享同一已安装环境与 capability 发现，避免每任务重新加载大型上下文；波次末使用独立 reviewer 检查整个分支。另一选择是 Subagent-driven：每任务新实现代理与独立 reviewer，审查更密集但上下文开销更高。计划交付后由用户确认执行方式，再加载相应执行 skill。
