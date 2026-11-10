# A0 锁定与干净安装

## 固定输入

Python要求 `>=3.12,<3.13`；本机使用3.12.12、uv0.12.17。项目源仅清华镜像，配置写在项目内，不改变系统pip/uv设置。真实 Semantica fork固定0.7.0+ontologyworkspace.3，纯Python wheel与原始0.7.0 wheel在vendor中保留MIT许可与源码；原始下载SHA256与清华simple-index公布值相同，补丁重建结果逐字节等于纳入仓库的wheel。

必要extras为documents/parse-pdf/shacl/tripletstore-oxigraph；SQLAlchemy在真实原生SQLite探针发现缺依赖后显式加入。RDFLib固定7.6.0，以确保本地词法parser/Literal slots适配有确定版本。spaCy固定3.8.18、官方CPU en_core_web_sm3.8.0，模型下载SHA256与官方checksum一致。没有Semantica[all]、transformers、torch、TensorFlow、Docling、大模型下载或训练。

uv.lock固定全部传递依赖/源/各平台wheel hash，包括本地补丁wheel与官方小模型hash；不手工编辑锁解决冲突。optional extras的元数据出现在锁中不代表这些extras被选中安装。根项目目前package=false，pytest明确包含src路径；A0-06实际产品包完成时再调整包发现，不凭空创建产品模块。

## 复现

在仓库根运行：

```sh
export UV_CACHE_DIR="$PWD/.cache/uv"
uv sync --locked --python python3.12
uv run --locked python -m pytest tests -q
uv run --locked python -m spikes.semantica.runner --output .runtime/a0
```

全新且不存在的环境可用 `UV_PROJECT_ENVIRONMENT=.venv-repro-a003` 执行相同sync/run；不删除或复用已有环境冒充全新安装。每次重新验收使用新目录名。模型首次同步需要网络；离线复现只在所有锁定wheel已缓存后有效，不宣称任意干净机器离线可用。

补丁重建可先将已核对SHA256的vendor/upstream原始wheel解压到新项目内临时目录，再运行 `python -m scripts.build_semantica_patch --base <verified-base-dir> --output <new-output-dir>`。真实test_patch_build从vendor原始wheel自动创建隔离临时目录并校验每项RECORD/文件hash/size，无需本机随机uv archive目录。

## 验收范围

锁生成成功，98锁条目/95当前平台安装包，源及模型/补丁hash已核对。默认新环境和独立新环境 `.venv-repro-a003` 均执行完整测试：103 passed +14 subtests，exit0；独立环境重放17/17原生G0通过，CLI exit0。原始/补丁wheel从vendor重新解压构建逐字节相同，4构建测试通过。A0-03本机锁与全新venv验收完成；使用已缓存wheel的全新venv不是未经联网缓存的离线机器，不混淆两者。原生runner自身的not_yet_verified列表仅表明该命令只验证native探针，单独锁定验收依据本文完整命令及测试输出。本机macOS arm64通过不代表Linux、Windows或Docker部署通过；跨平台与部署必须后续真实验收。锁定/安装不代替G-P0隔离/契约/升级验证。
