---
name: Stage C challenge reconciliation
sitting: architecture-QMX-2026-09-18
candidate_reviewed: qmx-workflows-arch-2026-09-18-a
candidate_reconciled: qmx-workflows-arch-2026-09-19-c
status: reconciled-not-ratified
---

# Challenge reconciliation — Stage C

This sitting reconciles independent Codex Stage B findings against frozen candidate `qmx-workflows-arch-2026-09-18-a`. It does **not** ratify the architecture, edit QMX production code, start Documentation Factory, or start implementation.

## 0. Identity of what was reviewed

| Item | Value |
|---|---|
| Candidate reviewed by Codex | `qmx-workflows-arch-2026-09-18-a` frozen 2026-09-18T12:39:51Z |
| Input ZIP SHA-256 | `4247e7e84eba458a2d73c696dd2783b0635a36379dd9e3144da87a6cba478b87` |
| Codex return ZIP | `QMX-CODEX-CHALLENGE-20260919T130812Z.zip` |
| Codex return SHA-256 | `e9394ed8919665534b37ee97792edae232f75b2b34a3790f8f9de82a5f58a4f5` |
| Pass-I baseline SHA-256 | `1c2c865d1cef50076682a737472174fa307cf1fc8eb3663b122ed04ab6f39fd8` |
| Docs pin | `b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3` (reconfirmed this sitting) |
| Implementation pin | `270e992995c2378ca63cf6343254ef8140a8c97e` (reconfirmed this sitting) |
| Stale audit revision | `8510c03` — not used for absence claims |
| Scenario catalog | **85** unique IDs (65 Pass-I + 20 Pass-II); none dropped |

Codex verdict accepted as the challenge result: the Stage A candidate is **directionally coherent, not architecture-complete, not ratified**. This file records dispositions and the amendments applied to produce reconciled candidate `qmx-workflows-arch-2026-09-19-c`. That reconciled candidate is still **not** operator-accepted.

## 1. Reconciliation verdict

**Architecture sitting is ready to hand to Documentation Factory in a fresh session.** It is still **not ratified** and **not implemented**.

OD-01 is **closed from the original transcript** (Book/BMS = default portfolio/risk/sizing implementation; a complete replacement is authored, evaluated, and — sequentially, after paper and L17 — deployed; consumers adopt). The earlier “approve later to go live” question was the wrong frame and is withdrawn.

Remaining outside this sitting (not operator Q&A):

1. **Documentation Factory** (operator-launched, fresh session) writes constitution L36 prose and folds AD-1..AD-31 into `docs/`.
2. **Implementation classification** — QMA Task Graph edges, product sessions, ContributionHit, owner dispatch, and QML→QMB→QMN remain proposed/unproven at `270e992`. Package tests are not integration.
3. Focused Codex recheck of AD-23..AD-31 **returned** 2026-09-19 (`CODEX-RECHECK-RETURN-2026-09-19.zip`). Disposition: **repairs required; not ratified**. Stage B still does not approve those ADs. Documentation Factory already ran; do not re-run it. Epics stay paused until RC-01..RC-17 desk-fix lands.

What this sitting did decide technically (not ratification):

- Preserve BR-MKT-02. Do **not** call sensing, research, or `UngovernedWorkConfig` a complete second trading system.
- Define Alternative Trading Composition (`AlternativeRunConfig` + `PolicyPair`) with accounting, risk, command, admission, evidence, and end-to-end journey.
- Keep dummy Book/BMS `INVALID_INPUT`. Keep Book/BMS as the protected default path.
- Close the safety/recovery block with one invocation/grant envelope, one fenced deployment machine, one task outbox, parent JobHandle vocabulary, join algebra, and an application-owned checkpoint manifest.
- Preserve all 85 scenario IDs. Pass-I rows stay independent requirements. Pass-II rows are accepted as candidate-derived obligations; none rejected.

## 2. AF-01 foundational resolution

Codex AF-01 is accepted as a real contradiction: frozen BR-MKT-02 / P1-MKT-002 require a complete non-Book composition that can be validated, simulated, **and deployed**, while Stage A AD-11 deferred live/node-paper without Book pending L36 and offered only ungoverned research / QMN sensing-only as the honest non-Book path.

