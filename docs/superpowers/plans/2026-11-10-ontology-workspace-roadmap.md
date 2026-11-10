# Ontology Workspace P0–P8 总体开发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans 执行经确认的波次实施计划。本文件是优先级、交付物和验收路线；不是已经完成的实现，也不替代各波次逐步骤的 TDD 计划。

**Goal:** 以 Semantica 企业适配层为基础，构建可认证、可验证、可发布部署的本体工具工作台，提供制造业工具扩展和 SQL/知识图谱双查询能力。

**Architecture:** 自建 React 前端与 FastAPI 治理/编排层；统一 SemanticBackend 隔离固定版本 Semantica。语义引擎不重写，行业能力采用版本化模板/插件，SQL 使用只读执行器，不把大量关系型业务数据复制成 RDF。

**Tech Stack:** Python 3.12、FastAPI/Pydantic、React/TypeScript/Vite、SQLite/PostgreSQL、Semantica 固定版本、Oxigraph 远端服务、Docker Compose。新依赖经探针与锁定后引入。

**Spec:** [工具工作台设计](../specs/2026-11-10-ontology-workspace-design.md)。首批实施见 [A0 计划](2026-11-10-ontology-workspace-a0.md)。

## Global Constraints

- 后端语义逻辑使用 Semantica，前端完全自建，不复制 Auto Ontology 应用栈。
- 只做工具开发，不生成制造业场景、案例、模拟生产数据或业务金标。
- 自动生成对象始终为候选；人工认证是独立治理行为，不由模型输出或测试结果代替。
- Fake Backend 仅测试；产品入口禁止 Fake，真实能力不足明确失败。
- 原始遥测留源系统，图谱保存趋势/异常/状态窗口与 provenance；聚合是确定性数据转换，不是替代 Semantica 的语义推理。
- P0 最高优先级；P8 的权限、凭据、run_id 等基础前置，不能因编号靠后而拖到最后。
- 原四项共享契约保留；新认证、查询、插件契约分别版本化，破坏性变化必须提升主版本并提供迁移说明。
- 执行前把每波拆为有精确文件/接口、失败测试、验收命令和任务提交的实施计划。下面所有任务初始状态 TODO，不伪造实际完成状态。

## Review Focus

1. 上游 API/异常/对象变化不得泄漏到业务层；升级前必须同一契约与真实后端比较。
2. 已认证对象修改、分支合并或依赖变动必须产生新 DRAFT revision；不复用旧认证。
3. SQL/SPARQL/图遍历/混合查询必须落实行列权限，不能靠结果页掩码弥补执行越权。
4. 时序、粒度、规则有效期和跨存储查询快照不一致时必须说明限制，不伪装同一时点答案。
5. Secret Provider 不可用或插件验签失败必须拒绝敏感操作，不回退明文存储/加载。

---

## 1. 优先级、依赖与波次

P 编号表示产品优先级与能力分组，不是必须等待前一编号全部结束的串行顺序。

| 优先级 | 工作包 | 主要依赖 | 集成门禁 |
|---|---|---|---|
| P0 | Semantica 企业适配层 | A0 基线、原生探针与锁 | G-P0：真实/Fake 共用契约、对象异常隔离、升级测试可执行 |
| P1 | 本体项目与工作空间 | P0；P8-01/02/04 基础 | G-P1：分层版本、草稿、语义差异合并与基本编辑 |
| P2 | 数据映射与抽取治理 | P0/P1；认证原语 | G-P2：候选可审核、来源完整、失败可重放 |
| P3 | 人工认证 | P1；P8-01/05 | G-P3：所有对象认证有权限、revision 和证据 |
| P4 | 验证与冲突 | P0/P1/P2/P3 | G-P4：结构、规则、冲突、无答案与回归可定位 |
| P5 | 发布部署 | P3/P4；P8 凭据与运行基础 | G-P5：正式发布阻断、健康检查、失败恢复与回滚 |
| P6 | 制造业工具扩展 | P1/P2/P3/P4；插件治理 | G-P6：模板、时序、证据与业务关联能力，不构造场景 |
| P7 | SQL/图谱双查询 | P1/P2/P3/P4；P8 行列权限 | G-P7：四种路径、安全执行、答案解释与无答案 |
| P8 | 企业运行与安全 | 从 P0/P1 起持续嵌入 | G-P8：权限/秘密/恢复/离线/签名演练 |

