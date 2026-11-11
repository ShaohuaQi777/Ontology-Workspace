# Scoped Source Connection Registry（B2-02）

## 当前能力与状态

ConnectionService实际SQLite持久化连接及不可变revision，创建/修改为BEGIN IMMEDIATE、live会话和项目edit重查，UPDATE当前指针以base_revision CAS；read/list需read，显式deny优先。创建返回opaque connection_id/revision/status=CONFIGURED，表示受控配置已保存，**不是连通或接入成功**。真实native读取/Pipeline另任务，飞书/PostgreSQL/OCR/RAG/CLIP未因此完成。

TargetRegistry只能operator在create_app的connection_targets参数组合，不接受HTTP建立server信任。默认empty，无target grant、无自动扫描环境或文件。CLI目前也默认empty；operator CLI配置装载另接入阶段，不能把本模块可组合接口冒称已提供全部部署配置工作流。

## 可信目标、项目和隐私

operator以Target(alias,kind,locator,credential_ref=None)及显式alias→project id集合声明目标，mapping/grant在构造时复制/frozen；不是前端role/header/URL/文件系统路径。SQLite locator要求private regular/UID/绝对无symlink路径，HTTP为固定HTTPS无userinfo/query/fragment、拒绝已知非global IP/localhost类名称；飞书限定open.feishu.cn根origin。此为配置预检，DNS/runtime IP pin、读取限额、alias/file freshness仍须在native执行阶段校验，**不是已运行的SSRF联网门禁**。

Target repr隐藏locator/ref；元数据只保存target_alias/kind/binding SHA，不保存locator、实际秘密或credential_ref。Target Binding包含operator配置；同alias重配location/ref/type时旧connection读用失败TARGET_CHANGED，显式持旧base_revision更新才能创建新绑定，旧revision保留。不解析秘密、不把秘密字段写进request/source，Env引用格式只允许显式env:ONTOLOGY_SECRET_...。

ConnectionView含connection_id/project_id/name/target_alias/kind/revision/CONFIGURED，包含target_alias不意味着用户有全部targets；只有operator为该项目显式grant的target可选。未知alias INVALID_CONNECTION，缺grant FORBIDDEN，不以globaladmin绕过operator源范围。role仍只由trusted session确定。name URI多authority/query credential沿用Wave1输入策略，不是完美自由文本DLP。

## HTTP 与验证

GET/POST /api/projects/{project_id}/connections；GET/PUT /api/projects/{project_id}/connections/{connection_id}。POST JSON只name/target_alias；PUT额外base_revision。客户端locator/credential_ref/header等extra字段422并不回显；Cookie/Origin/JSON128KiB/fixed code+run_id/no-store同既有入口。stale409、unknown alias400、crossproject connection404，权限403，未登录401。

实际模块和ASGI范围13测试、关联API合计30passed/13.88秒exit0。此前11RED缺模块；新增codes未在ServiceError中央允许表登记引起2RED，集中注册3固定错误码后11GREEN；HTTP composition未实现时2RED，再真实路由/strict DTO/defaultempty组合后全部30GREEN。完整suite结果记录在执行ledger/验收追踪，不把这30模块测试称真实外部连接已联通。

## 运维成本

同UID修改Python对象/源文件与外部替换database path不由这个config Registry防御；private descriptor/hash/runtime execution checks在后续读取阶段必须落实。不将单机目录权限称OS沙箱。metadata history尚无用户history API（revision表实际保存），只声明当前get/list/CAS；下一波完整changeset治理另实现。
