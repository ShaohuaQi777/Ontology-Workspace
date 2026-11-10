# 真实候选 G0 通过：0.7.0+ontologyworkspace.3

通过范围仅 native_probe_evidence_only，不是 G-P0、企业安全认证或整个项目交付。

完整候选实测 17 项原生 case 全通过，CLI exit0；全仓测试 101 passed、14 subtests passed，exit0。所有 native 方法实际从已安装本地版本包调用，未 mock metadata/module；基线环境与之前失败证据仍保留。

Semantica base=0.7.0，真实候选分发版本=0.7.0+ontologyworkspace.3，固定 wheel SHA256=e6482366b1d7a3425503d96a9657307f6a64e5bcf39491ea72b3e58b90e8de74。构建校验原始固定 RECORD、每个源码文件哈希/大小与许可，加入有哈希的原生文档/本地词法 parser 扩展，更新实际代码/metadata/RECORD，确定性 wheel 可复建。

原生文档支持安全 Turtle/NT 子集，无损保留匿名 restriction、imports 声明、typed literal 原始词法，不 fetch imports。label 编辑返回新文档，限定命名类/属性且只变更目标语句；语言大小写不敏感。RDFLib 全局 flags/registry 不修改。本地 strict_literal 保留 lexical str 与 native value/type/language/ill_typed 元数据。

## 独立审查与修复

E1/E2 提前审查曾 REQUEST CHANGES：嵌套 JSON-LD context 可联网，XML/JSONLD literal lexical normalization、named graph 丢失、语言匹配与 token 空白问题。均已实测 RED 并处理。

JSON-LD/XML 暂未安全支持，当前明确拒绝格式；不是接受后丢数据、不是完整 P2 格式能力。数字 shorthand、token/normalizedString、typed Literal 的词法保真与原文不变都有真实回归。NT 的 raw TAB 与 escaped \\t 是等价 RDF 转义，测试不把转义拼写变化当三元组丢失，也不使用默认 Graph.parse 掩盖 normalization。

独立 reviewer .3 复审 APPROVE，仅针对最小原生文档补丁；通过两 datatype × Turtle/NT × 导入/再导入/无关编辑的 RDF term 身份检查，核对安装代码/manifest/RECORD/版本。该审查不代替未来 P0 全分支 review。

实体/依赖关系抽取现在实际使用 spaCy3.8.18 与官方 CPU en_core_web_sm3.8.0，ML/dependency provenance 检查通过。小模型 12,806,118 bytes，下载 SHA256 与官方 checksum_whl 一致；无 transformers/torch/训练/业务模拟。事件仍是真实 fixed keyword patterns，不是 LLM；别名 linking 不是全跨本体语义对齐。更完整能力按已批准 P1–P8 继续，不据 G0 夸大范围。

剩余 G-P0 门禁：锁与新安装、shared contracts、完整 Adapter/native object/error/log 隔离、Fake 产品工厂拒绝、upgrade compatibility。
