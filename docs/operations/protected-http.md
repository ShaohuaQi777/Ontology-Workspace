# B1-05 受保护 HTTP 服务

## 本波与入口边界

此波实现FastAPI ASGI入口、固定framework锁与真实请求测试。`create_app(store,artifact_root,secret_provider,allowed_origins,secure_cookies=True)`组合已有实际SQLite账户、Workspace、持久化Job及真实Semantica Worker。项目不是原项目移植，不提供前端静态页、不制造运行历史。

CLI入口为`uv run --locked --offline python -m ontology_platform.api.server`，必填`--database`为已有受保护绝对SQLite URL、`--artifact-root`为private目录、至少一个`--origin`精确origin。默认127.0.0.1:8765/HttpOnly/SameSiteStrict/Secure Cookie；本地HTTP测试须明确`--insecure-dev`且全部Origin限loopback。当前只支持loopback host，0.0.0.0或远端绑定直接拒绝，公开TLS部署另属发布运维，不靠改host偷偷暴露。

`--secret-ref`仅登记明确EnvironmentSecretProvider引用allowlist；不创建.env、不从所有环境变量扫描秘密、不接收聊天密码/token。账户初始化依赖已有受控AccountService的显式bootstrap步骤，HTTP无公开bootstrap端点；尚未初始化真实生产账号。CLI关闭accesslog/默认log_config、proxy_headers/WebSocket，使用asyncio/h11、32连接处理预算/5秒keepalive，固定启动失败信息，不打印配置/正文/密码。

B1-05验收时尚未启动真实监听URL；ASGI测试入口不是实际部署。B1-05此时CLI仅服务HTTP并持久化pending任务；B1-06已进一步真实验证后台自动消费、单实例占用和进程中断恢复，见[真实服务与恢复](backend-service.md)。不得据此声称全后端完成。

## 会话、Origin与真实数据限额

`/healthz`无敏感状态；`/readyz`实际SELECT1与已安装native版本0.7.0+ontologyworkspace.5检查，失败503，不回显数据库URL。`/api/session/login/logout/me`仅从HttpOnly Cookie解析当前会话，不读取X-Role/X-User-ID等伪造身份headers，不把原始会话token或Principal私有proof/digest放JSON。所有响应no-store，校验错、业务错、404/405用固定code和服务器生成request run_id，不回显Pydantic input、异常traceback或路径中的敏感标记。

配置Origin在create_app启动时检查，空allowlist、wildcard、userinfo/path/query/fragment与远程HTTP均拒绝。写入必须一个精确Origin及application/json；来源上传的唯一特例为application/octet-stream。未开放credentialed wildcard CORS、form或multipart。JSON实际stream累计<=128KiB，source实际stream<=1MiB；伪造Content-Length不能绕过chunk计数，重复/非ASCII/非整数/超过10位的length先固定400，超限413。不是仅信任header。

## 工具API

账户创建受当前global admin控制且仅接受password_ref；项目创建/枚举与成员权限均真实数据库校验。`/api/projects/{id}/members`提供授权枚举及显式grant；删除角色后下一请求即时失去相应权限。grant/remove在BEGIN IMMEDIATE事务内复查manage_members权限并写固定审计。角色来自显式管理员/owner设置，不由客户端身份header或自动生成对象推导。显式deny仍优先于全局admin和项目角色。

工作空间layers/revisions保留原CAS版本；source登记、枚举、读取按project隔离，不接受文件名/server path。不覆盖现有来源。来源格式不支持即拒绝，不假装完成OCR、SQL或SaaS连接。

`/api/projects/{id}/jobs`提交202与真实pending记录，不在该端点执行SDK。`/api/jobs/{run_id}`及events/cancel/replay/artifacts按数据库绑定项目再校验权限；artifact_id只是成功manifest中的下标，不是任意路径。API测试已提交CSV parse、调用实际NativeJobWorker并读取真实rows/events/制品。真实SDK测试成功不是专家认证或完整发布批准。

## 限制与后续验收

当前枚举是有界初版，项目limit<=100/offset及其他列表固定<=100；不是完整搜索/游标方案。未声明RSS/cgroup/OS网络沙箱、单机跨FS/DB原子事务、公开TLS/生产部署、自动恢复或分布式租约。B1-06须启动实际loopback服务、实际消费并检验存储重开/取消/中断与显式安全重放，以及Wave1独立审查，不能以TestClient/ASGITransport替代实际系统证据。
