# Backend Wave2 接入与 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans 按任务inline TDD执行；用户已选择自主实施，仅必要权限/上游缺口确认。一个末尾独立全波review，不逐任务dispatch。

**Goal:** 为既有真实服务增加受控connection、原生readonly读取和versioned Pipeline，不以配置记录或Fake宣称接入成功。

**Architecture:** 复用实际MetadataStore/AccountService/WorkspaceService/JobService；operator target alias隔离server locator，immutable/CAS连接与DAG，原生数据/语义留在Adapter。只有explicit可信target可读取/联网，能力缺口fail closed。

**Tech Stack:** Python3.12、锁定Semantica0.7.0+ontologyworkspace.5/FastAPI/SQLAlchemy、SQLite、已有HTTP/Pillow/spaCy；本波前置不增加大模型/系统安装。

**Spec:** [Wave2拆分设计](../specs/2026-11-11-backend-wave2-design.md)、[总体设计](../specs/2026-11-10-ontology-workspace-design.md)§8/P2/P8。

## 用户最新停点（2026-11-11）

用户明确选择：**只完成 Task3/B2-03 只读数据库接入后就展示**。完成后执行当前阶段全回归与一次独立审查，先普通推送 GitHub，再启动连接真实后端的阶段前端预览，停止开发等待用户反馈。不继续 Task4–6，也不开发其他后续后端；下列 Task4–6 保留为后续设计、当前 DEFERRED，不计完成。没有现成产品前端，允许的小范围阶段预览不等同完整产品前端或全后端完成；不得虚构运行历史。阶段预览源码单独提交并同步仓库，启动核验实际URL。原先全后端完成才push/前端展示的顺序被此checkpoint覆盖。

## Global Constraints

- 按最新checkpoint：B2-03阶段验收后普通GitHub推送并启动阶段预览，然后停止；完整产品前端仍需后续展示确认，不在本阶段开发所有页面。
- 无场景模拟/业务金标，真实native成功不冒充专家认证。全部候选DRAFT。
- 不读取全部环境/secretstore、不请求聊天密码/token、不让URL/query/source/结果含秘密。
- 无任意server path/URL/SQL/eval/插件脚本，无Fake product factory，no dependency pin/global config changes。
- Source/connection/target/DAG/revision/hash授权与新旧run绑定；修改不覆盖旧证据。
- 原生OCR/RAG/CLIP模型未知必须保持未验收；不能靠fallback hash、metadata或固定响应冒充。

## Review Focus

1. trusted alias同名配置变化/跨项目/失效session：创建与执行复查target hash/project许可，不复用旧授权。
2. private path/URL、IPv6 mapped/private mixed DNS/redirect/proxy：拒绝client locator，只有operator explicit trust，native pinning且不跟redirect。
3. source/schema credential字段/多URI/query与SQLite可执行view：写任何持久源前拒绝，列权限在native SELECT前生效。
4. Pipeline cycle/unknown operation/hash变动/取消中间状态：reject/revision-stale/failed后继不执行，新run不覆旧事件。
5. missing native model/secret provider/un联通第三方：fixed unavailable，不降级Fake，不记录成功或完成验收。

---

## Task 1 / B2-01：原生能力与依赖门禁记录

**Files:** Create tests/service/test_native_optional.py、docs/reports/backend-wave2-capabilities.md；纯探针不修改SDK或装依赖。

**Interfaces:** native fixed DBIngestor.execute_query/parse.ImageParser.extract_text/embeddings.TextEmbedder/多模态入口经installed source确认；探针只在测试/Adapter内导入SDK，环境查询不导入native对象进API。

- [ ] 添加技术negative/actual SQLite probe：真实readonlySDK SELECT有rows，UPDATE因ro失败；缺pytesseract/tesseract/transformers/torch的能力明确unavailable，fallback不算神经RAG；print/status无秘密。
- [ ] 先运行探针并保存真实结果/异常code，不将dependency presence当actual OCR/CLIP执行成功。
- [ ] 写精确native接口/限额/依赖/模型/未验收记录；无需要的新依赖就不动锁。涉及大模型/系统OCR/外部凭据时记录必要确认条件。
- [ ] `uv run --locked --offline python -m pytest tests/service/test_native_optional.py -q` exit0后commit `test(B2-01): record native ingestion and optional capability gates`。

