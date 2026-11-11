# Semantica 升级兼容性门禁

## 当前边界

这是仓库内开发验收工具，不是在线安装器或生产发布权限。当前批准并固定的 SDK 是 `0.7.0+ontologyworkspace.4`。没有收到新版本候选，因此当前真实验证仅为同一锁版本在两个独立 Python3.12 环境自对比；受控破坏 JSON 是比较器单元测试，不是运行过未来 SDK 的证据。

## 可复现入口

从仓库根目录执行，输出路径必须不存在，避免覆盖历史证据：

```bash
export UV_CACHE_DIR="$PWD/.cache/uv"
uv run --locked --offline python scripts/record_semantic_contract.py \
  --workdir .runtime/upgrade-baseline-cases --output .runtime/upgrade-baseline.json
UV_PROJECT_ENVIRONMENT="$PWD/.runtime/upgrade-candidate-env" \
  uv sync --locked --offline --python python3.12
UV_PROJECT_ENVIRONMENT="$PWD/.runtime/upgrade-candidate-env" \
  uv run --locked --offline python scripts/record_semantic_contract.py \
  --workdir .runtime/upgrade-candidate-cases --output .runtime/upgrade-candidate.json
uv run --locked --offline python scripts/compare_semantic_versions.py \
  --baseline .runtime/upgrade-baseline.json --candidate .runtime/upgrade-candidate.json \
  --output .runtime/upgrade-comparison.json
uv run --locked --offline python scripts/verify_a0.py \
  --evidence spikes/semantica/reports/0.7.0-ontologyworkspace.4/summary.json --verify-p0
```

`--verify-p0` 不是接收调用者布尔验收：实际执行共享契约、兼容性、原生文档与探针相关测试；生成当前环境真实报告；在项目内随机独立新目录离线锁定安装，再生成相同用例报告并比较。错误/超时/缺失用例/安装失败全部失败。门禁测试目录不参与内部测试调用，避免递归运行。新环境与所有报告保留在 `.runtime/gp0-*`，实际退出码记录于该目录。离线缓存缺失应报告安装失败，不能模拟 SDK 或偷偷改用网络/latest。

成功输出的 `scope=g_p0_execution_only`、`release_approved=false` 是有意区分：技术执行证明不代表独立安全审查、人类专家认证、完整产品、Linux/Docker 部署或发布批准。A0 状态在独立审查完成前仍是 REVIEW。

## 比较规则

真实报告固定声明 backend_kind/backend_version/adapter_version/contract_version、环境身份、请求/结果 Schema、能力，以及输入请求与来源修订的 SHA256。记录七类成功、七类错误哈希输入、有限规则语法失败，共十五个真实调用。实际 SDK/Adapter 执行只有产品工厂的 semantica 路径；没有 Fake 入口。测试专用固定契约输入不是业务场景或语义金标。

比较所有必需 case、同输入/版本 hash、Schema 字段/类型/枚举/required、能力约束、稳定错误与 retryable、来源与对象引用、确定性规则结论/前提引用/规则版本、图数据和 RDF 同构。仅支持有界 NT 图，最多128三元组/32空白节点，不读取 imports/外部 URL。随机空白节点标签不构成不兼容；SHACL 保留命名 Shape、约束、参数、严重级别与消息，仅归一化已识别的解析器随机匿名 Shape 标签。输入 Shape 改动仍由请求 hash 捕获。

抽取可能含非确定性模型采样：比较字段类型与 DRAFT 等审核状态契约，不比较重采样文本、候选数量或具体测量分数；null/数值类型变化会报告，来源绑定仍比较。不保证同一提示重采样逐字一致。

当前 Schema 比较保守：忽略 title/description 注释，其余结构变化均进入人工差异审查，不自动判定新字段一定向后兼容。未来约束放宽必须新增真实破坏测试并审查，不能静默放行。

## 收到显式未来候选后

先保留当前 lock、已核验 wheel/manifest、真实报告和旧环境。建立独立候选分支/工作树，并由授权明确指定版本或源码 commit；不得在测试当前分支时替换生产 lock、SDK 包、全局配置或安装 latest。核验来源/许可证/hash，将候选安装于不存在的项目环境；在候选分支明确修订 Adapter 支持版本门禁，运行同一 Adapter 及共享用例，保存原始差异与安装失败。候选接口缺口必须报告，不能让 Fake/平台算法补齐。

所有差异经独立代码与安全审查、人类必要批准后，才可形成新 lock/版本化 wheel、完整回归、部署验证与回退方案。旧环境和旧制品保留到新版本验收完成；回退应恢复已验收的旧 lock/制品/部署，而不是未经验证降级。该未来流程目前没有新候选执行证明。
