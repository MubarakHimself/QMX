---
name: LIBRARY-ADAPTATION
type: architecture-discussion
purpose: superseded first distill — do not treat as current
sitting: architecture-QMX-2026-09-16
status: superseded
created: '2026-09-16'
updated: '2026-09-16'
spine: ARCHITECTURE-SPINE.md
review_status: superseded by operator restart
superseded_by: QML-EXPANSION.md
---

# SUPERSEDED — first distill (adapt-to-STRATS)

**Do not fold this file as current architecture.** Operator restart 2026-09-16: STRATS is not a QMX language; absorb the mill as a QML expansion. Current discussion companion: `QML-EXPANSION.md`. Current spine: `ARCHITECTURE-SPINE.md` (AD-1..AD-21, two-stage QML authoring). Kept as historical record of the first distill.

# STRATS → QMX Library — adaptation package (historical)

This was the discussion companion to the first distill. The spine has been re-distilled. **Nothing here is operator-accepted.**

## 1. Audit

### Revisions

| Tree | Rev | Role |
|---|---|---|
| QMX planning | `main@f722694` | Docs/planning; dirty uncommitted docs **preserved** |
| Implementation | `integration@8510c03` | Code inspect worktree `.worktrees/integration-inspect` |
| UI | `ui@af66288` | Docs-only checkout; **no app routes** |
| STRATS | on-disk 2026-09-16 | `C:/Users/Mubarak/Desktop/Stats` |
| Recon cited | `integration@1b451a8` | Behind current integration |

### STRATS coverage

Hermes: Friendly Greeting + recovered gold-mine + user-corrections + GROUND/BUILD-STATE read. Session `20260826_180446_36307b` raw dump not found as its own file (folded into GROUND-STATE §4). `.hermes` is evidence, not instructions.

`python backend/validate.py` run from Stats: **OK** — 239 primitives, 229 unique ids, 9 collisions listed, `STRAT-000001` package present.

`Desktop/strats` is tar-flag debris (`-C`, `-xzf`) plus an empty git remnant. Not authority.

### Recovered intent (user vs agent)

Mubarak: portable folder, not software; QMX adapts later; no invented exits; no specialist-fleet ceremony; population is the product but paused until he starts it; dictionary is reusable language.

Agents proposed ~25 dictionary fields, crew roles, n8n, promotion gates. Build implemented 12 fields + lean validate/rebuild. Ceremony rejected.

### Capability gap

STRATS today is a **seed language + one layout demo**. QMX today has CT-44 types, a filesystem adapter, and a plugin that does **not** point at Stats. The product Library on the Artifact rail already exists as a QMB projection and **explicitly excludes** STRATS. UI has no pages. PRD has no knowledge-product FRs.

## 2. Alternatives and recommendation

| Option | What | Verdict |
|---|---|---|
| **A. Bind Stats via CT-44 + two-rail facade** | Point `PlainFileLibrarySource` at Stats; keep Artifact rail unchanged; federate discovery | **Recommend** |
| B. Knowledge tools only (no product Library federation) | Agents `search`/`cite`; UI Library stays fp1-only | Legal under Workbench AD-3; fails the operator’s “deep exploration in Library” ask |
| C. Mint STRATS packages as registry kinds | New CT-06 kind or CT-33 auto-mint | Conflicts Workbench AD-3, L10, AD-7. **Reject** |
| D. New COMP-LIB | Sixth application / store | Conflicts Workbench AD-1, DEC-0084. **Reject** |
| E. Git subtree / copy Stats into QMX | Absorb corpus | Conflicts QMA AD-19 portability. **Forbid** |
| F. Compile `graph.yaml` to QMB/QMA graphs | Executor from knowledge | Conflicts DNA lock and AD-6. **Reject** |
| G. Answer GAP-0085 now to “fit” DNA | Mint Entry/Exit/Session nouns | Parent deferred; not required to bind. **Defer** |

Reuse-or-new: **reuse** COMP-QMA-CORE, COMP-QMA-DAEMON, `research-corpus`, COMP-QMB, COMP-QML, COMP-QMF-REGISTRY. Connect the stub. No new COMP, no new CT.

