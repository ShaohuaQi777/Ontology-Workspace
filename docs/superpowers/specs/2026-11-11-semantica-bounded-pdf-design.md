# Semantica native bounded PDF extension — design for approval

## Intent and boundary

User chose to implement safe native PDF parsing before continuing, rather than defer PDF. Keep Semantica semantic parsing; no platform replacement extraction engine, no OCR/image recognition, no global decoder mutation or site-packages edits. Build a licensed Semantica distribution extension from pinned original plus existing document extension, increment patched version and genuine lock.

## Approach

Add `semantica.parse.bounded_pdf` with `validate_pdf_bytes(data) -> bounded PDF evidence` and `BoundedPDFParser.parse(path)` facade. Use the already-installed pdfminer/pdfplumber backend: a per-document PDFParser subclass wraps each freshly created PDFStream into a locally bounded decoder before any xref/object-stream resolution can decode it. Do not monkey-patch library globals. Resolve indirect length/filter/decode parameters using the same native object model, and walk every referenced xref object (including compressed object streams) under shared budgets. After validation, call Semantica PDFParser for text-only extraction on the same immutable bytes. The platform only invokes extension/preflight and projects results.

## Initial conservative limits

Input 1MiB; decoded stream 256KiB; total decoded bytes 1MiB; compression ratio 100; objects 512; pages 64; object/node traversal 10,000 nodes and depth32. Permit raw streams and bounded Flate decoding; filter chains/other filters, predictors other than identity, encryption, malformed xrefs/stream sizes, cyclic structural indirection and unsupported content are rejected explicitly, never fetched or repaired silently. Support valid classic-xref and bounded Flate xref/object streams only when verified; otherwise fail closed with capability limitation. Output text/JSON/artifacts 1MiB. A hard OS RSS/network sandbox is not claimed; preventing unbounded decoding is the specific objective.

## Verification and audit

TDD genuine text PDFs: raw and Flate success; tiny compressed expansion violation, cumulative/per-stream/ratio limits, filtered xref/object streams, indirect lengths, unsupported filters/predictors/encryption, malformed/cyclic references, excessive pages/nesting/objects. No large bombs; fixtures are bounded technical documents, not scenarios/gold labels. Assert decoder globals unchanged and original native baseline evidence preserved. Adapter malicious bootstrap/credential regressions remain mandatory. Independent reviewer checks decoding happens under the local decoder before Semantica opens input; no raw unsafe native PDF call permitted. Rebuild hash/RECORD/license validation, fresh locked environment, all17 native probes and whole suite, then A0-06 boundary review. Failure to prove safe object-stream routing blocks PDF support; it does not justify fallback.

## Alternatives not chosen

Deferral was offered and not selected. Linux-only RSS-limited execution does not satisfy the current macOS tool environment and adds deployment assumptions. A regex `/Length` scan cannot reliably protect filter chains/indirection/object streams. A separate platform PDF semantic engine violates the approved architecture.

Status: design and inline implementation plan explicitly approved by the user on2026-11-11. Implementation candidate is under independent security REVIEW; a source commit or passing technical tests is not release approval.
