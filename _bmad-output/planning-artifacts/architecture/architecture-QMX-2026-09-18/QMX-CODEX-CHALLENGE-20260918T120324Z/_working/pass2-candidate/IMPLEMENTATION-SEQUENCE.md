---
name: Staged implementation sequence
sitting: architecture-QMX-2026-09-18
status: proposed — factory after Documentation Factory + epics
---

# Implementation sequence (not this sitting)

No production coding in Stage A. After Stage C + Documentation Factory + epics:

## Slice 0 — substrate (observable)

1. ContributionHit concatenate on federated facade (additive wire DTO).
2. Operation descriptor type in qma-core; wrap three existing doors (library.search, analysis.project, qmb.run query/run split).
3. Product-session records + authoring/app-use grant intersection (sqlite amendment).
4. DAG topology validator (replace pairwise back-edge).
5. Persist Task Graph edges + successor dispatch (connect existing enums).

**Observable:** copilot/list/CLI can see ContributionHits; a 3-cycle template refuses; app-use session cannot call an ungranted op.

## Slice 1 — four proofs as thin fixtures

- Default Book/BMS regression still green.
- One ungoverned/non-Book recipe→artifact (no CT-33).
- App-use → change request → authoring session with v1 untouched.
- Export/import a headless pack into a second isolated tree without secrets.

## Slice 1b — one live-cycle failure

Shared-stream cancel **or** daemon restart restores a pinned Task Graph **or** UNKNOWN command blocks handover.

## Later

Data recipe kind (if metadata-sharing required), UI chrome (GAP-0081), GPU preflight, Caliper adapter, mutmut on WSL copies, L36 amendment **only if operator accepts C-05**.

## Blockers now

- QMA nested venv at mill-split worktree invalid — QMA tests not re-run.
- ADR-0023 still provisional (mill code reused anyway).
- C-05 live non-Book awaiting operator.
- GAP-0081 chrome, GAP-0058, GAP-0062 machine, MemoryProvider backend.

## Regression gates

Existing QMB compile/fragment/project/rerun tests; QMN conformance venue kinds; QML mill 32 tests (green 2026-09-18 @ 270e992). Do not weaken those to admit dummy Book.