**Chosen path: option 1** (preserve the requirement and define the alternative). Venue-touching is in architecture: sequential paper-then-live + L17, and QML/QMB/MIS/QMN **adopt** the selected composition. That is the transcript, not a later “may I go live?” ask.

Three legal classes, never collapsed:

| Class | Config type | Book/BMS keys | What it is | Validate | Simulate | Venue-touching deploy |
|---|---|---|---|---|---|---|
| Default trading system | `ResolvedRunConfig` | required | Existing Book/BMS path | yes | yes (`analysis.project` / `analysis.rerun`) | yes (existing QMN seats; L36) |
| Alternative Trading Composition | `AlternativeRunConfig` | **absent, not null** | Complete second trading system with its own `PolicyPair` | yes | yes (historical / internal paper-eval) | yes after sequential paper-then-live + L17; else typed `not_promoted`. OD-01 closed. |
| Ungoverned work | `UngovernedWorkConfig` | **absent, not null** | Research, data/ML, recipes, QMN sensing-only | n/a as trading | n/a as trading | never a seat |

Sensing-only is **not** a seat and **not** ATC. A dummy CT-22/CT-27/CT-33 remains mechanical `INVALID_INPUT`.

ATC must supply, without Book fields:

- **AccountingPolicy** — cash, position identity, fill application, valuation marks, currency, residual meaning.
- **RiskPolicy** — limits, halt, sizing, UNKNOWN handling, override principal. No-op / unlimited / pass-through is dummy and refused.
- **Command** — every command binds venue, account, role, instrument, adapter capability, credential ref, and command-owner epoch (AD-25).
- **Admission** — composition class, PolicyPair completeness, health, grants, and L36/OD-01 gate for venue clients.
- **Evidence** — ATC journal in the QMB JSONL family tagged `composition_class: alternative`; not qmf-core; not a second evidence database. Compare with the Book path only on conserved measures both policies define.
- **Journey J03b** — author PolicyPair → validate → simulate against pinned CT-10/replay → (if admitted) sequential fenced handover onto a QMN venue client.

OD-01 is closed from the transcript. Live ATC is sequential paper-then-live + L17. Dummy Book stays `INVALID_INPUT`. Sensing is not ATC.

## 3. Decision ledger AF-01 .. AF-20

Disposition vocabulary: `accept` | `accept-with-change` | `reject-with-evidence` | `defer-with-authority`.

Implementation classification: `existing` | `connect` | `amend` | `new` | `deferred`.

### AF-01 — Complete non-Book composition

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | Codex is correct that sensing/research is not the required second trading system. The operator transcript already said Book/BMS is one PM/risk/sizing stack and that swapping it must make QML/QMB/MIS/node/live adopt. Option 1 is taken: define ATC. L36 is a named amendment (default implementation, not ceiling). Sequential paper-then-live + L17 remain as operating discipline, not an architecture hold. |
| Counterevidence | `ResolvedRunConfig` still requires book/bms/bot at `270e992`. Dummy Book is already `INVALID_INPUT`. QMN venue selector remains closed. Those facts protect the default path; they do not satisfy BR-MKT-02. |
| Sections | AD-11 (amended); **AD-23** (new); CONTRACTS §§11–12; JOURNEYS J03, J03b, J10; REQUIREMENTS WF-R-09/10/19; CONFLICT C-05; OPERATOR OD-01 |
| Parent law / owner | constitution L36, L17, L35, L39; Workbench AD-5 (projection ≠ rerun); COMP-QMB (policy eval + ATC journal); COMP-QMN (venue command if admitted); COMP-QMF-RISK (default BMS only — not reused as dummy) |
| Scenarios | P1-MKT-001, **P1-MKT-002**, P1-MKT-003, P1-MKT-006, P1-DATA-008; P2-MKT-011 (fencing, not a substitute for ATC) |
| Classification | default path **existing**; ATC schema/journey **new**; venue-touching ATC **in architecture** (sequential paper-then-live + L17; not an open OD-01); sensing **existing** and **not** ATC |
| Tests before implementation claim | Default Book/BMS regression remains green. ATC fixture validates and simulates with PolicyPair and zero Book keys. Dummy Book still `INVALID_INPUT`. Live ATC without paper-then-live + L17 returns `not_promoted`. No QML→QMN claim from package tests. |
| Operator decision | **Closed from transcript** — Book/BMS is default PM/risk/sizing implementation, not the kit. Live ATC is sequential paper-then-live + L17, not a later “may I?” Architecture question. See OPERATOR-QUESTIONS.md. |

