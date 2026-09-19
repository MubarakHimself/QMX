---
name: Focused Codex recheck after Stage C material contract repair
sitting: architecture-QMX-2026-09-18
status: issued — OD-01 closed; Documentation Factory already ran; epics paused
date: 2026-09-19
---

# Focused Codex recheck (issued)

Stage B reviewed candidate `qmx-workflows-arch-2026-09-18-a`. Stage C produced `qmx-workflows-arch-2026-09-19-c` with material contract repairs (AD-23..AD-31). **The original Stage B review does not approve those new pages.**

This recheck was first skipped as operator process preference (GAP-0092). The operator reversed that skip on 2026-09-19, before epics-and-stories. Run this recheck now. Epics stay paused until Grok reconciles the return.

## What already happened (do not undo)

| Step | Status |
|---|---|
| Stage A freeze `qmx-workflows-arch-2026-09-18-a` | done |
| Codex Stage B challenge (85 scenarios; AF-01..AF-20) | done — reviewed **18-a only** |
| Stage C reconciliation → `qmx-workflows-arch-2026-09-19-c` | done |
| OD-01 | **closed from the original transcript** (not option A vs B as a live ask) |
| Documentation Factory fold into `docs/` (ADR-0024, L36 named amendment, SCN-0018..0022, DEC-0414..0451) | **already ran** in a later Grok session. Uncommitted working tree. Do not re-run DF. |
| `bmad-create-epics-and-stories` | **paused**. Do not start it. |
| This focused recheck of AD-23..AD-31 | **this Codex session** |

Documentation Factory folding those ADs into `docs/` is **not** Codex approval and is **not** a reason to skip this challenge. Treat the fold as a downstream absorption of Stage C. Challenge the machines. If the folded `docs/` drifted from the spine, say so.

## OD-01 (closed — paste this, do not re-ask)

Book and BMS are a **specific** portfolio-management, risk, and position-sizing system that arrived in this QMX version — the **default**, not the ceiling. The kit must let the operator **replace or improve** that stack. When they do, **everything attached adopts**: QML, QMB, optional MIS, QMN, paper, and live. Never dummy Book. Research/sensing is not a trading composition. Cutover is sequential, not hot-swap. Human L17 promote remains. QMN remains the only venue importer.

L36 was named-amended in Documentation Factory (DEC-0448). Live ATC still requires paper-then-live + L17.

## What to send Codex (focused packet — not the whole discovery pack)

1. This file
2. `CODEX-RECHECK-LAUNCH.txt` (the paste)
3. `CHALLENGE-RECONCILIATION.md` (AF ledger)
4. `ARCHITECTURE-SPINE.md` (AD-11, AD-23..AD-31)
5. `CONTRACTS.md`
6. `JOURNEYS.md`, `REQUIREMENTS-ADDENDUM.md`, `CONFLICT-REGISTER.md`
7. `OPERATOR-QUESTIONS.md` (OD-01 CLOSED)
8. Original 85-row `codex-challenge-20260919/SCENARIO-CATALOG.jsonl` + `codex-challenge-20260919/behavior/` (do not shrink)
9. Folded docs so Codex can see DF absorption: `docs/decisions/ADR-0024-workflows-construction-kit.md`, `docs/scenarios/SCN-0018`..`SCN-0022`, constitution L36 paragraph, `_docwork/riders/workflows-construction-kit-2026-09-19.md`

Do **not** re-derive Pass-I. Pass-I stays frozen at SHA-256 `1c2c865d1cef50076682a737472174fa307cf1fc8eb3663b122ed04ab6f39fd8`.

## Scope

Challenge only the material repairs:

- AD-23 Alternative Trading Composition and admission
- AD-24 invocation/grants
- AD-25 fencing
- AD-26 outbox / JobHandle / join
- AD-27 checkpoint
- AD-28 streams
- AD-29 session CAS / change-request
- AD-30 package lifecycle / pin
- AD-31 recipe-definition identity
- `CONTRACTS.md` payloads vs spine
- Whether DF-folded ADR-0024 / SCN-0018..0022 silently drifted from those ADs

Preserve all 85 scenario IDs. Pass-I rows are immutable requirements. Do not treat sensing as ATC. Dummy Book remains `INVALID_INPUT`. QMA AD-17 JobHandle vocab is parent law. Cheap-veto A1–A6 (field catalogues) are sitting machinery — challenge them if they are wrong; do not treat them as operator-spoken schemas.

## Return

Findings against the new ADs/contracts; whether any AF-01..AF-20 disposition is still open; whether the **machines** are architecture-complete enough for Grok to desk-fix docs and then (only after that) resume epics. Do **not** ratify. Do **not** edit QMX code. Do **not** start or re-run Documentation Factory. Do **not** start epics-and-stories.

## Not in this recheck

Production implementation, mutmut on the shared tree, Reticle, live broker, Documentation Factory, epics-and-stories, a new Pass-I, a sixth COMP.
