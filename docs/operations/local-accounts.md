# 本地账户与项目授权边界

本文件说明当前后端服务基础模块，不代表已部署HTTP登录服务、前端登录页面或第三方OAuth。完整后端/前端审批与推送顺序不变。

## 当前实现

账户初始化仅在空账户表进行一次，数据库singleton guard阻断并发重复bootstrap。创建账户必须有当前有效管理员Principal；新密码由SecretProvider引用解析，不接受明文配置回退。环境provider只解析显式allowlist的`env:ONTOLOGY_SECRET_*`引用，不扫描/返回其他环境字段。

密码使用随机16byte salt与600000次PBKDF2-SHA256，metadata只存salt/hash。Login输入为SecretStr瞬态；session为随机32byte URL-safe值，metadata只存SHA256摘要、user、8h expiry与revoked标记。其SecretStr及Principal repr不含凭据；未来HTTP层只能经HttpOnly/Secure/SameSiteStrict Cookie传递，不能放普通JSON/UI。数据库导出仍需私密保护：散列账户信息不是公开数据。

Principal是当前AccountService发出的不可变能力，私有proof绑定身份/角色显示值/session摘要，并以进程私有HMAC认证，不能靠修改dataclass或伪造用户名/role变成管理员。每次授权重新查session expiry/revocation、账户disabled及当前DB权限；Principal不是持久化通行证。HTTP不得直接接受Principal/digest/proof或身份header。

## 权限矩阵

| 项目动作 | 角色 |
|---|---|
| read | engineer、consultant、expert、admin、owner |
| edit/review | engineer、consultant、owner |
| certify | expert |
| approve_release | owner |
| deploy | admin |
| manage_members | admin、owner |

账户global admin仅提供admin职责，不自动成为专家或负责人。项目显式deny或`*`deny优先于任何角色，包括global admin。非成员与不存在/未知动作均拒绝，不返回可用于越权的项目内容。认证权限不等于已完成专家认证证据/发布门禁，后续治理模块必须绑定revision和依赖。

## 登录预算与审计

每个规范化用户名的摘要按5min固定窗口累计失败，五次失败后拒绝进一步登录；成功清除失败预算，窗口到期再允许。缺失账号与错误密码均执行等成本PBKDF2并返回固定失败码。失败预算和审计必须先提交，不能随着抛出公开错误而回滚。

真实双线程最后一个预算槽测试先RED：两次都通过预算检查而返回AUTHENTICATION_FAILED。SQLite legacy SELECT不会自动开启写事务，修复在查预算前`BEGIN IMMEDIATE`，让budget-check/hash/write串行原子化；新结果一项失败、一项限流，总计5次。当前是SQLite/V1策略，会短暂串行化本地登录；未来PostgreSQL应提供真实行锁/事务策略再验收，不能照搬或称为分布式限流。

审计仅actor/action/resource/outcome/time；不包含请求body、密码、session明文、provider返回值或原始异常。秘密provider不可用只返回固定SECRET_UNAVAILABLE，不在聊天索取秘密。当前技术回归使用测试provider与临时SQLite文件，不是生产账户或外部服务联通证明。