### AF-02 — Effect-specific idempotency and uncertain-outcome reconciliation

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-3 named effects and lifecycle verbs but supplied no idempotency key, logical invocation/attempt ids, or reconcile policy. A timeout-then-retry can duplicate external-egress while still matching the descriptor. |
| Counterevidence | None. L35 UNKNOWN discipline exists for jobs; it was not bound to AD-3 invocations. |
| Sections | AD-3 (pointer); **AD-24**; CONTRACTS §1b, §6 |
| Parent law / owner | L35 UNKNOWN; QMA AD-17 `unknown` holds lease; COMP-QMA-DAEMON (envelope persistence); effect owner executes; COMP-QMN for venue egress |
| Scenarios | P1-OP-002, P1-OP-004, P1-OP-005; P2-OP-006, P2-OP-007, P2-OP-008 |
| Classification | **new** envelope; **connect** to existing JobHandle/UNKNOWN; **existing** L35 |
| Tests | Timeout after upstream success → unknown, not duplicate order/append/export. Retry with same `logical_invocation_id` is no-op or reconcile. `never-retry` effect class refuses automatic retry. |
| Operator decision | none (technical) |

### AF-03 — Deployment command-owner fencing and stale predecessor restart

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-14 stated sequential handover; CONTRACTS §10 was a flat payload without epoch, fencing token, typed positions/orders, predecessor ack, or restart law. Dual writers remain conforming without a machine. |
| Counterevidence | Sequential-not-hot-swap intent is already aligned with C-10 / DEC-0366. That intent is not a fencing protocol. |
| Sections | AD-14 (pointer); **AD-25**; CONTRACTS §10 rewritten |
| Parent law / owner | L17 human promote; L35 UNKNOWN commands; NODE/CONNECT venue law; COMP-QMN issues venue fencing tokens; COMP-QMB issues internal ATC fencing tokens |
| Scenarios | P1-MKT-005..010; P2-MKT-011 |
| Classification | **new** state machine; **connect** to existing sequential default; venue ATC path uses the same machine after paper-then-live + L17 (OD-01 closed) |
| Tests | Exactly one command owner per (account, venue, role). Predecessor restart without current `(epoch, token)` is refused. UNKNOWN orders block activation. Software rollback after new-owner fill does not unfill. |
| Operator decision | none remaining — OD-01 closed; Book-path and ATC-path fencing are both in-scope |

### AF-04 — Atomic task completion, successor persistence, and dispatch

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-7 already required persisting edges and successor dispatch. No commit/outbox/replay law. At `270e992`, `TaskGraphStore` is in-memory, `TaskGraph` has no edges, dispatcher does not walk successors. |
| Counterevidence | Named `task_graph_state` projection already exists in QMA law — the hole is adoption, not a second scheduler. |
| Sections | AD-7 (amended); **AD-26**; CONTRACTS §9b |
| Parent law / owner | QMA AD-6 sole sqlite writer; QMA AD-9 dispatch lease; COMP-QMA-DAEMON. No QMB task-graph module. |
| Scenarios | P1-WF-006, P1-WF-007; P2-WF-008, P2-WF-009 |
| Classification | **connect** (persist named store + outbox); not **existing** |
| Tests | Crash before/after predecessor commit, eligibility write, outbox publish, dispatch ack. Exactly one logical successor effect after restart. |
| Operator decision | OD-02 if operator forbids adding sqlite tables to the already-named projection (recommendation: allow) |

### AF-05 — Invocation binding to contribution version, instance, config revision

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-10/AD-13 named instance_id; AD-3 payload and CONTRACTS §1 omitted contribution tuple, instance, config revision, and grant snapshot. Product-session context does not cover headless/nested calls. |
| Counterevidence | None. |
| Sections | AD-3, AD-13 (pointers); **AD-24**; CONTRACTS §1b |
| Parent law / owner | AD-2 contribution tuple; AD-13 instance_id; COMP-QMA-WIRE (envelope DTO); COMP-QMA-DAEMON (resolution) |
| Scenarios | P1-CAP-004, P1-CAP-005, P1-APP-003..008; P2-OP-006, P2-CAP-007, P2-DATA-009 |
| Classification | **new** (envelope fields); **amend** AD-3 payload |
| Tests | Two installed instances: invoke cannot silently take “latest”. Ambiguous resolution refuses. Waiting handle stays pinned across upgrade. |
| Operator decision | none |