执行波次：
- Wave 0：A0 + P0 的接口、真实/Fake 契约、升级兼容性；P8 秘密与日志边界先进入 DTO。
- Wave 1：P1 项目/版本与基本自建前端；P3 认证状态机原语；P8 身份、权限、任务基础。
- Wave 2：P2 映射/抽取/人工审核；P3 全对象认证界面；P8 数据范围权限。
- Wave 3：P4 验证、冲突、回归；P7 的模型与 answerability 契约/技术探针，但不抢占 P0。
- Wave 4：P5 联合发布、本地/Oxigraph 部署与回滚；P8 离线安装/备份恢复。
- Wave 5：P6 行业模板与工具扩展、P7 四种查询路径；P8 插件验签与升级收口。

## 2. P0：Semantica 企业适配层

| ID | 交付物 | 验收 | 对应 A0 |
|---|---|---|---|
| P0-01 | 固定 Semantica、Python、extras、传递依赖和能力矩阵 | 新环境 locked install；元数据匹配；版本不足明确失败 | A0-02/03 |
| P0-02 | SemanticBackend Protocol、DTO、Capability、BackendError | Ingest/Parse/Extract/KG/Ontology/SHACL/Reasoning 可经同一接口调用；业务层无原生对象 | A0-06 |
| P0-03 | SemanticaBackend 与异常翻译 | 原生异常、不可 JSON 序列化对象、ImportError 均规范化；敏感值不出 API/日志 | A0-06 |
| P0-04 | 共享契约套件与 FakeBackend | 同一正反例对 Fake 和真实 Adapter 运行；Fake 不被产品工厂接受 | A0-07 |
| P0-05 | 版本升级兼容性执行器与报告 | 基线/candidate 独立环境；Schema、规则语义、RDF 同构和错误行为差异可审查；不兼容阻断升级 | A0-08 |

统一结果保留 backend_version、adapter_version、run_id、输入 revision、source_refs 和 artifact_refs。Extract 候选额外携带 extractor/model_version、confidence（未测量为 null）、来源定位与 DRAFT 状态；模型或可选依赖不可用不生成伪结果。A0 的已有探针必须补真实 Extract，不仅测试 imports。

## 3. P1：本体项目与工作空间

| ID | 交付物 | 验收 |
|---|---|---|
| P1-01 | ProjectTemplate、NamespaceRegistry 与项目向导 | 中英文项目、唯一命名空间和模板版本可追溯；URI 冲突拒绝 |
| P1-02 | TBox/ABox/SHACL/rules/vocabulary 分层 revision | 保存、恢复与发布引用同一 workspace_revision；层之间引用可校验 |
| P1-03 | 草稿、ChangeSet、分支、差异、三方合并 | base/ours/theirs 可复现；同属性矛盾修改进入冲突；空白节点不被粗暴字符串 diff 破坏 |
| P1-04 | 自建概念/关系/属性树图编辑 | CRUD、domain/range、层级、标签与属性预览；不支持的 OWL 表达式保留 |
| P1-05 | SKOS/zh-en 标签、别名和术语治理 | 首选/替代标签、禁用词、重复术语与认证记录关联 |
| P1-06 | 外部标准本体复用与对齐工作区 | 仅加载用户提供或管理员许可的版本；记录许可/来源/哈希；对齐为候选并需认证 |

复用外部本体不等于自动联网拉取 owl:imports；V1 可离线导入依赖，再显式构成验证数据集。分支是工具领域对象而非让每个用户操作 Git。合并不自动继承 CERTIFIED。

## 4. P2：数据映射与知识抽取治理

| ID | 交付物 | 验收 |
|---|---|---|
| P2-01 | 可视化字段/关系映射、预览和差异 | 至少十条可用样例；源不足时显示真实条数；映射绑定 Schema/本体版本 |
| P2-02 | 值转换与枚举映射 | 单位/类型/空值/未知枚举正反例；白名单变换，禁止 eval；修正产生新 revision |
| P2-03 | 主数据实体对齐、别名/主键合并建议 | 跨源 ID、置信度、冲突值与撤回可追踪；高风险合并专家确认 |
| P2-04 | 文档实体/关系/事件抽取与来源视图 | Semantica 真实调用；段落/页/表格位置、source hash、模型版本、置信度齐全 |
| P2-05 | 候选断言队列与批量审核 | 接受/拒绝/修正保留原候选；批量操作逐项权限/结果，不掩盖部分失败 |
| P2-06 | 抽取失败重放 | 固定来源/参数/模型/Schema 快照重放；新 run_id 和 replay_of；不覆盖原证据、不重复应用已审核事实 |

“接受候选”只表示审核决策，不自动获得专家认证。语义相同的重试可以复用缓存，但模型重采样输出不得假称完全确定。实体、关系、事件分别输出评测结果，用户金标若缺失则报告未评测。

