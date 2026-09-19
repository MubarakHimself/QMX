# RESUME-STATE — Stage A freeze

**Status:** `AWAITING_CODEX_CHALLENGE`  
**Candidate:** `qmx-workflows-arch-2026-09-18-a`  
**Folder:** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/`

This candidate is **internally reviewed**, not final, not ratified.

## Decisions made (see `.memlog.md` + spine AD-1..AD-22)

- Fast/headless BMAD architecture path; no routine operator questions.
- Capability-oriented composition over hexagonal libraries; no sixth COMP.
- Four discovery rails; ContributionHit is a named DEC-0389 amendment; never fp1.
- Reuse+extend QMA as workflow runtime; DAG topology; persist Task Graph edges.
- Product sessions `psess:` 1:N to QMA `sess:`; authoring vs app-use.
- Dummy Book mechanically refused; `UngovernedWorkConfig` vs `ResolvedRunConfig`.
- mutmut optional WSL-only test-strength, not a dependency.
- Documentation Factory **not** issued.

## Sources read

- Staged handoff 00–14, transcript `Explore-Node-Editor-Architecture.md`, Codex reference recon ZIP.
- Docs AGENTS/constitution/stack; spines 2026-09-14, 2026-09-16, QMA/QMB/QML/NODE.
- Implementation `270e992` (not stale `8510c03`).

## Uncertain / residual

- QMA pytest not executed (broken nested venv).
- Reviewers assessed the pre-fix draft; lead applied C-1..C-5. Stage C re-gates.
- C-05 live non-Book is an operator question (`OPERATOR-QUESTIONS.md`).
- ADR-0023 mill package still provisional (code reused).

## Tests performed

- QML mill subset: 32 passed @ 270e992.
- QMN conformance: 5 passed, 1 skipped.
- QMA: blocked.

## Files produced

Spine + companions listed in `ARCHITECTURE-CANDIDATE-MANIFEST.json`. Workflow `qmx-workflows-stage-a-donors` launched for donor notes (optional; stack already web-checked).

## How to resume (Stage C)

1. Operator runs Codex with `CODEX-CHALLENGE-HANDOFF.md` + `CODEX-CHALLENGE-INPUTS.zip`.
2. Return Codex ZIP + `13-GROK-RESUME-AND-RECONCILE.md` to a new Grok sitting.
3. Check candidate hashes still match; record any repo delta.
4. Reconcile findings; re-run architecture reviewer gate; then Documentation Factory — not before.

## Do not

- Simulate Codex.
- Start production coding, trading, deployment, or Documentation Factory from this sitting.
