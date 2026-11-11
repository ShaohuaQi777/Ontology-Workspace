# Ontology Workspace 完整前端页面展示与实现边界

状态：DESIGN / 待用户展示确认。用户最新要求前端页面；旧后端 SQLite/Pipeline 等开发暂停。方案沿用已批准 React+TypeScript+Vite、自建工作台，不使用 Semantica Explorer。本文不把未实现后端功能称为交付。

## 1. 目的与已知事实

让交付人员从项目、接入、建模审核、验证到发布运维使用统一工作台，并能看清来源、运行与治理证据。最新后端代码已推送 a4f4578。当前真实 API：本地会话、项目/成员、分层 JSON 草稿 revision、来源上传与下载、CONFIGURED 连接 Registry、七种原生语义任务、取消/重放、事件和制品。没有产品前端；还没有 SQLite Registry 执行、SaaS、DAG Pipeline、完整可视化本体 CRUD、候选审核/发布/Action/Bad Case/查询专用 API。OCR 未配置；神经 RAG/CLIP 未验收。不能因底层 SDK 探针通过给页面显示“功能可用”。

当前展示是全页面信息架构和可点击设计原型：未连接 API、不创建账号、不开真实任务、不填写制造业模拟数据。不自动把任何空列表填成业务示例。用户确认本文和完整展示后再正式写 React 产品代码。后台实现不在本次范围扩张。

## 2. 方案选择（实现者提案，非新增人类批准）

A. 推荐：完整导航和页面结构 + 真实能力分级；只给当前 API 已有操作接入可执行表单，其他页面保留明确不可用的结构和后续接入位置。用户能看到整个工具，同时不会被假状态误导。

B. 仅登录/项目/来源/任务的小控制台：实现快，但无法展示用户要求的 Pipeline、业务规则、TBox/ABox、Action 和 Bad Case 全流程。

C. 只做视觉大屏/模拟运行：不能体现版本、权限、来源与审批；会制造虚构运行，拒绝采用。

实现者建议 A，页面视觉和导航细节由代理决定，用户可在完整展示后统一反馈。此前 React/TypeScript/Vite 技术栈已批准，不再询问相同事项。

## 3. 视觉与全局布局

深色左侧导航 + 浅色主工作区 + 青绿色强调、琥珀警告；不是装饰性数据大屏。1400px 桌面为侧栏、工作区、可选证据检查器三栏；平板收起检查器，窄屏使用可开关导航，表格在自身容器滚动。字体系统中文/Latin 字体，按钮至少40px；键盘 focus 明确，可跳转主内容。

全局：项目切换器、workspace_revision、后端连接状态、当前会话、页面标题、内容搜索、主操作。搜索只过滤已读取的当前项目内容，不冒称搜索全部分页结果。主题偏好可以本地保存；身份、来源正文、原始请求、运行结果、密码和 Token 不能写 localStorage。右检查器显示来源/依赖 revision、sha256、真实 run_id，缺失用“—/尚无证据”，不填模拟值。移动端关闭侧栏使用inert禁止屏幕外导航聚焦；菜单同步aria-controls/aria-expanded，打开聚焦当前导航，Escape/遮罩关闭返回菜单，选页返回主内容，跨断点调整不遗留隐藏焦点。

## 4. 完整页面目录与布局

### 4.1 项目概览

项目列表与创建（name/namespace），当前 workspace_revision，来源/连接/层/任务的当前页计数与列表。计数如分页截断需标“已加载/非全量”；项目先LIMIT/OFFSET再按权限过滤，某个可见页为空不能认定全部项目为空，保留显式下一页加载入口且不依赖items.length判断结束（没有total或has_more API时说明未知，不自动无限扫描）。未选择项目显示真实空入口；未登录显示登录引导；后端断连不假装空项目。健康来自 healthz/readyz，不能用 HTTP 200 页面加载当后端 ready。

### 4.2 数据来源

来源表：source_id、format、revision、size、sha256；上传面板与真实详情。选文件只在浏览器暂存，format 来自白名单，上传二进制最多1MiB。服务无文件名字段；不能把临时本地文件名当后端持久化名称。原文下载按当前已有接口/权限，不擅加 SQLite 文件支持；数据库入口当前禁用。

### 4.3 解析器中心

