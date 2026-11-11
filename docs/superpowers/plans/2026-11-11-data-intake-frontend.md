# F1-01 数据接入前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline。用户已明确批准此小模块修改和此前自治执行；不重复执行方法问答。独立助手只做API边界与CSS两个不重叠实现片段，最终一次聚焦审查。

**Goal:** 交付FDE数据接入首页/单源工作区/文件接入向导，实际来源+原生parse结果，不改其他业务。

**Architecture:** frontend/ 自建React模块，typed api.ts集中Cookie/限额/固定错误；intake.ts展示真实已解析DTO、确定性样本质量；App.tsx负责会话/项目/首页/三栏/向导和异步generation。现有HTML只有sources入口链接到独立模块。现有native Backend以operator本地方式运行，同源代理限定固定路径。

**Tech Stack:** React19.2.0、TS5.9.3、Vite7.2.2、Vitest3.2.4、TestingLibrary/jsdom，pnpm锁定；Python3.12现有锁环境，不改SDK。

**Spec:** ../specs/2026-11-11-data-intake-frontend.md（用户已确认逻辑/当前API差距）

## Global Constraints
- 只改数据接入前端；来源不可变；不伪造历史、名称持久化、配置联通、质量统计或映射保存。
- 所有原始文件（含JSON）非空<=1048576，API JSON请求体<=131072，Cookie/Origin/safe run_id固定错误，无本地身份/正文持久化。
- 已有API SourceSnapshot字段source_id/project_id/format/revision/sha256/size。Job.result.source_refs匹配成功证据，未知关联不猜。
- 用户框架授权已有；目标目录/业务备注/版本关系/DB读取未实现需明确不可用。

## Review Focus
- 切项目/注销竞态旧数据不能回填（App generation测试）。
- 上传失败/解析失败不冒称可用于建模，保留登记来源（向导状态测试）。
- CSV/JSON不同native形状，文档不是表格（intake真实DTO技术夹具测试）。
- 403与401/离线/空态分别显示，JSON错误不带提交正文（API测试）。
- 窄屏操作和弹窗键盘焦点不隐藏，真实视口验证仅此模块，不重复全项目检查。

### Task 1: API边界 + Native结果投影
Files: frontend/package.json/tsconfig.json/vite.config.ts/index.html; src/api.ts/types.ts/intake.ts; src/api.test.ts/intake.test.ts。
Interfaces: api.me/login/logout/projects/createProject/sources/jobs/connections/upload/parse/getJob/replay/sourceBytes，Source/Project/Job typed DTO；project请求接受AbortSignal；parse传source snapshot绑定+新幂等键。preview(data) -> columns/rows/text/issues，仅现有结果决定。
- [ ] 测试先固定1MiB/非空、Cookie、parse binding、新幂等键、fixed ApiError、403/401和结果投影。
- [ ] 跑vitest看到对应缺模块/行为RED。
- [ ] 实施typed fetch与展示投影，拒绝未支持格式参数/任意endpoint。
- [ ] 关联测试及bare frontend test GREEN，锁安装与typecheck。

### Task 2: 数据接入用户闭环
Files: frontend/src/App.tsx/App.test.tsx/styles.css/main.tsx。
Interfaces: App可注入同形api供隔离测试（仅测试），产品默认真实api，不提供演示backend。首页来源列表→选择→同源三栏，向导选文件/确认→upload→parse→真实状态结果。质量问题点选字段；备注无持久化API只说明，映射交接显示真实来源字段清单可复制/下载，不称映射已保存。
- [ ] 先测试无业务样例、空态/401、文件向导状态、联动与明确未实现DB入口、parse成功/失败、project异步切换。
- [ ] 跑对应RED后实现App，UI primary action只有该模块，其他页面不迁移。
- [ ] GREEN+bared tests+build，实际viewport desktop/mobile及文件夹具任务闭环。

### Task 3: 入口与交付
Files: docs/frontend/preview.html仅sources分支和必要链接；docs/frontend/data-intake-verification.md；frontend/README.md；ignored私有runtime服务。
- [ ] 实际服务健康/Origin/Cookie/API/原生parse smoke，私有测试夹具不进入用户业务目录；无凭据聊天/日志。
- [ ] 一次独立聚焦review，最小修复重要问题，运行frontend全测试/build及既有相关API/native/runtime后端回归。执行裁定：后端代码未改，历史全套约310秒，本次使用24项直接相关既有测试；不宣称全后端重验。
- [ ] 仅指定修改文件git diff check/commit F1-01/普通push同feature分支，核对远端SHA。
- [ ] 提供用户可访问实际模块URL，保留其他模块不变，明确阶段与缺口并停止。
