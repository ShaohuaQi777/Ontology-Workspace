# 数据接入前端（F1-01）

只实现用户确认的数据接入小模块。React 独立构建，默认 API 真实调用；其他模块仍保留原有展示，不迁移、不补后端。

## 实际入口与边界

本会话本地构建入口 http://127.0.0.1:58228/data/ ，原展示 /preview.html 的“数据接入”链接指向此入口。固定同源代理接原有后端端口58230；DSH GUI58333没有改变。该会话运行方式依赖私有.runtime，重启后开发运行可使用下面的Vite命令。

文件接入 CSV/JSON/PDF/DOCX，真实来源快照+parse队列+Semantica结果。主页搜索/格式筛选、单源三栏/结构/样本质量/证据版本、不可变快照、字段/质量联动、固定版本交接清单下载。文档/JSON根值不伪装成表格。文件名仅当前内存显示；来源命名/备注/逻辑分组/版本关联无后端API，不冒称保存。字段选择只是预览/交接清单，不改变原始上传范围或权限。

数据库/API/知识库真实读取尚未实现，向导显示具体原因；已授权连接可读CONFIGURED信息但不显示“已接入”。映射只有交接清单，不创建本体对象或保存映射。

## 开发与验证

使用现有Node22.22.1（Vite支持>=22.12）与已锁定pnpm。macOS中的Dsh签名bundledNode可能禁止加载Rollup native库；不要修改签名/放宽安全策略，项目test/build直接使用既有非hardened Node。pnpm安装按宿主要求使用bundledNode+pnpm脚本，本项目pnpm-workspace.yaml只授权必要esbuild脚本。

从frontend目录执行：

```sh
pnpm install --frozen-lockfile
node node_modules/vitest/vitest.mjs run
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
node node_modules/vite/bin/vite.js --host 127.0.0.1
```

Vite入口 http://127.0.0.1:58229/data/，固定代理后端58230，不改Origin、不接受任意远程endpoint。返回原预览链接仅在会话静态服务58228有该路径。生产build独立，无CDN字体/外部脚本；未嵌入任何凭据/业务夹具。

## 本地服务与账号

后端沿用仓库既有 `ontology_platform.api.server`，需要显式私有（0700）数据库父目录及artifact-root；metadata不放artifact-root内。纯HTTP只loopback开发使用 `--insecure-dev`，不是生产安全部署；正式环境必须HTTPS/Secure Cookie/精确Origin授权。

```sh
mkdir -p .runtime/data-intake-live/artifacts
chmod 700 .runtime/data-intake-live .runtime/data-intake-live/artifacts
.venv/bin/python -m ontology_platform.api.server \
  --database "sqlite:///$(pwd)/.runtime/data-intake-live/metadata.db" \
  --artifact-root "$(pwd)/.runtime/data-intake-live/artifacts" \
  --origin http://127.0.0.1:58228 --origin http://127.0.0.1:58229 \
  --port 58230 --insecure-dev
```

来源读写需真实本地账号。没有创建演示登录/绕过认证；本会话用户服务初始为空，验收在独立一次性私有服务完成，不向用户项目植入夹具。管理员可使用已有AccountService的一次性bootstrap配置账号。以下在仓库根的本地终端执行，只getpass读取、不打印/写入明文，不在聊天提供密码；若已初始化将以BOOTSTRAP_DISABLED拒绝。

```sh
.venv/bin/python - <<'PY'
from getpass import getpass
from pathlib import Path
from ontology_platform.infrastructure.metadata import MetadataStore
from ontology_platform.infrastructure.secrets import EnvironmentSecretProvider
from ontology_platform.application.accounts import AccountService
ref = 'env:ONTOLOGY_SECRET_LOCAL_INITIAL'
password = getpass('本地账号密码（至少12字节）：')
provider = EnvironmentSecretProvider({ref}, environ={ref[4:]: password})
store = MetadataStore('sqlite:///' + str(Path('.runtime/data-intake-live/metadata.db').resolve()))
store.initialize()
accounts = AccountService(store, provider)
accounts.initialize()
try:
    accounts.bootstrap_admin('local-admin', ref)
    print('本地管理员 local-admin 已创建，请在产品页面登录。')
finally:
    store.close()
PY
```

此配置利用既有账号服务；没有增加网络bootstrap端点、保存.env文件、复用GitHub凭据或自动为用户生成密码。

## 证据

见[数据接入验收记录](../docs/frontend/data-intake-verification.md)。组件/固定API请求测试、真实HTTP+原生任务、真实浏览器验收分别计证据，不以测试假数据充当产品后端。没有进行新一轮全后端416项回归，也不宣称完整本体平台已完成。
