# F0-01 完整前端静态展示验证

状态：DESIGN 展示已具备交用户确认条件；不是 React 产品、不是 API 集成验收、不是后端完整交付。正式 React 实施仍待用户展示确认。

## 当前范围

17个工作台页面：项目概览、数据来源、解析器、可信连接、Pipeline、TBox/ABox/SHACL/规则/词表工作室、字段映射、规则与行业模板、候选审核、对齐、验证冲突、双查询、运行中心、认证发布部署、Action维护、Bad Case、成员设置。

全部业务输入/保存/运行按钮在设计中禁用；导航、页面切换、主题、过滤和展示确认可操作。没有 fabricated 数据/历史/成功进度/身份，不调用 API，不写 localStorage/sessionStorage。后端仅已存在原语和接口标“已有”，未完成产品功能或依赖不足明确标注。

## 真实验证（2026-11-11）

- node --check（提取的单个内联脚本）exit0。
- Node VM 17页面分支覆盖、字段纠正、无 fetch/身份持久化、过滤[hidden]样式检查 exit0；仅静态设计分支检查，不是React单测或浏览器证明。
- 独立静态预览服务精确路由/UTF8/CSP connect-src none/healthz明确backend_connected=false/未知API、目录、.git路径404：actual urllib请求 exit0。
- 自有空profile Chrome DevTools私有pipe，显式Emulation.setDeviceMetricsOverride桌面1440×1100、移动430×950：两个实际CSS视口/scrollWidth一致；真实点击17页面、标题/主体存在、页面无整体横向溢出；导航搜索只返回一个实际可见匹配按钮；实际PNG截图已读取。没有读取或控制用户已有Chrome会话。
- 最初CLI截图 --window-size 未精确设置CSS视口，移动截图呈裁切；改用私有CDP明确视口后430无overflow。保留初始方法与更正，不把原截图当移动验收。
- 桌面menu CSS级联使移动开关仍可见：actual RED“desktop navigation toggle visibility”exit1；改.btn.menu优先级；actual桌面none/移动flex和全页复验exit0。

## 一次独立设计检查

独立工程师只读对照完整设计与真实API：nothing important left，不需要增加用户问答。附契约纠正已按代码确认：运行中取消Job仍running，事件cancel_requested；replay_of为旧job_id；artifact_id为artifact_refs整数索引；项目分页先LIMIT/OFFSET再权限过滤，空页非全量结束。

同次独立展示检查读取完整HTML和实际两截图，确认完整页面/空态/能力区分；发现一项Important：关闭移动侧栏只移出屏幕仍可聚焦，选页后焦点留于隐藏按钮。原问题保留，不声称独立重新批准。

Important修复：关闭侧栏inert，打开移除inert并聚焦当前导航；menu aria-controls/expanded，Escape/遮罩关闭回菜单，选页回main；断点切换不保留隐藏焦点。actual RED“closed mobile drawer must be inert”exit1→修复→真实Tab不进入关闭侧栏、打开nav聚焦、Escape回menu、键盘Enter选sources后MAIN/main且inert=true，all17 desktop/mobile再通过exit0。

中间Enter测试未给CDP text=carriage-return，键只定位按钮未激活，title仍概览/inert=false；最小修正测试事件而非盲改页面。正确Input.dispatchKeyEvent Enter含text/unmodifiedText后真实激活来源页并回main。最终验证job24c657d23cf94850 exit0，纯branch/无API检查亦exit0。尚未运行正式React构建或集成，不能称已完成。

## 安全与使用

预览服务仅loopback随机端口，精确返回本HTML和设计healthz，无repo目录浏览/代理/POST/账号/运行。CSP禁止网络连接、表单提交、外部资源；本文件inline CSS/JS可离线浏览。设计确认只改变下一阶段开发授权，不审批事实/规则/发布/部署。

正式页面按设计先实现已有真实API，缺失后端保持不可用、不扩大后端波次；当前用户请求覆盖“全后端完成后才前端”的历史顺序。目标宿主paused/disarmed限制仍保留，当前设计依据用户新前端直接请求完成，未自动恢复旧后端。