解析器能力卡、来源选择、当前允许参数、任务提交、结果/来源片段面板。CSV/JSON/PDF/DOCX按真实 ParseRequest，有界 PDF 文本不冒称 OCR。OCR 标依赖未配置；只能提交已有真实 parse 任务，不拼 invented operation。解析执行状态与任务绑定，不保留假的进度条百分比。

### 4.4 连接器中心

File/SQLite/HTTP/飞书能力矩阵；已有 Registry列表与新建/编辑 name/target_alias（PUT带base_revision）。CONFIGURED中文“配置已保存”，不得显示“连接成功”。允许目标由operator预配置；没有 target catalog API，不能伪造可选目标目录。表单用显式别名输入+格式约束+无grant403说明；不接受locator、数据库密码、任意URL、身份header。数据库真实读取、HTTP/飞书“联通测试”禁用并说明后端缺口。

### 4.5 Pipeline工作台

版本/节点库、DAG画布、参数、输入输出、检查点、来源绑定及运行入口。当前无 DAG API，只展示非执行结构示意“来源→解析→抽取→构图→验证”，节点不是历史运行。RAG/数据库/CLIP节点标未接入或依赖不足，保存/运行禁用；不通过七任务自行拼一个未获实现的服务端DAG。

### 4.6 本体工作室

TBox/ABox/SHACL/规则/词表分页，三栏概念树/画布/属性与依赖检查器；原文 JSON 草稿及版本列表为已有 API 可执行范围。可视化类/属性编辑、TTL导入导出、语义差异/合并专用操作没有 API 时禁用；不可把JSON结构改成未声明的三元组API。支持查看复杂公理文本，未来可视化不覆盖的表达式不能被过滤删除。保存是新 DRAFT，CAS409需重新读取并显式选择，不自动覆盖。

### 4.7 字段映射

源字段、目标属性、转换规则与前后预览、枚举/主数据对齐、验证结果。当前映射API缺失，不能假保存或任意eval。保留工具结构、等待用户来源，不提供行业模拟数据。

### 4.8 规则与模板

规则/行业模板列表、版本、适用期、依赖、证据、认证。现有rules JSON层只做草稿，行业模板/可视化规则编译/认证专用API未实现。人工规则说明不是可执行或已认证规则，禁自动自然语言生成专家结论。

### 4.9 候选审核

实体/关系/事件候选、原始来源片段、模型版本、置信度、接受/拒绝/修正批量操作。现有extract任务可展示真实结果；审核持久化接口没有时审批按钮禁用。null置信度显示未知；不填1.0，未审核不能被称正式事实。

### 4.10 实体与多模态对齐

候选对、比较面板、来源/匹配证据与建议。当前无产品对齐API；RAG fallback不能显示语义检索就绪，CLIP无模型明确缺依赖。没有证据不虚构候选/置信度。

### 4.11 验证与冲突

SHACL任务的输入/真实发现与制品；CQ、规则覆盖、回归与冲突证据的结构空页。已有validate_shacl任务可接入，不称完整发布质量门禁。缺发布证据标“未验证”，不把没有失败当验证通过。修复只产生草稿提案，缺ChangeSet API不得伪造应用。

### 4.12 双查询与回答

SQL/SPARQL/混合路径选择、受控查询输入、授权范围、答案/实际查询/来源/推理链。产品查询API缺失，执行禁用；输入区设计不允许任意UPDATE/SERVICE。不能用浏览器RDF库替代Semantica后端回答。

### 4.13 运行中心

真实jobs列表与run_id详情；operation/state/attempt/replay_of/error_code/result；事件实际字段id/state/created_at。事件不能伪装完整日志；无message/traceback字段。Job.state呈现pending/running/cancelled/interrupted/failed/succeeded；运行中请求取消仍为running，实际事件state为cancel_requested，不伪造cancellation_requested任务状态。取消不冒称立刻终止；中断/失败保留旧证据，重放是新run_id，replay_of指旧job_id而非旧run_id，不覆盖原运行。artifact_id是Job.result.artifact_refs的整数索引，下载必须通过权限API，不虚构独立artifact实体字段。

### 4.14 认证、发布与部署

