# Wave1：真实本地服务与恢复

## 组合与启动

本地CLI现已组合受保护HTTP与一个实际NativeJobWorker后台消费者，而非只登记pending任务。启动参数仍为绝对受保护SQLite URL/private artifact root/精确Origin；默认127.0.0.1:8765、生产Secure Cookie，本地HTTP需明确`--insecure-dev`。不创建生产账号、不索取聊天秘密、不修改当前DSH GUI服务。账户通过受控AccountService显式初始化，SecretProvider只允许明确引用。

消费者开始前在数据库同目录的private `*.worker.lock`持有O_NOFOLLOW/O_CLOEXEC描述符及非阻塞排他flock；检查regular/UID/0600及路径inode，拒绝hardlinked数据库以免不同路径别名绕过owner文件。不能使用数据库inode本身flock：实际macOS实验显示其与SQLite写锁相冲突；独立owner文件保留互斥同时允许BEGIN IMMEDIATE。

启动只有获得该单机占用后才对固定local-worker的旧running任务执行interrupted恢复，证明旧服务不再持有占用。第二个占用者失败，不擅自把仍活跃的任务恢复。此机制要求所有本地消费者通过此入口，不是分布式租约或对抗同UID恶意修改的OS沙箱。目录/数据库被外部替换不是受支持运维流程。

消费者用200ms事件等待处理pending，原生业务仍只调用真实Semantica factory。后台基础设施异常使readiness503，不把HTTP活着等同于Worker正常。退出先停接新任务/等待在途native步骤，最多100秒，期间不提前释放占用；强制进程中断则下一启动保留旧interrupted证据，只有显式replay创建新run_id。不会自动重试或把原任务补成success。

## 真实验证

自动化实际TCP测试覆盖createproject→source上传→202排队→后台native parse→events/rows/manifest，停止重启后相同会话/数据/成功任务仍可读。另实际SIGKILL观察到running extraction、重启看到interrupted/result=null、显式新run重放成功且旧任务仍interrupted。技术输入有界：重复100句仅用于实际计算/抢到运行边界，不是业务场景或质量金标；最初1500句在受限native路径返回BACKEND_FAILURE已保留；未细分确认该原生失败原因，不修改任何原生预算或伪造结果迎合测试。

独立managed服务确实在http://127.0.0.1:64961启动，实际health/readiness200、native.5/parse rows与manifest SHA校验、匿名401/Origin403/CSV密码字段404且无输入回显。该端口是本次技术fixture临时地址，测试后SIGTERM收集job并实际connect_ex确认关闭；不是长期部署链接。当前DSH GUI端口未改动。

单独fresh locked环境执行CLI help及完整回归；确切数量/用时见本波验收报告。仅本波单机工具服务完成：PostgreSQL、OCR/飞书/SaaS/RAG/CLIP/Pipeline、完整发布治理、Action/BadCase、生产TLS/系统资源网络隔离仍在后续范围，不冒称完整后端交付。

## 权限、秘密与可用性闭合

独立全波review原判CHANGES REQUESTED，三项Important：首个URI后隐藏第二userinfo/query credential、CSV密码列变成native结果/制品、同步来源预检阻塞ASGI事件循环。保留原判，不伪造独立复审批准。修复逐项先9RED，再所有URI/标准化credential query检查、CSV header复用JSON credential key策略、完整来源登记线程池；不把自由文本扫描说成完美DLP。Source权限/预检仍先于写文件/DB，真实语义解析未搬到平台。

来源JSON仍128KiB HTTP限额/raw1MiB，预检在线程池运行而非事件循环；并发使用框架有界线程池及服务器32处理预算。调度回归的300ms delay是明确test-only外围探针，随后调用真实登记；不是Fake Semantica，也不假称跑了20秒病态PDF。实际PDF预检路径保持私有有界子进程。

FS与DB不跨介质原子。崩溃前native子进程/私有staging可能留下未发布制品，不能靠job恢复杜撰OS子进程完全回收；显式replay用不同run目录，旧残留未列成功manifest。后续manifest盘点/备份恢复另行实现，不盲删文件。
