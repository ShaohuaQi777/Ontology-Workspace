# 后端 Wave1 实际验收报告

日期：2026-11-11，分支feat/p0-semantic-backend。本报告是单机基础服务波次，不是完整后端交付，也不是业务专家认证。

## 当前完成范围

实际受保护绝对SQLite/事务schema，PBKDF2账户/散列session/私有Principal proof/live项目RBAC，CAS layered revisions/private源/certification证据原语，七种真实Semantica任务/原子claim/cancel/显式replay family最多3实际尝试/成功manifest，Cookie/Origin/JSON限额/错误脱敏HTTP入口与一个private owner占用的native后台消费者。无Fake产品factory、生产账号、React页面或场景运行金标。

## 最新验证

- Fresh路径[本波fresh环境](../../.runtime/b1-fresh-7c8b130bd7a14982a8e41b7ae21d3558/server-help.txt)：Python3.12.12、`UV_PROJECT_ENVIRONMENT=<fresh> uv sync --locked --offline`，100已锁包安装377ms/102包解析25ms，无新依赖下载/版本变更；实际CLI help exit0。
- 在该fresh环境执行`uv run --locked --offline python -m pytest tests -q --tb=short`：**400 passed、14 subtests passed、255.47秒、exit0**，含当前修复、实际native共享契约及既有真实两环境门禁。执行job bash-a79cd1a8072c49ca已收集exit0。
- 新runtime三项actual native/TCP/stop-restart/SIGKILL-interrupted→显式replay：3passed/10.75秒exit0；review修复+runtime+API联合29passed/15.50秒exit0。
- managed独立项目service job bash-4a4105f9333c47ba，实际URL http://127.0.0.1:64961，health/readiness200、native0.7.0+ontologyworkspace.5、202提交/CSV native parse succeeded、真实rows和manifest SHA256验证。匿名401、Origin403、credential CSV source404无marker回显。证据[execution](../../.runtime/b1-managed-c6d4dffa5ad9405fbe54ccbd910e0a6e/execution.json)，无密码/session原值。测试后job SIGTERM收集，实际socket connect_ex确认监听已关闭。不是持久运行链接，未改当前DSH GUI。

## 实际失败与修复，不删除失败事实

初始3RED/44.67秒：runtime缺失与实际HTTP pending永不消费。加入消费者/占用后3failed/19.17秒，真实Darwin数据库inode flock导致BEGIN IMMEDIATE被锁，服务起不来。独立最小SQLite实验确认同inode锁失败、释放锁成功、独立private owner锁成功；只改owner载体，不改SQLite/timeout来掩盖问题。

首次实际crash重放长文本1500句1failed/2passed：受限native路径返回BACKEND_FAILURE。进一步terminal-state probe1failed/13.16秒固定同错误；该路径有明确资源/输出预算，但未细分确认此次原生失败原因。改技术fixture为100句，使测试仍真实捕获running→SIGKILL，并在实际成功的有界输入范围真实重放；不增大预算、伪造结果或恢复旧success。

独立fresh whole-wave审查原判CHANGES REQUESTED，三项Important。原判及9RED→GREEN一次修复见[独立审查关闭记录](backend-wave1-review.md)，不假称独立APPROVED或release_approved=true。缺陷涉及多URI/credential-query与CSV字段秘密流、事件循环阻塞；原生语义仍由Semantica，纯输入policy与线程调度在平台。

## 运维及完整后端剩余门

运行/占用/恢复说明见[单机服务操作边界](../operations/backend-service.md)；FS与DB非原子、private orphan子进程/staging不自动盘点清除，不声称同UID/网络/RSS OS隔离。PostgreSQL/飞书SaaS/图像OCR/RAG/CLIP/Pipeline/完整本体发布治理/Action/维护/BadCase/只读SQL-SPARQL/备份恢复/生产TLS与插件安全仍在[完整后端追踪](../progress/backend-acceptance.md)。

只在全部后端实际验收之后普通推送用户指定GitHub；当前不提前推送。再制作完整前端展示并等明确人类确认才开发React。Wave1测试/native成功不越过这些门。