## Task 2 / B2-02：可信 Target 与 scoped Connection Registry

**Files:** Create domain/connections.py、infrastructure/connection_schema.py、application/connections.py、tests/service/test_connections.py、docs/operations/connections.md（source文件均在src/ontology_platform/）；Modify api/app.py、api/models.py。

**Interfaces:** `TargetRegistry(targets:dict[str,Target],project_grants:dict[str,set[str]])`只来自operator；`Target(alias,kind,locator,credential_ref=None)`private冻结repr不含locator；`ConnectionService(store,accounts,targets)` initialize/create(actor,pid,name,target_alias)/update(actor,pid,id,base_revision,name,target_alias)/get/list -> frozen ConnectionView(id,project_id,name,target_alias,kind,revision,status='CONFIGURED')。SQLite locator绝对无symlink/private/regular；http固定HTTPS无userinfo/query/fragment，远端http拒绝；feishu固定https://open.feishu.cn。公共DTO不得提交locator/ref/header/role。

- [ ] RED：模块缺失；创建正确权限/opaque id/CONFIGURED；cross-project target无grant403；unknown alias400、malformed locator/credential URI拒绝；GET不泄path/secretref；CAS旧revision409；explicit deny覆盖admin；target配置同alias改变绑定拒绝重用。
- [ ] 最小schema：connections/revisions不可变记录、project FK、target binding hash、CAS current_revision；创建/修改BEGIN IMMEDIATE内live权限及target grant复查与audit。public get/list只projectread。
- [ ] `/api/projects/{pid}/connections` GET/POST，`/{id}`GET/PUT；create_app增加可选operator TargetRegistry（default empty），客户端不能配置server targets。JSON/Origin/错误/限额复用Wave1。
- [ ] `uv run --locked --offline python -m pytest tests/service/test_connections.py tests/service/test_api.py -q` GREEN；commit `feat(B2-02): register scoped trusted source connections`。

## Task 3 / B2-03：真实 native SQLite读取与 source policy

**Files:** Create infrastructure/sqlite_source_policy.py、tests/service/test_database_connections.py；Modify semantic/dto.py、semantic/backend.py、infrastructure/semantica_adapter/backend.py/worker.py/input_policy.py、application/connections.py/jobs.py、infrastructure/workspace_schema.py、source_policy.py、application/workspaces.py、api/app.py/models.py。

**Interfaces:** `DatabaseReadRequest(Request): source,source_revision,table,columns:list[str],limit:int(1..1000)`与DatabaseReadResult；SemanticBackend `read_database(request)`/job operation `read_database`。ConnectionService snapshot(actor,pid,id,base_revision)->SourceSnapshot受target允许table/columns约束；source.constraints由server写入immutable源记录并纳入job绑定，不信任client allowed_columns。HTTP禁止原始SQLite source下载。只生成单条quoted SELECT，不接受原始SQL/where。

- [ ] RED：actual技术DB schema/rows通过SDK readonly native；UPDATE/attach/异常tables/views/virtuals/credential columns rejected；table/columns跨scope在SDK前拒绝；limit/size<=1MiB；source SHA变动与target binding/revision失效；结果onlypermittedfields，raw DB GET403。
- [ ] 增加SQLite预检（readonly schema/bytes、无可执行view/virtual、所有bounded数据credential策略），private snapshot只在许可内登记，无密码字段持久化；constraints检查发生query前。
- [ ] SDK DBIngestor.execute_query在private mode=ro/immutable snapshot运行，typed结果/完整manifest；扩展operation whitelist与replay/pre-run/pre-successbinding而不开放任意operation。保持SDK/异常/日志在private Adapter。
- [ ] `uv run --locked --offline python -m pytest tests/service/test_database_connections.py tests/service/test_jobs.py tests/contract/test_semantic_boundary.py -q` GREEN；commit `feat(B2-03): read authorized SQLite sources through native SDK`。

## Task 4 / B2-04：受控HTTP与飞书SaaS读取

**Files:** Create infrastructure/http_source_policy.py、infrastructure/semantica_adapter/remote_sources.py、application/remote_sources.py、tests/service/test_http_connections.py、tests/service/test_feishu_connector.py；Modify connections/API/typed DTO与job bindings。