## 5. P3：人工认证机制

认证覆盖概念、关系、属性/术语、规则、映射、抽取结果和冲突处理策略。

| 状态 | 含义 | 允许进入方式 |
|---|---|---|
| DRAFT | 自动生成或人工草稿，未认证 | 新建/修改 revision；生成器只能写此状态 |
| REVIEWED | 交付人员已检查 | 有项目审核权限者记录检查结论与证据 |
| CERTIFIED | 领域专家确认 | 专家角色签署当前 revision 与依赖 revision |
| PUBLISHED | 已进入正式发布快照 | 仅成功发布流程生成发布引用，不能直接手动切换 |
| DEPRECATED | 停止新使用，历史仍可追溯 | 授权维护者记录原因与替代 revision；旧发布不修改 |
| REJECTED | 明确拒绝 | 授权审核者记录拒绝原因，保留对象与证据 |

| ID | 交付物 | 验收 |
|---|---|---|
| P3-01 | CertificationRecord、状态机与角色策略 | 生成器不能升级状态；跳过 REVIEWED 直达 CERTIFIED 被拒绝；拒绝必须有原因 |
| P3-02 | 对象 revision 与依赖认证 | CERTIFIED/PUBLISHED 内容变化产生新的 DRAFT；dependency change 使新发布认证无效 |
| P3-03 | 全对象人工认证页面和批量检查 | 来源/差异/有效期可见；批量检查不是批量自动专家认证 |
| P3-04 | 认证门禁与审批集成 | 发布所用治理对象全部 CERTIFIED；参与事实已审核；需要专家确认的抽取对象有认证；策略变更必须重新认证 |

不可变内容 revision 与生命周期记录分离：PUBLISHED 是引用正式 Release 的事件，非覆盖原 revision；DEPRECATED 不篡改已发布制品。一个 revision 可关联多个 Release。REJECTED 的修订产生新的 DRAFT，拒绝历史不抹除。专家可兼任交付角色，但不能用生成者身份冒充专家签署；组织是否要求不同自然人双签作为可配置策略，默认要求相应权限与明确人工操作。

门禁按 object_id + revision + dependency_revision 精确校验；“已 REVIEWED”“测试通过”和“存在认证字段”都不等于 CERTIFIED。

## 6. P4：验证与冲突中心

| ID | 交付物 | 验收 |
|---|---|---|
| P4-01 | RDF/OWL 基础检查、SHACL 编辑执行 | 语法/URI/未定义引用与约束定位到资源；不宣称完整 OWL DL 推理 |
| P4-02 | Competency Questions 与用户 SPARQL 金标 | SELECT/ASK；结果顺序、空值、类型和重复行规则明确；保留原金标，不为适配实现改答案 |
| P4-03 | 规则覆盖率和无答案测试 | 明确规则总数/激活数/被测试规则数；unsupported≠通过；无答案区分无数据/无模型关系/无权限 |
| P4-04 | 数据/规则/版本/时序/粒度冲突 | 五类独立测试、双方证据与适用窗口/粒度、处理策略和认证状态齐全 |
| P4-05 | 发布前后语义回归 | 比较查询、Shapes、推导与认证依赖；不期望破坏阻断发布 |
| P4-06 | 修复建议与定位跳转 | finding 指向 object_id/revision/source_artifact/span；跳转检查项目权限；修复生成 ChangeSet 不自动应用 |

Semantica 负责原生推理/冲突发现；平台组织五类冲突的证据、策略与版本治理。上游缺少原生检测能力时记 capability 缺口，不用前端列表造“已检测”。规则有效期判断是确定性编排门禁；推理算法仍由 Semantica 执行。

## 7. P5：本体联合发布与部署

| ID | 交付物 | 验收 |
|---|---|---|
| P5-01 | 联合 Release 与 Manifest | TBox、ABox、SHACL、映射、规则、词表、验证/认证报告、依赖版本和哈希绑定同一快照 |
| P5-02 | 发布审批、失败拦截和不可变制品 | 未认证、验证失败、旧快照报告/失效认证均阻断；正式版不可覆盖 |
| P5-03 | 本地 RDF 文件与 Oxigraph 服务 Adapter | Dry-run、上传、hash/解析与核心 Smoke Test；失败保留旧活动版本 |
| P5-04 | 部署状态、回滚与报告 | 上一成功版本回滚后健康/核心查询通过；Markdown/HTML 交付报告含来源和限制 |
| P5-05 | GraphDB/Neo4j 等扩展目标契约与探针 | 新 Adapter 独立发布/测试；Neo4j RDF→LPG 的语义映射与损失需明示，不称无损 RDF 部署 |

