# Stage 7 independent source-blind red-team re-review

Status: **PASS — NO OPEN DOCUMENTATION FINDINGS**

Verdict: the final corpus makes genuinely unresolved implementation work explicitly non-buildable and navigable, and the focused correction pass found **no remaining OPEN documentation defect**. The published ownership/topology graph is internally consistent for the attacked paths. No documentation defect is treated as a source gap.

Review posture: independent, source-blind engineer working from the final `docs/` corpus. After reading the Stage 7 role brief, I did not read transcripts, chunks, extractions, the ledger, gaps source, inventory, ratification packet, state, repository implementation artifacts, or any `_docwork/` artifact other than the prior version of this report.

Status meanings:

- **OPEN** — a present documentation defect requires correction.
- **RESOLVED** — the final docs remove the prior contradiction or navigation defect.
- **RESOLVED-AS-BLOCKED** — the source semantics are still missing, but the docs explicitly make the dangerous task non-buildable, non-releasable, and navigable to its GAPs. This status is never used for a documentation defect.

## Final counts

| Measure | Count |
|---|---:|
| Attacks completed | 7 / 7 |
| Stable findings assessed | 16 |
| OPEN — CRITICAL | 0 |
| OPEN — HIGH | 0 |
| OPEN — MEDIUM | 0 |
| RESOLVED | 10 |
| RESOLVED-AS-BLOCKED | 6 |

OPEN findings: **none**.

## Exact corpus inspected

Before the source-blind boundary began, I read these role instructions completely:

- `C:/Users/Mubarak/.agents/skills/documentation-factory/SKILL.md`
- `C:/Users/Mubarak/.agents/skills/documentation-factory/stages/07-review.md`

After that boundary, I inspected only the prior `_docwork/review-redteam.md` and the final `docs/` corpus. The corpus-wide pass read all **82** final files (**54 Markdown, 28 YAML**):

- Root: `docs/AGENTS.md`, `docs/changelog.md`, `docs/constitution.md`, `docs/gap-report.md`, `docs/glossary.md`, `docs/index.md`.
- Architecture: `docs/architecture/dependencies.yaml`, `docs/architecture/overview.md`, `docs/architecture/stack.md`.
- Components: `docs/components/calendar-feed.md`, `ctrader.md`, `dukascopy.md`, `object-storage.md`, `qmf-core.md`, `qmf-data-backup.md`, `qmf-data-ingest.md`, `qmf-data-store.md`, `qmf-data.md`, `qmf-indicators.md`, `qmf-registry.md`, `qmf-risk.md`, `qmf-structure.md`, `qmf-venue.md`.
- Contracts: every file from `docs/contracts/ct-01-money-quantity.yaml` through `docs/contracts/ct-26-store-backup-input.yaml` (all CT-01 through CT-26 files).
- Decisions: `docs/decisions/ADR-0001-authority-and-document-first.md` through `ADR-0011-deferred-consumer-products.md` (all 11 ADR files).
- Knowledge and registry: `docs/knowledge/traceability.md`, `docs/registry/variables.yaml`.
- Lenses: `docs/lenses/bugs/triage.md`, `docs/lenses/observability/logging-spec.md`, `docs/lenses/observability/metrics-and-alerts.md`, `docs/lenses/ops/incident-playbook.md`, `docs/lenses/ops/runbook.md`, `docs/lenses/performance/budgets.md`, `docs/lenses/security/security-model.md`, `docs/lenses/testing/fixtures-and-scenarios.md`, `docs/lenses/testing/test-strategy.md`.
- Scenarios: `docs/scenarios/SCN-0001-core-freeze-gate.md` through `SCN-0010-risk-boundary-conflicts.md` (all 10 scenario files).

