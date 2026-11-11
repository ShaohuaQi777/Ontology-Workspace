# Semantica Bounded PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close demonstrated PDF decompression exposure without replacing Semantica parsing.
**Architecture:** Per-document pdfminer parser/stream subclasses enforce decoding budgets before any native text parsing. Facade validates immutable input bytes, then uses Semantica PDFParser. Adapter invokes facade, not unrestricted PDFParser.
**Tech Stack:** Python3.12, pinned pdfminer/pdfplumber, native Semantica patched wheel and real uv lock.
**Spec:** docs/superpowers/specs/2026-11-11-semantica-bounded-pdf-design.md (approved by user).

## Global Constraints
- Input1MiB, decoded stream256KiB, decoded total1MiB, ratio100, objects512, pages64, nodes10000/depth32, output1MiB.
- Raw and verified Flate streams only; unsupported filters/predictors/encryption/malformed/cyclic structures fail closed. No global decoder mutation, OCR, downloading models, native site-packages edits or scenarios.
- Preserve upstream MIT provenance, original failed probe evidence, task-ID commits and real native verification.

## Review Focus
- Xref/object streams decode before ordinary object traversal: test budget applies on first resolution.
- Indirect lengths/filter parameters: test actual native object-reference resolution, not lexical scanning.
- Malformed/cyclic object/page trees: rejection before original parser execution.
- Aggregate small streams exceed total: test shared per-document budget.
- Global decoder unchanged and artifact bytes immutable: test independently before/after native invocation.

### Task PDF-01: Native bounded decoder and facade
**Files:** Create patches/semantica/bounded_pdf.py; tests/native_document/test_bounded_pdf.py.
**Interfaces:** validate_pdf_bytes(data:bytes)->dict[str,int]; BoundedPDFParser.parse(path:Path)->dict; ValueError for invalid/budget inputs, NotImplementedError for unsupported forms.
- [ ] Write RED tests for raw/Flate text success, per-stream/ratio/aggregate limits, indirect length, xref/object streams, unsupported filters/predictors/encryption, malformed/cyclic reference/page trees and excessive pages/nesting/objects; no oversized bombs.
- [ ] Run `.venv/bin/python -m pytest tests/native_document/test_bounded_pdf.py -q`, observe missing implementation RED.
- [ ] Implement local PDFParser subclass intercepting newly created PDFStream after inherited stream token parsing, replacing before use with budget-aware PDFStream. PDFDocument object traversal/page budget uses the same local parser. Bounded Flate via zlib.decompressobj max_length; reject unsupported decoding rather than invoke unbounded super.decode. Facade validates then invokes native Semantica text-only parser on identical bounded bytes.
- [ ] Run same tests GREEN; independent decoder/security review required before PDF support claims.
- [ ] Commit `feat(PDF-01): add native bounded PDF parsing extension` only after review and verified wheel build.

### Task PDF-02: Reproducible SDK package and Adapter routing
**Files:** Modify scripts/build_semantica_patch.py, patches/semantica/manifest.json, vendor/README.md, pyproject.toml, uv.lock, adapter backend/input_policy/worker; create vendor licensed .4 wheel as approved extension version.
**Interfaces:** semantic distribution0.7.0+ontologyworkspace.4 exports semantica.parse.bounded_pdf; metadata must match Adapter/probes/lock.
- [ ] Write RED build/installed-version and Adapter safe PDF success/rejection tests. Native .3 baseline remains immutable evidence.
- [ ] Extend deterministic wheel builder with bounded_pdf module, rebuild from vendored original, verify RECORD/SHA/license, update project-only lock and fresh locked environment.
- [ ] Route typed PDF parse through bounded facade and native bounded preflight before persistence; no raw parser fallback.
- [ ] Run full tests, all17 native probes and gate, fresh installed boundary tests, git diff --check; review new evidence without relabeling old .3 evidence.
- [ ] Commit `build(PDF-02): lock native bounded PDF backend and route adapter`.

### Task PDF-03: Resume A0-06 acceptance
- [ ] Re-review bootstrap -P, typed-format and canonical credential preflight, directory-capability isolation, all resource and real native regression tests.
- [ ] Record actual statuses/commands/limits; commit remaining A0-06 only after all Important/Critical defects resolved. Continue A0-07/08 thereafter.

Execution method remains user-authorized native inline. This plan is a bounded security extension, not a new product wave.
