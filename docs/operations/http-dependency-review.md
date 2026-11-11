# B1-05 HTTP依赖选择预检

日期：2026-11-11 Asia/Shanghai。候选最初只读官方PyPI metadata，随后完成固定锁定/安装与ASGI验证；读到没有适用告警不等于整个后端安全认证。

## 固定候选

FastAPI 0.162.4：[官方版本metadata](https://pypi.org/pypi/fastapi/0.162.4/json) HTTP200，MIT，Python>=3.10，Pydantic>=2.9.0、Starlette>=0.46.0，未设置旧<0.47限制。当前项目Python3.12/Pydantic2.14.3满足声明要求，vulnerabilities空。wheel SHA256 f093bc306d3958278d30ffd14f3834ca3d9b144fbb898ab5c9b652cf6e75f869。选择bare fastapi，不引入standard/all/cloud-cli/SDK模型或部署云副作用。新必需的annotated-doc、opentelemetry-api等传递依赖要经过lock与告警核查；API库不是启用遥测导出SDK的授权。

Starlette 1.3.1：[官方版本metadata](https://pypi.org/pypi/starlette/1.3.1/json) HTTP200，BSD-3-Clause，Python>=3.10，anyio>=3.6.2,<5，vulnerabilities空。wheel SHA256 c7372aae11c3c3f26a42df7bd626cec2f47d03483d261d369516a615a53714c6。后续ASGI测试优先既有locked HTTPX ASGITransport，避免仅为TestClient引入httpx2/optional full依赖。

Uvicorn 0.54.0：[官方版本metadata](https://pypi.org/pypi/uvicorn/0.54.0/json) HTTP200，BSD-3-Clause，Python>=3.10，click>=7.0/h11>=0.8，vulnerabilities空。wheel SHA256 505bdb0f318731d45f1f712071fc781a8981f6847a31c902c9f5e652d4f67faf。选择bare uvicorn，实际启动时强制h11/asyncio、禁accesslog/proxy_headers，默认loopback。已locked h11/click版本的兼容和告警也需核查，不能因顶层metadata无告警推导整条链安全。

Ruling：基础框架MIT与BSD-3-Clause为如实记录的宽松第三方许可，不将Starlette/Uvicorn伪称MIT；最终vendor/发行包保留对应许可证。选择固定版本，不运行latest/standard/all作为默认。

## 拒绝的旧候选

[Starlette 1.2.1官方metadata](https://pypi.org/pypi/starlette/1.2.1/json) HTTP200明确列出适用告警，未安装。GHSA-82w8-qh3p-5jfq/CVE-2026-54283/PYSEC-2026-249：urlencoded form parser忽略配置上限，fixed 1.3.1。[告警](https://osv.dev/vulnerability/GHSA-82w8-qh3p-5jfq)。GHSA-jp82-jpqv-5vv3/CVE-2026-54282/PYSEC-2026-248：非slash path跨越重构URL的authority边界，fixed 1.3.0。[告警](https://osv.dev/vulnerability/GHSA-jp82-jpqv-5vv3)。重复PYSEC/GHSA别名不计为四个独立漏洞。

API本身仍将拒绝form/multipart写入，按实际stream对JSON128KiB/rawsource1MiB计数，并使用明确allowlist Origin而非重构URL hostname做授权；这些应用防护不能代替选用patched框架。此前FastAPI0.115.12仅存在性read，不作为安全默认。

## 实际锁定与安装

B1-05首次10项ASGI测试RED（缺少API模块）之后加入上述固定bare依赖。首次online `uv lock`因既有官方spaCy模型release-assets网络超时退出2；未重下载模型、修改model pin/URL或注入site-packages。`uv lock --offline`先明确缺少FastAPI cache；项目限定mirror的固定三包`uv pip compile`只暖registry metadata，不安装、不触碰model source，然后`uv lock --offline`成功102包，仅新增FastAPI/Starlette/Uvicorn/opentelemetry-api四包，保留已有所有版本。`uv sync --locked`实际安装成功。

新增opentelemetry-api固定1.45.2，Apache-2.0，wheel SHA256 2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34。FastAPI/Starlette/Uvicorn及新增API，连同已有h11 0.16.0、click 8.5.1、anyio 4.16.0共七项逐版本重新读取官方metadata；active vulnerabilities均为空，许可如实为MIT/BSD-3-Clause/Apache-2.0。未安装opentelemetry-sdk/OTLP exporter或启动遥测导出服务。FastAPI bare的NoOp tracing API不冒充授权外发遥测。

ASGI请求已真实验证Cookie/Origin/JSON流式限额/项目权限/原生排队执行；实际loopback启动与后台自动消费/中断恢复仍为B1-06。禁止修改已有Semantica wheel/原生pin或全局包管理配置；无产品前端、真实用户秘密、公开监听或GitHub推送。