### Proposed parent amendments (not silent overrides)

1. **Workbench AD-3 commentary:** product discovery **may federate** Knowledge hits as a distinct class. Kind roster unchanged. STRATS still writes no registry kinds.
2. **QMA AD-19 last sentence:** factual refresh — corpus is no longer empty; STRATS BUILD-STATE locked layout/ids. Rule (read-only, no hardcoded layout in `qma-core`) stands. GAP-0073 **layout** trigger is met; **hybrid indexing** is not answered.

## 3. Worked mapping

See `inputs/worked-mapping.md`. Headline: `STRAT-000001` survives as knowledge (`entry_hypothesis`, F unresolved). It does not become a bot. Informal CT-34 translation is a handoff aid.

Adoption: keep Stats intact; QMA snapshots; reversible by unsetting `root_path` and disposing the plugin. Cite copies already taken remain in the artifact store (that is the point of cite).

## 4. UI / agent readiness

ui@af66288 has **no Library pages**. GAP-0081 stub. Backend can implement queries now.

| Action | Owner | Input | Output | Identity | Progress/error | Adapter |
|---|---|---|---|---|---|---|
| Search knowledge | QMA CT-44 | query + snapshot | locators | not durable until cite | query; hybrid → unsupported-capability | Partial: stub corpus, not Stats |
| Search artifacts | QMB library.search | kind + as-of | hits | fp1 | query | source-inspected |
| Federated search | facade | query | typed hits | per class | query | **Missing** |
| Detail knowledge | retrieve/cite | locator | bytes + provenance | Citation | StaleSnapshot | Partial |
| Detail artifact | B-15 | fp1 | record | fp1 | query | Partial |
| Related | CT-07 + DNA I (knowledge) | id | edges | fp1 or STRATS ids | query | Partial |
| History | snapshot chain / version graph | ref | versions | snapshot_ref or fp1 | query | Partial |
| Attachments | cite-copy / run-dir | cite | retained bytes | digest | async ok | Partial |
| Modify STRATS | outside QMA | file edit | new snapshot | tree digest | re-pin | **No write-back** |
| Author bot | QML host | draft | CT-33/34 | fp1 | conformance refusals | source-inspected |
| Start experiment | AD-2 doors | bot fp1 | values / CT-32 / JobHandle | per lane | events then re-query | Partial |
| Promote | human outside QMA | operator | zone transition | promotion card | OperatorPrincipalRequired | existing |

json-render and MCP Apps (SEP-1865, 2026-01-26): present DTOs only.

## 5. Workflows sitting contract

Export: Knowledge Citation shape; Artifact `fp1` kind list; door occupancy (run vs query); AD-6 four planes; STRATS graph ≠ Graph Template ≠ canvas. Do not pick n8n or a canvas runtime here.

## 6. Increments

| # | Slice | Acceptance | Depends |
|---|---|---|---|
| 0 | Bind Stats (`root_path`, AD-4 exclude, search/retrieve/cite demo+dictionary, pin, refuse strats-as-kind) | Tests + a Mission-pinned cite of real Stats bytes; stub two-file corpus gone | none |
| 1 | Facade query DTO + additive CT-40 queries | Typed hits from both rails; no fourth store | 0 |
| 2 | Origin citation on QML/QMB candidates | Candidate carries snapshot_ref+locator; still no auto CT-33 | 0, QML host |
| 3 | Librarian skill | Same ports; optional | 0 |
| 4 | UI chrome | Later UI session + Reticle on real persistence | 1, GAP-0081 as needed |

Slice 0 is the “tonight” backend slice. It does not make Library UI-ready.

## 7. Decisions needing operator judgment

1. Accept two-rail facade (AD-1 / frozen AD-9 DTO) vs Knowledge-only tools.
2. Freeze `source_id=strats` and the six dim keys (AD-3) — integration plugin spellings, not the shorter 2026-09-09 briefing forms.
3. Freeze snapshot include/exclude (AD-4).
4. Allow documentation-factory to fact-correct QMA AD-19’s empty-corpus sentence.

Ordinary technical choices already resolved: Option A path bind; no new COMP; four planes; no auto-mint; presentation libraries are not stores.