V1 保留已确认本地 + Oxigraph 首个远端承诺。GraphDB/Neo4j 属于扩展目标路线，不因产品清单出现而同时承诺全部实现；更换首个远端目标须重新确认。原始源秘密不进入发布包。

## 8. P6：制造业专用工具扩展

| ID | 交付物 | 验收 |
|---|---|---|
| P6-01 | ISA-95 风格模板 Schema 与本体模板治理 | 工厂/产线/工位/设备/工序层级可配置、版本化、认证；标注“风格参考”，不冒称标准认证 |
| P6-02 | ERP/MES/SCADA/QMS/CMMS 映射模板 | 系统字段绑定由用户配置；模板含版本/来源/转换约束，不内置企业真实连接或记录 |
| P6-03 | 产品/批次/工艺版本/刀具/部件/人员关联工具 | 关联模板与约束经 Semantica 管理；人员字段受数据范围权限控制 |
| P6-04 | 高频时序聚合接口 | 趋势/异常/状态窗口可配置，输出 window/unit/granularity/source URI/hash；幂等重算与跨时区/迟到数据测试 |
| P6-05 | 故障假设与证据治理 | 用户维护支持/反向/缺失证据；缺失≠反证；规则范围/有效期可查询，专家认证后使用 |
| P6-06 | 维修前后及质量→订单关联视图 | 用户输入驱动的状态比较与多跳查询工具；缺少关系明确不可回答，不生成故障结论或案例 |
| P6-07 | 多模态派生结果映射 | 图片/热像/频谱/声音分析 JSON 与业务对象关联，保留 analyzer_version/时间窗口/confidence/review/status/original URI/hash |

工具模板、可配置聚合、证据管理与关联接口属于开发范围；制造业场景内容、具体故障因果、模拟数据、训练与原始媒体识别仍不开发。行业模板中的概念/映射元数据不得被当作具体企业专家结论；未经专家确认不得默认 CERTIFIED。

## 9. P7：SQL 与知识图谱双查询

流水线：用户问题 → 查询路由 → answerability 检查 → 生成查询计划 → 验证字段/关系/过滤值和权限 → 执行 → 答案、SQL/SPARQL/遍历计划、来源及推理路径。

| ID | 交付物 | 验收 |
|---|---|---|
| P7-01 | QueryRequest/Plan/Result 与 answerability | 绑定 project/actor/model_revision/认证词条/source_scope；缺字段/关系/规则报告 gaps，不猜答案 |
| P7-02 | SQL/SPARQL/traversal/hybrid 路由 | 只读聚合优先 SQL、多跳语义与推理优先图；路径可人工选择，路由说明可审查 |
| P7-03 | 查询生成与静态/目录校验 | SQL AST 白名单、单语句、允许表列/连接/过滤值；SPARQL 禁 UPDATE/SERVICE；不可验证查询拒绝执行 |
| P7-04 | 四种受控执行器与混合关联 | 参数化过滤、只读账号/事务、超时/行数/图跳数限制；跨源 join 基数和单位明确；零写入 |
| P7-05 | 答案与证据/推理路径 | 返回实际执行语句、结果类型、来源引用、模型/规则 revision 和 applied_scope，不生成虚构路径 |
| P7-06 | 无答案、权限、结果回归评测 | 区分 blocked/unanswerable/empty/failed；用户金标执行正确；无权限信息不通过解释/缓存泄漏 |

目录映射和认证词条是 grounding 来源。NL 语义生成与图语义路由优先通过 Semantica 已验证能力；SQL 计划校验、只读执行与跨源 join 属平台工程层，不另建语义引擎。若 Semantica 缺少 NL→SQL/查询生成能力，先提供用户显式查询的受控入口并报告自动生成缺口；另引生成后端需要方案确认，不默认接 Auto Ontology/NIM 或固定收费服务。

只有用户明确配置的模型才能使用；离线环境模型缺失时保留显式 SQL/SPARQL 入口，不自动向云发送 Schema/数据。查询日志只记录授权允许的元数据/脱敏参数，不保存全部敏感行。行列权限在目录、生成、执行、缓存和解释阶段均生效，deny 优先；SQL 写操作/系统目录绕过、敏感列 SELECT *、越权间接 join 与表达式均需负例。

混合查询固定查询计划所用模型/规则/映射 revision，并登记源数据库 snapshot/as_of 与图版本；无法实现跨源原子快照时返回 consistency='best_effort' 与各源时点，不能冒称全局同一时点。空集不等于缺乏模型回答条件。

## 10. P8：企业运行与安全

