# Semantica capability investigation

Task: A0-02. Candidate: semantica 0.7.0, CPython 3.12.

Status: source inspection only. The fixed wheel has downloaded to the local uv cache; the complete dependency installation is still running. No native case has passed yet, and G0/G-P0 have not passed.

The cached wheel METADATA declares Version 0.7.0 and Requires-Python >=3.10,<3.14. Core dependencies include scientific libraries and pyarrow. Selected extras are documents/parse-pdf/shacl only; all/model/GPU extras are not installed.

| Capability | Candidate native API / source | Runtime evidence |
|---|---|---|
| File ingest | semantica.ingest.file_ingestor.FileIngestor.ingest / ingest_file | Pending complete installation and real case |
| PDF/DOCX parse | semantica.parse.document_parser.DocumentParser.parse_document | Pending complete installation and real case |
| Extract | semantic_extract module; precise configured entry point to be verified | Pending; no auto-download of models |
| KG | semantica.kg.graph_builder / knowledge_graph | Pending exact native signature and real case |
| Ontology candidate | semantica.ontology.engine.OntologyEngine.from_data | Source signature inspected; not runtime-tested |
| SHACL | semantica.ontology.ontology_validator.run_shacl_validation; OntologyEngine.validate_graph | Source entry point inspected; positive/negative cases not run |
| Reasoning | semantica.reasoning.reasoner.Reasoner.add_rule / add_fact / forward_chain | Source signature/result fields inspected; not runtime-tested |

## Preliminary findings (not acceptance)

- OntologyEngine lives in ontology/engine.py, not ontology_engine.py. SHACL helpers live in ontology_validator.py, not shacl_validator.py. Guessed URLs returned 404 and are not used as API proof.
- InferenceResult exposes conclusion, rule_used, premises, confidence and metadata. Adapter must convert rule objects and premise refs into stable platform values.
- Native DocumentParser and OntologyEngine include exception text in native progress/log paths. P0 must test native log containment as well as returned error DTOs before sensitive source operations are enabled.
- Source inspection is not proof of parse, inference, ontology roundtrip or SHACL runtime success. Actual test case results, versions, inputs, checks and artifact hashes will be recorded by the runner after installation.

## Pinned source references

- https://github.com/semantica-agi/semantica/blob/v0.7.0/semantica/ontology/engine.py
- https://github.com/semantica-agi/semantica/blob/v0.7.0/semantica/ontology/ontology_validator.py
- https://github.com/semantica-agi/semantica/blob/v0.7.0/semantica/parse/document_parser.py
- https://github.com/semantica-agi/semantica/blob/v0.7.0/semantica/reasoning/reasoner.py