**Interfaces:** target alias固定endpoint profile，native `request_with_ssrf_guard`（DNS/IP pin/TLS）读取+native JSONParser；`RemoteSourceService.fetch(actor,pid,connection_id,revision,page_limit)`返回registered sanitized source/run证据。feishu固定wiki/docx只读endpoint分页，不提供任意path/query/header/POST写入。

- [ ] RED：unknown origin/redirect/proxy/private mixed DNS/ipv6mapped/URLcredential、secret absent先拒绝、body<=1MiB/paging<=20/重复cursor/429有限重试、crossscope/stale/ref变动；敏感upstream error/header/body不回显。
- [ ] 复用native SSRF pin、trust_env=False/no redirect/timeouts；credential只transient provider/IPC，禁止request.json中实际token；只持久化sanitizedbody/hash/location/source ACL。
- [ ] 实际loopback技术HTTP验证generic读取/分页/拒绝，用explicit operator本地target且不是fake语义；飞书没实际安全授权就NOT_READY，不称联通。必要操作者安全引用/外网权限单独确认。
- [ ] targetedHTTP/feishu tests GREEN，commit `feat(B2-04): ingest bounded trusted HTTP and SaaS sources`；真实Feishu联调缺口保持追踪未DONE。

## Task 5 / B2-05：有界 versioned Pipeline与 deterministic transforms

**Files:** Create domain/pipeline.py、infrastructure/pipeline_schema.py、application/pipelines.py、infrastructure/transforms.py、tests/service/test_pipelines.py；Modify API/worker job binding。

**Interfaces:** `PipelineService.save(actor,pid,base_revision,nodes,edges)->PipelineRevision`；`run(actor,pid,revision,source_bindings,idempotency_key)->PipelineRun`；最多16nodes/32edges；固定source/connection/native ops与select/rename/cast/null/enumeration白名单。checkpoint(input_hash,output_hash,node_id,job_run_id,state)持久。

- [ ] RED：cycles/duplicateids/unknownop/坏类型/eval拒绝；真实CSV parse→clean→extract或graph实际SDK链；失败不执行后继；节点与workspace/connection/source绑定；stop/restart checkpoint、cancel boundary、explicit new-run replay保留旧，crossscope403。
- [ ] 最小拓扑排序+typed节点与immutable DAG CAS，白名单pure transform（不是语义重写），真实native节点提交同持久JobService；产生DRAFT/source provenance，不自动认证/发布。
- [ ] targeted pipeline/job/security GREEN，commit `feat(B2-05): execute versioned bounded native pipelines`。

## Task 6 / B2-06：OCR/RAG/CLIP门禁与全波验收

**Files:** Create infrastructure/semantica_adapter/optional_capabilities.py、tests/service/test_optional_capabilities.py、docs/reports/backend-wave2-report.md；Modify capability API/acceptance追踪（不提前实现frontend）。

- [ ] RED：provider/model unavailable/模型path或hash失配/禁止联网download/大图/权限/false hash fallback；已许可native依赖才actual小技术OCR/embedding/retrieve/CLIP图文probe，未许可则明确UNAVAILABLE及未验收证据，不靠字段名生成成功。
- [ ] 接入真实chunk/source locations/vector/model/index/retrieval边界必须绑定provenance；不训练、不模拟质量金标。必要大模型/系统OCR权限在此门单独确认（无聊天token）。
- [ ] 真实loopback连接→读取→Pipeline/native→恢复/安全，fresh locked完整suite；一个独立全波review、一次Important RED→GREEN修复。实际未联通能力仍在报告pending，不称全部完成。
- [ ] commit `test(B2-06): verify ingestion pipelines and optional native gates`。

## 计划自检与剩余范围

所有五类review focus各有所属失败测试；业务接口定名与固定限额上列。未细化future模型provider的实现细节，以实际探针/必要许可决定，不在缺模型时偷偷新增依赖或替代产品SDK。完整changeset/模板/认证/发布、Actions/BadCase/只读查询/运维另波，与最新后端先行门一致。inline执行方式已由用户选择，不重开执行菜单。
