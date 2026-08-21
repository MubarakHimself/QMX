---
id: OPS-RUNBOOK-QMF-V1
title: QMF V1 Operations Runbook
type: runbook
status: ratified
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-STORE, COMP-QMF-DATA-BACKUP, COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, COMP-OBJECT-STORAGE]
decisions: [DEC-0001, DEC-0003, DEC-0004, DEC-0005, DEC-0008, DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0051, DEC-0052, DEC-0053, DEC-0059, DEC-0065, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0106, DEC-0112, DEC-0117, DEC-0118, DEC-0119, DEC-0121, DEC-0135, DEC-0136, DEC-0137, DEC-0138, DEC-0139, DEC-0141, DEC-0142, DEC-0143, DEC-0146, DEC-0147, DEC-0149, DEC-0150, DEC-0151, DEC-0152, DEC-0153, DEC-0155, DEC-0157, DEC-0158]
sources: [DEC-0001, DEC-0003, DEC-0004, DEC-0005, DEC-0008, DEC-0009, DEC-0030, DEC-0041, DEC-0045, DEC-0051, DEC-0052, DEC-0053, DEC-0059, DEC-0065, DEC-0096, DEC-0099, DEC-0100, DEC-0101, DEC-0102, DEC-0103, DEC-0106, DEC-0112, DEC-0118, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md, _docwork/gaps.yaml, docs/architecture/dependencies.yaml, docs/registry/variables.yaml, docs/contracts/ct-09-registry-persistence.yaml, docs/contracts/ct-11-evidence-persistence.yaml, docs/contracts/ct-13-journal.yaml, docs/contracts/ct-14-backup-restore.yaml, docs/contracts/ct-15-external-source-adapter.yaml, docs/contracts/ct-19-venue-command.yaml, docs/contracts/ct-20-venue-event.yaml, docs/contracts/ct-21-venue-secret-session.yaml]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# QMF V1 Operations Runbook

QMF V1 is design-only and has no ratified start, stop, restart, deploy, migration, rollback, or live-connection command. QMF is a reusable toolbox rather than an application runtime; this document records operational boundaries and the decisions still required before executable procedures can exist. [DEC-0008] [DEC-0009]

## Permission boundary

This runbook grants no permission to initialize the project, deploy code, access credentials, connect to a broker, submit an order, promote an artifact, change a Book mode, flatten exposure, or operate live money. Project initialization remains with operator tooling, and promotion into the live zone remains human-only. [DEC-0005] [DEC-0041]

Agents may inspect documented contracts, run already-approved read-only validation, and preserve evidence. Agents may not infer an operational command from a recommendation, a GAP, a study, or an external provider's examples. [DEC-0003] [DEC-0004]

## Environments and commands

| Operational need | Current procedure | Status |
|---|---|---|
| Supported runtime and host | CPython 3.14 is pinned across all packages, CI, and factory sandboxes; tier-1 targets are Windows 11 x86-64 and Ubuntu LTS x86-64; QMF stays pure-Python and OS-neutral (DEC-0099). | Ratified; other platforms work by construction but are untested in V1. |
| Workspace installation | One uv workspace repository with seven installable packages importing as the `qmf.*` PEP 420 namespace, `src/` layout, `uv_build` backend, one committed `uv.lock`, lockstep roster versioning (DEC-0100). | Ratified. |
| Local validation | Canonical commands `poe fmt | lint | types | test | check` (ruff format + lint, pyright strict, pytest); coverage floor 80% per package with 100% branch on CT-01/CT-02 primitive modules; every package ships executable tests and reference usage as tier-1 artifacts (DEC-0101, DEC-0096). | Ratified. |
| CI validation and release | Three quality tiers bound to factory events: tier 1 `poe check` on every work unit; tier 2 `poe check-integration` (adds integration + contract tests, each package in an isolated environment) on landing into the integration branch; tier 3 `poe check-release` (adds package builds + clean-install smoke on both tier-1 OSes) on ship; host-neutral until a CI remote exists (DEC-0102). Two version ladders: SemVer lockstep code packages and per-contract integer format versions (DEC-0103). | Ratified. |
| Start, stop, and restart | No QMF-wide operation exists because the libraries do not form a runtime; any process-specific command belongs to its owning application or the trading node, decided at the node/ops sitting (DEC-0008, DEC-0009). | Node/ops territory; not a foundation gap. |
| Deploy or rollback | No deploy target, artifact, command, or environment is ratified; QMF ships as installable packages, and deployment topology is a node/ops decision. Schema migrations run preflight → backup → dry-run → migrate → verify with a documented restore path (DEC-0118). | Deploy is node/ops; migration process ratified, per-schema steps per-contract. |