### AF-06 — Recipe-definition identity distinct from output-release fp1

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | Stage A AD-12 made recipe v1 identity the output release fp1 and `recipe_id` display-only. That collapses definition, run, and result. Workbench AD-13 still owns **output** identity as fp1; it does not forbid a separate definition identity. |
| Counterevidence | Derived-dataset fp1 law is kept for releases. CT-06 recipe *registry kind* stays deferred. |
| Sections | AD-12 and AD-16 (amended); **AD-31**; CONTRACTS §5 |
| Parent law / owner | Workbench AD-13 (release fp1); CT-07 lineage; COMP-QMB wrap of COMP-QMF-DATA |
| Scenarios | P1-DATA-003, P1-DATA-005, P1-DATA-006; **P2-DATA-010** |
| Classification | **amend** sitting AD-12; **new** definition identity; output fp1 **existing** |
| Tests | Two executions of one definition produce two release fp1s and one stable `recipe_def_id`. Metadata-only display change does not mint a new definition. Release without complete lineage refuses. |
| Operator decision | none (CT-06 kind remains deferred until metadata-sharing is required) |

### AF-07 — JobHandle attempts, partial artifacts, cancel races, terminal vocabulary

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | CONTRACTS §6 drifted to `succeeded` / `awaiting_approval`. Parent QMA AD-17 states `queued \| running \| done \| failed \| cancelled \| aborted \| unknown` with a fixed mapping onto Task states. Drift would mint a second job dialect. Finding is accepted; the *candidate’s extra states* are rejected in favour of parent law. Add attempt records, artifact completeness, and cancel/complete CAS. |
| Counterevidence | QMA AD-17 is adopted parent law. `awaiting_approval` remains a Mission/Task gate, not a JobHandle state. |
| Sections | **AD-26** JobHandle clause; CONTRACTS §6 rewritten; conventions |
| Parent law / owner | QMA AD-17, AD-12; L35; COMP-QMA-DAEMON maps JobHandle ↔ environment_lease |
| Scenarios | P1-OP-003, P1-OP-004, P1-OP-005; P2-OP-007, P2-OP-008 |
| Classification | **amend** sitting contract; parent vocab **existing**; attempts/inventory **connect** |
| Tests | Worker death after one artifact → non-success + partial inventory. Cancel vs complete: first durable terminal wins. Timeout → `unknown`, never `aborted` or `failed`. Expired artifact is not an empty success. |
| Operator decision | none |

### AF-08 — Replay/live sequence, cutover, gaps, backpressure, shared leases

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-12 stated intentions; CONTRACTS §7 had only phase/cursor/shared and conflated provider with venue (`ctrader-live`). |
| Counterevidence | Provider ≠ venue is already sitting law; the example contradicted it. |
| Sections | AD-12 (pointer); **AD-28**; CONTRACTS §7 rewritten |
| Parent law / owner | COMP-QMF-DATA / QMB wrap for market facts; stream subscription ≠ trading permission; COMP-QMN for live venue streams |
| Scenarios | P1-STR-001..005; P2-STR-006 |
| Classification | **new** protocol; provider≠venue **existing** as rule, **amend** as example |
| Tests | Atomic cutover at watermark. Duplicate/gap/late events observable. Bounded buffer policy visible. Cancelling one of two consumers leaves the other. Replay provenance cannot authorize live commands. |
| Operator decision | none |

### AF-09 — Product-session CAS and reconnect without replayed intent

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-8 has `context_revision` and named commands but no CAS, durable command ids, or reconnect protocol. Runtime product sessions absent at `270e992`; `_handle_client` drains bytes. |
| Counterevidence | Sessions-not-tabs is already sitting law; it is unenforceable without CAS. |
| Sections | AD-8 (amended); **AD-29**; CONTRACTS §3 |
| Parent law / owner | QMA Session remains `sess:` execution container; product_session is journal projection; COMP-QMA-DAEMON / COMP-QMA-WIRE |
| Scenarios | P1-SES-001, P1-SES-002, P1-SES-005; P2-SES-007, P2-SES-009 |
| Classification | **new** CAS protocol; product_session record **connect**; runtime **not existing** |
| Tests | Stale `expected_revision` conflicts. Reconnect replays durable results, not unacked intent. Two clients cannot clobber grants. Tab identity is absent from the row. |
| Operator decision | none |

