# Ontology Workspace

面向 FDE 与企业项目交付人员的本体构建工作台。项目只开发工具，不制作行业场景模拟、业务数据或业务金标。系统以项目、不可变来源快照、分层本体修订和语义任务为核心对象，语义计算通过 `SemanticBackend` 适配层调用固定版本的 Semantica。

## 当前可用能力

- 本地账号、项目与项目权限
- CSV、JSON、PDF、DOCX 文件登记、解析和来源证据
- TBox、ABox、SHACL、规则、词表五类 JSON 草稿修订
- ingest、parse、extract、build_graph、ontology、validate_shacl、reason 七类语义任务
- React 数据接入与 FDE 本体构建工作台
- SQLite 开发元数据基线、受控连接配置和任务制品

发布、部署、可视化模型命令、能力问题、业务回归套件与 HTTP 认证接口仍待建设。界面会直接展示这些边界。Fake Backend 仅用于自动化测试。

## 代码结构

- `src/ontology_platform`：应用服务、HTTP API、Semantica 适配层与基础设施
- `frontend`：React/TypeScript 工作台
- `contracts`：稳定的跨层契约
- `tests`：服务、契约、原生文档和安全回归测试
- `docs/decisions`：仍然有效的架构决策
- `docs/operations`：当前运行与维护说明

## 验证

后端使用锁定的 Python 3.12 环境：

```bash
uv run --locked --offline python -m pytest -q
```

前端从 `frontend` 目录执行：

```bash
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

本地原型可以使用单用户模式直接进入工作台：

```bash
uv run --locked --offline python -m ontology_platform.api.server \
  --database sqlite:////absolute/path/metadata.db \
  --artifact-root /absolute/path/artifacts \
  --origin http://127.0.0.1:58229 \
  --port 58230 --insecure-dev --single-user
```

`--single-user` 仅适用于回环地址上的本地原型。服务仍会建立内部工作台身份并记录审计事件；多用户部署继续使用原有会话认证。

开发环境与运行制品保存在 Git 忽略目录中。凭据不得进入源码、日志或发布包。
