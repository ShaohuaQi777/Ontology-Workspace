# 固定 Semantica 依赖制品

本目录仅分发 MIT 许可的上游 Semantica 0.7.0 原始 wheel 与用户授权的最小原生文档补丁 wheel。不是旧项目业务代码，不包含业务模拟、秘密或生产数据。保留 wheel 内的上游 MIT LICENSE 与源码。

原始 wheel SHA256：`faf27d6259ae813ddb44c5213e2f8867592f27e6e3d6b47cea10f1844513799f`，从用户授权清华镜像下载并核对镜像 simple-index 公布值。原生补丁 wheel SHA256：`e6482366b1d7a3425503d96a9657307f6a64e5bcf39491ea72b3e58b90e8de74`，从固定原始 RECORD/文件内容加受控补丁确定性构建。

Ruling：将纯 Python 原始/补丁 wheel 纳入仓库，避免依赖本机 uv archive 随机目录或未发布的索引版本；代价是仓库增大约数 MB，收益是干净 checkout 可直接锁定安装与源码重建。小型 spaCy 模型不存入此目录，通过官方 URL 与锁中 SHA256 安装。

安装只读取固定补丁 wheel，不能从上游索引悄然切回不支持文档 API 的 0.7.0。重新构建的逐字节一致性由真实测试检查；后续补丁改变需要新版本、新 manifest/hash、新 wheel、更新 uv.lock 和完整兼容性验收。
