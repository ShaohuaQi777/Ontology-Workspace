# 工具契约 0.1.0 提案

JSON Schema2020-12与OpenAPI3.1的本工具提案，不表示双方已冻结，也不表示HTTP服务器已经实现。

## 文档范围

scenario-pack是预先已有名称的技术交付源包清单，不是场景模拟器。Pack major支持1，包含本体入口、可选Shapes/映射/规则/测试入口与来源；source.id重复拒绝，凭据只允许cred引用。验证函数不执行查询、脚本或解析源语义。

ValidationResult记录workspace/graph/suite/backend/run版本与finding证据；推导finding必须提供rule_version与非空premise_refs。通过状态不能附错误或error severity finding。

ReleaseManifest版本绑定内容、hash/size、验证运行与approval_id，只是清单与文件完整性校验，不实现审批/签名/部署发布。制品限定64MiB，路径必须相对POSIX、真实resolve在指定root内，symlink逃逸与重复resolved artifact拒绝；SHA256流式计算且size核对。

BackendOperation包含14操作的显式source/graph/schema/suite/ruleset/release输入ID、版本化请求/响应与平台BackendError。生成candidates只能DRAFT，confidence未知保留null，不转换为1。object_refs/certification_refs/scope_ref/adapter_version为后续治理/鉴权/查询预留，不表示相关授权已实现。请求parameters只是有界JSON，不承诺所有语义参数已被原生执行。

## 可执行校验

`uv run --locked python -m contract_tools.validate --kind KIND --file PATH`验证结构，JSON或受限safe_load YAML，大小/节点数有界；错误只返回JSON Pointer/code/通用message，不附原值、native exception或traceback。

真实路径与制品检查是显式Python接口 `validate_pack_paths(root, manifest)` 与 `verify_release_files(root, manifest)`，结构CLI本身不冒充完成这些文件检查。它们不实施项目RBAC或打开远程URI；调用者必须先提供已授权root。Schema引用由本地固定Registry解析，禁止随文档加载网络Schema。

独立联合门禁：`uv run --locked python scripts/verify_a0.py --evidence PATH --verify-contracts`真实运行contract pytest，并同时检查17项native证据；不能由CLI调用者提交contract_exit_code=0伪造通过。范围仅native_and_contract_evidence_only，不是G-P0。完整Adapter对象/异常/日志隔离、shared Fake/real契约和upgrade门禁将在A0-06–08继续。
