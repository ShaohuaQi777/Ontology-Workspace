# F1-01 数据接入模块验收（2026-11-11）

## 交付范围

独立React+TypeScript数据接入模块，原preview只修改sources入口名称/说明/链接，其余页面未迁移，后端代码/依赖/原生语义引擎未修改。文件真实来源+parse接口已接入；完整平台/数据库读取/知识库/映射/逻辑源版本历史未实现。

用户入口 http://127.0.0.1:58228/data/ ，原工作台仍 http://127.0.0.1:58228/preview.html ，API固定loopback58230，DSH GUI58333不变。会话local开发显式insecure-dev，只授权127.0.0.1 Origin；不宣称HTTPS生产部署。账号需管理员在本地初始化，详见 [运行说明](../../frontend/README.md)。没有登录绕过/植入用户业务记录。

## 当前实测

最终验证作业bash-ee36671fe034407e收集exit0：
- frontend全套88通过（API58、result projection10、styles7、App13），0失败；tsc --noEmit成功；Vite7.2.2 build成功，31modules，CSS9.53kB/JS223.68kB（非运行性能指标）。
- 精确/data/与assets路由、原preview、目录/编码路径拒绝均通过；同源固定代理实际health/ready200。本会话后端断开时UI仍200、API安全返回NOT_READY/503，再以相同私有存储重启后health/ready恢复200；此为实际本地中断恢复，不是生产部署/灾备认证。
- 真实React + 真实Cookie登录 + 创建独立技术项目 + 文件选择 + raw upload + 不可变source snapshot + 真实Semantica CSV parse worker + job状态/结果 + 质量/字段联动 + handoff显示 + 注销后数据清空，实际Chrome验收通过。
- 实际viewport1440/1100/430的document.scrollWidth均等于viewport，没有整个页面横向溢出；工作区分别三栏/两列布局/单列。真实选中tab颜色#0f766e与未选中白色可区分，手机Tab/Escape可用，向导步骤替换后焦点仍在dialog内。
- API/native/runtime针对性后端回归作业bash-74d5c63bad704e06 exit0：tests/service/test_api.py、test_server.py、test_runtime.py合计24passed9.42秒。没有重新运行历史416项全后端回归。

技术夹具只在独立一次性服务58439/58440、私有原生metadata/artifact-root与全新Chrome profile执行；主用户服务58228/58230为空，未复制测试项目/记录到用户业务服务。使用既有Native factory，没有产品Fake或网络mock。临时测试密码仅内存经既有SecretProvider与真实bootstrap账户hash，未写入代码、.env、文档或日志，browser已实际logout并停止。

最终浏览器产物位于本机ignored `.runtime/frontend-preview-8db578feb2df43e59508d88fca0d73bf/intake-proof-f869fa52313e4cc4a8f29e9006e41257/`（desktop/medium/mobile.png），仅验收过程资产，不是业务来源或平台内容。

## 独立审查与回归

一次只读独立审查dfe9c4b1报告5Important：旧会话分页/创建回填，登录正常异步项目请求被废弃，poll网络中断永久卡pending，关闭/重开上传向导结果串线，项目分页入口/游标。主代理逐项实际RED回归后修复，最终全套GREEN；没有让同一审查者反复重审。

关键新回归使用真实React组件和延迟Promise：项目分页/创建在logout后resolve，等待act回调完成再断言，避免waitFor(null)在旧响应尚未执行时假通过；source旧项目回填被generation阻止；page游标从50到100；上传未完成时不能新开竞争向导；临时轮询错误可重试，刷新合并同run的tracked真实终态。

追加可见交互修正：dialog被卸载步骤控件不丢焦点；合法JSON scalar/root仍显示真实根值；面包屑避免误继承source行width100%。相应RED→GREEN记录在ignored执行ledger。jsdom样式定位和真实Chrome渲染分开证据，不把jsdom当媒体断点验收。示例无业务含义，实际CSV空值提醒不等于全量数据验证通过。

## 未覆盖与明确缺口

仅CSV走完本次真实浏览器原生闭环；JSON（含根值）、PDF、DOCX的前端形状/请求边界有组件/API测试，不宣称本次都已真实文件端到端验收。PDF仅既有bounded文本层，不支持扫描OCR。样本展示最大200rows、正文最大50000chars；没有做大宽表/10k节点极限性能压测。

目前无服务端源名称/备注持久化、逻辑分组/版本关系、数据库读取/目录/字段范围保存和映射API。当前文件名称仅内存别名，备注只随清单导出，checkbox不是行列安全策略，上传新文件是独立snapshot。来源被登记不等于ready，只有成功parse证据才开放handoff。连接CONFIGURED不代表接入成功。