### AF-10 — Structured grants bound to version, instance, effect, parameters, account, audience, expiry

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | `granted_ops` as op-id strings can be retargeted by upgrade/re-resolution. Intersection authority (AD-9) needs a record, not a string list. |
| Counterevidence | Host-grants-not-prose is already law. |
| Sections | AD-8, AD-9 (amended); **AD-24** GrantRecord; CONTRACTS §3b |
| Parent law / owner | AD-9 intersection; QMA AD-24 operator principal; COMP-QMA-DAEMON |
| Scenarios | P1-SES-004, P1-APP-003..008; P2-SES-008, P2-SES-011 |
| Classification | **amend** granted_ops; **new** GrantRecord |
| Tests | Grant for instance A / version V / effect `read` refuses instance B, version V+1, or `external-egress`. Expiry and revocation are evidence. Install/upgrade does not mutate existing session grants. |
| Operator decision | none |

### AF-11 — Package install/activation/migration/index/rollback/uninstall and verified secret stripping

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-18 named operations and fail-closed deps but no transition journal, atomic index swap, pinned-run protection, or export oracle. `exports_secrets: false` is self-asserted. |
| Counterevidence | QMA AD-21 already has load-time refusal, LIFO dispose, `down` vs `forward_only`, backup-before-migrate. Sitting AD-18 must connect to that, not invent a second plugin loader. |
| Sections | AD-18 (amended); **AD-30**; CONTRACTS §8 |
| Parent law / owner | QMA AD-21 plugin lifecycle; L34 secrets-as-refs; DEC-0361 marketplace stays dead; COMP-QMA-DAEMON |
| Scenarios | P1-CAP-001..006; P2-CAP-008 |
| Classification | **connect** to QMA AD-21; **new** export scanner oracle; **amend** manifest claim |
| Tests | Failed migration restores prior roster bytes. Uninstall names dependants; pinned run keeps old bytes. Independent scanner rejects secret/path/transcript payloads even if manifest says false. |
| Operator decision | none |

### AF-12 — Deterministic join and partial-retry semantics

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-5 listed mapping modes and empty policy, not join-key uniqueness, watermark, late arrival, failure aggregation, or branch-level retry. |
| Counterevidence | Cartesian-requires-flag already exists. |
| Sections | AD-5 (pointer); **AD-26** join clause; CONTRACTS §9c |
| Parent law / owner | AD-6 DAG; COMP-QMA-DAEMON join node kinds |
| Scenarios | P1-WF-003, P1-WF-004; P2-WF-008 |
| Classification | **new** algebra on existing mapping enum |
| Tests | zip/keyed/cartesian 3×2 fixtures. Duplicate keys follow declared policy. Late partition after watermark is `late`, not silently merged. Retry of one failed partition does not re-execute successful ones (same logical invocation). |
| Operator decision | none |

### AF-13 — Cross-store checkpoint, restore ordering, orphan reconciliation

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-16 correctly rejects a second evidence database and keeps owner-specific stores. It supplied no checkpoint manifest, restore order, or orphan policy, so locally-correct stores can reconstruct an impossible product state. |
| Counterevidence | QMA AD-27 five-step restore and “no journal trim” already exist for daemon projections. They do not cover QMB JSONL + QMF rooms + QML blobs + artifacts as one application checkpoint. |
| Sections | AD-16 (amended); **AD-27**; CONTRACTS §13 |
| Parent law / owner | QMA AD-27; QMF backup primitives; each COMP owns its store; COMP-QMA-DAEMON owns the **manifest**, not the bytes |
| Scenarios | P1-PLC-004, P1-PLC-003, P1-PLC-006; P2-SES-009, P2-PLC-007 |
| Classification | **new** manifest; stores **existing**; restore orchestration **connect** |
| Tests | Restore with one divergent store quarantines rather than merges. Missing artifact fp1 is `orphan`. External-effect hook runs after local restore; absence of ack is not non-execution. |
| Operator decision | none |

