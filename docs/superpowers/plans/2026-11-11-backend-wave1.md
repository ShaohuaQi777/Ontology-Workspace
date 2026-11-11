# Backend Wave 1 — 可信服务与持久化执行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (用户已选择inline) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本计划细化已批准后端设计，不启动产品前端；用户新顺序覆盖旧Wave1前端/提前A0push步骤。

**Goal:** 交付真实本地账户/项目权限、工作空间revision、来源制品、持久化任务和FastAPI服务，使既有Semantica七操作经受权限保护的HTTP任务生命周期执行。

**Architecture:** 延续domain/application/infrastructure/api模块化单体。SQLAlchemy Repository负责元数据事务，SQLite开发基线/PostgreSQL后续真实交付；文件制品单独存储，Semantica仅Adapter。API只入队，单Worker领取任务并执行，事件与状态持久化；不宣称分布式/RSS/网络OS沙箱。

**Tech Stack:** Python3.12；当前locked Semantica0.7.0+ontologyworkspace.5、Pydantic2.14.3、SQLAlchemy2.1.8；FastAPI/Uvicorn/HTTPX在首次HTTP任务进行固定版本来源/许可证/兼容性探针后锁定，不安装standard/all额外栈。Auth采用stdlib PBKDF2-SHA256（600000迭代、随机16-byte salt）及高熵opaque会话，DB只保存session摘要；Cookie HttpOnly/SameSite Strict，部署Secure必需。

**Spec:** docs/superpowers/specs/2026-11-10-ontology-workspace-design.md（14、73–89、109–117、213–215），docs/superpowers/plans/2026-11-10-ontology-workspace-roadmap.md（P1/P3原语/P8前置），用户2026-11-11最新完整后端优先/前端整版展示确认要求。本文是既定架构的执行细化；产品前端方案仍需未来整版展示审批。

## Global Constraints

- 后端语义逻辑使用Semantica，前端完全自建；本波不开发产品UI。
- 只做工具开发，不生成制造业场景、案例、模拟生产数据或业务金标。
- Fake Backend仅测试；产品入口禁止Fake，真实能力不足明确失败。
- 自动生成对象始终为候选；人工认证是独立治理行为，不由模型输出或测试结果代替。
- API不接受客户端伪造身份header；每个项目操作检查授权，隐藏按钮不算权限控制。
- 秘密只用环境变量/SecretProvider引用，普通DTO/日志/URI/报告/制品不保存明文密码/token。Login密码SecretStr瞬态处理；session只以HttpOnly Cookie传输，不出现在JSON/UI，持久化仅摘要。
- 新依赖先核验/兼容探针，再项目内锁定；不改全局设置、不装large模型、不静默发送源数据外网。
- 新内容revision DRAFT、immutable；认证附属证据绑定内容与依赖revision，修改产生新DRAFT，认证不自动继承。
- 单应用实例、单Worker持久化任务；取消仅在边界生效，不假称立即终止native进程。
- 完整后端真实验收后直接安全GitHubpush，无再次提醒；本波子集不视作完整后端。不force、不自动合并。

## Review Focus

1. Cookie/身份header/项目ID伪造、已撤销session、非成员访问源/任务/制品或worker越权。
2. JSON/body/validation异常/日志/持久化泄露密码、URI userinfo或原始native异常；SecretProvider不可用不得降级明文。
3. revision并发覆盖、认证跨revision复用、同幂等键不同输入与worker重复领取造成重复副作用。
4. 用户路径/符号链接/大body/坏hash导致制品逃逸；元数据DB与可上传文件隔离，可信server-root边界不是OS沙箱。
5. 任务崩溃恢复/取消/过期权限/输入快照变动仍写成功，或health/startup失败被伪称部署成功。

## File Structure 与接口

- `infrastructure/metadata.py`：SQLAlchemy schema/engine/transactions/version gate，真实SQLite文件、foreign keys，未来PostgreSQL同schema但未实测不声称交付。
- `domain/service_errors.py`：稳定非敏感ServiceError(code/status)，HTTP不得返回exc/input/traceback。
- `application/accounts.py`：账户/密码hash/session/项目成员授权；没有浏览器UI。
- `infrastructure/secrets.py`：SecretProvider Protocol与显式环境引用provider；不扫描全部环境/不回退明文配置。
- `application/workspaces.py`：项目namespace唯一、层revision CAS、不可变内容与草稿、来源registration。
- `application/jobs.py`：提交/领取/事件/取消/interrupted/CAS完成与权限检查；payload绑定actor/project/revisions。
- `application/worker.py`：一步真实Semantica执行器，输入由登记SourceSnapshot解析，不接受任意文件路径。
- `api/{app.py,models.py,auth.py,middleware.py,server.py}`：protected HTTP API、body/origin/error边界、loopback启动。
- `tests/service/{test_metadata.py,test_accounts.py,test_workspaces.py,test_jobs.py,test_api.py,test_runtime.py}`：小型技术输入/实际数据库/真实Adapter，不做业务模拟。

## Task 1 / B1-01：事务元数据基线

