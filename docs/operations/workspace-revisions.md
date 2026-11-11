# 工作空间、来源与认证原语

## 已实现的本波范围

项目namespace唯一并拒绝userinfo；创建者登记owner成员。TBox、ABox、SHACL、rules、vocabulary内容以有界canonical JSON保存，内容与显式依赖共同计算SHA256，父workspace revision形成变更链。写操作先校验项目权限，以SQLite写事务和条件更新做CAS；stale base不会提交新revision，旧内容不覆盖。每次save生成新的DRAFT，payload中的state不能改变平台治理状态。

依赖必须是同一项目的实际对应layer revision，不接受跨项目、缺失或类型不匹配引用。此处是治理元数据，不自行执行语义推理、OWL建模或规则求值；真实语义仍走Semantica Adapter，后续任务/治理波次完成工具界面与业务操作链。

## 专家证据原语，不是发布完成

Expert角色可对当前layer及当前依赖绑定原语证据。证据为有界、拒绝凭据字段/URI的JSON，保存原文、SHA256、操作者、对象及依赖revision、时间。保存证据不代表测试夹具具有领域专家业务正确性；发布审批、完整验证集、证据评估、changeset评审及release门禁仍由后续产品治理完成，不能因这条记录自动发布或宣称完整认证。

对象或依赖改变后不复用有效CERTIFIED。历史证据不可覆盖而继续保留；读取在同一个实际SQLite快照内计算当前有效状态，失效时回到DRAFT。原先“仅存在认证记录即CERTIFIED”的实现被真实依赖变化测试RED重现并关闭。修改内容同样产生新DRAFT，并拒绝再认证陈旧对象/依赖。

## 来源文件安全

注册只接受明确format和bytes，不接受上传filename/任意路径。输入<=1MiB；JSON凭据键/URL、DOCX ZIP展开路径/数量/大小/比率、原生PDF有界预检在任何来源持久化前完成。原生PDF预检为已验证的独立安静进程，未修改父进程logging，不隐藏orphan-page/decompression拒绝。

每项目独立0700目录，源文件0600、随机UUID文件名、exclusive创建。使用既有Directory dir_fd/O_NOFOLLOW能力，不跟随目录/文件symlink。读取先授权，检查项目sourceID、实际size/常规文件类型/SHA256；不因文件存在即允许读取。metadata数据库不得位于上传根目录中。SourceSnapshot绑定项目、sourceID、revision、格式、大小与hash；不暴露服务器绝对路径。

这不是OS隔离：同UID敌对进程不承诺隔离；源文件写入与metadata事务不是跨介质原子提交。异常断电/DB提交失败可能留下未登记的私有孤立文件，不可作为已登记source读取，后续运维备份/恢复需按metadata登记清单清点，不能仅扫目录当成功任务或盲目删除文件。没有承诺生产级RSS/网络沙箱或SaaS联通。

## 当前验收

真实临时SQLite与私有文件验证CAS、旧revision、重新打开、项目隔离、哈希/大小/symlink、credential URI、正常PDF及原生budget拒绝、父日志安静与有效认证依赖失效。仅技术夹具，不生成默认本体/制造业场景或伪造pipeline历史。整个后端仍未完成；继续Worker/API及后续连接器/治理/发布运维，不提前推送或开发前端。