### AF-14 — Change-request base identity, conflict/rebase, apply evidence

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-8 already forbids app-use apply. CONTRACTS §4 lacked base hashes, context revision, source instance/config, request hash, validation/conflict/rebase, and apply evidence. |
| Counterevidence | App-use cannot `promote` (L17) and cannot edit implementation — retained. |
| Sections | AD-8 (pointer); **AD-29**; CONTRACTS §4 rewritten |
| Parent law / owner | QMA AD-22 staging + new kind `change_request`; COMP-QMA-DAEMON staging store |
| Scenarios | P1-SES-003; P2-SES-010 |
| Classification | **amend** payload; apply path **connect** to AD-22; runtime **not existing** |
| Tests | Stale base hash → conflict. App-use emit does not mutate working tree. Only authoring session with operator principal applies. Validation evidence is durable. |
| Operator decision | none |

### AF-15 — Discovery-pin-invoke availability race

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-2 already says missing/disabled plugin ⇒ typed unavailability, not stale fp1. Contracts did not define pin identity, invoke-time revalidation, or tombstones. Implementation freeze is still `KnowledgeHit \| ArtifactHit`. |
| Counterevidence | ContributionHit remains a named DEC-0389 amendment, not current wire behavior. |
| Sections | AD-2 (amended); **AD-30** pin/invoke; CONTRACTS §2 |
| Parent law / owner | DEC-0389 amendment; COMP-QMA-WIRE DTO; COMP-QMA-DAEMON `published_contributions()` |
| Scenarios | P1-CAP-004, P1-CAP-005; P2-CAP-007, P2-DATA-009 |
| Classification | ContributionHit **new** (amendment); pin/tombstone **new**; current union **existing** two-class |
| Tests | Pin then disable → invoke returns tombstone/unavailable, never another version. Hit is not a grant. |
| Operator decision | OD-03 only if operator wants contributions invisible in Library chrome (recommendation: show typed hits) |

### AF-16 — Finite `event`, provider-versus-venue, complete descriptor examples

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-3 includes `event`; CONTRACTS §1 omitted it. Stream example used `provider: ctrader-live`. Descriptor examples omitted required AD-3 fields. When payload and spine differ, the incomplete payload wins in practice. |
| Counterevidence | AD-3 Rule already lists `event`. Closed `VenueClientKind` is existing QMN law. |
| Sections | CONTRACTS §1, §7 (normative examples); AD-3 unchanged except pointer that examples are schema-complete |
| Parent law / owner | AD-3; CONNECT/NODE venue kinds; COMP-QMA-CORE descriptor types |
| Scenarios | P2-OP-007, P2-DATA-011; P1-DATA-002 |
| Classification | **amend** examples; descriptor type **new**; venue kinds **existing** |
| Tests | Conformance: every public descriptor carries the closed field set. Provider and venue fields cannot be the same slot. |
| Operator decision | none |

### AF-17 — View / shared-parameter / reconnect DTOs without UI authority

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-17 boundary is correct (presentation adapters are not authority). Missing mount/dispose, view version, parameter binding, snapshot/cursor/resync, stale-context refusal lets adapters infer authority from chrome. |
| Counterevidence | json-render/MCP Apps remain unpinned presentation candidates. GAP-0081 chrome stays deferred. |
| Sections | AD-17 (pointer); CONTRACTS §14; UI-HOST.md table |
| Parent law / owner | AD-3 input_schema; AD-9 grants; COMP-QMA-WIRE DTOs; GAP-0081 |
| Scenarios | P1-APP-001..008 |
| Classification | **new** DTOs; authority rule **existing**; chrome **deferred** |
| Tests | Dispose view does not cancel job. Stale snapshot refuses invoke. json-render catalog entry cannot add fields to `input_schema`. MCP App HTML cannot grant tools. |
| Operator decision | none (host stack still unchosen) |

