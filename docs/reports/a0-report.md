# A0 / P0 语义底座完成报告

2026-11-11；分支 feat/p0-semantic-backend，验收代码 HEAD e30673344eb4daefa32277ff4e1f19ebad2d87c5。结论仅为 A0/P0 底座完成，不是完整后端服务或产品交付。按用户最新顺序，完整后端验收后直接普通推送指定 GitHub；当前不提前推送。产品前端需先完成整版展示并获得用户确认。

## 已完成任务与责任提交

- A0-01：从零仓库、Python3.12、忽略规则与隔离 worktree；基线 cee24b0。没有导入旧 PoC。
- A0-02：真实 Semantica 探针、能力矩阵与失败证据；989d624 等保留原始0.7.0缺口，授权原生文档扩展后06c2adf具备17项原生证据。
- A0-03：5994bf7固定依赖/干净安装/许可证/制品hash；PDF-02 fdaecc3与PDF-03 81b979a版本化至当前修复候选.5，旧wheel/报告不覆写。
- A0-04：b18c293 ADR与G0实际证据门禁。
- A0-05：6577a79共享JSON Schema/OpenAPI及有界验证器。Schema本身不冒充运行时授权/执行沙箱。
- A0-06：5137735原生七操作Adapter，d3ac011修复URI authority、父进程PDF私有日志与相对RDF base；native对象/异常不越平台边界。
- A0-07：31f1083测试专用固定Fake、真实共享61项契约与产品工厂拒绝Fake。Fake不证明native语义能力。
- A0-08：a5e3d80升级比较、真实报告生产器和G-P0实际执行；e306733使用Adapter内native lexical-preserving NT同构比较，不能将01与1词法损失归一化隐藏。

## 本轮新鲜验收

执行环境 Python3.12，项目内 UV_CACHE_DIR，全部 locked/offline；实际输出与退出码由completion账本保留。

- Task6：158 contract测试通过13.03s，exit0。
- Task7：61 real/Fake共享测试通过3.71s，exit0；真实case无skip计入。
- 当前.5 native17全部passed，G0 exit0；随后真实共享契约gate contract_exit_code0。
- Task8/全仓库：300passed+14subtests113.26s，exit0；包含真实报告、fresh独立环境离线锁定安装、当前.5两环境同一15调用比较和G-P0 execution-only门禁。
- 前一验证保留：300+14subtests162.81s，post-commit专项46通过4.04s；不把旧输出冒充本轮时间。
- .4真实历史基线对比实际新.5报告：15调用，Schema/capability/semantic/error差异空，compatible=true，exit0。没有提供/安装/测试未来upstream SDK。
- git diff --check和工作树status检查exit0，代码树干净（本报告及随后文档提交独立记录）。

## CLI 与真实证据

```bash
export UV_CACHE_DIR="$PWD/.cache/uv"
uv sync --locked --offline --python python3.12
uv run --locked --offline python -m pytest tests -q
uv run --locked --offline python -m spikes.semantica.runner --output .runtime/next-native-check
uv run --locked --offline python scripts/verify_a0.py --evidence .runtime/next-native-check/summary.json --verify-p0
uv run --locked --offline python scripts/record_semantic_contract.py --workdir .runtime/next-cases --output .runtime/next-report.json
uv run --locked --offline python scripts/compare_semantic_versions.py --baseline BASELINE --candidate CANDIDATE --output NEW_OUTPUT
```

所有新报告/工作目录使用不存在的路径；离线缓存缺失失败，不静默联网、更换模型、安装latest或用Fake顶替。

可审查的执行证据入口：[当前原生摘要](<spikes/semantica/reports/0.7.0-ontologyworkspace.5/summary.json>)、[fresh独立环境执行记录](<spikes/semantica/reports/0.7.0-ontologyworkspace.5/upgrade/gate-execution.json>)、[真实.4→.5差异](<spikes/semantica/reports/0.7.0-ontologyworkspace.5/upgrade/comparison-4-to-5.json>)、[升级操作说明](<docs/operations/semantica-upgrades.md>)。

## 审查与裁决

独立整分支审查员 f6f6fd6b-4754-4c6a-8586-be1ef31d4182 对cee24b0..a5e3d80只读审查，REQUEST CHANGES，五项Important、未substantiated Critical。主执行均以8项RED重现，然后一次有界重要修复通道GREEN加全仓库回归；详细记录：[原始审查与修复裁决](<docs/progress/a0-review-a5e3d80.md>)。保持原始结论，不伪称第二次独立复审。Minor M1 unsupported PDF过滤的错误分类仍安全拒绝但误归BACKEND_FAILURE，按inline规范记录延期。

未判断的穷尽vendor法律/任意规模font或interpreter/跨平台、未来波次与同UIDOS隔离：接受为明确范围限制，不用于宣传全面安全。已批准的MIT wheel与领域无关技术探针制品属于明确版本化例外，不是企业生产数据/大模型/第三方仓库搬运。旧单独PDF审查task的运行状态不是任何批准证据。

## 实测限制与后续入口

Adapter仍是POSIX开发用有界同步子进程，descriptor containment与CPU/输出约束不是RSS/网络OS沙箱；可信caller-root不是RBAC。PDF只允许小型raw/Flate安全子集，orphans/fallback、filterchains/predictors/encryption等拒绝；native预检在quiet单次子进程，不修改父logger/globaldecoder。

推理仅有限正向非递归规则；SHACL白名单，不自动fetch imports或全OWL DL。未知置信度null，生成对象DRAFT，测试不能代替专家认证。原生查询/normalize等探针不等于已经交付受权限保护的产品查询API。

尚未完成的完整后端：HTTP/可信会话/RBAC、持久化工作空间治理、任务Worker、源/连接器与Pipeline、人工认证/验证/联合发布部署、Action/维护规则/BadCase、完整运维恢复。后续分波次实现；OCR/飞书/RAG/CLIP新增能力先做真实API/依赖探针，缺口明确报出，秘密只以引用安全配置，不在聊天索取。

目前没有React页面，因此无截图。下一波先实现既定本地账户、SQLite/PostgreSQL元数据与API/任务基础；前端展示与产品开发顺序遵循用户新审批门。完整后端未完成前，不将本报告当作向GitHub正式交付后的完成通知。
