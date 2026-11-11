# A0 分支独立审查及修复记录

审查范围 cee24b00691f123ff28973751bd51cff98c2da48..a5e3d805bf403c3df81ef334b588ebfdb7cf7dbc。独立审查员 f6f6fd6b-4754-4c6a-8586-be1ef31d4182 在只读约束下检查批准计划、执行账本、全部关键执行代码，未安装、联网、修改源码或派生审查。此前单独 PDF 审查任务的状态不作为批准。

## 原始结论

REQUEST CHANGES；不准合并。未 substantiated Critical，不等于不存在。重要问题五项：

- I1 URI authority credentials 通过 base_uri/subject_uri/source_refs/scope_ref 在检查前持久化或公开；标准 URL userinfo，不是自由文本秘密推测。
- I2 6209 字节经典 xref PDF：声明零页、65 orphan Page；预检 pages0，实际 native fallback65，突破64页预算。
- I3 父进程 PDF 原生预检在 DEBUG 日志中输出原始技术私有元数据，子进程日志隔离未覆盖。
- I4 `<Node> a owl:Class` 同请求重放忽略明确 base_uri，绑定随机 staging file:///URI，身份不稳定且泄露内部路径。
- I5 升级比较默认 RDFLib 规范化，错误视 lexical integer01与1为相同，可能漏报数据损失。

Minor M1 explicit unsupported PDF filter 被映射 BACKEND_FAILURE 而非 UNSUPPORTED_CAPABILITY；安全拒绝仍存在。按 inline 执行规范不在本次重要问题修复通道内做可选小项，保留后续裁决。

审查员新鲜验证：192 contract/native-document/compatibility 测试12.51s；6 lock/provenance 测试1.01s，均退出0。它们不覆盖这些重现。全292/G-P0及安装未在只读审查重跑；历史主执行结果不是审查员新证据。

## 主执行验证与当前修复候选

主执行为五类问题建立8个真实/受控小输入回归，对应 URI边界/私有日志/重放、孤页预算、词法身份用例。八项全部先 RED，3.03s exit1：base/source/scope 未拒绝、subject 已创建 runs、日志含技术marker、相对URI不绑定、orphans未拒绝、比较错判一致。

I1 DTO统一拒绝可识别 URI authority username/password，包括 source:/scope:前缀，在 boundary JSON重校验时拒绝；4个真实接口病例 GREEN0.30s，证明未创建 runs。不是对任意自由文本做猜测。

I3 原生 PDF 预检移动到单次 quiet Python3.12子进程：可信模块 -P/PYTHONPATH、stdin最多1MiB+1、CPU15秒/墙钟20秒、只返回固定状态词、native stdout/stderr隔离；不修改调用者 logger 或全局 decoder。真实 DEBUG metadata 用例 GREEN2.81s。仍不是RSS/网络OS沙箱。

I2 新 native PDF 版本.5拒绝 orphan/fallback依赖页、校验Pages.Count，真实解析页数必须等于已验证页数且最多64。原始.4 wheel/证据保留不覆写。源测试23GREEN1.02s；必须另验证已安装.5，不把 source import 误称 installed SDK。

I4 import/edit/export传递已验证 typed base_uri；SHACL graph/shapes使用各自稳定内容hash-based urn base，不再由cwd隐式绑定。真实相对导入重放 GREEN1.66s。无法在给定opaque base解析的相对语法仍应失败，不回退到文件路径。

I5 比较通过Adapter内原生 lexical OntologyDocument API进行有界NT同构，只返回bool，不泄漏native graph；17Comparer GREEN1.53s，包含 lexical integer差异及BNode同构。没有修改 RDFLib进程全局NORMALIZE_LITERALS。

版本化native.5 wheel SHA8787a8706d63054e003f82d5f4f34eb13f7e97ce29de95c4d498359222ac7245，PDF源 SHAf70c24586ee4c4f78a84da36008abceff6f0998e0355d24371371f402093b8b5。来自同一核验original0.7.0 base，MIT/RECORD继承；project-only offline lock/sync，未用latest或改变全局设置。安装后五类回归+相关源nativePDF/comparer46GREEN4.11s exit0。旧installed-version断言观察到3FAIL/17PASS后按当前明确pin升级.5；不是更改语义预期让安全测试通过。

最终新鲜验证：.5 native17全部通过、shared contract exit0；全仓库 locked/offline300passed+14subtests162.81s exit0，包括实际 G-P0 当前.5在两个独立环境真实调用、fresh离线锁定安装，所有执行退出0。另以保留的真实.4报告对比实际新.5十五调用报告，schema/capability/semantic/error差异为空，compatible=true/exit0。主执行按一次 Important修复通道将I1–I5判定已修复；保留原始 REQUEST CHANGES，不把修复后的主执行验证伪称为第二次独立审查。MinorM1保留。以上是修复与执行证据，不代表产品发布或P1–P8交付。

## Declined-to-judge 的主执行裁决

- 历史全suite/native17/install报告不作为审查员独立重跑证明：接受，分别保留主执行来源。
- 旧单独 PDF task 不视作批准：接受。
- 前端/P1–P8/RBAC/certification/deploy/persistentWorker/RSS-networkOS隔离与未来SDK属于明确后续波次：本轮不虚构交付，继续在其计划中验收。
- 穷尽依赖审计、法律结论、任意规模font/interpreter、跨平台部署/业务gold correctness未判断：接受为当前范围限制，不能用于宣传全面安全。
- 同UID敌对进程OS隔离在可信caller-root边界之外：接受；descriptor I/O不是沙箱。