Corpus checks independently confirmed: 82 files; no broken relative Markdown links; every file is reachable from `docs/index.md`; 98 unique DEC IDs (`DEC-0001`–`DEC-0098`), 49 unique GAP IDs (`GAP-0001`–`GAP-0049`), and 27 unique FEAT IDs (`FEAT-0001`–`FEAT-0027`) are represented in `docs/knowledge/traceability.md`; exactly 10 scenarios exist; all 14 component specs contain scenario backlinks.

The final focused correction pass semantically re-read: `docs/lenses/ops/runbook.md`; `docs/architecture/overview.md`; `docs/architecture/dependencies.yaml`; `docs/components/qmf-venue.md`; `docs/components/ctrader.md`; `docs/components/qmf-registry.md`; `docs/components/qmf-data.md`; `docs/components/qmf-structure.md`; `docs/components/qmf-indicators.md`; `docs/lenses/data/data-layer.md`; `docs/lenses/observability/logging-spec.md`; `docs/lenses/testing/test-strategy.md`; CT-01, CT-04, CT-06, CT-07, CT-12, CT-13, CT-16, and CT-18 through CT-21; plus the prior report. The corpus-wide link/count check again covered all 82 final docs files.

## Attack summary

| Attack | Concrete task attempted | Result |
|---|---|---|
| qmf-core change | Add an Instrument alias/rename without changing existing canonical identities; then trace every CT-01/CT-04 consumer affected by a Core change. | The change itself stops safely at SCN-0001 and GAP-0005/GAP-0007–0012. The consumer audit passes: Data carries CT-01/04 and CT-06/07 consistently, Structure carries CT-06, and the component, manifest, architecture, and data-lens views agree. |
| ingest/store/restore | Request corrected Dukascopy/calendar evidence through CT-15, normalize to CT-10, persist CT-11/CT-13, take CT-26 backup input, transfer CT-14, and attempt non-destructive recovery. Also trace the patched CT-13 producer topology. | The data and recovery semantics stop safely at their GAPs. The runbook routes the recorder through Data-Ingest rather than making it a CT-15 consumer; Registry's CT-13 role is consistently intended/unwired and CT-09 is explicitly not a journal. |
| venue outage/reconciliation | Submit one authorized command, lose acknowledgement, reconnect, reconcile, and prevent duplicate execution. | No submission is authorized and uncertainty is explicitly implementation-blocking. Every Venue↔cTrader diagram labels CT-18–20 reserved/unwired and CT-21 no-operation, while the component dependency graph has no active Venue→cTrader edge. |
| risk/paper-mode change | Move a live Book to paper while preserving open exposure, in-flight commands, account continuity, and human authority. | Safely non-buildable: CT-24 is evidence-only, has no active consumer, needs operator confirmation, and enumerates transition gaps. |
| test plan | Write executable acceptance tests for core compatibility, source correction/restore, uncertain venue submission, and paper transition. | Safely non-buildable. The docs explicitly distinguish a blocked specification from test-complete or releasable work; scenarios do not manufacture executable fixtures or passing behavior. |
| navigation/cross-references | Start at the docs-only front door, locate every component/contract/scenario and exhaustively resolve DEC/GAP/FEAT references and relative links. | Pass: index, traceability, gap catalog, 10-scenario bank, component backlinks, and relative links are complete under the checks above. |
| constitution-only safety | Use Constitution plus its required AGENTS entry point as the authority preflight for provisional contracts, live money, credentials, paper transitions, restore, and destructive actions. | Pass: provisional/GAP material grants no implementation or live authority; AGENTS makes the destructive/live gates and blocked-not-complete rule explicit. |

## Findings

### RT-001 — Core identity change remains intentionally non-buildable