**Files:** Create infrastructure/metadata.py、domain/service_errors.py、tests/service/test_metadata.py。Modify包marker按需，不新增额外依赖。

**Interfaces:** `MetadataStore(url:str)`；`initialize()->None`；`transaction()->ContextManager[Connection]`；`close()->None`。只接受当前显式支持的SQLite URL；unsupported方言在真实adapter实现前拒绝，不把engine能创建当成PG验收。schema_version=1，已存在未来版本拒绝，不自动drop/migrate。server-owned目录/DB0600、目录0700；不得沿现有db symlink打开。sqlite foreign_keys=ON、busy_timeout5000；trusted server-root，同UID敌对OS隔离不承诺。

- [ ] 写真实tmp SQLite持久化/reopen、rollback、foreignkey、未来schema拒绝、URLuserinfo/path/symlink拒绝、filemode测试；`uv run --locked --offline pytest tests/service/test_metadata.py -q` RED缺模块。
- [ ] 最小实现schema_version及transaction，schema组件可随后续task显式新增，不能提前宣称全部业务schema完成。
- [ ] 同命令GREEN，加现有contract边界回归；实际check DB文件mode与foreignkey行为。
- [ ] `git diff --check`；commit `feat(B1-01): add transactional service metadata storage`。

## Task 2 / B1-02 / P8-01–02：本地账户、可信会话与权限

**Files:** Create application/accounts.py、infrastructure/secrets.py、tests/service/test_accounts.py；extend metadata schema users/sessions/memberships/projects最小目录（完整workspace在Task3）。

**Interfaces:** `AccountService(store,secret_provider,clock)`；`bootstrap_admin(username,password_ref)`仅空账户表/明确ref；`create_user(actor,username,password_ref)`仅admin；`login(username,password)->session_secret`仅瞬态内部；`resolve_session(secret)->Principal`；`revoke_session(secret)`；`require_project(actor,project_id,action)`从server DB读取roles/memberships，不从header/payload读role。

角色canonical：engineer/consultant/expert/admin/owner，deny优先。账户只存salt/hash，session随机32-byte生成仅存SHA256摘要+expires_at，8h有效、logout撤销，禁用账户立即无权。密码长度12..256byte，600000PBKDF2+constant time；不存在账号同成本验证；5次失败/5min持久化限流。新密码仅SecretProvider引用解析，provider失败拒绝。测试使用技术test-provider，不声称真实第三方login已联通。

- [ ] RED：密码/会话不在DB或repr、wrong/expired/revoked/disabled、fakePrincipal角色提升、cross-project deny、bootstrap重复、secretUnavailable、login限流/reopen。
- [ ] 最小实现与审计固定event字段（actor/action/resource/outcome，不存password/session/body）。
- [ ] GREEN真实SQLite+clock；secretprovider引用测试，无聊天索密/真实token写repo。
- [ ] commit `feat(B1-02): enforce local accounts and project authorization`。

## Task 3 / B1-03 / P1-01–02、P3原语：workspace/revision/source

**Files:** Create application/workspaces.py、tests/service/test_workspaces.py；extend metadata projects/memberships/revisions/sources/certification_records；extend secure_io only若必要且RED。

**Interfaces:** `create_project(actor,name,namespace)`唯一、userinfo拒绝、owner成员；`save_layer(actor,project_id,layer,base_revision,content,dependencies)->Revision`；layer限定tbox/abox/shacl/rules/vocabulary，CAS base_revision匹配才写。canonical JSON hash标识内容/依赖，旧revision不可覆盖；新内容DRAFT，REVIEWED/CERTIFIED不由save请求直接传入。认证仅本波state/evidence原语，不宣称完整专家发布流程。

`register_source(actor,project_id,format,bytes)->SourceSnapshot`：<=1MiB、typed json/docx/pdf preflight-before-persist，server生成sourceID/路径而非用户filename；source scope/revision/hash绑定，credential key/URI拒绝。每project独立private文件根，metadataDB目录不可上传，读取source/artifact都先require_project。

- [ ] RED：namespace冲突/userinfo、非成员、staleCAS、immutable旧revision、依赖变化DRAFT、cross-project refs、坏hash/oversize/path、SecretURI、PDF日志/budget回归、重启持久化。
- [ ] 实现最小治理/SourceSnapshot；不添加业务模板内容/制造默认示例数据。
- [ ] GREEN +A0 secure_io/native文档回归。
- [ ] commit `feat(B1-03): persist scoped workspace and source revisions`。

## Task 4 / B1-04 / P8-04：持久化任务与native Worker

**Files:** Create application/jobs.py、application/worker.py、tests/service/test_jobs.py；extend metadata jobs/job_events。

**Interfaces:** `submit(actor,project_id,operation,request,expected_workspace_revision,idempotency_key)->Job`；seven operations only，typed request重验证，用户refs必须是本项目登记快照，server补scope/paths/revisions；同幂等键同canonicalhash返回原job，不同内容409。`claim(worker_id)`原子pending→running；attempt/max3、heartbeat、input_revision与actor绑定。

