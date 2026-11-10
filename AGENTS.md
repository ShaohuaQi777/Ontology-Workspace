# Repository execution rules

## Scope

- Build the ontology delivery tool from scratch. Do not import previous PoC code or create manufacturing simulations/business gold labels.
- Use Semantica for semantic logic via infrastructure/semantica_adapter only. Keep native objects and exceptions out of platform APIs.
- Build the React frontend independently. Never display fabricated pipeline histories as real runs.
- Fake backends are test-only. Do not wire them into the product backend factory.

## Implementation

- Read the current spec, plan, relevant source files and execution ledger before changes.
- TDD: write a failing test, run it, implement the smallest correct behavior, rerun targeted and regression tests.
- Use Python 3.12 and locked dependencies. Do not install semantica[all], silently change pinned versions or auto-download large models.
- Record necessary plan rulings, actual commands and exit statuses in the task ledger; statuses are TODO/IN_PROGRESS/REVIEW/DONE/BLOCKED.
- Make one responsibility per commit with task ID (A0-01 etc.). Work on an isolated feature branch/worktree; do not overwrite user files or force-push.
- A successful test using Fake is not evidence of native Semantica support. Preserve failed native probe evidence.

## Security and governance

- Generated objects are DRAFT. Review, expert certification and publication are separate explicit steps.
- Never store plaintext passwords/tokens in metadata, source, logs, UI responses or releases. Use credential references and fail closed.
- Check authorization, source scope, path containment, query read-only constraints and file limits before executing user inputs.
- Certification binds object and dependency revisions; modifications invalidate certification for a new release.
- Deployment success requires actual health/smoke checks and a tested recovery/rollback path.
- Install/push only within user authorization. Never modify global Git settings or request secrets in chat.

## Reporting

Claim completed features only after current verification output. Distinguish unit tests, native capabilities and system delivery. Report unknown/unsupported/unavailable without hiding gaps.