- **Status:** RESOLVED-AS-BLOCKED
- **Severity:** HIGH (source risk; no open documentation defect)
- **Classification:** implementation-blocking source gaps, safely gated
- **Doc / section:** `docs/scenarios/SCN-0001-core-freeze-gate.md`; `docs/components/qmf-core.md` — Behavior, Configuration, Failure modes; CT-01 through CT-05; `docs/constitution.md` — L29; `docs/AGENTS.md` — Release gate.
- **Attempted task:** Add alias/rename support to Instrument while preserving prior CT-05 identities.
- **Forced assumption:** None is permitted. CT-03/CT-05 shapes, alias rules, canonical bytes, hashing, collision, versioning, compatibility, refusal, package layout, and tests remain null under GAP-0002, GAP-0005, and GAP-0009–0012.
- **Attack evidence:** SCN-0001 says implementation must stop before code or serialized data; AGENTS says blocked is not test-complete or releasable.
- **Suggested doc fix or new-gap need:** No new gap. Retain the freeze gate and resolve the cited existing GAPs before code is authorized.

### RT-002 — Registry's CT-02/CT-03/CT-04 Core consumption is aligned

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** `docs/components/qmf-registry.md` — Interfaces and Identity and registration; `docs/components/qmf-core.md` — Interfaces; CT-02, CT-03, CT-04; `docs/architecture/dependencies.yaml`; `docs/architecture/overview.md`.
- **Attempted task:** Trace Registry's migration/test blast radius for a Core time, identity, or refusal change.
- **Forced assumption:** None. All inspected graph surfaces now name Registry as a CT-02/CT-03/CT-04 consumer.
- **Suggested doc fix or new-gap need:** None for topology; underlying schemas remain gated by their existing GAPs.

### RT-003 — The runbook routes the standalone recorder through Data-Ingest

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected; separate CT-15 schema/source gaps remain safely blocked
- **Doc / section:** `docs/lenses/ops/runbook.md` — Operational units, “Standalone calendar recorder”; CT-15; Data-Ingest, Calendar Feed, and Data component specs; architecture overview.
- **Attempted task:** Implement the standalone calendar recorder's single bounded acquisition call without bypassing Data-Ingest or CT-10.
- **Forced assumption:** None. The runbook now says the application invokes a bounded Data-Ingest operation, does not consume CT-15 directly, and leaves the application-facing call unratified. Data-Ingest owns/calls CT-15 against Calendar and produces CT-10 to Data.
- **Attack evidence:** CT-15, the runbook, component specs, architecture, and test matrix agree on caller, provider, request/response, and Data's non-participation in CT-15.
- **Suggested doc fix or new-gap need:** None for topology. GAP-0028/GAP-0029 still govern the future application API, provider, legal posture, schedule, and retry behavior.

### RT-004 — Store-to-Backup is explicit but snapshot semantics remain blocked

- **Status:** RESOLVED-AS-BLOCKED
- **Severity:** CRITICAL (source risk; no open documentation defect)
- **Classification:** former topology defect corrected; implementation-blocking source gaps safely gated
- **Doc / section:** CT-26; `docs/components/qmf-data-store.md` — CT-26 behavior and FM-7; `docs/components/qmf-data-backup.md`; `docs/lenses/data/data-layer.md`; `docs/scenarios/SCN-0004-off-machine-backup.md`; dependency manifest and architecture overview.
- **Attempted task:** Capture a complete, consistent snapshot during concurrent writes and bind it to CT-14.
- **Forced assumption:** None is permitted. CT-26 now names Store as owner and Backup as consumer but explicitly leaves shape, completeness, consistency, concurrency, abort/cleanup, and manifest binding null.
- **Attack evidence:** Store must not describe CT-26 output as a complete snapshot; SCN-0004 stops before transfer/recovery claims.
- **Suggested doc fix or new-gap need:** No new gap. Resolve GAP-0020, GAP-0022, GAP-0026, and GAP-0027 before implementing snapshot capture.

### RT-005 — Operational recovery and cutover remain explicitly prohibited