`run_one(worker_id)->bool`调用真实产品factorysemantica，先重查actor权限/来源hash/workspace snapshot，结束CAS running且未cancel/inputs未变才success。native错误固定码，真实输出Artifact refs/metadata持久化；cancel为cancel_requested，步骤边界最终cancelled，取消后不写success。重启running→interrupted，不盲目auto-retry；safe纯步骤重放产生新run_id/replay_of，旧证据保留。部署操作不在自动重试白名单。

- [ ] RED：并发claim只一次、badidempotencyhash、pending/running取消、actor撤权、staleinput拒绝、restart interrupted、no-unsafe-retry、原生ingest/ontology/SHACL/reason结果真实。
- [ ] 最小实现原子领取/状态事件与真正SDK调用，无fake产品注册。
- [ ] GREEN真实文件/SQLite/SDK，Fake仅外围错误inject测试且不得当能力证明。
- [ ] commit `feat(B1-04): execute persisted authorized semantic jobs`。

## Task 5 / B1-05：受保护FastAPI

**Files:** Create api/app.py、models.py、auth.py、middleware.py、server.py、tests/service/test_api.py；Modify pyproject/uv.lock。

依赖：先只读官方metadata/MIT核验，选择支持Pydantic2/Python3.12且无已知适用安全告警的固定FastAPI/Uvicorn/Starlette版本，完整记录选择/lock/hash；不使用旧0.115.12约束Starlette<0.47作为默认安全基线（先前只读metadata仅可证明存在，不等于当前安全安装决定）。HTTPX使用已locked版本若兼容。

**Interfaces:** `create_app(store,artifact_root,secret_provider,allowed_origins,secure_cookies=True)->FastAPI`；`/healthz`无敏感信息，`/readyz`实际DB+native版本验证；`/api/session/login/logout/me`；`/api/projects`、`/api/projects/{id}/members/layers/sources/jobs`、`/api/jobs/{run_id}/events/cancel/artifacts/{artifact_id}`。操作前session+project授权；never readrole/useridentityheaders。源rawbody<=1MiB，JSON<=128KiB，接受长度header不可信、stream也计数。请求异常统一code/run_id，不返回Pydanticinput或native traceback。

Session secret只放HttpOnly/SameSiteStrict Cookie、生产Secure，无responseJSON token；写操作检查Originallowlist+application/json（rawsource明确ContentType特例也Origin检查）；不开放credentialedwildcardCORS。Docs默认关，loopback开发OpenAPI JSON不包含secret值。开启TLS之外的远端暴露必须显式部署配置，server默认127.0.0.1；accesslog/body logging关闭，固定审计事件代替。

- [ ] RED：401/403/header伪造、Origin/CSRF拒绝、sessionCookie flags、敏感validationerror回显、chunkedoversize、cross-project源/任务/制品、staleCAS409、queued202不阻塞SDK、secretproviderunavailable。
- [ ] 固定依赖lock/sync与最小HTTP入口；secret不写.env或chat。
- [ ] GREEN ASGI/TestClient和完整实际SDKjob，无前端资源或占位UI。
- [ ] commit `feat(B1-05): expose authenticated ontology service API`。

## Task 6 / B1-06：真实服务运行与恢复门禁

**Files:** Create tests/service/test_runtime.py、docs/operations/backend-service.md、docs/reports/backend-wave1-report.md；server/worker CLI按上任务契约组合。

- [ ] RED无serverCLI/health、restart持久化与interrupted路径，真实loopbackHTTP createproject→uploadtechnicalCSV→queueingest→worker→event/result，攻击请求拒绝。技术账号/源只留test tmp，不冒充企业业务场景。
- [ ] managed background启动项目独立服务（不修改当前DSH GUI/server），核验准确URL，health/readiness、真实cookie权限/native执行；停机/重启后验证数据/任务和失败恢复。所有managedjob记录/收集并结束测试服务。
- [ ] 新fresh locked env、完整suite、cross-scope/security regressions；一个独立新上下文review本波branch差异，重要问题RED→GREEN修复，scope limits明确。
- [ ] 报告真实命令/退出码/URL/支持范围与尚未做的PostgreSQL/生产TLS/系统能力；不把ASGI单测当实际服务部署。
- [ ] commit `test(B1-06): verify real service lifecycle and recovery`。

## 完整后端后续波次与前端门

本波不是用户全部后端。后续独立实施计划补：DB/SaaS飞书连接Registry与SecretProvider/SSRF、PDF/OCR/RAG/CLIP真实探针及Pipeline运行/重放；完整本体模板/映射/人工认证/验证/对齐；联合发布/Oxigraph部署/健康/回滚；Action/维护规则/BadCase/插件/备份/行列权限与只读双查询。语义由Semantica，不自行训练/伪造能力；外部凭据或实际上游缺口需要用户必要确认。每阶段可验收且最终fullbackend完成才push。

前端此时只有未来需求约束，无React页面开发、截图或伪造pipeline历史。完整后端完成→指定GitHub普通push→完整前端页面展示→用户确认→前端开发/联调。现有总体路线的前端earlyWave步骤按最新用户要求延期。
