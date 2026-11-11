# Wave2 native 能力探针（不等同产品接入验收）

已锁Semantica0.7.0+ontologyworkspace.5/Python3.12。执行`uv run --locked --offline python -m pytest tests/service/test_native_optional.py -q --tb=short`：3passed/1.55秒/exit0；每个SDK探针为私有subprocess，无native对象/异常进入HTTP，无下载/新增依赖。

## 实际结果

1. DBIngestor.execute_query(connection_string,query,**params)真实SQLAlchemy SQLite mode=ro/immutable实际SELECT返回技术行id=n1/value=7；实际UPDATE拒绝，源SHA未变。底层连接支持，不称产品Registry/列权限/PostgreSQL已经完成。
2. ImageParser.extract_text(path)实际尝试32x32自生成技术PNG；pytesseract包不在本环境且PATH无tesseract，SDK实际拒绝。不能把ImageParser的PIL metadata-only方法叫OCR成功。OCR状态UNAVAILABLE/尚未验收。
3. TextEmbedder().embed_text技术字符串实际运行/get_model_info.method='fallback'，得到向量仅是SDK fallback，不是已配置神经模型。sentence_transformers/torch/transformers缺失，未执行CLIP模型；不把fallback hash向量宣称RAG语义模型或CLIP对齐。neural RAG/CLIP未验收。

## 固定接口与安全前置

installed native ingest/db_ingestor.py的DBIngestor.execute_query绑定params，返回row dict list；SQL用户输入不安全，产品只能server生成许可table/columns单条SELECT。在private readonly snapshot执行并绑定源hash，不能仅最后掩码列。native ingest/api_ingestor.RESTIngestor存在，但默认会response.json/text全量buffer；不可直接把默认buffer当平台1MiB限额。

native ingest/ssrf.py.request_with_ssrf_guard(method,url,session,allow_private_ips,max_redirects,...)已经包含public DNS/IP pin/TLS hostname与每跳防护，后续Adapter复用并禁redirect/environment proxy/有界stream，再真实native JSONParser。未发生当前外部网络读取/飞书授权联调，没账号不假称联通。

## 必要后续条件

OCR需要explicit operator Tesseract可执行文件+语言模型与pytesseract。RAG/CLIP需要明确许可且固定hash/local模型、相应Python依赖与offline加载。尚未有这些授权，不安装系统软件或静默下载大模型。飞书真实接入需操作者在自己SecretProvider安全配置，只提交引用，不在聊天/源码/报告保存token。当前优先继续无外部依赖Registry/SQLite/Pipeline；这些未知能力均不计入完整后端完成。