- **Status:** RESOLVED-AS-BLOCKED
- **Severity:** CRITICAL (source risk; no open documentation defect)
- **Classification:** implementation-blocking source gap, safely gated
- **Doc / section:** CT-14 and CT-26; Data, Store, Backup, and Object Storage component specs; data layer; operations runbook; incident playbook; security model; SCN-0004.
- **Attempted task:** Recover a destroyed workstation/store into a clean target, verify cross-links, replay post-snapshot evidence, and cut over without overwriting the only good copy.
- **Forced assumption:** None is permitted. The docs distinguish off-machine transfer, routine restore verification, disaster recovery, operational recovery, and cutover, and state that no recovery/cutover may be implemented while GAP-0027 is open.
- **Suggested doc fix or new-gap need:** No new gap. GAP-0027 must ratify clean-target restore, compatibility, replay, validation, rollback, evidence preservation, authority, and cutover.

### RT-006 — Venue↔cTrader topology is unmistakably reserved/no-operation

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** `docs/architecture/overview.md` — C4 Level 1, C4 Level 2, Layer view, Runtime and data shape, and Component index; dependency manifest; Venue and cTrader specs; CT-18 through CT-21.
- **Attempted task:** Determine whether any QMX/QMF-to-cTrader command/session or cTrader-to-QMF capability/event path is currently wired.
- **Forced assumption:** None. Every Venue↔cTrader diagram label now says CT-18–20 are reserved/unwired and CT-21 is no-operation; prose repeats that no live handoff exists. Venue's component and manifest `depends_on` lists omit cTrader, while cTrader has no dependencies.
- **Attack evidence:** CT-18/20 have empty active consumers, CT-19 has no caller/authorization owner, CT-21 is reserved-no-operation, and the diagrams no longer present those contracts without their state label.
- **Suggested doc fix or new-gap need:** None. GAP-0035–0039 remain the explicit non-buildable boundary for future wiring.

### RT-007 — Uncertain venue submission is safely non-buildable

- **Status:** RESOLVED-AS-BLOCKED
- **Severity:** CRITICAL (source risk; no open documentation defect)
- **Classification:** implementation-blocking source gap, safely gated
- **Doc / section:** `docs/components/qmf-venue.md` — FM-3 through FM-6; `docs/components/ctrader.md` — FM-4; CT-19/CT-20; SCN-0005; operations runbook and incident playbook.
- **Attempted task:** Recover after timeout following a possible submission, reconcile external state, deduplicate late events, and decide whether new commands may resume.
- **Forced assumption:** None is permitted. GAP-0036 explicitly requires identities, complete states/transitions, readback/cursors, retry/duplicate rules, terminal/uncertain states, new-command gating, journal evidence, and human flattening authority before submission code exists.
- **Attack evidence:** SCN-0005 forbids submit, retry, success/failure inference, flatten, or resume; the incident playbook repeats the stop.
- **Suggested doc fix or new-gap need:** No new gap. Resolve GAP-0036/GAP-0038/GAP-0039 before assigning or building CT-19/20.

### RT-008 — Paper-mode transition is evidence-only and safely blocked

- **Status:** RESOLVED-AS-BLOCKED
- **Severity:** CRITICAL (source risk; no open documentation defect)
- **Classification:** former wiring ambiguity corrected; implementation-blocking source gaps safely gated
- **Doc / section:** CT-24; `docs/components/qmf-risk.md` — paper-mode behavior and FM-4/FM-5; ADR-0009; SCN-0006; AGENTS FEAT-0027 fence; security model.
- **Attempted task:** Move a live Book to paper while preserving open positions, in-flight commands, account binding, continuity, rollback, and human authority.
- **Forced assumption:** None is permitted. CT-24 has no active consumer, is explicitly evidence-only pending operator confirmation, and leaves states, triggers, account roles, atomicity, rollback, duplicate prevention, continuity, and audit unresolved.
- **Suggested doc fix or new-gap need:** No new gap. Resolve GAP-0018, GAP-0019, GAP-0039, and GAP-0041 and obtain operator confirmation before any transition implementation.