## Operational units

| Unit | What can be operated | What remains prohibited or unresolved |
|---|---|---|
| QMF libraries | Installed and invoked only after their package and contract gaps are ratified. | No application loop, scheduler, deployment service, or QMF-wide daemon exists. [DEC-0008] [DEC-0009] |
| `COMP-QMF-DATA-INGEST` | A bounded adapter invocation after source contracts are ratified. | Scheduling, process supervision, retries, and bulk acquisition are application-owned by ratified boundary (DEC-0119, AD-21); the news-provider legal archiving posture remains an open operator item, and cTrader tick specifics (trendbar price basis, daily boundary) are measured per broker at first connection under the verify-or-refuse suite (DEC-0135). |
| Standalone news-calendar recorder | A separate future application invokes a bounded Data-Ingest operation; Data-Ingest owns and calls CT-15 against the news-calendar provider (COMP-CALENDAR-FEED), then produces governed CT-10 input to Data. The application does not consume CT-15 directly. | The recorder keeps provider-native identity and revisions through idempotent intake (DEC-0119); the application-facing call, provider, schedule, and retries are application-owned and unratified, and the provider legal archiving posture remains an open operator item. [DEC-0052] |
| `COMP-QMF-DATA-STORE` | The store stack is ratified — Parquet, DuckDB, SQLite, JSONL behind QMF-owned contracts, no database server (DEC-0117) — and the migration process is preflight → backup → dry-run → migrate → verify (DEC-0118). | Per-schema column layouts, partition mechanics, and compaction are documentation-time detail; no store path or recovery procedure is invented, and no in-place mutation of the only copy. |
| `COMP-QMF-DATA-BACKUP` | Contract and provider-boundary design only. | GAP-0027 is answered: the backup design (nightly, encrypted, versioned, off-machine, with automated sample-restore tests and periodic full-restore rehearsal) is ratified under DEC-0118, so `registry:backup_cadence` is nightly; only the numerics `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, and `registry:restore_verification_cadence` stay null pending the node/ops sitting. [DEC-0118] |
| `COMP-QMF-VENUE` | The ratified venue-adapter contracts CT-18 (capability), CT-19 (command), CT-20 (event + reconciliation), CT-21 (secret/session); the adapter's connection manager is the sole owner of venue sessions and its `WriterId` (DEC-0136, DEC-0137, DEC-0138). | No live venue caller is assigned in QMF; the command caller is the account-facing risk layer — the Book owns the command path, the BMS supervises the account — ratified as **defined-unwired** surface (DEC-0143). No live connection, command, or flatten is buildable from these docs, and command retry is prohibited. The first-connection verification suite (below) is verify-or-refuse throughout; order-path internals and the trigger→level→effect matrix stay node/risk sitting territory, tracked in `tracker/trading-node-notes.md` (DEC-0142), while flatten authority is assigned and the adapter never initiates a flatten (DEC-0150). [DEC-0059] |
| `COMP-QMF-RISK` | Ratified, **defined-unwired** risk contracts on qmf-core nouns, composition-root mediated: CT-22 Book definition, CT-24 binding transition, CT-25 risk journal, CT-27 BMS definition, CT-28 binding, CT-29 exit record, CT-30 control action, CT-31 control window, CT-32 performance result. | The contracts have no active caller or consumer; CT-24 is evidence-only and CT-25 is not wired to Data. No risk evaluation, order authorization, exit action, Book transition, or live operation is implementation-ready from these docs — the design is ratified (DEC-0143 through DEC-0155) and implementation arrives only through the factory pipeline. A binding is admissible only where the venue's CT-18 declaration and its venue-observation profile satisfy the Book's declared required capabilities, checked at **bind time** (DEC-0143, DEC-0146). [DEC-0065] |

## Scheduled work

| Work | Schedule source | Operator boundary |
|---|---|---|
| Off-machine evidence backup | `registry:backup_cadence` records the ratified nightly cadence | The design (nightly, encrypted, versioned, off-machine, with sample-restore tests and full-restore rehearsal) is ratified; QMF provides the primitives while the schedule and execution are application/ops-owned, and encryption key custody plus numeric objectives are named at the node/ops sitting (DEC-0118). [DEC-0045] |
| Historical backfill | No recurring schedule is ratified. | qmf-data defines idempotent (source, source-native id, revision) intake and separately-identified tick sources (Dukascopy history vs broker feed); bulk acquisition is a first-install/operator action, scheduling application-owned (DEC-0119). [DEC-0051] [DEC-0053] |
| News-calendar recording | No registry schedule is ratified. | The standalone news-calendar recorder keeps provider-native identity and revisions through the idempotent intake; provider, schedule, and retries are application-owned, and the legal archiving posture remains an open operator item (DEC-0119). [DEC-0052] |
| Venue session duties | The adapter declares the duties; the application's scheduler drives them (DEC-0141). | Heartbeat (the ratified safe bound is 10 seconds, DEC-0135), token refresh, reconnect, gap replay, and verification monitors are **declared schedulable duties** — the adapter defines the work, the application runs it, and **session recovery never resubmits a command** (DEC-0141, DEC-0137). The scheduler itself is application/node territory. |
| Forward broker capture | Venue market data enters as CT-10/CT-15 source observations; no live account or supervisor is authorized here. | Which broker fronts the cTrader platform is deployment configuration, never architecture (DEC-0139); opaque `VenueId`/`AccountId` identity and account bindings suffice. No live command is buildable from these docs; the command caller is the account-facing risk layer, ratified as **defined-unwired** surface (DEC-0143). [DEC-0053] [DEC-0059] |

## Venue first-connection and session procedures

The venue-adapter contract is ratified (DEC-0138); these procedures are ratified design, and implementation authorization arrives only through the factory pipeline, never from this runbook. When any step runs in production, its scheduling and consequences are application/node/risk territory, tracked in `tracker/trading-node-notes.md` (DEC-0142).

### First-connection verification suite (verify-or-refuse)

The capability surface is two artifacts: a **static capability declaration** (importable without credentials, marked `static` or `measured-at-connection`) wired at construction, and a per-`(VenueId, account)` **venue-observation profile** produced post-connect by the verification suite before the first command and before any evidence-bearing decode (DEC-0138). The suite is a named contract part and is **verify-or-refuse throughout** — a `measured-at-connection` capability is `unavailable dependency` until its profile exists:

| Verification | Rule | Refusal on failure |
|---|---|---|
| Spot-timestamp unit | Assert milliseconds by magnitude at first connection (the unit is undocumented, DEC-0135). | An unverified spot-timestamp unit refuses spot evidence. |
| Daily-boundary measurement | Derive the actual daily-bar boundary from the venue's own timestamps per broker; once measured and verified, mint it as a **venue-scoped market-hours calendar identity**, giving venue-native bars a legal BarSpec anchor (DEC-0135, DEC-0138). | An unmeasured daily boundary leaves venue daily bars **ungoverned**, never assumed aligned to QMF's forex 17:00-NY calendar. |
| Bar-basis reconciliation | Reconcile trendbar OHLC against explicitly-BID/ASK tick history per broker and symbol class; record the verified quote side (DEC-0135). | A failed bar-basis reconciliation refuses bar evidence. |
| Pip-formula validation | Validate `pipSize = 10^-pipPosition` against known symbols at first connection (DEC-0135). | A failed pip-formula validation refuses metadata-derived parameters. |
| Money exponent | Require the per-message `moneyDigits` exponent before decoding money (DEC-0135). | An absent money exponent refuses that message's money decode — never a default to 2. |

Measurements and verification verdicts journal as `data quality` events (DEC-0138).

### Session duties

The adapter's periodic session duties are **declared schedulable work the application's scheduler drives** — the adapter defines the work, the application runs it (DEC-0141): heartbeat (the ratified safe bound is 10 seconds, DEC-0135), token refresh, reconnect, gap replay, and verification monitors including the continuous daily-boundary monitor. **Session recovery never resubmits a command**, and command retry is prohibited — retryability rides typed refusals (DEC-0141, DEC-0137). Retry, pool, and deadline constants are do-not-default node values.

### Warm-up rider

The operator's rider is a **~1-week warm-up/observation period before live trading** (DEC-0135). This runbook authorizes no live trading; the rider records the operator's stated precondition, not a grant.

## Risk bindings, control actions, and paper mode

The risk contracts are ratified design, **defined-unwired**: no code exists, the composition root mediates, and implementation authorization arrives only through the factory pipeline, never from this runbook. When any step runs in production, the trigger→level→effect matrix and order-path internals stay node/risk territory, tracked in `tracker/trading-node-notes.md` (DEC-0142).

### Bind-time capability check

A binding couples one Book instance to one BMS instance on one `(VenueId, account)` command stream. The BMS is the **account-facing supervising layer** — one per account, serving many Books; a Book binds exactly one BMS at a time, dated and append-only (DEC-0143). A binding is admissible only where the venue's CT-18 declaration **and** its venue-observation profile satisfy the Book's declared required capabilities — including the account settlement currency matching the Book's `accounting_currency`, the shared-flatten signature where the account is netted, a present SQS baseline for every sensor the Book's doors read, the live-path rung baseline on this deployment's tuple, and a control-rank table the Book does not contradict — a shortfall refusing **at bind time**, never at trade time (DEC-0143, DEC-0158). A Book whose control policy contradicts its BMS's rank table is refused at bind time (DEC-0151).

### Three-layer admission

A new Book or BMS proves itself in three layers, with no trial period, probation window, or paper-performance gate (DEC-0146): Layer 1 — machine linters at registration (completeness against the declared contract format version, a unit on every parameter, exact-rational or scaled-integer values, resolvable references, worked-example arithmetic recomputed by invoking the cited producer contracts, control-rank uniqueness); Layer 2 — a technical shakedown on a demo/paper binding (connect, register a bot, execute), with a recorded live-path rung baseline on this deployment's tuple and a present baseline artifact for every sensor the Book's doors read as named prerequisites; Layer 3 — one operator signature on one assembled page carrying both proofs, the binding identity, the capability-satisfaction result, and the resolved BMS fingerprint. A Book whose admission bar holds any not-yet-ruled threshold or pending slot binds to non-live roles freely, and binding to a live account is a `policy rejection` (DEC-0146).

### Control-action vocabulary

Control actions are typed and each defined once (DEC-0150): `suspend_new` (no new entries; everything open or resting untouched), `drain` (no new entries and resting orders run to their own terminal state; nothing force-closed), `flatten` (close the scope), `resume`. The **kill switch** is the global authority that stops all new trading live and paper; the **kill line** is a per-Book capital floor whose breach automatically flattens that binding's scope and stands the Book down. `resume` is **operator-only** — escalation automates, de-escalation does not. Flatten authority is assigned — the operator always (inalienable, never removable), Book policy through pre-declared triggers, the protection authority per the node's severity policy, nobody else — and the adapter never initiates a flatten. The **exit-preservation invariant** binds: no control action, of any authority, at any scope, may block a risk-reducing act (DEC-0150).

### Paper flip and paper-epoch reset

Paper is a Book-level mode — `LIVE | PAPER` — expressed as a dated change of the Book's execution binding, minting a new **binding epoch**, never a new Book (DEC-0149). The **paper flip is an operator-ratified dated action**. The paper starting balance is a Book/family-scoped configurable UI-editable default, sized for data-collection realism, frozen at flip, and **never hand-adjusted** (DEC-0149, DEC-0157). A **reset is not an adjustment**: it mints a new **operator-signed, dated paper epoch record** with a fresh declared balance and a lineage edge to the epoch it follows; the running balance is never mutated. Paper P&L never becomes Treasury cash, never crosses the money boundary, and never buys a seat (DEC-0149).

## Node/ops time-audit obligations

The two-lens time audit produced operational clock rules that bind the trading node and its VPS. They are **stated obligations for the node/ops sitting, binding later sittings — not implemented runbook steps yet**, and QMF exposes only the seams (typed refusals, `WriterId`, gap records, day-boundary calendars) they hang on (DEC-0106, DEC-0112; companion `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md`).

| Obligation | Stated rule | Binds |
|---|---|---|
| Authoritative clock | The VPS OS clock runs chrony with ≥4 sources (iburst, makestep boot-only); it is the sole stamper of QMF-owned event times. A travelling Windows laptop is declared unfit to stamp authoritative evidence. | Node/ops sitting |
| No-trade-before-sync | The node must not trade before clock sync is confirmed (`chronyc waitsync`, after `time-sync.target`). | Node/ops sitting |
| Slew-only while live | Only slewing is permitted while live; a clock step happens only with the node stopped and must be observable (a wall-vs-monotonic divergence detector marks a suspect window). | Node/ops sitting |
| Drift bands with typed refusals | Numeric drift bands sized to ~1s decisions (ok / warn / no-new-entry / halt); exceeding a band is a typed refusal plus a journal record plus a node state change, never silent. Clock health is a per-decision-cycle precondition. | Node/ops sitting |
| Gap records for suspect windows | Every unsynchronized, stepped, or paused window (including a VPS live-migration/pause) is an explicit data-gap record and a node no-trade window, so backtests never read holes as "no ticks". | Node/ops sitting |
| RTC in UTC | Linux RTC in UTC, system tz UTC, `TZ=UTC`; the Windows RTC local-time caveat is handled for any Omakub dual-boot window. No local time is ever stored, keyed, or compared. | Node/ops sitting |
| Writer identity on the shared VPS | The trading node and the tick recorder share the VPS, so writer identity (`WriterId`) is stamped in every record to keep their streams distinct. | Node/ops sitting |
| Prop-firm day boundary | A prop firm's daily-loss/trading-day boundary is evaluated in its stated timezone via an account-scoped day-boundary calendar; QMF holds only the seam, no prop firm is modeled in V1. | Node/ops + later prop-firm work |

These obligations do not authorize any live operation now; they record what the node/ops sitting must implement.

## Secrets handling

The venue secret lifecycle is ratified as law (DEC-0136): QMF handles opaque `SecretRef` references, never values; values are injected at the composition root from the deployment environment's protected store (`systemd-creds`-class on the VPS), and only the adapter's connection manager holds `SecretValue`s in memory, through an injected `SecretStore` port. Rotation is store-before-discard with one live refresher per credential; the compromise-recovery drill is anchored on cTID re-authorization (see [OPS-INCIDENT-QMF-V1](incident-playbook.md)). Store mechanics and key custody land at the node/ops sitting, and credential entry/management UI is platform territory (DEC-0136). This runbook grants no credential-bearing operation; implementation authorization arrives only through the factory pipeline.

Object-storage encryption key custody is named at the node/ops sitting (DEC-0118). The news-calendar recorder keeps provider-native identity and revisions through idempotent intake (DEC-0119); the news- and historical-provider legal archiving posture remains an open operator item, and the cTrader trendbar price basis is measured per broker at first connection under the verify-or-refuse suite (DEC-0135). No credential-bearing operation is authorized at any of these boundaries.

## Data migration, backup, and restore

The migration process is ratified: preflight checks → backup first → dry-run → migrate → verify, with a documented restore path and never in-place mutation of the only copy; every serialized contract carries an integer format version whose meaning never mutates (DEC-0118, DEC-0103, DEC-0030). The exact per-schema migration steps are documentation-time detail owned by each CT; no agent runs a migration without the ratified process.

CT-14 carries the ratified backup design (nightly, encrypted, versioned, off-machine, with automated sample-restore tests and periodic full-restore rehearsal); QMF provides the backup, restore, and verify primitives, while numeric `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, and `registry:restore_verification_cadence`, encryption key custody, and the crypto dependency are named at the node/ops sitting (DEC-0118). No agent may run a destructive restore or cutover; execution is application/ops-owned. [DEC-0045]

