---
name: Reconcile spine against load-bearing inputs
sitting: architecture-QMX-2026-09-18
status: gaps-only — not an architecture rewrite
scope: ARCHITECTURE-SPINE.md vs 01-GROK-ARCHITECTURE-PROMPT.md, REQUIREMENTS-ADDENDUM.md, CONFLICT-REGISTER.md, RECON-RETURN.md, operator reminders
---

# Gaps that did not land

Spine checked against: `01-GROK-ARCHITECTURE-PROMPT.md`; `REQUIREMENTS-ADDENDUM.md`; `CONFLICT-REGISTER.md`; `RECON-RETURN.md`; operator reminders (Artifact Library, capability discovery, app orchestration, copilot; mutmut as principle not dependency; two copilot profiles; no sixth COMP; stop at Codex challenge).

Companions cited only to prove a requirement exists unbound in the spine, or is missing even there. **Autofixable** = can be written into an existing AD/companion from already-stated law, with no new investigation and no new operator question.

Operator-named items **did** land (AD-1, AD-2, AD-8/AD-9, AD-10, AD-19, `review_status`). C-01..C-18 dispositions match the spine. WF-R-01..10 and WF-R-12..18 match. Those are not listed.

## A. Quiet requirements — no AD clause

| ID | Did not land | Source | Autofixable |
|---|---|---|---|
| G-01 | Operation **output shape omits `event`**. AD-3 freezes `value \| artifact_ref \| job_handle \| stream`. Prompt and OP-NEW-05 require events as a distinct lifecycle shape (not the AD-17 UI `events` contribution). | Prompt §13; OP-NEW-05; W11 | **Yes** — add `event` to AD-3 + `CONTRACTS.md` §1 |
| G-02 | AD-3 descriptor is a subset of the required public contract. Missing: **configuration/defaults, operation-level dependencies, resource needs, documentation, validation, units, version compatibility** (pack compatibility is AD-18 only). | Prompt §5; W2 | **Yes** — extend the AD-3 bullet; keep transport out |
| G-03 | Typed dataflow never distinguishes **reference / data / event / control** ports. AD-5 only names collection mapping. | Prompt §5; W3; original brief connections | **Yes** — AD-5 clause; unspecified port kind refuses |
| G-04 | **Trigger ≠ workflow definition** (schedule/webhook/Routine fire vs Graph Template). AD-7 names RoutineScheduler; never states the split or trigger dedupe. | Prompt original; W3; OP-047 | **Yes** — AD-4 or AD-7 sentence |
| G-05 | **Install ≠ catalogue-activate ≠ session-grant ≠ account-activate.** AD-18 has install/enable; AD-8 has grants; AD-13 “published package ≠ activation on an account” is the *trading* sense. OP-NEW-11’s three-state pack lifecycle is unnamed, so enable and grant collapse. | Prompt §13; OP-NEW-11; J08/J21 | **Yes** — name the three pack states on AD-18 and point grants at AD-8 |
| G-06 | **Composite authority is not a union.** AD-10 never says intersection (or an explicit declared set) of host grants. JOURNEYS J12 forbids union; the spine does not. Nested invoke / callback must not propagate extra tools. | Prompt §13; OP-NEW-15; J12 | **Yes** — AD-10 sentence + nested-invoke refuse |
| G-07 | Copilot/catalog **unavailable states**. Prompt: availability ≠ granted ≠ configured ≠ reachable ≠ healthy. AD-15 has those five states for *compute only*. AD-9 intersects published ∩ grants ∩ profile ∩ health and does not catalogue unavailable contributions. OP-NEW-02 requires the index to show unavailable. | Prompt §6; OP-NEW-02; OP-008 | **Yes** — bind AD-2/AD-9 to AD-15’s five states |
| G-08 | OP-NEW-01 required an **AD on extra Library query-hit tags**. AD-2 only adds `saved-view` \| `analysis.published`. Unanswered: derived datasets, workflow definitions, installed apps as ArtifactHit rows vs owner-only vs ContributionHit. Silent omission is not the required AD. | OP-NEW-01; operator Artifact Library | **Yes** — explicit refuse (or named allow-list). Conservative refuse matches AD-2: those surfaces stay owner/ContributionHit, not new ArtifactHit tags |
| G-09 | **Result comparability**: compare only where accounting/evaluation meanings align; do not force unrelated policies into old R vocabulary or relabel filtered trades as a rerun. Not in AD-11. | Prompt §7; OP-077; W1; J03 | **Yes** — AD-11 clause |
| G-10 | **Venue/account command targeting.** Dashboard/home aggregation and tab/account filters are not command targets. Same symbol on two venues is two instruments. Analysis access ≠ execution permission. No Workflows AD; CONNECT is inherited but not applied to apps/copilot/dashboard. | Prompt §8; INT-10; OP-NEW-13; J05 | **Yes** — AD-8 (and AD-13 identity) clause |
| G-11 | **Local file on a remote worker: stage as portable artifact or refuse.** AD-3 bans machine-local paths as global ids; AD-15 bans laptop-coordinator durability. Neither states the placement preflight. | Prompt §13 extra interactions; OP-NEW-17; J07/J22 | **Yes** — AD-15 clause |
| G-12 | **WF-R-11 is not fully in AD-12.** Addendum requires recipes to pin inputs/**transforms/splits**. Prompt/W5 also require calendars, alignment, temporal + missing-data policy, point-in-time membership. `CONTRACTS.md` has splits/`known_at_policy`; the spine does not bind them. | WF-R-11; Prompt §8; OP-001/003; W5 | **Yes** — thicken AD-12 to match WF-R-11 + existing contract payload |
| G-13 | Stream law stops at **replay-to-live + don’t cancel the other consumer**. Missing: buffering, backpressure, gaps, late/out-of-order, disconnect, catch-up, heartbeat, unhealthy-source, lifetime, **stream ≠ trading permission**. | Prompt §8; OP-006; OP-NEW-10; J17 | **Yes** as required stream laws on AD-12; schemas stay in `CONTRACTS.md` |
| G-14 | Sequential deploy is not a **command-ownership state machine**. AD-14 has stopped/flat, UNKNOWN, residual positions, rollback≠unfill. Missing named: command-ownership record, **old process must not resume**, dual command writers refused, **partial fills**, distinct-accounts-first (OP-NEW-08 unknown; operator: distinct first). | Prompt §7; OP-NEW-08; W6; J10 | **Yes** — thicken AD-14. Distinct-accounts-first can be the default without a new operator Q |
| G-15 | **Reuse vs invalidate** after semantic rewiring. AD-13 says projection ≠ path-dependent rerun. W3/OP-044 require: reuse prior results only when inputs/ports still valid; invalidate after actual semantic change; layout edit must not. | Prompt §5; W3; OP-044 | **Yes** — AD-4 or AD-13 clause |
| G-16 | **Headless pack = reusable step** (typed op / node / CLI / export) with no navigation pane. COPILOT-AND-APPS says it; AD-17/AD-18 do not. Workflow does not automatically specify UI, permissions, or deployment. | Prompt §10; OP-NEW-16 | **Yes** — one sentence on AD-17 or AD-18 |
| G-17 | **Mini-app shared parameters are typed edges, not globals** (dates/universes/models). Recon transferable contract; OP-061 **E**. Absent from AD-10. | RECON-RETURN Codex recon; OP-061 | **Yes** — AD-10 clause |
| G-18 | **Skill validation and activation** is in Stage A acceptance coverage and OP-053 **E**. Spine: skills do not grant; Caliper deferred. Missing: author ≠ verifier, install separated from authoring, desired/undesired activation with neighbors present, no self-scored gate. | Prompt §6/§12; 09-OUTPUTS acceptance; OP-053; J11 | **Yes** as AD-9 principles. Caliper adapter stays deferred |
| G-19 | Product-session **memory/privacy policy**. AD-9: retrieval is explicit/attributed and cannot retarget. Missing: retention/export/deletion, token budgets, conflict/supersession, revocation, **explanations cite saved records not recollection**, **internal context via schemas not screenshots as default**. | Prompt §6; 07-COPILOT; W4 | **Yes** as AD-9 policy clauses (not a MemoryProvider backend; GAP-0072 stays) |
| G-20 | **Revoke / uninstall-with-dependants / credential revoke** while runs stay pinned. AD-8 forbids silent *widening* on upgrade; AD-18 has dependency-removal. Missing: revoke does not retarget other accounts; half-activated package; dependants named before disable. | Prompt §13; OP-064; OP-NEW-11; J20/J21 | **Yes** — AD-18 + AD-8 |
| G-21 | **App ships a versioned copilot integration profile** (context, ops, docs/skills, execution refs). Mini-app grouping is in the companion; AD-8 lists session fields, not the pack artifact. | Prompt §6; OP-056 | **Yes** — AD-8/AD-18: profile is a pack contribution the host grants |
| G-22 | App-use → change request → authoring → **validation** → v2. Sequence diagram skips validation. | Prompt §6 | **Yes** — extend the AD-8 sequence; validation uses existing gates, not `promote` |
| G-23 | Provider **name ≠ meaning**. Missing on AD-12: similarly named fields are not interchangeable; source-native identity; event vs known-at time; revisions; currencies/units; entity mapping; raw vs adjusted; **a new provider tomorrow must not rewrite yesterday’s experiment**; operator spot preferences do not hardcode research coverage. | Prompt §8; W5; OP-004 | **Yes** — AD-12 clause |
| G-24 | **Settings/provisioning**: connection tests that do not mutate accounts; scoped defaults/inheritance; effective configuration; secrets as refs (L34 already). No AD. | Prompt §9; W7; J20 | **Yes** — AD-15 or AD-18 principles |
| G-25 | Persistence **recovery protocol**. AD-16 splits owners. Missing: orphan detection, corruption, disk exhaustion, cross-store consistency, restart reconstruction, evidence retention, concurrent draft saves. J18 is a journey with no spine law. | Prompt §9; W8; J18 | **Partial** — principles on AD-16 **yes**; a full cross-store protocol is not a one-line patch |
| G-26 | Compute **quota, preemption, data-transfer policy**, hardware/image compatibility. AD-15 has five health states, starve-protection, checkpoint/resume, unknown/cancel. | Prompt §9; OP-069; W7 | **Yes** — AD-15 |
| G-27 | UI contribution list omits **editors**; never says the catalogue is **not cards/buttons-only**. | Prompt §10; W9 | **Yes** — AD-17 |
| G-28 | Public operations need **start / query-state / lifecycle** APIs as well as streaming. AD-3 has progress + `job_handle` only. | Prompt §13 | **Yes** — AD-3 |
| G-29 | **Composite identity unresolved.** OP-NEW-03 unknown: package kind vs installed instance graph. AD-10 “cites contribution ids” does not choose. AD-2 forbids mini-apps as registry kinds, so the implied answer is instance graph — unstated. | OP-NEW-03; AD-2 | **Yes** — “installed instance graph, not a registry kind” |
| G-30 | **Loop `stopping_condition` is an opaque string** (memlog hole to close in-place). AD-6 says loops are node state; does not type the stop. | `.memlog.md`; W3 | **Yes** — AD-6: stop/budget/iteration are typed fields, not opaque strings |
| G-31 | RECON **F-03**: mill graduation does not compile DNA→bot; e2e QML→QMB→QMN unverified. Spine does not bind the first as a rule (the second is correctly unclaimed). | RECON-RETURN F-03 | **Yes** — AD-4 / inherited mill: graduation ≠ DNA compile, ≠ e2e |
| G-32 | RECON **F-06**: new venue *protocol* ≠ extra *account*. Inherited `VenueClientKind` closed; Workflows never restates it against provider/account configuration. | RECON-RETURN F-06; Prompt §8 | **Yes** — AD-12 / AD-10: extra account on a closed kind is not a new adapter |
| G-33 | Local/supervised vs continuous-hosted are **placement profiles**, not a product SKU, and not every system is VPS-only. Deferred only as GAP-0058 (single-machine node). | Prompt §7; INT-21; OP-024 | **Yes** — AD-15 named profiles; GAP-0058 remains the machine increment |
| G-34 | Headless risk/model apps need **observable readiness/status**, not a global green light. | Prompt §7; W6; OP-070 **E** checks | **Yes** — AD-14/AD-21: readiness is named checks, not a lamp |

## B. Not spine-content, but blocks “stop at Codex challenge”

Prompt §0/§12 and `10-STAGED-PROCESS-AND-REVIEW-CONTRACT.md` require a freeze. Spine `review_status` claims internally-reviewed candidate awaiting Codex. Handoff exists; freeze does not.

| ID | Did not land | Autofixable |
|---|---|---|
| G-35 | `ARCHITECTURE-CANDIDATE-MANIFEST.json` (id, UTC, source commits, file hashes) | **Yes** — hash the candidate tree |
| G-36 | `CODEX-CHALLENGE-INPUTS.zip` | **Yes** — zip the sitting dir per 10-STAGED (no secrets/venvs) |
| G-37 | `RESUME-STATE.md` | **Yes** — from `.memlog.md` + RECON-RETURN + this file |
| G-38 | `reviews/` is empty; handoff tells Codex to read “internal reviews under `reviews/`”. This reconcile is input-trace, not the required adversarial architecture review. | **No** — needs the installed skill’s review pass; do not invent findings |

`JOURNEYS.md` traces J01, J03, J06/J13, J08/J24, J10, J12, J17 only. Prompt §12 / 09-OUTPUTS also require **J02 isolation, J05 multi-broker, J09 headless parity** as design coverage. J09 has AD-21; J02/J05 have no representative oracles (J05 is G-10). Companion gap, not a new AD if G-10 and AD-8 isolation clauses are written.

## C. Deliberately not gaps

- C-05 live non-Book / L36 — held; Q1.
- GAP-0081 chrome, GAP-0058 machine, GAP-0072 MemoryProvider, Caliper CLI, mutmut-in-CI — deferred on the spine.
- Subworkflow-as-a-new-kind (OP-042) — spine reuses Graph Template; that is a landing.
- WF-R-18 / mutmut-as-principle, two profiles, no sixth COMP, Artifact Library kinds unchanged — landed.