DRAFT/REVIEWED/CERTIFIED/PUBLISHED/DEPRECATED/REJECTED状态说明、release快照、证据与审批门禁、制品清单、dry-run、健康/rollback面板。当前发布与部署API没有，按钮禁用，不能给“部署成功”的静态绿色状态。专家认证服务原语不等于已有HTTP认证端点；状态不能由前端role字段切换。

### 4.15 Action与维护规则

声明式动作列表、参数、权限、影响、审批、幂等与执行审计；维护规则和适用期。无actionAPI故保存/执行禁用。禁止shell/eval、任意URL或自动重试外部副作用；前端不持有源系统Token。

### 4.16 Bad Case回流

真实run/source/revision关联、错误类别、处理决策、ChangeSet与回归/重放；当前无Bad CaseAPI，只有真实失败任务可查看，不自动创建模拟工单。“暂无记录/功能待接入”与“没有失败”必须区分。

### 4.17 项目设置与成员

命名空间/current revision只读；真实members读取/添加/撤销。角色工程师/顾问/专家/admin/owner只是后端记录；不能允许前端伪造X-Role。后端没有当前用户项目权限详情API，不能凭global_role推断所有按钮权限；权限元数据缺失时高风险操作保守禁用，低风险已接入调用仍处理后端403。账户创建只使用operator引用，不在前端索取源系统秘密；无账户列表API则不造用户目录。

## 5. 登录与 API 契约

登录表单仅产品内、TLS或明确loopback开发场景，凭据只作为瞬时POST /api/session/login输入，不存本地、不写请求日志/报错/Toast。Session Cookie HttpOnly/SameSiteStrict，使用credentials:include；不能从localStorage创建BearerToken。App启动先/session/me；401清空内存身份/项目受保护数据，403不冒称离线空页。

同源方案：Vite开发代理与交付反向代理固定转发 /api/healthz/readyz（实际 /healthz /readyz 独立路径），不是任意URL代理。源Origin必须保留且包含于后台精确allowlist；不能fake Origin。开发HTTP Cookie必须operator明确--insecure-dev；生产TLS、Secure默认。禁止简单另起跨域前端后为“修复CORS”放宽后端白名单。前端源/后台服务各自独立于DSH GUI。

JSON请求128KiB/文件1MiB；UUID幂等键仅提交动作新建，网络模糊超时需查真实jobs不能自动另发任务。固定错误code/run_id，客户端输出格式化错误，不回显输入或内部路径。GET jobs/events有限轮询并在后台页暂停/销毁定时器；并发响应绑定当前project_id/session generation，旧项目/注销后的响应不能回填。

## 6. 可执行入口对应现有端点

现有已读：api/app.py、models.py、middleware.py、application/jobs.py。POST项目 -> /api/projects；GET列表 -> {items}。connections GET直接数组，POST201/PUT200，不能统一误认为{items}。source upload raw bytes + query format，201；来源列表{items}。layers GET {items}, PUT {base_revision,content,dependencies}。jobs POST202 {operation,request,expected_workspace_revision,idempotency_key}，事件/列表{items}；直接Job没有created_at/进度百分比，不添加伪字段。memberlist上限100，无全量统计保证。当前七operation仅ingest/parse/extract/build_graph/ontology/validate_shacl/reason。

## 7. 前端实现者边界与交付

正式React按feature目录+typed API client+共享Shell/EmptyState/ErrorState/CapabilityNotice，原生语义只后端。可采用React Router与轻量CSS，不自动安装复杂画图库/大模型。领域结构未ready前图画布只受控布局、不造数据。表单全部可访问标签、键盘、确认/取消和dirty-state；适当复制run_id/sha256，不复制秘密。

阶段1全页展示和状态设计确认；阶段2React可运行壳+登录/项目/来源/连接/层草稿/任务/members现有接口，其他页明确不可用；阶段3测试/真实服务验收/独立审查/普通push/实际URL。不能为赶前端而继续未获范围的后端开发。构建成功不等于集成成功；真实API列表空态、权限/Origin/CAS、取消/重放、上传限额和切项目竞态均须验证。当前UI权限元数据与operatortargetcatalog缺口保守处理，不承诺后端不存在的API。

## 8. 展示确认门

本设计及完整可浏览展示待用户确认。确认仅覆盖页面范围、布局、真实/规划边界与正式React实施，不代表审批任何候选/发布/部署，也不代表缺失后端完成。收到确认后写实施计划；此轮不先创建React项目或安装依赖。