| ID | 交付物 | 前置时点 | 验收 |
|---|---|---|---|
| P8-01 | 项目 RBAC 与会话授权 | P1 首个 API | 后端逐请求校验；伪造身份 header/跨项目 ID 访问拒绝 |
| P8-02 | SecretProvider 与凭据引用 | P0 DTO/P2 接入 | 元数据/日志/制品不含明文；provider 缺失/不完整拒绝连接配置/执行，不回退 JSON 明文 |
| P8-03 | 行列权限与数据范围 | P2 目录/P7 之前 | allow/deny 配置；采样、映射、生成、执行、答案、缓存与解释一致 |
| P8-04 | 持久化队列、恢复、run_id 与 Pipeline 日志 | P1/P2 | 子步骤 parent_run_id、重启 interrupted、幂等重放；不把请求取消写成已经终止 |
| P8-05 | 审计日志 | P1/P3 | 谁/何时/对象 revision/审批/认证/来源可追溯；秘密字段永不写入 |
| P8-06 | 离线安装、备份恢复 | P5 | 指定镜像/依赖包与许可清单；空环境恢复演练；离线无外部网络依赖 |
| P8-07 | 插件签名、版本和兼容性 | P6 扩展加载之前 | 可信公钥集合、manifest 签名、逐文件哈希、SDK 范围；篡改/撤销 signer/不兼容版本拒绝加载 |
| P8-08 | 内部信任边界与运维收口 | API/部署全程 | Worker/数据库/图服务不对外裸露；入口独立鉴权，网络隔离不能替代身份授权 |

V1 保持单应用/单 Worker，队列表支持后续替换，但不承诺现在实现分布式队列。插件先支持受限声明式模板/映射包，不是任意 Python/JS 上传执行；签名证明完整性与发布者，不证明任意代码安全。签名与制品 SHA256 是不同机制，Release hash 不冒充签名。

## 11. 联合契约及质量出口

新增设计契约：certification-record.schema.json、query-plan.schema.json、query-result.schema.json、plugin-manifest.schema.json。P0 预留对象 revision/认证引用/作用范围；新契约的运行时服务分别在 P3/P7/P8 实现，避免全部塞进首批 A0。

认证记录绑定 actor、role、object kind/id/revision、dependency_refs、decision、reason、evidence、有效期与审计 ID。查询计划绑定只读操作类型、表/字段/关系 allowlist、参数、授权 scope、图/源快照、超时/行数；结果绑定实际语句/路径、來源与状态。插件清单绑定 package_id/version、sdk_range、签名算法/key_id、制品哈希、依赖与声明式能力范围。

每波次报告真实测试、失败明细和未实现能力。P6 没有业务场景包、P7 没有用户业务金标时，验收“工具行为与安全”，不报告制造业正确率或 30 项业务问题完成。

## 12. Auto Ontology 参考与本项目控制措施

已读取官方 [Connections](https://github.com/NVIDIA/auto-ontology/blob/main/docs/connections.md) 与 [README](https://github.com/NVIDIA/auto-ontology/blob/main/README.md)，读取日期 2026-11-10；仅核实文档陈述，未安装或审计该产品。

Connections 文档写明未配置 Vault 时 UI 连接对象（含密码）以未加密 JSON 保存于 Postgres；部分 Vault 配置会警告并回退明文。文档还说明接入与问答对于 UI 连接/环境连接的优先级不同。README 写明后端信任前端转发的用户身份 header、接入服务部分端点无独立鉴权，要求相关服务放私网；README 描述人工 certification，但不能据此认定它使用本计划的六状态状态机。

本项目不复制这些回退/信任方式：统一 SourceConnectionRegistry 供接入/问答/部署授权选择，秘密仅引用；未配置 SecretProvider 禁止持久化凭据；所有敏感 API 检查可信会话/服务身份，拒绝伪造 header，并以网络最小暴露做纵深防护。六状态是用户要求的本项目机制，不是对 Auto Ontology 已有实现的宣称。

## 13. 待细化而非阻塞当前文档整合的事项

- P0 实测后确定语义能力缺口与扩展方式；必要能力不足阻断对应实现。
- GraphDB/Neo4j 追加目标的具体版本与语义映射，在 P5-05 探针后决定；不覆盖 Oxigraph 已确认基线。
- P7 自动生成能力/模型部署和源数据库类型，在其独立详细设计中确认；先支持 SQLite/PostgreSQL 只读基线，不承诺全部 SQL 方言。
- 插件 signer/公钥轮换策略由企业部署决定；本项目提供管理与验签工具，不接收私钥。
- 实施方法尚未选择，文档整合不是启动全部 P0–P8 的授权，也不伪造 GitHub 已同步。
