# 后端 Wave2：接入 Registry、原生读取与 Pipeline

## 依据与范围

按用户已批准完整后端顺序及[总体设计](2026-11-10-ontology-workspace-design.md)§8、P2/P8继续实施；用户已经要求自主推进，仅必要权限/上游缺口确认，不重复要求选择执行方式或批准同一架构。本文件是实现者对既定后端范围的拆分，不伪称用户已逐项批准新增平台能力。仍为Python3.12/Semantica native.5、自建未来React、无场景模拟/业务金标。

Wave1有真实HTTP/任务/权限/存储/恢复。下一阶段把来源从手动上传扩为受控connection revision与native database/HTTP读取，再以versioned DAG串联真实数据处理。后续changeset/认证/发布/Action/BadCase/query/operations另波，不用Registry配置记录冒充可用连接。

## Approach 与实现者裁决

采用既有模块单体、不可变connection/DAG revision、可信operator target alias、原生Adapter读取与持久化run，不复制外部项目。拒绝任意客户端server path/URL代理或源包脚本；拒绝把native失败替换Fake或hash embedding宣称神经语义能力。SQL/HTTP传输安全策略在平台及Adapter前置，实际语义/DB/解析仍调用固定Semantica。

外部接入可能需要SDK/模型/凭据。当前已实际查验：PATH中无tesseract，项目中pytesseract/torch/transformers/sentence_transformers缺失。尚未执行OCR/CLIP神经模型，不称支持；不自动安装系统OCR或下载大模型。可以先完成无外部依赖的SQLite/Registry/安全/Pipeline；必要外部依赖权限与真实飞书授权联调只在能力门禁处单独确认，不在聊天索取秘密。

## Connection 和 operator trust

连接是项目scope下的opaque id/revision，与target alias关联。operator在server组合时明确给target registry：SQLite private绝对位置或固定HTTPS base origin/path、类型、允许table/columns、credential_ref（仅引用）、是否显式允许本地技术HTTP。HTTP客户端不能创建这些server信任目标，也不能提交path/URL/auth headers。连接DTO仅alias/type/id/revision/name/status，绝不包含server locator/秘密。

连接创建/修改要求项目edit，target选择只限operator allowlist；read只限项目read，deny仍优先。每个修改新revision/CAS；未经读取真实源只CONFIGURED，不用“连通成功”。执行前再次检查session/project/connection revision/target binding/source hash，保留失败run。SourceRegistry和connection是不同对象，禁止把connection信息写进含凭据制品。

## Native SQLite 读取

只读、<=1MiB的实际SQLite文件，由operator alias指明或用户明确上传整份授权来源。实际格式/schema/credential字段预检、拒绝views/virtual table/异常标识符；DB中的credential字段/URI不得复制成普通source。只支持声明式table/column/limit参数，无原始SQL/where/eval。选择器先校验target允许table/columns，server生成引用identifier的单条SELECT与绑定limit；native DBIngestor.execute_query在private readonly snapshot的mode=ro/immutable URI运行。禁止INSERT/UPDATE/ATTACH/load_extension，Schema/rows/result/source hash由真实SDK产生并保留。

整份private DB仅供server run输入；HTTP原始DB下载禁止，结果只含执行前已许可的字段。不要用取出全部列后再掩码冒充列权限。没有row policy的目标明确为operator许可全部行，后续只读SQL查询行列策略另波；不称已完成任意源数据库RLS。

## HTTP/SaaS/飞书读取

只能固定target与声明式endpoint/page，不是任意URL转发。HTTPS默认/public-only，拒绝userinfo、credential query、file/http远端、DNS私有/loopback/linklocal/IPv4-mapped/多地址混入；认证从explicit SecretProvider解析，provider失败先拒绝。native semantica.ingest.ssrf固定实现有DNS/IP pin和TLS hostname校验，Adapter复用它并禁止redirect/环境proxy，体积与分页均有界。请求Auth只在瞬时内存/授权IPC，不进入request.json/日志/DTO；响应credential字段也拒绝，不回显上游error body/header。

generic HTTP需实际技术server/分页/status/限额/redirect/security运行；技术server只证明通用connector，不冒称飞书授权联通。飞书wiki/docx connector固定open.feishu.cn endpoints、只读API、has_more/page_token/cursor重复保护/429 retry_after有界，保存真实document定位/源ACL与body hash。缺少操作者安全配置授权时CAPABILITY_NOT_READY/SECRET_UNAVAILABLE，不捏造文档或连接成功。

## Pipeline 与能力门禁

Pipeline是不可变bounded DAG revision，最多16 nodes/32 edges，无环、unique node ids、依赖/operation schema固定。source/connection、parse/extract/build_graph/ontology/SHACL/reason走已有真SDK；白名单clean transform仅rename/select/cast/null/enumeration，不eval/脚本。node输入输出绑定hash/run/source/dependency/DAG revision，生成都是DRAFT。

实际run逐节点checkpoint/event、取消边界、显式replay新run、不覆盖原证据；节点native失败阻断后继，不自动跳过。Pipeline运行不得开放陌生operation或把来源重新取样冒充同一快照。认证/发布不会由Pipeline成功自动产生。

OCR/RAG/CLIP capability记录接口/依赖/模型hash/offline配置和真实探针结果。native RAG chunk/embed/index/retrieve必须说明实际backend；sentence-transformers缺失时native fallback不能被称为完成神经模型RAG。CLIP不因名字匹配/元数据提取称图文对齐。许可大模型或外部API需必要确认和安全operator ref，技术输入只用小自生成图文，无质量金标。

## 验收与边界

每任务TDD/实源/permission/crossscope/credential/size/revision/restart；一波末尾fresh全回归与一个独立review，不逐任务多代理。所有未知/未联通保持显式未完成。完整后端全门结束才普通GitHub push，之后全版前端展示需明确人类确认。