### AF-18 — Headless semantic parity while QMB remains the only operator CLI

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-21 said “identical across supported doors” and then “reconcile new CLI-backed operations,” which can mint forbidden QMA/QMN CLIs. |
| Counterevidence | QMB is the only operator CLI (existing law). QMA/QMN ship none. |
| Sections | AD-21 rewritten; CONTRACTS §15 door matrix |
| Parent law / owner | NODE/QMA no-operator-CLI; COMP-QMB owns `qmb` CLI; other COMP library/wire |
| Scenarios | P1-OP-001, P1-PLC-005, P1-CAP-001; **P2-CAP-009** |
| Classification | **amend** AD-21; CLI absence **existing** |
| Tests | Same `op_id` through library, QMB CLI (if it is a QMB-owned op), wire, node, app-use: equivalent semantics. `qma`/`qmn` CLI binaries remain absent. Unsupported door → typed `unsupported_door`. |
| Operator decision | none |

### AF-19 — Complete data-recipe temporal/unit/licensing/environment policies

| Field | Value |
|---|---|
| Disposition | **accept-with-change** |
| Reasoning | AD-12 named calendars/alignment/known-at/missing; CONTRACTS §5 omitted them plus units, adjustment, entitlements, environment pins, completeness. |
| Counterevidence | Preview ≠ export ≠ stream already sitting law. |
| Sections | **AD-31**; CONTRACTS §5 complete schema |
| Parent law / owner | COMP-QMF-DATA; CT-10/CT-12; CT-07; Workbench AD-13 |
| Scenarios | P1-DATA-001..008; P2-DATA-010, P2-DATA-011 |
| Classification | **amend** recipe schema; data rooms **existing** |
| Tests | Metamorphic: source order does not erase disagreement; future data does not change earlier known-at; truncated ≠ empty ≠ denied. Licensed/unavailable source refuses rather than substituting. |
| Operator decision | none |

### AF-20 — Do not describe current implementation as implemented integration

| Field | Value |
|---|---|
| Disposition | **accept** |
| Reasoning | Codex source-inspection matches Stage A recon: in-memory TaskGraph, incomplete DAG validator, no product sessions, two-class federated union, no owner dispatch. QML 47 + QMN 5/1skip are package evidence only. |
| Counterevidence | QML mill/store and QMN venue selector **are** existing bounded evidence — keep those labels honest rather than under-claiming. |
| Sections | this ledger; IMPLEMENTATION-SEQUENCE; STACK-AND-EVALUATION testing plan; conventions “Docs vs code” |
| Parent law / owner | DEC-0286 class/test existence is not e2e |
| Scenarios | **P2-INT-001** (unsupported integration); all others remain specified-not-executed |
| Classification | labels only; no new design |
| Tests | Cross-component proof required before any claim moves from `connect`/`new` to `existing`. P2-INT-001 is that proof for QML→QMB→QMN. |
| Operator decision | none |

## 3b. Pass-I lifecycle words vs parent JobHandle vocab

Pass-I §4.7 names queued, running, awaiting approval, paused, interrupted, unknown, succeeded, failed, cancelled, expired. Those remain independent observables. They are **mapped**, not dropped:

| Pass-I word | Where it lives |
|---|---|
| queued, running, unknown, failed, cancelled | QMA AD-17 JobHandle |
| succeeded | JobHandle `done` (parent spelling) |
| aborted (parent, not Pass-I) | JobHandle `aborted` — known environmental non-completion |
| awaiting approval | Mission/Task gate, not a JobHandle state |
| paused, interrupted | Task/occupancy, distinct from handle terminality |
| expired | artifact completeness on the handle inventory |

## 4. Pass-I / Pass-II scenario preservation

- **65 Pass-I scenarios** remain independent requirements. None rewritten to match the design.
- **20 Pass-II scenarios** accepted as candidate-derived obligations. None rejected.
- BDD files remain specification. They are not execution evidence.
- Catalog count stays **85**. This sitting does not substitute a smaller set.

Pass-II that look like “already designed” (ContributionHit, change_request, recipe-definition identity) are accepted because Stage A named the seam incompletely; the scenario still has force as a test oracle.

## 5. Resulting candidate amendments (index)

Applied in this sitting to produce `qmx-workflows-arch-2026-09-19-c`:

