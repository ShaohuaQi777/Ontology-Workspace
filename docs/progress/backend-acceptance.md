# 完整后端能力与验收追踪

本表服务于用户2026-11-11新要求：完整后端先真实验收→直接普通GitHub推送→完整前端展示确认→前端开发。不是演示功能清单；任何UNKNOWN/TODO不得计入完整后端交付。

| 范围 | 当前证据/状态 | 完成必须提供 |
|---|---|---|
| Semantica语义底座 | A0/P0 DONE；native17/共享契约/真实两环境门禁 | 后续产品API仍需授权/持久化/运行验收 |
| 元数据事务 | B1-01 DONE：10RED→10GREEN；33关联回归；完整310+14subtests114.11s exit0 | 完整后端还需账户/项目/任务schema与重启恢复 |
| 可信会话/项目RBAC | B1-02本地模块DONE：14RED+并发1RED→GREEN、全331+14subtests117.05s；B1-05 Cookie/Origin/错误脱敏/stream限额及显式成员审计DONE；21 HTTP/CLI测试与全388+14subtests251.78s | 明文秘密不持久化、撤销/失效/越权拒绝、真实权限路径 |
| HTTP服务/任务Worker | B1-04本地持久化队列/native Worker DONE：真实七操作、取消/重放家族预算/输入授权复查；全367+14subtests163.14s；B1-05受保护ASGI/API及local CLI DONE，21HTTP/CLI测试、全388+14subtests251.78s；B1-06真实loopback/native后台消费/owner互斥/实际SIGKILL与显式重放、fresh完整400+14subtests255.47s DONE；全波独立review三Important经9RED→GREEN修复，原判保留 | 实际loopbackURL/health/readiness/真实排队执行/取消与恢复 |
| PDF解析 | .5有界raw/Flate native子集DONE | 项目来源登记、权限/来源定位与产品API；不能把限制隐藏 |
| OCR解析 | B2-01已实际调用native ImageParser.extract_text，小技术PNG因缺pytesseract/Tesseract拒绝；UNAVAILABLE未验收 | 固定原生API/模型依赖，小技术输入真实OCR；不以PDF文本层冒充OCR |
| Database连接器 | B2-01 actual native SQLite SELECT/readonly UPDATE拒绝/sourceSHA不变；B2-02 scoped Configured Registry/strict HTTP/CAS/target hash/grant模块DONE，13测试+17API关联30passed13.88s、全416+14subtests310.99s；实际统一接入执行仍TODO B2-03 | SQLite/PostgreSQL授权配置、secretref/只读/Schema/实际连接；其他方言独立验收 |
| 飞书知识库/SaaS | UNKNOWN未真实探针/实现 | 合规分页/限流/来源定位/ACL、固定SDK或受控connector、SecretProvider、实际授权联调；未联通不可标DONE |
| Pipeline清洗/治理 | TODO | 版本化DAG/节点Schema、deterministic transform白名单、任务事件/检查点/重放/权限 |
| RAG | B2-01 native TextEmbedder实际method=fallback；无神经模型，不能计neural RAG完成，chunk/index/retrieval产品链TODO | 文档chunk/embedding/index/retrieval/context/prompt/model与来源可追溯，未知质量不编金标，模型/外传显式配置 |
| CLIP对齐 | B2-01确认torch/transformers不存在；未实际加载/运行CLIP，UNAVAILABLE未验收 | 原生multimodal API/固定模型/真实图文派生证据、置信度及资产位置；不因名称匹配宣称对齐 |
| TBox/ABox/SHACL/rules/vocab | B1-03 scoped revision/source及专家证据原语DONE；全348+14subtests163.65s；完整changeset/验证/发布治理仍TODO | 分层immutable/CAS/依赖/草稿/差异/合并/专家认证失效规则 |
| 业务规则/行业模板 | TODO P6 | versioned声明式工具模板/适用期/来源/编辑认证；不编制造业场景 |
| 本体抽取/建模/验证/对齐 | 原生技术探针DONE；产品治理TODO | 固定输入/模型/来源、候选审核、专家认证、验证finding与version；所有入口授权 |
| 联合发布/部署 | TODO P5 | hash清单/完整认证与验证门禁、真实Oxigraph健康/核心query、失败恢复/上一版回滚 |
| Action定义/维护规则 | TODO | 声明式action与参数权限/影响预览/审批/幂等/执行审计，外部副作用不盲目重试 |
| Bad Case回流 | TODO | 真实run/source/revision证据关联、分类/审核/修正Changeset/回归与replay，不伪造历史 |
| SQL/图谱双查询 | native查询探针存在；产品P7 TODO | SQL AST/账号只读/表列权限、SPARQL禁UPDATE/SERVICE、有界遍历、best_effort跨源时点 |
| 发布运维安全 | TODO P8 | 备份空环境恢复/离线安装/插件manifest签名/审计/部署边界；不能将descriptor称OS沙箱 |

## 交付门

每项至少实际API/CLI执行路径、成功/失败/权限/大小/重启/敏感信息回归，记录确切依赖/命令/退出码。真实第三方服务缺凭据只提供安全配置方式，不在聊天索取；联调缺口如实报告，不用固定Fake或“连通成功”占位顶替。

后端服务未全部完成，不执行提前A0push或称已交付。最终普通推送到用户指定GitHub无需重复提醒或询问已授权普通push；远端分支冲突、不可逆动作、必要新权限/秘密配置或原生能力重大缺口仍需必要确认。不强推、不自动合并。

产品前端整版预览在后端完成后提供并等待人类确认；当前不开发React页面，不制造截图或生产运行数据。
