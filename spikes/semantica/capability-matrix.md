# Semantica 实测能力矩阵

A0-02 原始 0.7.0：14/17 passed，G0 failed。用户授权最小原生文档扩展后，真实分发 `0.7.0+ontologyworkspace.3`：17/17 passed，G0 native evidence only passed（CLI exit0），G-P0 尚未通过。

| 范围 | 实际原生 API | 实测边界 |
|---|---|---|
| CSV/JSON/SQLite | FileIngestor.ingest_file、CSVParser.parse、JSONParser.parse、DBIngestor.ingest_database | bytes/rows/type；SQLite显式 mode=ro、表/行限制；源码必要 SQLAlchemy |
| PDF/DOCX | PDFParser.parse、DOCXParser.parse | 实际生成技术文档文本/页/段落断言，无OCR/Docling |
| 抽取 | methods.extract_entities_ml、extract_relations_dependency、EventDetector.detect_events | 真实离线 spaCy 小模型及 ml/dependency provenance，模式降级失败；事件仅fixed patterns不是LLM |
| 图/本体生成 | GraphBuilder.build、OntologyGenerator.generate_ontology、OWLGenerator.generate_owl | 禁止默认ML合并/自动冲突解决；实际Node/linksTo类属性 |
| 无损文档/编辑 | semantica.ontology.document.OntologyDocument.from_rdf/serialize/with_label | 用户授权原生扩展；Turtle/NT完整三元组/BNodes/OWL/imports，typed literal词法、有限label编辑/新文档；不fetch，XML/JSONLD暂拒绝 |
| SHACL | ontology_validator.run_shacl_validation | pyshacl真实正/负约束、focus/path/mincount/report；不是placeholder validate |
| 推理/冲突/溯源 | Reasoner.infer_with_results、ConflictDetector.detect_value_conflicts、ProvenanceManager.export_prov | 正向有限非递归技术规则premises/rule；值冲突source/quote；PROV不含所有source位置字段 |
| SELECT/ASK | TripletStore(oxigraph)、SPARQLReasoner.execute_query | PyOxigraph本地真实URI bindings/正负ASK；AST先拒SERVICE/FROM/mutation/customFn；不是远程部署验收 |
| normalize/alias | TextNormalizer.normalize_text、EntityNormalizer.link_entities | NFC/显式alias canonical；不是完整跨本体语义匹配 |

真实结果、源码/hash/model/许可及失败基线均保留在报告目录。全仓当前 101 tests +14 subtests passed，包括26原生文档/独立审查回归；计数不意味着101项原生能力。

## 限制与剩余门禁

JSON-LD/XML在安全数据集/词法保真实现前拒绝；完整可视化OWL/SKOS/SHACL字段并未因基本标签编辑而完成。单进程 Python logging/stdio/cache guards不是网络/进程沙箱。认证/授权/来源字段scope/发布回滚/P1–P8仍须产品实现和实际验收。

G-P0 尚需 uv.lock干净安装、共享真实/Fake契约、完整Adapter原生类型/异常/日志隔离、产品factory拒Fake、upgrade compatibility及P0结束独立全分支review。
