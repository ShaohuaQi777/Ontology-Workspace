# 固定 Semantica 依赖制品

本目录仅分发 MIT 许可的上游 Semantica 0.7.0 原始 wheel 与用户授权的最小原生文档补丁 wheel。不是旧项目业务代码，不包含业务模拟、秘密或生产数据。保留 wheel 内的上游 MIT LICENSE 与源码。

原始 wheel SHA256：`faf27d6259ae813ddb44c5213e2f8867592f27e6e3d6b47cea10f1844513799f`，从用户授权清华镜像下载并核对镜像 simple-index 公布值。历史文档补丁 `.3` wheel SHA256：`e6482366b1d7a3425503d96a9657307f6a64e5bcf39491ea72b3e58b90e8de74`，保留其原始制品/证据。用户批准的有界 PDF 扩展候选 `.4` wheel SHA256：`56a2450c3dcd2457e338048e6054b7937e3e314859c424274a31bae0c91193cb`；从同一固定原始 RECORD 加文档/PDF 补丁确定性构建，RECORD/许可证/逐字节重建检查通过。`.4` 曾锁定安装并通过原有测试，但独立整分支审查 REQUEST CHANGES，发现 orphan Page repair 可以绕过页预算等五项重要问题；历史制品/失败与成功证据保留，不把它称为已验收版本。

当前修复候选 `.5` wheel SHA256：`8787a8706d63054e003f82d5f4f34eb13f7e97ce29de95c4d498359222ac7245`；native PDF源 SHA256：`f70c24586ee4c4f78a84da36008abceff6f0998e0355d24371371f402093b8b5`。同一核验original RECORD确定性重建，拒绝orphan/fallback页、核对树Count与实际解析页数；平台另修 URI userinfo、quiet bounded parent-preflight、稳定RDF base与lexical比较。已 project-only offline lock/sync，真实native17与共享契约gate通过。完整新鲜回归与A0验收仍需收尾；不是独立发布批准。

Ruling：将纯 Python 原始/补丁 wheel 纳入仓库，避免依赖本机 uv archive 随机目录或未发布的索引版本；代价是仓库增大约数 MB，收益是干净 checkout 可直接锁定安装与源码重建。小型 spaCy 模型不存入此目录，通过官方 URL 与锁中 SHA256 安装。

安装只读取固定补丁 wheel，不能从上游索引悄然切回不支持文档 API 的 0.7.0。重新构建的逐字节一致性由真实测试检查；后续补丁改变需要新版本、新 manifest/hash、新 wheel、更新 uv.lock 和完整兼容性验收。