### RT-009 — CT-22 through CT-25 active/intended roles are explicit

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** CT-22 through CT-25; `docs/components/qmf-risk.md`; Registry and Data component specs; dependency manifest; security model; AGENTS FEAT-0027 fence.
- **Attempted task:** Plan Book charter registration, risk evaluation, mode evidence, and journal integration.
- **Forced assumption:** None. All four contracts have empty active consumer sets; intended targets are documentary only; CT-23 has no caller; CT-24 is evidence-only; CT-25 is not wired to Data; direct store writes are prohibited.
- **Suggested doc fix or new-gap need:** None for topology. Existing GAP-0039–0046 remain the non-buildable semantics boundary.

### RT-010 — The test plan explicitly distinguishes blocked from complete

- **Status:** RESOLVED-AS-BLOCKED
- **Severity:** HIGH (source/tooling risk; no open documentation defect)
- **Classification:** implementation-blocking source gaps, safely gated
- **Doc / section:** testing strategy — Test levels, contract matrix, completion rule; fixtures and scenarios — binding and scenario matrix; AGENTS — Release gate; all 10 scenarios.
- **Attempted task:** Implement executable acceptance tests for restore, uncertain submission, and paper transition.
- **Forced assumption:** None is permitted. Runner, commands, layout, runtime, schema-valid payloads, exact outputs, isolation, clocks, and fingerprints remain GAP-bound; the docs explicitly say a blocked scenario is not a passing test, test-complete, implementation-ready, or releasable.
- **Suggested doc fix or new-gap need:** No new gap. Resolve GAP-0001–0004 and each contract-specific gap before turning the blocked specifications into executable tests.

### RT-011 — Scenario bank and component backlinks exist

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** `docs/scenarios/SCN-0001-core-freeze-gate.md` through `SCN-0010-risk-boundary-conflicts.md`; Related sections of all 14 component specs; index; testing fixtures/scenarios lens.
- **Attempted task:** Follow exact Given/When/Then references for core, correction, backup, venue uncertainty, and paper mode.
- **Forced assumption:** None. Exactly 10 scenario documents exist, and all 14 component specs backlink to applicable scenarios. Unresolved values/actions are explicitly marked blocked rather than invented.
- **Suggested doc fix or new-gap need:** None.

### RT-012 — Docs-only navigation and exhaustive traceability pass

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** `docs/index.md`; `docs/knowledge/traceability.md`; `docs/gap-report.md`; ADRs; component Related sections.
- **Attempted task:** Navigate from the docs root to all files and resolve DEC/GAP/FEAT prerequisites without opening private provenance.
- **Forced assumption:** None. The index reaches all 82 files, no relative Markdown links are broken, and traceability exhaustively maps 98 DEC, 49 GAP, and 27 FEAT identifiers. FEAT-0027's operative safety fence is docs-local.
- **Suggested doc fix or new-gap need:** None. Out-of-corpus provenance may remain provenance, but must not become required normative context.

### RT-013 — Constitution and AGENTS carry the non-authorizing safety boundary

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** `docs/constitution.md` — L4, L17, L29; `docs/AGENTS.md` — Hard rules, routing, and Release gate; operations and security lenses.
- **Attempted task:** Determine whether provisional contracts, recommendations, or GAPs can authorize implementation, credential use, live orders, paper transitions, restores, destructive migrations, or incident actions.
- **Forced assumption:** None. Constitution L29 says provisional contracts/recommendations/GAPs grant no implementation, credential-bearing, live-money, or destructive-data authority; AGENTS makes the specific stop conditions and human-only boundaries explicit.
- **Suggested doc fix or new-gap need:** None.

### RT-014 — Roster role, kind, layer, and distribution are separate axes

