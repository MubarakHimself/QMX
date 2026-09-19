---
name: Staged implementation sequence
sitting: architecture-QMX-2026-09-18
status: proposed — factory only after operator acceptance + Documentation Factory + epics
---

# Implementation sequence (not this sitting)

No production coding in Stage C. After OD-01, focused Codex recheck, operator acceptance, Documentation Factory, and epics:

## Slice 0 — substrate (observable) — connect / new

1. ContributionHit concatenate on federated facade (additive wire DTO) + pin/tombstone.
2. Operation descriptor type in qma-core; InvocationEnvelope + GrantRecord.
3. Product-session records + CAS commands + authoring/app-use grant intersection.
4. DAG topology validator (replace pairwise back-edge).
5. Persist Task Graph edges + outbox successor dispatch (connect existing enums).
6. JobHandle parent vocabulary (done/aborted/unknown) on any new handle DTO.

**Observable:** copilot/list/CLI can see ContributionHits; a 3-cycle template refuses; app-use session cannot call an ungranted op; crash between A complete and B dispatch yields one logical B.

## Slice 1 — four proofs as thin fixtures

- Default Book/BMS regression still green (**existing**).
- One ATC PolicyPair validates and simulates with zero Book keys (**new**). Venue client without OD-01 returns `venue_requires_book`.
- One ungoverned/non-Book recipe→release (no CT-33) with stable `recipe_def_id` (**amend** identity).
- App-use → change request (base hashes) → authoring session with v1 untouched.
- Export/import a headless pack into a second isolated tree; independent scanner passes.

## Slice 1b — safety failures

Pick at least two: shared-stream cancel + cutover; daemon restart restores pinned Task Graph via outbox; UNKNOWN command blocks handover; stale predecessor restart refused; grant refuses other instance.

## Later

Data recipe CT-06 kind (if metadata-sharing required), UI chrome (GAP-0081), GPU preflight, Caliper adapter, mutmut on WSL copies, ATC **venue** path **only if OD-01 is A**.

## Blockers now

- **OD-01** unanswered — venue ATC admission.
- QMA nested venv at mill-split worktree invalid — QMA tests not re-run.
- ADR-0023 still provisional (mill code reused anyway).
- Material contracts not Codex-rechecked.
- GAP-0081 chrome, GAP-0058, GAP-0062 machine, MemoryProvider backend.

## Regression gates

Existing QMB compile/fragment/project/rerun tests; QMN conformance venue kinds; QML mill tests (Codex 47 focused @ 270e992; Stage A 32). Do not weaken those to admit dummy Book. Do not report package tests as QML→QMB→QMN integration (P2-INT-001 remains unsupported).