## Pre-operation checklist

The foundation, data, and registry contracts are ratified: runtime and packaging (GAP-0001 through GAP-0006, DEC-0099 through DEC-0104), exact core value/time/identity/refusal/fingerprint/result-label (GAP-0007 through GAP-0012, DEC-0105 through DEC-0110), and store/schema/migration/retention/restore/split/journal/adapter law (GAP-0020 through GAP-0030, DEC-0114 through DEC-0119). An operator must still stop before mutation when any of the following is unresolved:

- Look-ahead registration gate and attempt counter: GAP-0016 and GAP-0017, deferred to the backtesting sitting (DEC-0121) — artifacts registered before then carry no causality evidence.
- Venue secret lifecycle, command law, adapter contract, and capability discovery are ratified (GAP-0035 through GAP-0038 answered, DEC-0136 through DEC-0139). Before any live operation the first-connection verification suite must pass verify-or-refuse, the command caller is the account-facing risk layer ratified as **defined-unwired** surface (DEC-0143), flatten authority is assigned (DEC-0150), and the trigger→level→effect matrix plus reconciliation-verdict consequences stay node/risk sitting territory (DEC-0142).
- The operator's ~1-week warm-up/observation rider before live trading (DEC-0135).
- Book, BMS, exit, paper-mode, news, SQS, formula, bench, and priority contracts are ratified as **defined-unwired** surface (DEC-0143 through DEC-0155); no live binding, order, exit, or mode change is buildable from these docs, and wiring arrives only through the factory pipeline.
- The node/ops time-audit obligations above (clock sync, drift bands, gap records) before any live-clock trading.
- Human authorization for promotion or any live-money boundary. [DEC-0041]

## Incident handoff

Operational failures route to [OPS-INCIDENT-QMF-V1](incident-playbook.md). No failure grants an agent implicit authority to promote, trade, flatten, rotate credentials, restore data, or override a Book. [DEC-0001] [DEC-0041]
