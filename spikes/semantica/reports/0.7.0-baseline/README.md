# Semantica 0.7.0 实测基线（G0 未通过）

本目录保留真实原生探针结果，非 Fake、非场景模拟。测试输入仅为领域无关技术夹具。

## 实测结论

固定 Python 3.12.12 与 Semantica 0.7.0，用户批准的清华 PyPI 镜像。完整原生 CLI 对 17 项探针执行后：14 项通过、3 项未通过，退出码 1；不得据此宣称 G0/G-P0 或项目完成。

通过：CSV/JSON/只读 SQLite 接入、PDF/DOCX 解析、图构建、本体生成、真实 SHACL 正反例、带规则/前提的正向推理、值冲突与来源证据、PROV 导出、本地 Oxigraph SELECT/ASK、Unicode 规范化/显式别名链接。

失败和不可用：
- 实体/关系/事件：原生方法调用真实发生，但缺少本地 spaCy 配置时仅获得 pattern DATE 实体、无关系，ML/dependency provenance 检查失败。事件是真实固定关键词模式，不是 LLM 抽取。
- ontology_roundtrip：输入 9 三元组，输出 7；匿名 restriction、imports 和全图同构检查全部失败。严格夹具与实际输出保留在本目录，未缩小验收。
- ontology_edit：无已核实可调用的原生通用编辑 API，状态 unavailable / NATIVE_API_UNAVAILABLE；未自行改 dict 或 RDFLib 图补出原生成功。

## 证据及边界

- [完整原生证据](native-evidence.json)：固定 case ID、版本、原生符号、输入引用、检查和制品 SHA256。
- [依赖来源记录](dependency-provenance.json)：安装来源和版本；393 个安装后的 Semantica Python 源文件均与之前官方下载缓存 SHA256 一致。未独立验证 wheel 原始归档 SHA256，且不等于锁定/干净安装证明。
- [NLP 实际结果](run-e983ea9d607d4b08a8535634e09fac20/result.json)：明确记录 pattern 降级，未接受为 ML 成功。
- [复杂 OWL 输入](run-819b4ececcee45a0a3799834dbb2b6e4/complex.ttl) 与 [原生往返输出](run-819b4ececcee45a0a3799834dbb2b6e4/roundtrip.ttl)。

普通证据/错误/只读 AST/日志隔离回归 53 项通过（exit 0），包括真实 SDK logging 与 stdout 的秘密抑制测试；这不是 53 项原生能力证明。原生完整 pytest 首轮为 12 passed / 6 failed（其中 1 项为真实安装版本检查），之后修复本项目对 dict 输出的错误转换、补齐源码明确要求的 SQLAlchemy/PyOxigraph 并逐项验证；最终完整 CLI 基线如上。

只读 AST 明确拒绝 UPDATE/INSERT/DELETE、CONSTRUCT、SERVICE、FROM/FROM NAMED、外部自定义函数，并允许文字常量中的这些单词。该语法门禁和串行 Python 日志/cache 守卫不是完整进程网络沙箱、授权隔离、执行超时或企业验收。显式别名链接不是跨本体语义匹配；PROV Turtle 也不是所有 source quote/location 的完整导出。

G-P0 仍需可复现锁、共享 Fake/真实契约、完整 Adapter 隔离与升级兼容验证。上游能力缺口需必要授权决定，不允许隐瞒或替代引擎。

## 复现

从项目根运行 `.venv-probe/bin/python -m spikes.semantica.runner --output .runtime/a0-recheck`；当前未修补的 0.7.0 基线预期退出 1。运行 `.venv-probe/bin/python -m pytest tests/spikes/test_native.py` 会真实执行全部验收，不 skip/xfail；普通隔离单元测试的 metadata fixture 不作用于这个模块。