| Document | Change |
|---|---|
| ARCHITECTURE-SPINE.md | AD-2 pin/tombstone; AD-3 envelope pointer + event reminder; AD-5 join pointer; AD-7 outbox; AD-8 GrantRecord + CAS pointer; AD-11 three classes; AD-12/16 recipe-definition identity; AD-14 fencing pointer; AD-17 DTO pointer; AD-18 lifecycle pointer; AD-21 door matrix; **AD-23..AD-31** new; Deferred/C-05 restated; parent amendment 7 restated |
| CONTRACTS.md | Complete payloads §§1–15; JobHandle parent vocab; provider≠venue; ATC + PolicyPair; invocation/grant; fencing; outbox; join; checkpoint; UI DTOs; door matrix |
| JOURNEYS.md | J03 rewritten; J03b ATC; J10 fencing; J17 stream protocol; failure list expanded to Codex first-unsupported transitions |
| REQUIREMENTS-ADDENDUM.md | WF-R-09/10 restated; WF-R-19..WF-R-28 added; WF-R-10 no longer pretends sensing is the second system |
| CONFLICT-REGISTER.md | C-05 closed from transcript |
| OPERATOR-QUESTIONS.md | OD-01 closed; OD-02/03 yes |
| IMPLEMENTATION-SEQUENCE.md | Safety envelopes before any ATC venue work; classification gates |
| UI-HOST.md | Reconnect/CAS and view DTOs referenced |
| COPILOT-AND-APPS.md | Grants are GrantRecords |
| RESUME-STATE.md | Stage C status |

## 6. Remaining contradictions and operator decisions

### OD-01 — closed

No remaining architecture question. Transcript: Book/BMS is a specific PM/risk/sizing stack; the kit must replace or improve it; attached surfaces adopt; never fake a Book; sequential paper-then-live. L36 named amendment goes to Documentation Factory as constitution prose.

### OD-02 / OD-03 — yes (technical defaults)

### Not asked / already standing

QMF is one framework. Dummy Book forbidden. Data/ML need not be a bot. Sessions own context. App-use cannot edit or self-apply. Specialists remain. Trading-floor PM = Portfolio Manager. BDD is specification. mutmut optional, WSL/POSIX, disposable copy, never `mutmut apply` on the shared worktree. No sixth COMP. No n8n/Hermes/OpenBB import.

### Technical leftovers that are not operator questions

- CT-06 recipe registry kind still deferred.
- GAP-0081 chrome still deferred; DTOs only.
- json-render / MCP Apps unpinned.
- ADR-0023 mill package still provisional; code reused.
- QMA pytest still blocked in the mill-split nested venv; no green claim.
- F07 synthetic portfolio still deferred.

## 7. Revised coverage status

Statuses mean requirement-to-design trace, **not** implemented behavior.

| Family | Stage A | After Stage C | Remaining hole |
|---|---|---|---|
| BR-CAP | Partial | Candidate-defined lifecycle + pin/tombstone + export oracle | Implementation; scanner harness |
| BR-OP | Partial | Envelope + parent JobHandle vocab | Implementation; door matrix tests |
| BR-WF | Candidate-defined; code refutes adoption | Outbox + join algebra specified | Durable edges still absent at pin |
| BR-SES | Partial, runtime absent | CAS + GrantRecord + change-request completeness | Runtime absent |
| BR-DATA | Partial | Recipe-definition identity + full policy fields | CT-06 kind deferred |
| BR-STR | Partial | Stream protocol specified | Implementation |
| BR-MKT | **Contradictory** on non-Book deploy | ATC defined; consumers adopt; L36 named amendment pending docs prose | Dummy Book still forbidden; Book path regression |
| BR-PLC | Partial/deferred | Checkpoint manifest + restore order | Cross-store proof |
| BR-SKL | Partial | Unchanged (not an AF blocker) | Evaluator still later |
| BR-APP | Partial | View DTOs + door matrix | Chrome GAP-0081 |
| Cross-component | Unsupported | Still **unsupported integration** | P2-INT-001 |

Codex “first unsupported transitions” 1–8 now have normative machines in AD-24..AD-30. They are **not** evidenced.

## 8. Ready for a separate operator acceptance gate?

**No.** Documentation Factory already ran (2026-09-19). Focused Codex recheck of AD-23..AD-31 **returned** (`CODEX-RECHECK-RETURN-2026-09-19.zip`, SHA-256 `aa64bc8a431d543d86da77b182b2c18e449d3a6665fe837709902dc95b3adeb4`): disposition **repairs required; not ratified**. Epics stay paused until desk-fix of RC-01..RC-17 lands. Do not re-run Documentation Factory. Do not claim Codex approved AD-23..AD-31.