- **Status:** RESOLVED
- **Severity:** MEDIUM (former defect)
- **Classification:** documentation defect corrected
- **Doc / section:** `docs/architecture/dependencies.yaml`; `docs/architecture/stack.md` — Component taxonomy and roster; `docs/architecture/overview.md` — C4 Level 2 and component index; Constitution L14.
- **Attempted task:** Scaffold distributions while preserving the fixed five-library/two-module public roster and internal seams.
- **Forced assumption:** None. The manifest separates `roster_role`, `kind`, `layer`, and `distribution`; distribution remains null under GAP-0002. Risk may have `kind: library` while its roster role is `public-module`; Data-Ingest may have `kind: middleware` while its roster role is `internal-seam`.
- **Suggested doc fix or new-gap need:** None for taxonomy. GAP-0002 must still settle package/import/distribution identities before scaffolding.

### RT-015 — Registry's CT-13 role is consistently intended/unwired

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected; CT-13 schema/handoff semantics remain safely blocked
- **Doc / section:** CT-13; Registry and Data component specs; dependency manifest; architecture overview; data-layer and logging lenses.
- **Attempted task:** Add Registry operational/research journal evidence without writing a private store or confusing Registry persistence with journal persistence.
- **Forced assumption:** None. Registry now declares CT-13 as `out (reserved)` toward intended Data, the manifest lists CT-13, and dotted architecture/data-lens edges mark the handoff intended/unwired. Registry does not acquire an active Data dependency.
- **Attack evidence:** Registry explicitly says CT-09 must not carry operational/research journal evidence and FM-7 rejects that confused-deputy path. CT-13 retains Data→Store as the only wired journal path.
- **Suggested doc fix or new-gap need:** None for topology. GAP-0025/GAP-0026 still govern the future producer/consumer handoff, failure, mutation, ordering, retention, and redaction semantics.

### RT-016 — Data and Structure interface topology is aligned

- **Status:** RESOLVED
- **Severity:** HIGH (former defect)
- **Classification:** documentation defect corrected; underlying schemas remain safely blocked
- **Doc / section:** CT-01, CT-04, CT-06, CT-07, CT-12, and CT-16; Core, Data, Registry, Indicators, and Structure component specs; dependency manifest; architecture overview; data-layer lens.
- **Attempted task:** Trace Data's blast radius for money/price/quantity and typed-refusal changes, then trace Data/Structure registration-lineage handoffs without accidentally activating reserved consumers.
- **Forced assumption:** None. Data lists CT-01/04/06/07 in its sources, interface table, manifest, local diagram, architecture overview, and data-layer ownership/topology. Structure lists CT-06 alongside CT-07/08 in its spec, manifest, and architecture view.
- **Attack evidence:** CT-12 has empty `consumers`/`active_consumers` and only intended Registry/Indicators/Structure consumers; those components do not claim CT-12 interfaces. CT-16 likewise has empty active consumers, names Structure only as intended, and Structure has no CT-16 interface or Indicators dependency. This prevents the interface repair from creating accidental active edges.
- **Suggested doc fix or new-gap need:** None for topology. GAP-0007/GAP-0011, GAP-0014/GAP-0015, GAP-0024, and GAP-0031–0033 still block the respective schemas and consumer wiring.

## Review verdict

The dangerous missing source semantics are now handled correctly: core changes, snapshot/recovery, uncertain submissions, paper transitions, and executable acceptance tests are explicitly non-buildable, non-operational, and non-releasable until their GAPs are ratified. Navigation, traceability, scenario coverage, authority boundaries, and roster taxonomy pass the source-blind attacks.

The source-blind adversarial documentation review **PASSES with zero OPEN findings**. RT-003, RT-006, RT-015, and RT-016 are corrected across their authoritative and local views, and the focused cross-effect checks found no accidental active CT-12, CT-16, or Venue→cTrader dependency.

This PASS does not authorize implementation of features marked RESOLVED-AS-BLOCKED. Core schemas, snapshots/recovery, uncertain venue submissions, paper transitions, and executable acceptance tests remain intentionally unavailable until their existing source GAPs are resolved and the documented human/live/destructive gates are satisfied.
