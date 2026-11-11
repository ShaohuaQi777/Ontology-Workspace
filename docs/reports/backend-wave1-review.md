# Wave1 独立审查原判与一次 Important 修复

## 独立证据

审查者为独立新上下文subagent 4acccb1c-ebed-44f8-836c-0308fa851431，只审查，不修改文件或派生额外审查者。范围BASE 7fae1285150f4e6c290dccc76586cb921a1f4fb7→HEAD 6c2dab5336041b4c3120f31201bba1c7efcebed5及实际staged Task6 runtime/app/server/tests；不是全部后端完成审查。

原判 **CHANGES REQUESTED**：未建立Critical，三项Important，未列阻塞Minor。保留此原判；下面是实施者基于实际RED/GREEN的关闭记录，不冒充独立复审批准或release_approved=true。

审查者只选定21回归，实际6.98秒/exit0：metadata、角色/并发、certification、原子重放家族预算、HTTP非成员；另3个小实验包括真实native CSV parse/SQLite/manifest读取与revision持久化，输出仅布尔/status。没有伪造真实TCP/完整suite验证。

## 三项 Important

I1：旧[URI检查](../../src/ontology_platform/semantic/dto.py)使用re.search只检查首个authority，普通URL后第二个userinfo URL能进[JSON源策略](../../src/ontology_platform/infrastructure/source_policy.py)及真实layer revision；credential query参数也漏检。明确识别credential语法而非自由文本DLP。先4RED元数据与2来源RED，再扫描所有URI起始、逐个authority及normalized/decoded credential query key，保持普通URL查询允许。

I2：[source_policy](../../src/ontology_platform/infrastructure/source_policy.py)对CSV只扫描URI，password/Access Token列绕过JSON字段策略。独立真实native parse确认技术marker进入结果/SQLite/manifest。先2CSV来源RED，再有界非语义CSV header预检复用JSON canonical credential key gate，文件/DB持久化之前拒绝，不自行重写Semantica语义解析。标记均合成非live，无真实秘密。

I3：[async upload](../../src/ontology_platform/api/app.py)直接调用同步登记，其PDF私有subprocess预检最多20秒会阻塞sole ASGI event loop。独立300ms外围delay调度实验建立饥饿路径，不谎称实际跑20秒PDF。实施者先1RED（health延迟约315ms），再await有界body后把整个登记/权限/预检/持久化run_in_threadpool。调度probe后仍实际登记source，无Fake语义backend。

实施者9RED/4.66秒exit1，修复后review_security/runtime/API联合29GREEN/15.50秒exit0。完整fresh环境/native/loopback证据见[验收报告](backend-wave1-report.md)。这是本波计划中的一个fresh whole-wave review与一次Important修复，不追加逐任务review循环。

## 不夸大范围

SQLite-only/single owner、不是分布式lease/hostile同UID沙箱、边界取消、私有orphans/FS–DB不原子、生产TLS/PostgreSQL/OCR/SaaS/完整发布/前端待实施均是明确限定，不把它们藏起来或用本波单测冒充全产品能力。
