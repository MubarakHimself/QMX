---
stepsCompleted: [1, 2, 3, 4]
validated: true
inputDocuments:
  - _docwork/workflows-epics-handoff.md
  - _docwork/riders/workflows-construction-kit-2026-09-19.md
  - docs/decisions/ADR-0024-workflows-construction-kit.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/CONTRACTS.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/JOURNEYS.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/REQUIREMENTS-ADDENDUM.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/UI-HOST.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/codex-recheck-return-20260919/CODEX-RECHECK-RETURN.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/codex-recheck-return-20260919/DESK-FIX-CONTRACTS.md
  - _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/codex-recheck-return-20260919/RECHECK-RECONCILIATION.md
  - docs/scenarios/SCN-0018-contribution-hit-honesty.md
  - docs/scenarios/SCN-0019-app-use-change-request.md
  - docs/scenarios/SCN-0020-two-trading-compositions.md
  - docs/scenarios/SCN-0021-outbox-jobhandle.md
  - docs/scenarios/SCN-0022-pack-lifecycle-headless.md
  - _docwork/workflows-increment-brief.md
  - _docwork/workflows-increment/confirmation/RUBRIC.md
  - _docwork/feature_inventory.yaml (FEAT-0051..FEAT-0057; blockers FEAT-0050, FEAT-0041, FEAT-0046, FEAT-0040, FEAT-0042, FEAT-0037, FEAT-0044, FEAT-0033, FEAT-0029, FEAT-0031)
  - _docwork/ledger.yaml (DEC-0414..DEC-0451 ratified)
  - _docwork/gaps.yaml (GAP-0092..GAP-0100)
  - docs/contracts/ct-40-qma-wire-envelope.yaml (ContributionHit usage annotation; format mint is FEAT-0051)
  - docs/constitution.md (L36 named amendment DEC-0448)
  - docs/components/qma-wire.md
  - docs/components/qma-daemon.md
  - docs/components/qma-core.md
  - _bmad-output/planning-artifacts/epics-QML-RESEARCH-2026-09-16.md (Epic 52 — extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md (Epics 40–48 — extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics-WORKBENCH-2026-09-14.md (Epics 34, 36, 37 — extend, do not duplicate)
  - _bmad-output/planning-artifacts/epics.md (Epic 10 Book/BMS — extend, do not duplicate)
  - integration@270e992995c2378ca63cf6343254ef8140a8c97e (brownfield: ContributionHit / product_session / durable edges / envelopes / ATC PolicyPair absent)
excludedDocuments:
  - _bmad-output/planning-artifacts/epics.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-QMA-2026-08-29.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-CONNECT-2026-09-11.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-WORKBENCH-2026-09-14.md (must not be rewritten)
  - _bmad-output/planning-artifacts/epics-QML-RESEARCH-2026-09-16.md (must not be rewritten)
  - _bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md (must not be rewritten; GAP-0061)
  - _bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/DESIGN.md (empty scaffold)
  - _bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/EXPERIENCE.md (empty scaffold)
  - _docwork/qml-research-epics-handoff.md (FEAT-0047 mill — wrong increment)
delegation: "operator 2026-09-19 — autonomous epics run; menus auto-continued; Workflows increment only; docs authority; no factory launch; no Documentation Factory; no architecture reopen"
epicNumbering: "Epic 53–59 — reserved so WORKFLOWS never collides with Phase-1 (1–23), trading-node (24–30), CONNECT (31), WORKBENCH (32–38), QMA (40–48), or QML-RESEARCH (49–52). Epic 39 left unused as a buffer."
baseInventory: "integration@270e992995c2378ca63cf6343254ef8140a8c97e (inspect only; do not use 8510c03 for absence claims)"
feature: FEAT-0051..FEAT-0057
adr: ADR-0024
architectureStatus: "docs folded (ADR-0024, DEC-0414..DEC-0451 ratified as docs authority). Focused Codex recheck of AD-23..AD-31 returned repairs-required (not ratified). Grok desk-fix of RC-01..RC-17 landed in CONTRACTS.md / spine AD-3/AD-23..AD-31 and folded SCN-0019..0022. Do not claim Codex ratified AD-23..AD-31. Implementation authorization remains factory-pipeline-only."
decisions: [DEC-0414, DEC-0415, DEC-0416, DEC-0417, DEC-0418, DEC-0419, DEC-0420, DEC-0421, DEC-0422, DEC-0423, DEC-0424, DEC-0425, DEC-0426, DEC-0427, DEC-0428, DEC-0429, DEC-0430, DEC-0431, DEC-0432, DEC-0433, DEC-0434, DEC-0435, DEC-0436, DEC-0437, DEC-0438, DEC-0439, DEC-0440, DEC-0441, DEC-0442, DEC-0443, DEC-0444, DEC-0445, DEC-0446, DEC-0447, DEC-0448, DEC-0449, DEC-0450, DEC-0451]
---

# QMX - Epic Breakdown

## Overview

This document is the epic and story breakdown for the **Workflows construction-kit** increment (FEAT-0051..FEAT-0057): absorb the 2026-09-19 spine (architecture-QMX-2026-09-18 local AD-1..AD-31, candidate `qmx-workflows-arch-2026-09-19-c`) so existing applications compose as one construction kit — capability / extension / workflow / mini-app / widget — **without** minting a sixth COMP, a new contract id, a dummy Book, or a marketplace.

It decomposes the **docs-authority** 2026-09-19 corpus — ADR-0024, DEC-0414..DEC-0451, SCN-0018..SCN-0022, desk-fixed `CONTRACTS.md` after RC-01..RC-17, and brownfield defects at `integration@270e992` — into implementable stories for the factory lanes.

The Phase-1 file (`epics.md`, Epics 1–23 and trading-node Epics 24–30) stays untouched. CONNECT (`epics-CONNECT-2026-09-11.md`, Epic 31) stays untouched. WORKBENCH (`epics-WORKBENCH-2026-09-14.md`, Epics 32–38) stays untouched. QMA (`epics-QMA-2026-08-29.md`, Epics 40–48) stays untouched. QML-RESEARCH (`epics-QML-RESEARCH-2026-09-16.md`, Epics 49–52) stays untouched. **Epic numbering starts at Epic 53**, a reserved block so this increment never collides with those files. Epic 39 remains unused as a buffer.

Requirement prefixes carry the **WF** marker because these requirements derive from the Workflows construction-kit docs corpus and child spine, not from a PRD rewrite. The 2026-08-21 PRD has no ContributionHit / product_session / ATC / outbox FRs. GAP-0061 stays deferred. FR-WF-* live on GAP-0093..GAP-0097 as the implementation holes this increment specifies. Rules carried forward from `epics.md`: each FR's cited artifact is the epic boundary and the source of its acceptance criteria; FR granularity is deliberately coarser than story granularity — never size a lane by counting FRs.

This increment **extends** Epic 52 (two-class federation), Epic 41 (CT-40 wire), Epic 48 (desk packs), Epic 40 (qma-core), Epic 42 (daemon substrate), Epic 43 (Task Graph / Graph Template), Epic 37 (procedures), Epic 45 (JobHandle / QMB door), Epic 36 (connect door), and Epic 10 (Book/BMS). It does not duplicate those stories. It **closes** the missing third hit class, pin/tombstone, operation descriptors, InvocationEnvelope/GrantRecord, product_session CAS, full DAG validation, durable Task Graph edges/outbox, and the thin honesty fixtures those stories left open. It **forbids** claiming those machines exist as wired surface at `270e992`, claiming Codex ratified AD-23..AD-31, filling GAP-0081 chrome / GAP-0058 / GAP-0099 / GAP-0100, dummy Book, sensing-as-ATC, a sixth COMP, or JobHandle states `succeeded` / `awaiting_approval`.

Preflight verdict (ADR-0024 / DEC-0446): **reuse** existing applications. **new COMP: none. new CT: none.** Additive CT-40 family annotations are already on the contract; **format mint of ContributionHit fields is FEAT-0051**. Cheap-veto A1–A6 (DEC-0447) are sitting machinery — stories may cite them; they are not operator-spoken schemas.

Nothing in this document grants implementation, credential, order, paper-mode, promotion, live-money or destructive authority; that arrives only through the factory pipeline (ADR-0024; DEC-0445). **This session does not launch factory lanes.**

Codex standing (GAP-0092): focused recheck of AD-23..AD-31 **ran** 2026-09-19 (`CODEX-RECHECK-RETURN-2026-09-19.zip`, SHA-256 `aa64bc8a431d543d86da77b182b2c18e449d3a6665fe837709902dc95b3adeb4`). Disposition **repairs-required; not ratified**. Grok desk-fix of RC-01..RC-17 landed. Stories implement the **repaired** contract behavior. Do not claim Codex approved those ADs.

## Requirements Inventory

### Functional Requirements

**A. Discovery — ContributionHit concatenate + pin/tombstone (DEC-0415 / DEC-0449 / AD-2 / AD-30; FEAT-0051)**

- FR-WF-01: Federated discovery concatenates typed hits including `ContributionHit` on the additive CT-40 family and is never a fourth store and never a door run. (AD-2; DEC-0415)
- FR-WF-02: A `ContributionHit` exposes exactly `hit_class=contribution`, `plugin_id`, `point`, `qualified_id`, `package_id`, `package_version`, `availability_revision`, `availability`. (CONTRACTS §2)
- FR-WF-03: Contribution identity is the live `published_contributions()` tuple and is never fp1, a registry kind, or `ArtifactHit.kind`. (AD-2; SCN-0018)
- FR-WF-04: Facade refuses `hit_class` values `strats` and `qml_candidate`, and refuses hypothesis listing on the Library facade. (DEC-0449)
- FR-WF-05: Discovery occupancy on this path is none; daemon never `import qmb`; QMB never opens daemon sqlite. (DEC-0449)
- FR-WF-06: Publishing or discovering a `ContributionHit` does not authorize invoke (a hit is not a grant). (AD-9; SCN-0018)
- FR-WF-07: Pin stores `(qualified_id, package_version, availability_revision)`, not a descriptor digest. (AD-2; cheap-veto A4)
- FR-WF-08: Invoke revalidates the pin; missing/disabled/uninstalled yields typed `unavailable` or `tombstone`, never another version, never a stale fp1. (AD-30; SCN-0018)
- FR-WF-09: Pack `contributes` are `{point, local_id}` objects; qualification defaults to `package_id + ":" + local_id`; collision on `(point, qualified_id)` at enable refuses. (RC-13)
- FR-WF-10: `availability_revision` publishes atomically with roster swap. (RC-13)
- FR-WF-11: Uninstall/disable names dependants and in-flight `pin_leases`; GC only when leases empty; in-flight pinned runs keep started bytes. (RC-14; SCN-0018)
- FR-WF-12: Discovery listings distinguish published vs configured vs granted vs reachable vs healthy; `view:*` is a wire DTO only until GAP-0081. (AD-15; AD-17)
- FR-WF-13: No new CT number; ContributionHit is additive CT-40 format mint only (do not mint CT-52). (DEC-0446; GAP-0094)

**B. Capability interface — descriptor, envelope, grants (DEC-0416 / DEC-0437 / AD-3 / AD-24; FEAT-0052)**

- FR-WF-14: Every public operation publishes a versioned descriptor with the complete AD-3 / CONTRACTS §1 field catalogue, including separate `input_cardinality` / `output_cardinality` and `supported_doors`. (RC-16)
- FR-WF-15: Closed `output_shape`, `effect_class`, `placement`, and per-side cardinality; mapping is not on the descriptor. (AD-3; AD-5)
- FR-WF-16: Closed `lifecycle_verbs` `start` | `query-state` | `cancel` | `await`; refusal codes include `INVALID_INPUT`, `UNAVAILABLE`, `UNSUPPORTED_DOOR`, `STALE_OBSERVATION`, `GRANT_MISMATCH`. (CONTRACTS §1)
- FR-WF-17: Every public call carries `InvocationEnvelope` with the CONTRACTS §1b field set. (AD-24; cheap-veto A3)
- FR-WF-18: Envelope is signed/bound request context, not authority; every hop resolves contribution/descriptor/GrantRecord and refuses stale/mismatch before execution. (RC-03)
- FR-WF-19: Caller issues `idempotency_key`; uniqueness domain `(principal, op_id, op_version, instance_id, config_revision, grant_id, target, canonical_input_hash)`; collision refuses; replay returns prior result. (RC-04)
- FR-WF-20: Nested public calls carry `parent_logical_invocation_id` and `call_depth`; child id is deterministic. (RC-04)
- FR-WF-21: `input_hash` preimage is canonical JSON of the `input_schema`-validated payload; secrets never inlined. (RC-04)
- FR-WF-22: Effect-specific outcomes: `none`/`read` may retry; `append-evidence` dedupes; `mutate-config` is CAS; `place-run` uses `logical_invocation_id` as run identity; `external-egress` obtains a receipt or becomes `unknown` and never blind-retries. (RC-04; SCN-0021)
- FR-WF-23: `GrantRecord` is immutable and does not carry `revoked_at`; fields per CONTRACTS §3b. (RC-05)
- FR-WF-24: Revocation is append-only `GrantRevocation`; already-accepted work may finish; new dispatch after revoke/expiry is refused; upgrade cannot widen/retarget without re-grant. (RC-05)
- FR-WF-25: Manifests request; host grants; transport never bypasses the envelope; only parameter authority is `input_schema`. (AD-3)
- FR-WF-26: Door matrix is per `op_id`+version; unsupported → typed `unsupported_door`; QMB is the only operator CLI. (RC-17; AD-21)

**C. Product session — CAS + grant intersection (DEC-0421 / DEC-0442 / DEC-0422 / AD-8 / AD-29; FEAT-0053)**

- FR-WF-27: `product_session` is a journal-projected record with ids `psess:` distinct from QMA Session `sess:`; 1 product_session → many QMA Sessions; not a new sqlite class. (AD-8; AD-16)
- FR-WF-28: Durable fields: `product_session_id`, `profile`, `principal`, `context_revision`, `app_instance_id`, `granted_ops`, `selected_refs`, `account_scope`, `resume_cursor`, `cursor_generation`. (CONTRACTS §3)
- FR-WF-29: `profile` is closed immutable-at-create `ProductSessionProfile` ∈ `{authoring, app-use}` and is not `qma.core.ontology.Profile`. (AD-8)
- FR-WF-30: `granted_ops` stores GrantRecord ids, not bare op strings. (AD-24)
- FR-WF-31: Closed `selected_refs` kinds; layout/widget/json-render trees are forbidden. (AD-8)
- FR-WF-32: CAS mutate results `ok` | `conflict` | `duplicate` | `in_progress`; `command_id` namespace `(product_session_id, principal, command_id)`. (RC-11)
- FR-WF-33: Reconnect is a query from `(resume_cursor, cursor_generation)` and never replays unacked intent; tab change writes nothing. (AD-29; SCN-0019)
- FR-WF-34: Copilot tool availability is the intersection of published ContributionHits, host grants, product_session GrantRecords, and health; skills do not grant. (AD-9)
- FR-WF-35: App-use may inspect, invoke exposed ops, adjust permitted inputs, and mint change-request only — never edit package source, install code, elevate grants, or retarget accounts. (AD-8)
- FR-WF-36: Change path is three records: immutable `ChangeRequest`, `ChangeValidationRecord`, append-only `ChangeApplyRecord`. (RC-12; SCN-0019)
- FR-WF-37: `request_hash` preimage is requester facts + patch only; app-use mints; authoring + operator applies; `promote` is L17 and not this path. (RC-12)
- FR-WF-38: Pack states stay distinct from session authority: installed ≠ enabled ≠ session-granted. (AD-13)

**D. Graph Template DAG (DEC-0417 / DEC-0419 / AD-4 / AD-6; FEAT-0054)**

- FR-WF-39: Graph Template is an authored, versioned, stateless DAG; compile identity `(qualified_id, version)`. (AD-4)
- FR-WF-40: `validate_graph_template_topology` refuses self-loops and any directed cycle (DFS; pairwise reverse-edge checks are insufficient). (AD-6)
- FR-WF-41: Four layers stay distinct; Board layout is client-only; Stage 0 `graph` is none of these and never compiles to bot, Graph Template, or `run_slice`. (AD-4; DEC-0411)
- FR-WF-42: Edge mapping is explicit; Cartesian requires an explicit flag; conditional skip is a node kind. (AD-5)
- FR-WF-43: Selected-subgraph execution is `MissionCompiler(template.qualified_id, template.version, node_ids)` of an already-registered template. (AD-4)
- FR-WF-44: Do not fingerprint templates onto the Artifact rail; ExperimentSpec successors are lineage, not control-flow. (AD-4; AD-7)

**E. Durable Task Graph — edges, outbox, JobHandle, join (DEC-0420 / DEC-0439 / AD-26; FEAT-0055)**

- FR-WF-45: Persist `task_graph_state` including `edges: {from, to, mapping}` in daemon sqlite; no second scheduler. (AD-7; GAP-0095)
- FR-WF-46: Completing A and making B ready is one sqlite transaction plus outbox. (AD-26; SCN-0021)
- FR-WF-47: Outbox unique key `(graph_run_id, successor_node_id, predecessor_revision, partition_id)`; persist target + `envelope_hash`; states dispatched / accepted / effected. (RC-07)
- FR-WF-48: At-least-once dispatch; exactly-once logical acceptance under the receiver ledger via `logical_invocation_id` dedupe. (SCN-0021)
- FR-WF-49: JobHandle uses QMA AD-17 vocab exactly; never `succeeded` or `awaiting_approval` on a handle. (AD-26)
- FR-WF-50: Timeout/lost supervisor → `unknown`, never `failed` or `aborted`; first durable terminal wins. (SCN-0021)
- FR-WF-51: Occupancy is existing `environment_lease` + door law, not a separate table. (AD-7)
- FR-WF-52: Join algebra binds graph/run/node/edge/definition/join revisions; `first-wins` order `(event_time, receive_time, source_event_id)`. (RC-08)
- FR-WF-53: Skills never compile to Missions and never grant tools. (AD-7)

**F. Thin proof fixtures (DEC-0424 / DEC-0436 / DEC-0444 / DEC-0443 / DEC-0448; FEAT-0056)**

- FR-WF-54: Book/BMS default path regression: `ResolvedRunConfig` still requires Book/BMS/bot keys; do not weaken compile tests. (SCN-0020; J03)
- FR-WF-55: Dummy Book/BMS/PolicyPair is `INVALID_INPUT` at compile, register, validate, simulate, and seat. (DEC-0448)
- FR-WF-56: ATC simulate: `AlternativeRunConfig` with keys absent (not null), `composition_fp`, versioned PolicyPair identity, command including `command_owner_epoch`, and authoritative host `admission`. (RC-01; RC-02)
- FR-WF-57: PolicyPair identity is `{policy_pair_id, policy_pair_version, policy_pair_hash}`; inline bodies are snapshots. (RC-01; cheap-veto A1)
- FR-WF-58: Admission is a host result; live without paper+L17 is `not_promoted`; stale observations refuse. (RC-02)
- FR-WF-59: When ATC is selected, QML/QMB/optional MIS/QMN adopt it; sensing/`UngovernedWorkConfig` is not ATC; evidence is QMB JSONL `composition_class: alternative`. (SCN-0020)
- FR-WF-60: RecipeDefinition identity `(recipe_def_id, recipe_def_version, recipe_def_hash)` with full AD-31 catalogue; credentials as typed refs. (RC-15; cheap-veto A5)
- FR-WF-61: Two runs of one definition are two releases; non-trading outputs need no CT-33/Book/QMN wrap; CT-06 recipe kind stays deferred. (AD-31)
- FR-WF-62: App-use change-request fixture: three-record path; v1 untouched; app-use never applies. (SCN-0019)
- FR-WF-63: Pack lifecycle: journaled `PackTransition` with CAS on `roster_generation`; atomic roster; missing dep is a hard error at enable. (RC-14; SCN-0022)
- FR-WF-64: Migrations `down` | `forward_only` with prepare/commit/rollback; failed path restores last usable roster. (RC-14)
- FR-WF-65: Independent versioned `ExportScanReport` is the export oracle; self-asserted `exports_secrets: false` is not evidence. (SCN-0022)
- FR-WF-66: Thin fixtures must not claim or close GAP-0098 / P2-INT-001 e2e adoption. (DEC-0450)

**G. Safety fixtures (DEC-0438 / DEC-0439 / DEC-0441 / DEC-0437; FEAT-0057)**

- FR-WF-67: Stream cancel + cutover: split subscription/data/control records; derived refcount from leases; `source_id` ≠ `venue_id`. (RC-10; J17)
- FR-WF-68: Cutover requires barrier + `cutover-ack`; replay provenance cannot authorize a live command; subscription is not trading permission. (AD-28)
- FR-WF-69: Outbox restart fixture: crash between A terminal+outbox and B dispatch ack → replay; B accepted once logically. (SCN-0021)
- FR-WF-70: `unknown-blocked` is a terminal branch of the fencing attempt; operator reconcile mints a new attempt/epoch — never automatic retry. (RC-06; cheap-veto A2)
- FR-WF-71: Deploy payload includes role, attempt, epoch, token uniqueness, snapshots, CAS guards, timeout/escalation. (CONTRACTS §10)
- FR-WF-72: Stale predecessor restart without current `(epoch, token)` is refused; software rollback cannot unfill. (AD-25)
- FR-WF-73: Grant refuses wrong `instance_id` / `config_revision` (`GRANT_MISMATCH`) before execution. (RC-03)
- FR-WF-74: Implement at least two of FR-WF-67..73; do not invent GAP-0100 chrome; mutmut is not architecture proof. (FEAT-0057 inventory)

### NonFunctional Requirements

- NFR-WF-01: No sixth COMP; no new CT number; additive CT-40 family only. (DEC-0446)
- NFR-WF-02: Typed CT-04 refusals at every public boundary; doors render, never swallow. (AD-3)
- NFR-WF-03: Persistence owners stay split; hypotheses stay in QML `research_root`; ATC evidence stays QMB JSONL. (AD-16)
- NFR-WF-04: v1 daemon additions are a closed list: `product_session` journal projection; durable `task_graph_state` including AD-26 outbox; mini-app instance rows in existing plugin-install projection; GrantRecord rows beside product_session. No other new sqlite class. CheckpointManifest is journal-projected (AD-27 / cheap-veto A6), not a new store. (DEC-0429)
- NFR-WF-05: Headless/CLI/library semantic parity across an operation’s supported doors only. (AD-21)
- NFR-WF-06: Packages export without author secrets/private chats; scanner oracle fail-closed. (AD-18)
- NFR-WF-07: mutmut optional (WSL/POSIX, disposable copy, never `mutmut apply` on the shared worktree); not architecture proof. (AD-19)
- NFR-WF-08: Identities stay separate: artifacts fp1; hypotheses `research_ref`; contributions `(qualified_id, package_version)` never fp1; `psess:` ≠ `sess:`; recipe def ≠ release fp1. (AD-13)
- NFR-WF-09: Compute placement states distinct: available / configured / authorized / reachable / healthy. (AD-15)
- NFR-WF-10: CheckpointManifest protocol per CONTRACTS §13; restore order is data-dependency; bootstrap authority is the separately stored copy. (AD-27; RC-09; A6)
- NFR-WF-11: Portfolio Manager is a display label; keep `desk_slug=pm` (GAP-0083 out). (AD-22)
- NFR-WF-12: UI contribution DTOs may exist as wire contracts; chrome remains GAP-0081; json-render/MCP Apps own neither identity nor permission. (AD-17)
- NFR-WF-13: Inspect SHA honesty at `270e992` (DEC-0450). Class/test existence is not e2e (DEC-0286).
- NFR-WF-14: Cheap-veto A1–A6 may be cited as sitting machinery; must not be treated as operator-spoken schemas. (DEC-0447)
- NFR-WF-15: Do not claim Codex ratified AD-23..31; RC-01..RC-17 desk-fix has landed and is normative for repaired contract behavior. (GAP-0092)
- NFR-WF-16: Envelope signing algorithm / key hierarchy is GAP-DESK-ENVELOPE-CRYPTO (implementation choice); mismatch refuse behavior is specified.
- NFR-WF-17: Stories specify factory work; they do not authorize live trading, credentials, or go-live. (DEC-0445)

### Additional Requirements

- AR-WF-01: DTO owner of ContributionHit is COMP-QMA-WIRE; live query owner is COMP-QMA-DAEMON `published_contributions()`.
- AR-WF-02: ATC evidence owner is COMP-QMB (QMF-RISK supplies default shapes only — SCN-0020 desk-fix).
- AR-WF-03: Recipe wrap owner is COMP-QMB wrap of COMP-QMF-DATA; CT-06 kind deferred.
- AR-WF-04: Fencing issuers: QMN issues venue tokens; QMB issues internal ATC-simulate tokens.
- AR-WF-05: Pin persistence uses AD-30 `pin_leases`; must not invent a sixth sqlite class.
- AR-WF-06: Qualification default `package_id + ":" + local_id` (GAP-DESK-QUALIFY-FORMULA).
- AR-WF-07: Golden scenarios SCN-0018..SCN-0022 are specification oracles; 85 Codex catalog IDs stay as a pointer, not 85 new SCN files. BDD is specification, not executed proof.
- AR-WF-08: Starter template: none. This increment extends existing packages.
- AR-WF-09: Blockers (inventory): FEAT-0051 ← 0050/0041/0046; 0052 ← 0041/0040; 0053 ← 0052/0042; 0054 ← 0042/0037; 0055 ← 0054/0042/0044/0033; 0056 ← 0051..0055 + 0029/0031; 0057 ← 0055/0056. Inventory still marks those parents `planned`; stories extend prior *story law*, they do not re-author it.
- AR-WF-10: Brownfield at `270e992` to forbid claiming done: two-class federation only; `product_session` absent; descriptors/envelopes/grants absent; TaskGraph in-memory with edges dropped; topology check is reverse-edge only; PolicyPair absent; P2-INT-001 unsupported.
- AR-WF-11: Out of this increment: GAP-0081 chrome, GAP-0058, GAP-0085, GAP-0061/0062/0063, GAP-0099, GAP-0100, marketplace, dummy Book, sensing-as-ATC, sixth COMP, mill FEAT-0047, FEAT-0001.

### UX Design Requirements

The 2026-09-01 UX spine (`DESIGN.md` / `EXPERIENCE.md`) is an empty scaffold and is **not** a contract. GAP-0081 chrome is out of scope. Only AD-17 UI-host **wire** contracts fold:

- UX-DR-WF-01: Navigation host binds contribution descriptor DTOs from desks/`scope_path` + plugin roster query — not layout chrome. (UI-HOST; FEAT-0051)
- UX-DR-WF-02: Commands bind AD-3 `op_id` — not command-palette chrome. (FEAT-0052)
- UX-DR-WF-03: Parameter-form chrome / UiFlag catalog is GAP-0081. AD-26 in this sitting is outbox, not a form AD. Do not invent the collision. **Out of this increment.**
- UX-DR-WF-04: Context providers bind ContextCompiler refs + product-session blob (CAS). (FEAT-0053)
- UX-DR-WF-05: Events/logs bind wire events + QMN evidence HTTP; snapshots authoritative. (FEAT-0052/0053)
- UX-DR-WF-06: Reconnect uses `producer_id` + attach/`since_seq`; must not cancel jobs; must not replay intent. (FEAT-0053; SCN-0019)
- UX-DR-WF-07: Native pane / JSON Render / MCP Apps own neither identity nor permission; mount/dispose must not start or kill durable work. (AD-17; FEAT-0052)
- UX-DR-WF-08: Rich `ui_view` remains GAP-0081 — explicitly not in this epic set.

### FR Coverage Map

FR-WF-01: Epic 53 — concatenate ContributionHit
FR-WF-02: Epic 53 — DTO fields
FR-WF-03: Epic 53 — never fp1 / registry kind
FR-WF-04: Epic 53 — refuse strats / qml_candidate / hypotheses
FR-WF-05: Epic 53 — occupancy none
FR-WF-06: Epic 53 — hit is not a grant
FR-WF-07: Epic 53 — pin tuple
FR-WF-08: Epic 53 — tombstone
FR-WF-09: Epic 53 — contributes objects
FR-WF-10: Epic 53 — atomic availability_revision
FR-WF-11: Epic 53 — pin leases
FR-WF-12: Epic 53 — published vs granted vs healthy
FR-WF-13: Epic 53 — no CT-52
FR-WF-14: Epic 54 — descriptor catalogue
FR-WF-15: Epic 54 — closed shapes
FR-WF-16: Epic 54 — lifecycle verbs / refusal codes
FR-WF-17: Epic 54 — envelope fields
FR-WF-18: Epic 54 — hop revalidation
FR-WF-19: Epic 54 — idempotency domain
FR-WF-20: Epic 54 — nested identity
FR-WF-21: Epic 54 — input_hash preimage
FR-WF-22: Epic 54 — effect outcomes
FR-WF-23: Epic 54 — GrantRecord immutable
FR-WF-24: Epic 54 — GrantRevocation
FR-WF-25: Epic 54 — transport never bypasses
FR-WF-26: Epic 54 — per-op_id doors
FR-WF-27: Epic 55 — psess: projection
FR-WF-28: Epic 55 — durable fields
FR-WF-29: Epic 55 — ProductSessionProfile
FR-WF-30: Epic 55 — granted_ops are grant ids
FR-WF-31: Epic 55 — selected_refs kinds
FR-WF-32: Epic 55 — CAS
FR-WF-33: Epic 55 — reconnect / tabs
FR-WF-34: Epic 55 — grant intersection
FR-WF-35: Epic 55 — app-use limits
FR-WF-36: Epic 55 — three-record types (fixture in Epic 58)
FR-WF-37: Epic 55 — request_hash / apply authority
FR-WF-38: Epic 55 — pack vs session states
FR-WF-39: Epic 56 — Graph Template identity
FR-WF-40: Epic 56 — DAG validator
FR-WF-41: Epic 56 — four layers / Stage 0
FR-WF-42: Epic 56 — explicit mapping
FR-WF-43: Epic 56 — MissionCompiler induced DAG
FR-WF-44: Epic 56 — not Artifact rail
FR-WF-45: Epic 57 — persist edges
FR-WF-46: Epic 57 — one transaction
FR-WF-47: Epic 57 — outbox key and states
FR-WF-48: Epic 57 — at-least-once / exactly-once acceptance
FR-WF-49: Epic 57 — JobHandle vocab
FR-WF-50: Epic 57 — timeout → unknown
FR-WF-51: Epic 57 — occupancy
FR-WF-52: Epic 57 — join algebra
FR-WF-53: Epic 57 — skills never grant
FR-WF-54: Epic 58 — Book regression
FR-WF-55: Epic 58 — dummy INVALID_INPUT
FR-WF-56: Epic 58 — ATC simulate payload
FR-WF-57: Epic 58 — PolicyPair identity
FR-WF-58: Epic 58 — admission host result
FR-WF-59: Epic 58 — adopt ATC; sensing is not ATC
FR-WF-60: Epic 58 — recipe definition
FR-WF-61: Epic 58 — recipe release
FR-WF-62: Epic 58 — change-request fixture
FR-WF-63: Epic 58 — pack lifecycle
FR-WF-64: Epic 58 — migrations
FR-WF-65: Epic 58 — ExportScanReport
FR-WF-66: Epic 58 — do not close GAP-0098
FR-WF-67: Epic 59 — stream cancel + cutover
FR-WF-68: Epic 59 — cutover-ack / replay not live
FR-WF-69: Epic 59 — outbox restart fixture
FR-WF-70: Epic 59 — unknown-blocked terminal
FR-WF-71: Epic 59 — fencing payload
FR-WF-72: Epic 59 — stale predecessor
FR-WF-73: Epic 59 — grant/instance mismatch
FR-WF-74: Epic 59 — at-least-two floor; no GAP-0100

## Epic List

Seven epics, one per inventory feature, in inventory order. They stay separate because ContributionHit is a named amendment of DEC-0389 with a genuine risk of forking a second facade (53 vs 52); because envelopes/grants are a different type system from discovery hits (54 vs 53) even though both touch COMP-QMA-WIRE; because product_session is a journal projection beside QMA Session, not a fold of it (55); because full DAG validation is a hole under Story 43.3 reverse-edge checks (56); because durable edges/outbox are a different machine from topology validation (57); and because thin proofs and safety fixtures are honesty oracles against already-specified machines, not new product surfaces (58, 59). Consolidating 53+54 would mix discovery identity with invocation authority. Consolidating 56+57 would let a builder “complete” DAG validation by dropping edges again.

Weight tags route factory lanes: **H** heavy (`args.build_model = grok-4.6`), **L** light (`grok-4.5`). Wave numbers are the inventory waves from `validate_inventory.py --handoff`, not a required build order beyond `blocked_by` and file-disjointness.

### Epic 53: Search can cite a live contribution and a disable does not silently retarget (Wave 16, H)

The operator (and later an agent) can concatenate a live `ContributionHit` onto the existing Knowledge+Artifact facade, pin `(qualified_id, package_version, availability_revision)`, and after disable/uninstall receive typed `unavailable`/`tombstone` — never another version.

**FRs covered:** FR-WF-01..FR-WF-13
**Feature:** FEAT-0051
**Notes:** Blocked by FEAT-0050, FEAT-0041, FEAT-0046. Extends Epic 52 / Stories 41.1, 48.4, 34.1. SCN-0018 is the golden scenario. Delivers for FEAT-0056. GAP-0094.

### Epic 54: Every public call names its operation, grant, and retry identity (Wave 5, H)

Every public operation publishes a complete versioned descriptor; every public call carries an InvocationEnvelope that is revalidated on every hop; host grants are immutable GrantRecords with append-only revocation.

**FRs covered:** FR-WF-14..FR-WF-26
**Feature:** FEAT-0052
**Notes:** Blocked by FEAT-0041, FEAT-0040. Cheap-veto A3. GAP-0096. Delivers for FEAT-0053 and FEAT-0056.

### Epic 55: A product session owns context and grants; a tab owns nothing (Wave 10, H)

The operator can open a `psess:` product session (authoring or app-use), mutate it under CAS, and see copilot tools as the intersection of published hits, host grants, session GrantRecords, and health. App-use may mint a change-request; it cannot apply.

**FRs covered:** FR-WF-27..FR-WF-38
**Feature:** FEAT-0053
**Notes:** Blocked by FEAT-0052, FEAT-0042. SCN-0019 types live here; the apply fixture is Epic 58. GAP-0093.

### Epic 56: An illegal graph cannot register (Wave 17, L)

Registration refuses self-loops and any directed cycle. Graph Template, Task Graph, Board layout, and Stage 0 `graph` stay distinct. Mapping is explicit on edges.

**FRs covered:** FR-WF-39..FR-WF-44
**Feature:** FEAT-0054
**Notes:** Blocked by FEAT-0042, FEAT-0037. Closes the reverse-edge-only hole under Story 43.3 / DEC-0312. Delivers for FEAT-0055.

### Epic 57: Completing A cannot forget B, and a handle never says succeeded (Wave 18, H)

Task Graph edges and the AD-26 outbox persist in daemon sqlite. Completing predecessor A and making successor B ready is one transaction. JobHandle stays on QMA AD-17 vocabulary.

**FRs covered:** FR-WF-45..FR-WF-53
**Feature:** FEAT-0055
**Notes:** Blocked by FEAT-0054, FEAT-0042, FEAT-0044, FEAT-0033. SCN-0021. GAP-0095. Delivers for FEAT-0056 and FEAT-0057.

### Epic 58: Four honesty proofs as thin fixtures (Wave 19, H)

Thin fixtures prove: (1) Book/BMS regression and dummy `INVALID_INPUT`; (2) ATC simulate with zero Book keys and a complete PolicyPair; (3) RecipeDefinition ≠ release fp1; (4) app-use change-request without self-apply; (5) pack export scanner oracle and pin/invoke honesty. They do not close GAP-0098.

**FRs covered:** FR-WF-54..FR-WF-66
**Feature:** FEAT-0056
**Notes:** Blocked by FEAT-0051..0055, FEAT-0029, FEAT-0031. SCN-0019, SCN-0020, SCN-0022. GAP-0097. Owner of ATC evidence is COMP-QMB.

### Epic 59: Safety fixtures against the same envelopes (Wave 20, H)

At least two (this file specifies all five) of: stream cancel+cutover; outbox restart; UNKNOWN blocks handover; stale predecessor refused; grant refuses the wrong instance. No readiness dashboard.

**FRs covered:** FR-WF-67..FR-WF-74
**Feature:** FEAT-0057
**Notes:** Blocked by FEAT-0055, FEAT-0056. J17, J10, J26/J27. GAP-0100 stays out.

### Stories in other increment files that this increment extends (do not duplicate)

| Existing story | What it already delivered | What WORKFLOWS must not redo | What WORKFLOWS closes |
|---|---|---|---|
| 52.1–52.3 | KnowledgeHit \| ArtifactHit only; concatenate two queries; hypotheses off facade | Second facade; `strats` / `qml_candidate` hit class | Third class `ContributionHit` + pin/tombstone (53) |
| 41.1–41.3 | CT-40 envelope, additive-only, command idempotency | New CT number; a second wire package | Format mint of ContributionHit / InvocationEnvelope / GrantRecord fields (53, 54) |
| 48.1 / 48.4 | Plugin loader + five desk packs | New plugin model | `{point, local_id}` contributes expand to ContributionHit (53) |
| 34.1–34.2 | Library kinds = fp1 roster; three query surfaces | Graph Templates / Skills as Library kinds | Keep the refusal; contributions are not ArtifactHit.kind (53) |
| 40.2 / 40.3 | Closed vocabularies + plugin contribution surface | Second ontology | Operation descriptors on that surface (54) |
| 42.1–42.4 | Sole-writer journal; closed store list | New sqlite class | `product_session` + GrantRecord rows + durable `task_graph_state` (55, 57) |
| 43.1 / 43.3 | Mission Compiler; GT ≠ Task Graph; reverse-edge refuse | Pairwise reverse-edge as “DAG done” | Full cycle refusal (56); persist edges (57) |
| 37.1–37.3 | Procedures in QMA; no QMB task graph; ExperimentSpec successors | QMB wizard; walking CT-07 as control-flow | DAG gate + durable outbox (56, 57) |
| 45.4 / 45.8 | JobHandle parent vocab; QMB door law | `succeeded` / `awaiting_approval`; `import qmb` | Keep vocab exact on the outbox path (57) |
| 36.2 / 36.5 | Real CLI transport; occupancy / cancel | Merge worker outbox (41.4) with AD-26 | Task Graph outbox is a different noun (57) |
| 41.4 | Remote-worker dial-out outbox | Treating it as AD-26 Task Graph outbox | Cite only (57) |
| 45.5 | QMA Session `sess:` | Folding `psess:` into Session | Distinct product_session (55) |
| 47.3 | RefinementProposal stage/apply | Confusing it with app-use change-request | Three-record change-request (55, 58) |
| 10.* / FEAT-0029 | Book/BMS grammar; governed compile requires Book keys | Weakening those tests for ATC | Regression fixture + dummy refuse (58) |
| 32.2 | Tab-close cancels nothing | New cancel authority | Restate for product_session reconnect (55) |

---

## Epic 53: Search can cite a live contribution and a disable does not silently retarget

The operator and later an agent can concatenate a live `ContributionHit` onto the existing Knowledge+Artifact facade, pin `(qualified_id, package_version, availability_revision)`, and after disable/uninstall receive typed `unavailable` or `tombstone` — never another version, never a stale fp1. A hit is not a grant.

**Factory touch ownership:** exclusive writable surfaces are COMP-QMA-WIRE (additive CT-40 family **format mint** of ContributionHit fields — currently usage annotation only) and COMP-QMA-DAEMON `published_contributions()` (live query). Must not rewrite Stories 52.1–52.3’s two-class concatenate, Story 47.2’s CT-44 port, Story 34.1’s Library kinds, or Story 48.1 loader law. Must not mint CT-52. Must not add occupancy. Must not treat `view:*` as a ContributionHit (GAP-0081).

**Traceability for the epic:** FR-WF-01..FR-WF-13, UX-DR-WF-01, NFR-WF-01, NFR-WF-08, NFR-WF-13, NFR-WF-15, AR-WF-01, AR-WF-05, AR-WF-06, AR-WF-10, SCN-0018.

**What must already exist:** FEAT-0050 / Epic 52 (KnowledgeHit \| ArtifactHit concatenate); FEAT-0041 / Epic 41 (CT-40 envelope); FEAT-0046 / Story 48.4 (desk packs as contribution publishers). Inventory still marks those `planned` — this epic **extends** their story law; it does not re-author them.

**What this delivers:** UI/agent search can cite ContributionHit with honest pin/tombstone. FEAT-0056 pack fixtures wait on it. GAP-0094.

### Story 53.1: Federated DTO gains ContributionHit on additive CT-40

As a UI or agent author,
I want the frozen federated hit DTO to include a third class `ContributionHit`,
So that clients can cite a live published contribution without inventing fp1 identity or a new contract id.

**Traceability:** FR-WF-01, FR-WF-02, FR-WF-03, FR-WF-13, UX-DR-WF-01, NFR-WF-01.

**Acceptance Criteria:**

**Given** Epic 52’s frozen DTO (`KnowledgeHit` \| `ArtifactHit`) on additive CT-40
**When** FEAT-0051 lands the format mint
**Then** a hit is exactly one of: `KnowledgeHit {hit_class: knowledge, source_ref, snapshot_ref, locator}`, `ArtifactHit {hit_class: artifact, fp1, kind}`, or `ContributionHit {hit_class: contribution, plugin_id, point, qualified_id, package_id, package_version, availability_revision, availability}`
**And** there is no other `hit_class`. (FR-WF-01; FR-WF-02; DEC-0449; Story 52.1)

**Given** a `ContributionHit`
**When** identity is stored or compared
**Then** identity is the live `published_contributions()` tuple
**And** it is never fp1, never a registry kind, and never `ArtifactHit.kind`. (FR-WF-03; SCN-0018 Then 5; DEC-0415)

**Given** the DTO owner
**When** the package is named
**Then** it is COMP-QMA-WIRE as an additive CT-40 family format mint of existing fields
**And** no new CT number is minted (do not mint CT-52). Usage annotation already on `ct-40-qma-wire-envelope.yaml` is not this story’s pass — `schema.fields` / discovery query names must land. (FR-WF-13; GAP-0094; DEC-0446)

**Given** `hit_class: "strats"` or `qml_candidate` or a hypothesis kind
**When** a client sends or a server emits it
**Then** it is refused
**And** DEC-0412 stays dead; hypotheses stay on the QML research surface (Story 52.3). (FR-WF-04)

**Given** inspect SHA `270e992`
**When** this story is accepted
**Then** tests prove the third class on the wire after this story, not class existence of the two-class DTO
**And** claiming ContributionHit already existed at that SHA fails the story. (NFR-WF-13; DEC-0450; SCN-0018 Branch D)

### Story 53.2: Concatenate live published_contributions(); pack contributes expand at enable

As an operator,
I want federated search to concatenate the live contribution roster onto the two existing queries,
So that enabling a pack makes its contributions appear as hits without a fourth store.

**Traceability:** FR-WF-01, FR-WF-05, FR-WF-09, FR-WF-10, AR-WF-01, AR-WF-06.

**Acceptance Criteria:**

**Given** a federated search after Story 53.1
**When** it runs
**Then** it concatenates (1) CT-44 Knowledge search, (2) COMP-QMB `library.search`, and (3) COMP-QMA-DAEMON `published_contributions()`
**And** it is never a fourth store and never a door **run**. Occupancy remains none. (FR-WF-01; FR-WF-05; Story 52.2)

**Given** QMB
**When** federated search runs
**Then** QMB never opens daemon sqlite
**And** the daemon never `import qmb`. (FR-WF-05; DEC-0449)

**Given** a pack manifest
**When** `contributes` is declared
**Then** each entry is a `{point, local_id}` object (never an opaque string such as `"capability:qmb.analysis.project"`)
**And** qualification to `qualified_id` defaults to `package_id + ":" + local_id` (or the pack-declared rule). (FR-WF-09; RC-13; AR-WF-06)

**Given** two contributes that collide on `(point, qualified_id)`
**When** enable is attempted
**Then** enable refuses
**And** the previous roster stays consistent. (FR-WF-09; SCN-0022)

**Given** a successful enable
**When** the roster publishes
**Then** `availability_revision` publishes atomically with the roster swap
**And** ContributionHits for those contributes appear on the next concatenate. (FR-WF-10; AD-30)

**Given** ranked/semantic/hybrid search
**When** requested on this path
**Then** it is `unsupported-capability` (GAP-0073)
**And** v1 stays concatenate of live tuples. (Story 52.2)

### Story 53.3: Pin tuple, invoke revalidation, and disable yields tombstone

As an operator,
I want a pin of a ContributionHit to survive only while that exact published revision is live,
So that disable or uninstall cannot silently retarget me to another version.

**Traceability:** FR-WF-07, FR-WF-08, FR-WF-11, SCN-0018, NFR-WF-14 (A4).

**Acceptance Criteria:**

**Given** a live `ContributionHit` from Story 53.2
**When** a caller pins it
**Then** the pin stores `(qualified_id, package_version, availability_revision)`
**And** it does not store a descriptor digest or an fp1. (FR-WF-07; cheap-veto A4; SCN-0018)

**Given** that pin
**When** invoke (or pin revalidation) runs
**Then** the host revalidates against the live published roster and `availability_revision`
**And** a matching live tuple may proceed to grant checks (Story 54 / 55) — the pin alone is not a grant. (FR-WF-08; FR-WF-06; SCN-0018 Then 1–2)

**Given** the contributing plugin is disabled or uninstalled (or the contribution leaves the live roster)
**When** a later invoke targets the same pin tuple
**Then** the result is typed `unavailable` or `tombstone`
**And** the pin does not resolve to another `package_version`, another contribution, or a stale fp1. (FR-WF-08; SCN-0018 Then 3; Branch A forbidden)

**Given** in-flight work already pinned to an instance
**When** uninstall names dependants and `pin_leases`
**Then** that work keeps the bytes it started with
**And** GC is eligible only when `pin_leases` is empty and no dependant remains. Side-by-side versions remain allowed. (FR-WF-11; RC-14; SCN-0018 Then 4)

**Given** SCN-0018
**When** this story is accepted
**Then** every Then branch of that scenario holds
**And** implementing a Failure branch (silent retarget, hit-as-grant, ContributionHit as fp1, claiming implemented at `270e992`) fails the story. (AR-WF-07)

### Story 53.4: A hit is not a grant; listings distinguish published from healthy

As a Quant or copilot author,
I want discovery listings to say whether a contribution is published, configured, granted, reachable, and healthy,
So that seeing a hit cannot be mistaken for permission to invoke.

**Traceability:** FR-WF-06, FR-WF-12, FR-WF-04, FR-WF-05, UX-DR-WF-01.

**Acceptance Criteria:**

**Given** a published `ContributionHit`
**When** a skill, listing, or copilot prose describes it
**Then** publishing or discovering the hit does not authorize invoke
**And** treating the hit as a grant is forbidden (SCN-0018 Branch B). (FR-WF-06; AD-9)

**Given** discovery listings
**When** they render contribution status
**Then** they distinguish **published** vs **configured** vs **granted** vs **reachable** vs **healthy**
**And** a ContributionHit is not a grant even when published and healthy. (FR-WF-12; AD-15)

**Given** `view:*` presentation DTOs
**When** they appear on the wire
**Then** they are AD-17 wire DTOs only
**And** they are not a plugin contribution point and not a `ContributionHit` until a named GAP-0081 `ui_view` increment. (FR-WF-12; UX-DR-WF-08)

**Given** Stage 0 hypotheses / `research_ref`
**When** federated Library search runs
**Then** they are not hits on this DTO
**And** occupancy on this path remains none. (FR-WF-04; FR-WF-05; Story 52.3)

**Given** session-granted `granted_ops`
**When** compared to pack enablement
**Then** they stay a separate AD-8 state
**And** this story does not mint `product_session` (Epic 55). (FR-WF-38 preview; AD-13)

---

## Epic 54: Every public call names its operation, grant, and retry identity

Every public operation publishes a complete versioned descriptor. Every public call carries an InvocationEnvelope that is revalidated against authoritative stores on every hop. Host grants are immutable GrantRecords; revocation is a separate append-only record.

**Factory touch ownership:** COMP-QMA-CORE (descriptor types / closed vocabularies) and COMP-QMA-WIRE (envelope + GrantRecord on additive CT-40). Must not rewrite Epic 41’s envelope families, Story 40.2 vocabularies, or Story 44.3 Tool Registry. Must not mint a new CT. Cheap-veto A3 covers the full field catalogue.

**Traceability:** FR-WF-14..FR-WF-26, UX-DR-WF-02, UX-DR-WF-07, NFR-WF-02, NFR-WF-05, NFR-WF-14, NFR-WF-16, GAP-0096.

**What must already exist:** FEAT-0041 / Epic 41; FEAT-0040 / Epic 40.

**What this delivers:** descriptors and envelopes specified on wire/core. FEAT-0053 waits on GrantRecords.

### Story 54.1: Versioned operation descriptor is complete and door-aware

As a pack author or host implementer,
I want every public operation to publish a complete versioned descriptor including supported doors,
So that callers cannot `execute(anything)` and unsupported doors cannot invent a new CLI.

**Traceability:** FR-WF-14, FR-WF-15, FR-WF-16, FR-WF-26, UX-DR-WF-02, NFR-WF-05.

**Acceptance Criteria:**

**Given** a public operation
**When** its descriptor is published
**Then** it includes `op_id`, `owner`, `version`, `input_schema`, `output_shape`, `input_cardinality`, `output_cardinality`, `empty_policy`, `configuration` (`defaults`, `required_keys`, `optional_keys`), `declared_operation_dependencies`, `resource_needs`, `documentation_refs`, `validation_class`, `units`, `compatibility`, `effect_class`, `permission_requests`, `placement`, `error_refusal_shape`, `progress`, `lifecycle_verbs`, and `supported_doors`
**And** CONTRACTS §1 is treated as the normative schema for this sitting (RC-16), not a fragment. (FR-WF-14)

**Given** cardinality
**When** it is declared
**Then** `input_cardinality` and `output_cardinality` are each `one` | `many`
**And** a single merged `cardinality` field is refused. Collection mapping is not on the descriptor (AD-5). (FR-WF-15)

**Given** closed vocabularies
**When** a descriptor is validated
**Then** `output_shape` ∈ `value` | `artifact_ref` | `job_handle` | `event` | `stream` (finite `event` ≠ persistent `stream`); `effect_class` ∈ `none` | `read` | `append-evidence` | `mutate-config` | `place-run` | `external-egress`; `placement` ∈ `local-library` | `daemon` | `worker` | `node`; `lifecycle_verbs` ∈ `start` | `query-state` | `cancel` | `await`
**And** `error_refusal_shape.codes` include at least `INVALID_INPUT`, `UNAVAILABLE`, `UNSUPPORTED_DOOR`, `STALE_OBSERVATION`, `GRANT_MISMATCH`. (FR-WF-15; FR-WF-16)

**Given** the door matrix
**When** it is recorded
**Then** it is keyed by `op_id` + `version`, not by owner
**And** unsupported door → typed `unsupported_door`; QMB remains the only operator CLI; QMA and QMN ship no operator CLI. (FR-WF-26; RC-17; SCN-0022 Then 4–5)

**Given** two operations of one component
**When** they advertise doors
**Then** they may differ
**And** an owner-wide matrix is a non-normative summary only. (CONTRACTS §15)

### Story 54.2: InvocationEnvelope is bound request context, not authority

As a host,
I want every public call to carry an InvocationEnvelope that is compared to authoritative stores on every hop,
So that a caller cannot label an external effect as `read` or pair a valid grant with another instance.

**Traceability:** FR-WF-17, FR-WF-18, FR-WF-21, FR-WF-25, NFR-WF-16.

**Acceptance Criteria:**

**Given** a public call (in-process, CLI, wire, or nested)
**When** it is dispatched
**Then** it carries `InvocationEnvelope` with `logical_invocation_id`, `attempt_id`, `op_id`, `op_version`, `contribution` (`qualified_id`, `package_version`), `instance_id`, `config_revision`, `caller_session_ref`, `callee_session_ref`, `grant_id`, `effect_class`, `idempotency_key`, `reconcile_policy`, `input_hash`, `parent_logical_invocation_id`, `call_depth`
**And** transport never bypasses that envelope. (FR-WF-17; FR-WF-25; cheap-veto A3)

**Given** that envelope
**When** each hop executes
**Then** the host resolves contribution, descriptor, and `GrantRecord` from authoritative stores, compares every bound field, and emits typed `stale` / `mismatch` / `GRANT_MISMATCH` before execution
**And** the envelope is signed/bound request context, not authority by assertion. (FR-WF-18; RC-03)

**Given** ambiguous `instance_id` or `config_revision`
**When** resolution is attempted
**Then** the call is a typed refusal
**And** it does not silently pick “latest.” (FR-WF-18; J12 forbidden latest-instance substitution)

**Given** `input_hash`
**When** it is computed
**Then** the preimage is canonical JSON of the `input_schema`-validated payload (sorted keys, no whitespace variance)
**And** secrets are never inlined. Concrete signature algorithm remains GAP-DESK-ENVELOPE-CRYPTO; mismatch refuse is still required. (FR-WF-21; NFR-WF-16)

**Given** inspect SHA `270e992`
**When** this story is accepted
**Then** tests prove the envelope on the wire after this story
**And** claiming Operation descriptor / InvocationEnvelope existed at that SHA fails the story. (GAP-0096; DEC-0450)

### Story 54.3: Idempotency domain, nested identity, and effect-specific outcomes

As a caller retrying a public operation,
I want idempotency and nested-call identity to be decidable,
So that a replay cannot duplicate an external effect and a child call cannot forge a parent.

**Traceability:** FR-WF-19, FR-WF-20, FR-WF-22.

**Acceptance Criteria:**

**Given** `idempotency_key`
**When** it is minted
**Then** the issuer is the **caller**
**And** uniqueness domain is `(principal, op_id, op_version, instance_id, config_revision, grant_id, target, canonical_input_hash)` with retention at least the journal lifetime of the invocation. (FR-WF-19; RC-04)

**Given** a collision with a different payload hash
**When** the same key is reused
**Then** the host returns a typed refusal
**And** replay of the same key within retention returns the prior result. (FR-WF-19)

**Given** a nested public call
**When** it is dispatched
**Then** it carries `parent_logical_invocation_id` and `call_depth`
**And** child `logical_invocation_id` derives from `(parent_logical_invocation_id, call_depth, child_op_id, child_canonical_input_hash)`. Nested invocation does not union permissions. (FR-WF-20; AD-10)

**Given** `effect_class`
**When** retry/reconcile is considered
**Then** `none`/`read` may retry; `append-evidence` dedupes on the key; `mutate-config` is CAS on `config_revision`; `place-run` treats `logical_invocation_id` as run identity; `external-egress` MUST obtain a receipt or become `unknown` and MUST NOT blind-retry
**And** `reconcile_policy` ∈ `query-then-decide` | `unknown-manual` | `never-retry`. (FR-WF-22; SCN-0021 Then 3)

### Story 54.4: GrantRecord is immutable; revocation is a separate record

As a host granting an operation to a product session,
I want minted grants to stay immutable and revocation to be append-only,
So that an upgrade cannot silently widen a grant and in-flight accepted work has a defined evaluation moment.

**Traceability:** FR-WF-23, FR-WF-24, FR-WF-25, FR-WF-30.

**Acceptance Criteria:**

**Given** a host grant
**When** it is minted
**Then** `GrantRecord` includes `grant_id`, `principal`, `audience`, `contribution` (`qualified_id`, `package_version`), `instance_id`, `config_revision`, `op_id`, `op_version`, `effect_class`, `parameter_ceiling.allow_keys`, `account_scope` (null unless granted), `expires_at`
**And** `revoked_at` is **not** a GrantRecord field. (FR-WF-23; RC-05)

**Given** revocation
**When** it occurs
**Then** an append-only `GrantRevocation` `{grant_id, revoked_at, principal, reason}` is recorded
**And** the minted GrantRecord bytes do not change. (FR-WF-24)

**Given** evaluation moments accept, dispatch, nested call, retry, external commit
**When** a grant is revoked or past `expires_at`
**Then** already-accepted work may finish under the grant that accepted it
**And** new dispatch is refused. (FR-WF-24)

**Given** upgrade, re-resolution, or a new package version
**When** an existing grant is considered
**Then** it cannot widen or retarget without an explicit re-grant that bumps `context_revision`
**And** manifests still only **request** — the host **grants**. (FR-WF-24; FR-WF-25)

**Given** `product_session.granted_ops` (Epic 55)
**When** it is specified in this story’s types
**Then** it stores `grant_id`s, not bare op-id strings
**And** this story does not mint `product_session` rows (Epic 55). (FR-WF-30)

---

## Epic 55: A product session owns context and grants; a tab owns nothing

The operator can open a `psess:` product session whose profile is `authoring` or `app-use` (immutable at create), mutate it under compare-and-set, and see copilot tools as the intersection of published ContributionHits, host grants, session GrantRecords, and health. App-use may mint a change-request; it cannot apply.

**Factory touch ownership:** COMP-QMA-DAEMON journal projection `product_session` plus GrantRecord rows beside it; COMP-QMA-WIRE CAS command shapes. Must not fold into QMA Session `sess:` (Story 45.5). Must not add a new sqlite class (NFR-WF-04). Must not confuse change-request with Story 47.3 RefinementProposal.

**Traceability:** FR-WF-27..FR-WF-38, UX-DR-WF-04, UX-DR-WF-06, NFR-WF-04, NFR-WF-13, SCN-0019, GAP-0093.

**What must already exist:** FEAT-0052 / Epic 54; FEAT-0042 / Epic 42.

**What this delivers:** `psess:` CAS and grant intersection. The apply fixture is Epic 58.

### Story 55.1: product_session is a journal projection with psess: ids

As an operator,
I want a product session record distinct from a QMA Session,
So that app-use and authoring can own context without pretending a tab is a session.

**Traceability:** FR-WF-27, FR-WF-28, FR-WF-29, FR-WF-31, NFR-WF-04.

**Acceptance Criteria:**

**Given** a product session
**When** it is minted
**Then** its id is `psess:` and is not a QMA Session `sess:` id
**And** cardinality is 1 product_session → many QMA Sessions. Current `sess:` attachment is a **query**, not a durable field. (FR-WF-27; Story 45.5)

**Given** the durable record
**When** it is persisted
**Then** it is a journal-derived projection on the existing daemon sqlite (not a new store class) with fields `product_session_id`, `profile`, `principal`, `context_revision`, `app_instance_id`, `granted_ops`, `selected_refs`, `account_scope`, `resume_cursor`, `cursor_generation`
**And** `scope_path` does not gain a segment. (FR-WF-28; NFR-WF-04; AD-8)

**Given** `profile`
**When** the session is created
**Then** it is `ProductSessionProfile` ∈ `{authoring, app-use}`, immutable at create
**And** it is not `qma.core.ontology.Profile`. (FR-WF-29)

**Given** `selected_refs`
**When** they are stored
**Then** allowed kinds are artifact fp1, `research_ref`, contribution `(qualified_id, package_version)`, template `(qualified_id, version)`, dataset/run/attempt refs, and node-id sets citing a template
**And** layout JSON, positions, widgets, and json-render trees are refused. Board layout is client-only (AD-4). (FR-WF-31)

**Given** inspect SHA `270e992`
**When** this story is accepted
**Then** tests prove `product_session` after this story
**And** claiming it existed at that SHA fails the story. (GAP-0093; SCN-0019 Branch E)

### Story 55.2: Mutations are CAS; reconnect does not replay intent

As a client that dropped and reattached,
I want compare-and-set mutations with durable command ids,
So that a reconnect cannot replay unacked intent and a tab switch writes nothing.

**Traceability:** FR-WF-32, FR-WF-33, UX-DR-WF-06, SCN-0019 Then 6.

**Acceptance Criteria:**

**Given** `mutate(product_session_id, expected_revision, command_id, payload)`
**When** it runs
**Then** results are `ok` | `conflict` | `duplicate` | `in_progress`
**And** `command_id` namespace is `(product_session_id, principal, command_id)` with retention equal to the session journal lifetime. Collision with a different `payload_hash` refuses. (FR-WF-32; RC-11)

**Given** `duplicate`
**When** it is returned
**Then** it carries the prior durable result
**And** `in_progress` carries the still-open attempt identity. Queries do not bump `context_revision`. (FR-WF-32)

**Given** reconnect
**When** the client resumes
**Then** it is a query from `(resume_cursor, cursor_generation)`
**And** it never re-issues unacked intent without the original `command_id`. Compacted history past the cursor yields snapshot/resync with a new `cursor_generation` — never a silent empty replay. (FR-WF-33; UX-DR-WF-06)

**Given** a UI tab change
**When** it occurs
**Then** it writes nothing
**And** sessions own context and grants; tabs do not. Closing a tab cancels nothing (Story 32.2). (FR-WF-33; SCN-0019 Branch D)

### Story 55.3: Copilot tools are the grant intersection

As a Quant using Copilot in a product session,
I want available tools to be the intersection of published hits, host grants, session GrantRecords, and health,
So that skill prose cannot authorize an operation.

**Traceability:** FR-WF-34, FR-WF-30, FR-WF-06, FR-WF-38, UX-DR-WF-04.

**Acceptance Criteria:**

**Given** tool availability
**When** it is computed
**Then** it is the intersection of (1) published ContributionHits, (2) host grants, (3) this `product_session`’s GrantRecords, and (4) health
**And** skills describe behavior; they do not grant. (FR-WF-34; AD-9; SCN-0019 Then 5)

**Given** `granted_ops`
**When** stored
**Then** they are `grant_id`s from Story 54.4
**And** not bare op-id strings. `account_scope` is null unless granted. (FR-WF-30)

**Given** pack enablement vs session grant
**When** both exist
**Then** installed ≠ enabled/activated ≠ session-granted
**And** a published package is not activation on a trading account. (FR-WF-38)

**Given** installation or upgrade of the app instance
**When** it runs
**Then** it MUST NOT mutate an existing row’s `granted_ops` or retarget `app_instance_id` as a side effect
**And** widening requires explicit re-grant. (FR-WF-35; SCN-0019 Then 3)

### Story 55.4: App-use mints a three-record change-request; it never applies

As an app-use operator,
I want to mint an immutable change-request after inspecting a run,
So that authoring plus an operator principal can apply a v2 without the app editing itself.

**Traceability:** FR-WF-35, FR-WF-36, FR-WF-37, SCN-0019.

**Acceptance Criteria:**

**Given** a `product_session` with profile `app-use`
**When** it requests a filter change
**Then** it may mint an immutable `ChangeRequest` with source `psess:`, source `instance_id`/`config_revision`, paired `{target_ref, base_hash}` records, `context_revision` at mint, typed patch, `copied_private_memory`, and `request_hash`
**And** it MUST NOT edit package source, install code, elevate grants, retarget accounts, or apply the request. (FR-WF-35; FR-WF-36; SCN-0019 Then 2)

**Given** `request_hash`
**When** it is computed
**Then** the preimage is canonical JSON over `(change_request_id, from_session, source_instance_id, source_config_revision, context_revision, app_instance, targets, patch, copied_private_memory)`
**And** no validation verdict and no apply evidence may enter the preimage. (FR-WF-37; RC-12)

**Given** validation
**When** authoring validates
**Then** a separate `ChangeValidationRecord` carries validator principal and verdict `conflict` | `rebase-required` | `valid`
**And** a separate append-only `ChangeApplyRecord` (authoring + operator principal) cites `request_hash`, applied base/result hashes, time, and outcome. Validation and apply never rewrite the request bytes. (FR-WF-36; SCN-0019 Then 1)

**Given** apply
**When** it is attempted from app-use
**Then** it is refused
**And** `promote` remains L17 and is not this path. Stale base hashes surface `conflict` / `rebase-required` — they do not apply. (FR-WF-37; SCN-0019 Branches A–C)

**Given** a new authoring session for the handoff
**When** it opens
**Then** it receives typed `selected_refs`
**And** not the app-use private transcript and not layout/widget trees. v1 instance, GrantRecords, and running jobs stay unchanged by the mint. (FR-WF-31; SCN-0019 Then 3–4)

**Given** Story 47.3 RefinementProposal
**When** compared
**Then** change-request is a distinct AD-22 staging kind `change_request`
**And** this story does not reuse RefinementProposal as the app-use path. (AR-WF-10)

---

## Epic 56: An illegal graph cannot register

Registration refuses self-loops and any directed cycle. Graph Template, Task Graph, Board layout, and Stage 0 `graph` stay distinct. Mapping is declared on edges; Cartesian requires an explicit flag.

**Factory touch ownership:** COMP-QMA-DAEMON / COMP-QMA-CORE `validate_graph_template_topology` (closes the reverse-edge-only hole under Story 43.3). Must not fingerprint templates onto the Artifact rail. Must not persist Board layout. Must not compile Stage 0 `graph` (DEC-0411).

**Traceability:** FR-WF-39..FR-WF-44, NFR-WF-01.

**What must already exist:** FEAT-0042 / Epic 42–43; FEAT-0037 / Epic 37.

**What this delivers:** illegal topologies refuse at registration. FEAT-0055 waits on it.

### Story 56.1: validate_graph_template_topology refuses any directed cycle

As a pack author registering a Graph Template,
I want registration to refuse self-loops and any directed cycle,
So that pairwise reverse-edge checks cannot let A→B→C→A through.

**Traceability:** FR-WF-40, FR-WF-39.

**Acceptance Criteria:**

**Given** Story 43.3’s reverse-edge refusal
**When** `validate_graph_template_topology` runs after this story
**Then** it refuses self-loops **and** any directed cycle (DFS / equivalent; pairwise reverse-edge checks are insufficient)
**And** a template `A→B→C→A` is refused. (FR-WF-40; AD-6; JOURNEYS high-risk)

**Given** a Runtime Loop
**When** topology is validated
**Then** the Loop remains node state
**And** it is not a template cycle. (FR-WF-40; Story 43.3)

**Given** a Graph Template that passes validation
**When** compile identity is recorded
**Then** it is `(qualified_id, version)` from the plugin manifest at enable
**And** rebuild-on-load MUST NOT change bytes of an enabled `(id, version)`; a byte change is a new version or a disable. (FR-WF-39)

**Given** inspect SHA `270e992`
**When** this story is accepted
**Then** tests prove full-cycle refusal
**And** claiming Story 43.3 already closed DAG law fails the story. (AR-WF-10)

### Story 56.2: Four layers stay distinct; Stage 0 graph is not a workflow

As an author,
I want Graph Template, Task Graph, Board layout, and Stage 0 `graph` to stay different kinds,
So that a mill hypothesis cannot silently become an executable procedure.

**Traceability:** FR-WF-41, FR-WF-43, FR-WF-44.

**Acceptance Criteria:**

**Given** Experimentation Board layout
**When** it is edited
**Then** it is client-only and writes nothing
**And** it MUST NOT be a field of `product_session`, Mission, Task Graph, Graph Template, or any sqlite row. (FR-WF-41; AD-4)

**Given** a Stage 0 `graph` (mill)
**When** a caller asks to compile it to a bot, Graph Template, or `run_slice`
**Then** it is refused
**And** DEC-0411 stays dead. (FR-WF-41; DEC-0451)

**Given** selected-subgraph execution
**When** it is requested
**Then** it is `MissionCompiler(template.qualified_id, template.version, node_ids)` where `node_ids` is a non-empty induced DAG of an already-registered template version
**And** it is not a live board scribble and not a board id. One compile → one Mission → one Task Graph whose `graph_template_ref` is the template `qualified_id`. (FR-WF-43)

**Given** a Graph Template
**When** identity is considered
**Then** it is not fingerprinted onto the Artifact rail
**And** ExperimentSpec successors remain lineage (CT-07 MUST NOT be walked as control-flow — Story 37.3). (FR-WF-44)

### Story 56.3: Mapping is explicit on edges; no silent Cartesian

As a workflow author,
I want each edge to declare its mapping,
So that zip vs broadcast vs keyed-join vs Cartesian cannot be guessed from JSON shape.

**Traceability:** FR-WF-42.

**Acceptance Criteria:**

**Given** a Graph Template edge
**When** it is registered
**Then** each port declares kind `reference` | `data` | `event` | `control`
**And** collection mapping on the edge is `one` | `zip` | `broadcast` | `keyed-join` | `cartesian`. (FR-WF-42; AD-5)

**Given** Cartesian mapping
**When** it is used
**Then** it requires an explicit flag
**And** silent Cartesian is refused. (FR-WF-42)

**Given** empty collections
**When** they arrive
**Then** skip or refuse follows the operation’s declared `empty_policy`
**And** conditional skip is a node kind, not dropped edges. Join algebra details wait on Story 57.4. (FR-WF-42)

---

## Epic 57: Completing A cannot forget B, and a handle never says succeeded

Task Graph edges and the AD-26 outbox persist in daemon sqlite. Completing predecessor A and making successor B ready is one transaction. Crash recovery is at-least-once dispatch with exactly-once logical acceptance under the receiver ledger. JobHandle stays on QMA AD-17 vocabulary.

**Factory touch ownership:** COMP-QMA-DAEMON `task_graph_state` including edges and outbox. Must not invent a second scheduler. Must not merge Story 41.4 worker outbox with this machine. Must not add JobHandle states `succeeded` / `awaiting_approval`. Must not drop edges.

**Traceability:** FR-WF-45..FR-WF-53, NFR-WF-04, NFR-WF-10, SCN-0021, GAP-0095.

**What must already exist:** FEAT-0054 / Epic 56; FEAT-0042 / Epic 42; FEAT-0044 / Story 45.4; FEAT-0033 / Epic 36.

**What this delivers:** durable edges and outbox recovery. FEAT-0056/0057 wait on it.

### Story 57.1: Persist task_graph_state edges in daemon sqlite

As a daemon operator,
I want a Mission’s Task Graph to persist `edges: {from, to, mapping}`,
So that successors can be walked after restart instead of being dropped.

**Traceability:** FR-WF-45, FR-WF-51, NFR-WF-04.

**Acceptance Criteria:**

**Given** the named projection `task_graph_state`
**When** a Task Graph is instantiated from a DAG-valid Graph Template (Epic 56)
**Then** it persists `edges: {from, to, mapping}` in daemon sqlite
**And** nodes do not carry successor lists. Today’s in-memory store that drops edges is the hole this story closes. (FR-WF-45; GAP-0095; DEC-0450)

**Given** occupancy
**When** a run-step occupies
**Then** occupancy is existing `environment_lease` + Workbench AD-8 door law folded into `task_graph_state`
**And** it is not a separate table; QMB does not write daemon occupancy. (FR-WF-51; Story 36.5; Story 37.2)

**Given** a second scheduler
**When** proposed
**Then** it is refused
**And** RoutineScheduler / Mission Compiler remain the procedure runtime (AD-7). (FR-WF-45)

**Given** inspect SHA `270e992`
**When** this story is accepted
**Then** tests prove durable edges after this story
**And** class existence of TaskGraph types is not this story’s pass. (NFR-WF-13; DEC-0286)

### Story 57.2: One transaction publishes A-terminal, B-ready, and the outbox row

As a daemon recovering from a crash between A completing and B starting,
I want an outbox whose replay cannot create a second logical B,
So that completing A cannot forget B and restart cannot duplicate B.

**Traceability:** FR-WF-46, FR-WF-47, FR-WF-48, SCN-0021.

**Acceptance Criteria:**

**Given** predecessor A completing with successor B eligible
**When** the daemon commits
**Then** one sqlite transaction (1) persists A terminal, (2) persists successor eligibility at a revision, (3) writes an outbox row per newly ready successor
**And** there is no window where A is terminal and B is silently forgotten without an outbox row. (FR-WF-46; SCN-0021 Then 2)

**Given** an outbox row
**When** it is persisted
**Then** unique key is `(graph_run_id, successor_node_id, predecessor_revision, partition_id)`
**And** the row persists complete `target` + `envelope_hash` plus `logical_invocation_id`, `transport_state` (`pending` | `dispatched`), `acceptance_state` (`accepted` | null), `effect_state` (`effected` | null), `receiver_acceptance_id`. (FR-WF-47; RC-07)

**Given** dispatch vs acceptance vs effect
**When** they are recorded
**Then** they stay distinct
**And** the outbox alone does not prove exactly one logical successor effect. (FR-WF-48)

**Given** a crash between A’s terminal write (and outbox row) and B’s dispatch ack
**When** restart runs
**Then** unacked / `dispatched`-not-accepted rows replay (at-least-once dispatch)
**And** receiver dedupe on `logical_invocation_id` returns the prior durable result (exactly-once logical acceptance). (FR-WF-48; SCN-0021 Then 1; Branch A forbidden)

**Given** Story 41.4 remote-worker outbox
**When** compared
**Then** it remains a different noun
**And** this story does not merge the two outboxes. (extension table)

### Story 57.3: JobHandle keeps QMA AD-17 vocabulary exactly

As a supervisor watching a procedure step,
I want JobHandle states to stay the parent vocabulary,
So that timeout cannot be labeled `aborted` and no one can add `succeeded`.

**Traceability:** FR-WF-49, FR-WF-50, FR-WF-53, SCN-0021.

**Acceptance Criteria:**

**Given** a JobHandle
**When** its `state` is read
**Then** it is exactly `queued` | `running` | `done` | `failed` | `cancelled` | `aborted` | `unknown`
**And** never `succeeded`. `awaiting_approval` remains a Mission/Task gate, not a handle state. (FR-WF-49; Story 45.4; SCN-0021 Branch C)

**Given** timeout or lost supervisor
**When** the job is outstanding
**Then** the handle becomes `unknown` (non-terminal, holds `environment_lease`)
**And** it is never `failed` or `aborted`. `cancelled` is explicit cancel; `aborted` is known environmental non-completion. (FR-WF-50; SCN-0021 Then 4)

**Given** a cancel/complete race
**When** both land
**Then** the first durable terminal wins
**And** later commands are no-ops recorded against that terminal. (FR-WF-50)

**Given** handle inventory
**When** recorded
**Then** each handle records `logical_run_id`, `attempt_id`, and artifact inventory with completeness `complete` | `partial` | `missing` | `expired`
**And** `external-egress` without a receipt stays `unknown` (Story 54.3). (FR-WF-50; CONTRACTS §6)

**Given** a Skill
**When** it is considered as a workflow
**Then** Skills remain knowledge
**And** they never compile to Missions and never grant tools. (FR-WF-53)

### Story 57.4: Join algebra is bound to revisions and a total order

As a workflow author joining partitions after a restart,
I want join state to name its definition and a deterministic first-wins order,
So that replay cannot change who won.

**Traceability:** FR-WF-52.

**Acceptance Criteria:**

**Given** a join node
**When** `JoinState` is persisted
**Then** it binds `join_id`, `graph_run_id`, `node_id`, `edge_id`, `definition_revision`, `join_revision`, `mapping`, `expected_cardinality`, `duplicate_key_policy`, `first_wins_order`, `watermark` (`kind` ∈ `all-expected` | `timeout` | `failed-aggregation`, `cause`, `closed_at`), `partitions` (with `source_event_id`, `event_time`, `receive_time`, `result_identity`), and `late_events`
**And** it is not guessed from JSON shape. (FR-WF-52; RC-08)

**Given** `first-wins`
**When** concurrent arrival or replay occurs
**Then** total order is `(event_time, receive_time, source_event_id)`
**And** late arrival after watermark is `late` with evidence, not silently merged. (FR-WF-52)

**Given** partial retry
**When** failed partitions are re-invoked
**Then** the same join definition (`definition_revision` + `join_revision`) is used
**And** successful partition `result_identity` values are reused. (FR-WF-52)

---

## Epic 58: Four honesty proofs as thin fixtures

Thin fixtures prove the four (inventory: five) honesty oracles: Book/BMS regression and dummy `INVALID_INPUT`; ATC simulate with zero Book keys and a complete PolicyPair; RecipeDefinition identity distinct from release fp1; app-use change-request without self-apply; pack export scanner oracle and pin/invoke honesty. They do not close GAP-0098 and do not fill GAP-0081 chrome.

**Factory touch ownership:** fixtures spanning COMP-QMB (ATC evidence + recipes + Book regression), COMP-QMF-RISK (default shapes only), COMP-QML (authoring adopt), COMP-QMN (seat honesty even if this epic stays at simulate), COMP-QMA-DAEMON / COMP-QMA-WIRE (change-request + pack). Must not invent harness-engineering product surface. Must not weaken Epic 10 / FEAT-0029 tests.

**Traceability:** FR-WF-54..FR-WF-66, SCN-0019, SCN-0020, SCN-0022, NFR-WF-13, GAP-0097, GAP-0098.

**What must already exist:** FEAT-0051..0055, FEAT-0029, FEAT-0031.

**What this delivers:** specified fixtures for factory stories. FEAT-0057 trails the same envelopes.

### Story 58.1: Default Book path still compiles; dummy Book is INVALID_INPUT

As an operator on the default money path,
I want existing Book/BMS compile tests to keep requiring Book keys,
So that ATC and dummy Book cannot sneak in through `ResolvedRunConfig`.

**Traceability:** FR-WF-54, FR-WF-55, SCN-0020 Then 1/3, NFR-WF-14 (A1 class vs fields).

**Acceptance Criteria:**

**Given** `ResolvedRunConfig`
**When** it is validated / simulated
**Then** `book_fp1` / `bms_fp1` / `bot_fp1` / fragments remain **required**
**And** existing compile/fragment tests are not weakened to admit ATC or ungoverned through this type. (FR-WF-54; SCN-0020 Branch D forbidden)

**Given** dummy Book/BMS/CT-33 or dummy PolicyPair (identity / no-op / unlimited / pass-through / sentinel fps including `NULL_BOOK`, empty-object Book, fake `mis_ref: null`)
**When** compile, register, validate, simulate, or seat is attempted
**Then** the result is `INVALID_INPUT`
**And** L36 default chain bot → Book → BMS → operator remains the default money path (DEC-0448). (FR-WF-55; SCN-0020 Branch A)

**Given** `UngovernedWorkConfig` or sensing/research
**When** it is labeled ATC or a QMN seat
**Then** that label is refused
**And** sensing-only is not a seat and not class (2). (FR-WF-59 partial; SCN-0020 Branch B)

### Story 58.2: ATC simulate with zero Book keys and a complete PolicyPair

As an operator selecting an Alternative Trading Composition,
I want validate/simulate to accept a complete PolicyPair with Book keys absent,
So that the second composition is honest rather than a dummy Book.

**Traceability:** FR-WF-56, FR-WF-57, FR-WF-58, FR-WF-59, FR-WF-66, SCN-0020, NFR-WF-14 (A1).

**Acceptance Criteria:**

**Given** `AlternativeRunConfig`
**When** it is selected
**Then** Book/BMS/bot keys are **absent, not null**
**And** the payload carries `config_class=alternative`, `composition_fp`, `{policy_pair_id, policy_pair_version, policy_pair_hash}`, inline `policy_pair` snapshot (accounting + risk fields per CONTRACTS §11), `command` including `command_owner_epoch`, and authoritative host `admission`. (FR-WF-56; RC-01; RC-02)

**Given** PolicyPair identity
**When** hash is computed
**Then** preimage is accounting + risk fields with no secrets
**And** inline bodies are snapshots, never the sole identity. Selection, grants, simulation evidence, fencing, and CT-07 bind to `composition_fp` + `policy_pair_hash`. Field catalogue is cheap-veto A1 sitting machinery. (FR-WF-57)

**Given** `admission`
**When** produced
**Then** it is an authoritative **host** result: typed `verdict`, `checked_grant_ids`, health evidence/revision, paper refs, L17 promote ref, evaluator principal, `decided_at`, `observation_freshness`
**And** client booleans cannot authorize. Closed verdicts include `admitted_simulate` | `admitted_paper` | `admitted_live` | `not_promoted` | `refused`. Stale observations refuse. Live ATC without paper+L17 is `not_promoted`. (FR-WF-58; RC-02)

**Given** ATC selected
**When** QML / QMB / optional MIS / QMN consume it
**Then** they adopt it (they do not stay secretly Book-shaped)
**And** validate/simulate write QMB JSONL tagged `composition_class: alternative` plus CT-07 lineage to `policy_pair_hash`. Owner is COMP-QMB; QMF-RISK supplies default shapes only. QMB issues internal ATC-simulate tokens. QMN remains the only `qmf-venue` importer. (FR-WF-59; SCN-0020 desk-fix)

**Given** this fixture
**When** it passes
**Then** it does **not** close GAP-0098 / P2-INT-001 e2e adoption
**And** claiming ATC implemented at `270e992` fails the story. (FR-WF-66; SCN-0020 Branch E)

### Story 58.3: RecipeDefinition identity is not the release fingerprint

As an operator joining two CT-10 inputs without a bot,
I want the authored recipe identity to stay distinct from the output release fp1,
So that two runs of one definition cannot pretend to be two recipes.

**Traceability:** FR-WF-60, FR-WF-61, NFR-WF-14 (A5).

**Acceptance Criteria:**

**Given** a `RecipeDefinition`
**When** it is reviewed before a run
**Then** identity is `(recipe_def_id, recipe_def_version, recipe_def_hash)`
**And** the definition includes the full AD-31 catalogue (CONTRACTS §5): inputs with coverage/schema/roles/units/timezone/calendar/freshness/provenance/`entitlement_ref`/licensing/revision; transforms with alignment, `known_at_policy`, missing/late policy, adjustment; `split_policy`; `environment_pin`; `output_schema`; `output_completeness_enumeration`; `completeness_required`. (FR-WF-60; RC-15; cheap-veto A5)

**Given** `recipe_def_hash`
**When** computed
**Then** inputs are `(recipe_def_id, recipe_def_version, inputs[], transforms[], split_policy, environment_pin, output_schema, completeness_required)` after canonical JSON normalization
**And** display rename and runtime credential **values** are excluded; credentials appear only as typed refs. (FR-WF-60)

**Given** a run
**When** it completes
**Then** it produces a new output **release fp1** with CT-07 lineage binding definition id/version/hash, every concrete input revision, transform/environment/code pins, `run_id`, and completeness
**And** two runs of one definition are two releases, not two recipes. Display `recipe_id` is not identity. Provider ≠ venue. Preview ≠ export ≠ stream. (FR-WF-61; J06)

**Given** a non-trading output
**When** it is stored
**Then** it needs no CT-33 / Book / QMN wrap
**And** CT-06 recipe kind remains deferred. Not a Library kind. (FR-WF-61; AD-11 class 3)

### Story 58.4: App-use change-request fixture — v1 stays; app-use never applies

As an operator walking J01,
I want a fixture that mints, validates, and applies the three-record change path,
So that app-use cannot write package source and a stale base hash cannot apply.

**Traceability:** FR-WF-62, SCN-0019.

**Acceptance Criteria:**

**Given** Stories 55.1–55.4 types
**When** the J01 fixture runs
**Then** app-use mints `ChangeRequest`; authoring writes `ChangeValidationRecord`; operator+authoring writes `ChangeApplyRecord`
**And** v1 instance, GrantRecords, and running jobs are unchanged by the mint. (FR-WF-62; SCN-0019)

**Given** app-use attempting apply, grant widening, account retarget, or package-source edit
**When** the fixture exercises those branches
**Then** each is refused
**And** stale base hashes yield `conflict` / `rebase-required`. (SCN-0019 Branches A–C)

**Given** a tab switch during the fixture
**When** it occurs
**Then** it patches nothing
**And** reconnect does not replay unacked intent (Story 55.2). (SCN-0019 Branch D)

### Story 58.5: Pack lifecycle, export scanner oracle, and unsupported_door

As an operator installing a pack on a second QMX,
I want atomic roster publication and an independent export scan,
So that missing deps cannot warn-and-continue and `exports_secrets: false` cannot authorize export.

**Traceability:** FR-WF-63, FR-WF-64, FR-WF-65, FR-WF-26, SCN-0022, SCN-0018.

**Acceptance Criteria:**

**Given** pack states `downloaded` → `installed` → `validated` → `enabled` ⇄ `disabled` → `uninstalled`
**When** a transition runs
**Then** it is journaled as `PackTransition` with CAS on `roster_generation`
**And** roster publication is atomic (stage, fsync, swap) and publishes `availability_revision`. Failed validation/migration/partial install restores the last usable roster. Missing dependency is a **hard error at enable**. (FR-WF-63; SCN-0022 Then 1; Branch A forbidden)

**Given** a migration
**When** it runs
**Then** `mode` ∈ `down` | `forward_only`; `phase` ∈ `prepare` | `commit` | `rollback`
**And** failed prepare/commit restores the last usable roster or records `recovery: "forward_only"` with operator confirmation. Uninstall names dependants; in-flight pin leases keep started bytes (Story 53.3). (FR-WF-64; RC-14)

**Given** export
**When** it is attempted
**Then** an independent versioned `ExportScanReport` is the oracle: threat model bounded to `secret_values` / `private_paths` / `transcripts`; detectors, coverage, typed findings, rewrite map, post-rewrite hash/signature; `result` ∈ `fail-closed-pass` | `fail-closed-fail`
**And** manifest `exports_secrets: false` without a passing scan is **not** evidence. Incomplete coverage or unhandled finding → `fail-closed-fail`. (FR-WF-65; SCN-0022 Then 3; Branches B–C forbidden)

**Given** an operation invoked through an unsupported door
**When** the fixture runs
**Then** the result is typed `unsupported_door`
**And** no `qma`/`qmn` operator CLI is minted. Behaviour of a supported `op_id` is identical across its supported doors (Story 54.1). QMB remains the only operator CLI. (FR-WF-26; SCN-0022 Then 4–5; Branch D forbidden)

**Given** a ContributionHit from the enabled pack, then disable
**When** invoke revalidates
**Then** `unavailable` / `tombstone`, never another version (Story 53.3 / SCN-0018)
**And** four composition modes (consume fp1; invoke through envelope; Graph Template coordinates two apps; composite cites contribution ids) remain available without core edits. (SCN-0022; J12)

---

## Epic 59: Safety fixtures against the same envelopes

Safety fixtures trail Epic 58 so failure modes are checked against the same envelopes. Inventory floor is **at least two** of the five candidates; this epic specifies all five so factory coverage is complete. Do not invent GAP-0100 readiness-dashboard chrome. Do not treat mutmut as architecture proof.

**Factory touch ownership:** COMP-QMN (fencing), COMP-QMA-DAEMON (outbox restart), COMP-QMB (streams wrap), COMP-QMA-WIRE (grant mismatch). Must not fill GAP-0100. Must not reopen GAP-0058.

**Traceability:** FR-WF-67..FR-WF-74, NFR-WF-07, NFR-WF-10.

**What must already exist:** FEAT-0055 / Epic 57; FEAT-0056 / Epic 58.

### Story 59.1: Stream cancel releases one lease; cutover needs ack

As two consumers of one tick subscription,
I want cancelling A to leave B running and cutover to require an explicit ack,
So that a shared feed cannot die with one client and replay cannot authorize a live command.

**Traceability:** FR-WF-67, FR-WF-68, J17.

**Acceptance Criteria:**

**Given** a `StreamSubscription` with two live leases
**When** consumer A cancels
**Then** A’s lease is released; derived `refcount` decrements; consumer B continues
**And** the shared feed stays until live leases are empty. `refcount` is never a bare independently written counter. (FR-WF-67; RC-10)

**Given** subscription fields
**When** recorded
**Then** they include `sub_id`, `channel`, `source_id` (provider), optional `venue_id` (never the same field), `epoch`, `sequence_domain`, `phase` ∈ `replay` | `cutover` | `live`, `cutover_watermark`, durable cursor, `backpressure_policy` ∈ `block` | `disconnect` | `spill-with-evidence`, and lease identities with expiry
**And** records split into `StreamSubscription`, `StreamDataEvent`, and control events `gap` | `duplicate` | `late` | `heartbeat` | `loss` | `cutover-ack` | `lease-expire`. (FR-WF-67; FR-WF-68)

**Given** replay reaching `cutover_watermark`
**When** cutover runs
**Then** barrier + `cutover-ack` are required before `live`
**And** missing watermark holds/refuses in `cutover`. Replay provenance cannot authorize a live command. A stream subscription is not trading permission. (FR-WF-68; J17)

### Story 59.2: Outbox restart fixture — one logical B after crash

As a daemon operator,
I want a crash-restart fixture on the Story 57.2 machine,
So that at-least-once dispatch and exactly-once acceptance are proven against the Epic 58 envelopes.

**Traceability:** FR-WF-69, SCN-0021 J27.

**Acceptance Criteria:**

**Given** Stories 57.2 and 54.2
**When** the fixture crashes the daemon between A terminal+outbox and B dispatch ack, then restarts
**Then** unacked rows replay and B is accepted exactly once logically
**And** a second logical B for the same `logical_invocation_id` fails the fixture. (FR-WF-69; SCN-0021 Branch A)

**Given** an `external-egress` whose acknowledgement is lost (J26)
**When** the caller retries with the same `logical_invocation_id`
**Then** state is `unknown` until reconcile
**And** the second attempt does not duplicate the side effect. (FR-WF-22; SCN-0021 Then 3)

### Story 59.3: UNKNOWN blocks handover; unknown-blocked is terminal for the attempt

As an operator replacing a live composition,
I want UNKNOWN orders to stop the fencing attempt,
So that dual writers and automatic retry cannot open a second command owner.

**Traceability:** FR-WF-70, FR-WF-71, SCN-0020 Then 5, NFR-WF-14 (A2).

**Acceptance Criteria:**

**Given** fence key `(account, venue, role)`
**When** sequential handover runs
**Then** happy path is `idle` → `drain-requested` → `draining` → `residuals-attributed` → `predecessor-acked` → `fenced-activate` → `active` → `retired`
**And** one command owner per key. State enum is cheap-veto A2 sitting machinery. (FR-WF-70; FR-WF-71)

**Given** UNKNOWN orders during drain/residual attribution
**When** they are observed
**Then** the attempt enters `unknown-blocked`
**And** that is a **terminal branch of this attempt** — it does not continue to `predecessor-acked`. Operator reconcile mints a **new** `attempt_id` / epoch with immutable evidence — never an automatic retry. (FR-WF-70; RC-06; SCN-0020 Then 5)

**Given** the deploy payload
**When** recorded
**Then** it includes `from_composition_fp`, `to_composition_fp`, `composition_class`, `account_id`, `venue_kind`, `role`, `command_owner_epoch`, `attempt_id`, `machine_revision`, `fencing_token` unique under account/venue/role/epoch, `issuer`, snapshots with `snapshot_id`, `residual_disposition` ∈ `flatten` | `transfer-to-successor` | `hold-manual`, `predecessor_ack`, timeout/escalation, `cas_guard`, `completion_evidence`
**And** QMN issues venue tokens; QMB issues internal ATC-simulate tokens. (FR-WF-71; CONTRACTS §10)

**Given** GAP-0100 readiness dashboard chrome
**When** proposed as this story
**Then** it is refused
**And** AD-25 fencing stays the transition machine. (FR-WF-74)

### Story 59.4: Stale predecessor restart is refused; rollback cannot unfill

As an operator whose old process restarts after fenced activate,
I want that restart refused without the current token,
So that software rollback cannot unwind fills.

**Traceability:** FR-WF-72, SCN-0020 Then 5.

**Acceptance Criteria:**

**Given** a new command-owner epoch and token after `fenced-activate`
**When** the predecessor process restarts presenting a stale epoch or token
**Then** it is refused
**And** CAS guards refuse mismatched epoch/token. (FR-WF-72; RC-06)

**Given** a new-owner fill
**When** software rollback is attempted
**Then** it cannot unfill
**And** outstanding positions, UNKNOWN commands, and shared-account concurrency remain separate refusal/drain cases. GAP-0058 stays its own increment. (FR-WF-72; AD-14)

### Story 59.5: Grant refuses the wrong instance or config revision

As a host dispatching an envelope,
I want a grant bound to instance and config to refuse a different target,
So that a valid grant cannot be pointed at another instance.

**Traceability:** FR-WF-73, FR-WF-18.

**Acceptance Criteria:**

**Given** a GrantRecord bound to `instance_id` / `config_revision` (Story 54.4)
**When** an InvocationEnvelope cites a different instance or config
**Then** the host returns typed stale/mismatch / `GRANT_MISMATCH` before execution
**And** it does not silently retarget. (FR-WF-73; RC-03)

**Given** FR-WF-74
**When** this epic is accepted
**Then** at least two of Stories 59.1–59.5 pass as fixtures (this file specifies all five)
**And** mutmut score is not architecture proof; GAP-0100 chrome is not shipped. (FR-WF-74; NFR-WF-07)

---

## Final validation (Step 4)

- **FR coverage:** FR-WF-01..74 each appear in the coverage map and in at least one story AC.
- **UX-DR coverage:** UX-DR-WF-01, 02, 04, 05, 06, 07 appear in stories. UX-DR-WF-03 and UX-DR-WF-08 are explicitly out (GAP-0081 / AD numbering collision).
- **Starter template:** none. Epic 53 Story 53.1 extends the existing CT-40 family; it does not scaffold a new distribution.
- **Entities:** journal projections created in the first story that needs them (`product_session` in 55.1; outbox rows in 57.2; GrantRecord in 54.4). No upfront Workflows database. No new sqlite class (NFR-WF-04).
- **Forward dependencies:** none inside an epic. 53.2 uses 53.1; 53.3 uses 53.2; 53.4 uses 53.1–53.3. 54.2 uses 54.1; 54.3–54.4 use 54.2. 55.2–55.4 use 55.1. 56.2–56.3 use 56.1. 57.2 uses 57.1; 57.3–57.4 use 57.1–57.2. 58.* are independent fixtures on prior epics. 59.* are independent fixtures on 57–58.
- **Epic independence:** Epic 53 is valuable without 54 (honest discovery + tombstone). Epic 54 is valuable without 55 (descriptors/envelopes/grants without sessions). Epic 55 needs 54’s GrantRecords (declared blocker). Epic 56 is valuable without 57 (illegal graphs refuse even if edges are still in-memory). Epic 57 needs 56’s DAG validity (declared blocker). Epic 58 needs 53–57 plus Book/node parents (declared). Epic 59 needs 55–58 envelopes (declared).
- **File churn:** 53+54 share COMP-QMA-WIRE **intentionally** (hit DTO vs envelope/grants — different type systems; consolidating would mix discovery identity with invocation authority). 55+57 share COMP-QMA-DAEMON **intentionally** (session projection vs task_graph_state — NFR-WF-04 closed list, different records). Consolidation of 56+57 was considered and rejected: topology validation is a genuine risk boundary from durable outbox. 58+59 share fixture packages by design (proofs then safety).
- **Architecture:** reuse-only; no new COMP; no new CT; GAP-0081 chrome / GAP-0058 / GAP-0085 / GAP-0061 / GAP-0099 / GAP-0100 unfilled; dummy Book forbidden; sensing is not ATC; mill FEAT-0047 not started; FEAT-0001 not started.
- **Codex standing:** recheck returned repairs-required; desk-fix RC-01..RC-17 landed; stories implement repaired contracts; **do not claim Codex ratified AD-23..AD-31**.
- **Factory:** this document does not launch factory lanes. Implementation authorization remains factory-pipeline-only (DEC-0445). `main` moves only by the operator’s squash-merge click.
