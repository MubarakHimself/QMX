---
id: DOC-CHANGELOG
title: QMF Documentation Changelog
type: changelog
status: provisional
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, _docwork/review-consistency.md, _docwork/review-redteam.md, docs/index.md, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-21
stale_after: 90d
---

# QMF Documentation Changelog

This records changes to the QMF knowledge base. It is not a software release log and does not convert provisional decisions into implementation authority.

## 2026-08-21 — QMB increment absorption (change mode)

Absorbed the 2026-08-20 QMB architecture sitting — the same-day child run of the QMF sitting, spine B-1 through B-15, FINAL and ratified by operator delegation — into the knowledge base. ADR: [ADR-0017](decisions/ADR-0017-qmb-experimentation-library.md) (new; architecture-preflight verdict: **new COMP-QMB**, the QMX experimentation/backtesting product — one pure library plus the `qmb` CLI built ON QMF, never a QMF roster package). The design is ratified; implementation authorization still arrives only through the factory pipeline.

| Field | Value |
|---|---|
| Mode | Change mode — fold the ratified QMB increment |
| Authority snapshot | 11 new ledger decisions (DEC-0159–DEC-0169); GAP-0048 **partially** closed (fidelity seams ruled, DEC-0164 — taxonomy values and calibration content stay open in their own sitting); GAP-0016/GAP-0017 stay deferred with look-ahead **prevention** now delivered by construction (DEC-0169/DEC-0121); the glossary's reserved future-backtesting-library slot realized and the experimentation/backtest rename settled (DEC-0159) |
| Provenance | Sources SRC-07 (the `architecture-QMB-2026-08-20/` sitting folder) and SRC-08 (`archive/qmf-7.txt`, the backtesting-direction session transcript) registered; extractions EXT-2071–EXT-2082; the two donor engines reverse-engineered into intake dossiers (never adopted as code, D1); the QMB spine gated through three reviewer rounds plus a docs-reconcile lens and ratified by operator delegation 2026-08-20 |
| New component | [COMP-QMB](components/qmb.md) — application-layer experimentation/backtesting product (layer middleware; depends on the six backend QMF components; **no** edge to COMP-QMF-VENUE — live wiring is trading-node territory) — plus feature FEAT-0029 |
| Contracts | [CT-32](contracts/ct-32-performance-result.yaml) adopted by QMB as the run result with declared chart-series and trade-event-reference extensions (downsamples display-only, AD-10-excluded) and QMB named its intended producer; [CT-13](contracts/ct-13-journal.yaml) gains the replay-world run-loop emission note; [CT-11](contracts/ct-11-evidence-persistence.yaml) restates the per-run-logs-operational-only boundary (DEC-0163). No QMF contract changes meaning; no dependency edge reverses direction |
| Registry | new configurable UI-editable rows (L38/DEC-0157): `qmb_governor_cpu_budget`, `qmb_governor_memory_budget`, `qmb_run_time_limit`, `qmb_run_memory_limit`, `qmb_stale_evidence_severity`; plus the exact stack pins `qmb_cli_pin` (click==8.4.2) and `qmb_sampler_pin` (optuna==4.9.0), an optuna major bump being a contract-versioning event (DEC-0168) |
| Operator flag | The Dukascopy data-licensing ops question was flagged OPEN by this increment (DEC-0166), then **RULED CLOSED the same day** by direct operator ruling: personal-use backtesting only, no redistribution; the per-window license-tag mechanism stays in force (DEC-0170) |
| Still open | None blocking. Deferred after this: GAP-0016/GAP-0017 (the registration gate — prevention delivered, DEC-0121), GAP-0048 content (fidelity taxonomy + calibration, its own sitting), GAP-0049 (thresholds/SR*/staged funnel), and GAP-0047 (the QML sitting, which may run first). Remaining BMad path: then the PRD, then BMad exit |

Touched docs: new [qmb.md](components/qmb.md) component spec, new [SCN-0012 QMB replay run](scenarios/SCN-0012-qmb-replay-run.md), and new [ADR-0017](decisions/ADR-0017-qmb-experimentation-library.md); the [glossary](glossary.md) (QMB, the settled experimentation/backtest rename, the Simulator as a separate deferred UI product that will consume QMB, and "as-of set" for registry state — the banned "snapshot" retired); [overview](architecture/overview.md), [stack](architecture/stack.md) (the click/optuna pins and `uv add qmb` distribution), and [dependencies.yaml](architecture/dependencies.yaml) (COMP-QMB minted, layer middleware, edges to the six backend QMF components with no COMP-QMF-VENUE edge); [variables.yaml](registry/variables.yaml) (the governor/limit/staleness configurables and the click/optuna pins); the [gap report](gap-report.md) (GAP-0048 partially closed, GAP-0016/GAP-0017 prevention-delivered); [traceability](knowledge/traceability.md); the [feature inventory](../_docwork/feature_inventory.yaml) (FEAT-0029); contracts [CT-32](contracts/ct-32-performance-result.yaml), [CT-13](contracts/ct-13-journal.yaml), and [CT-11](contracts/ct-11-evidence-persistence.yaml); and [index](index.md), [AGENTS.md](AGENTS.md), and this changelog. QMB consumes QMF contracts without redefining them and produces its evidence through them in `world = replay`; it is the first sanctioned composition root where the defined-unwired risk contracts are legally wired; it is never a QMF roster package, an engine, or a kernel.

## 2026-08-20 — Risk increment absorption (change mode)

Absorbed the 2026-08-20 risk sitting — spine AD-29 through AD-41 plus the reviewer gate's cross-AD amendments to AD-7, AD-10, AD-12, AD-16, AD-17, AD-18, AD-21, AD-24, AD-27, and AD-28 — into the knowledge base. ADRs: [ADR-0008](decisions/ADR-0008-book-and-risk-boundary.md), [ADR-0009](decisions/ADR-0009-book-level-paper-mode.md), [ADR-0010](decisions/ADR-0010-risk-vocabulary-clean-start.md) (each rewritten in place, superseding their GAP-defined placeholders; preflight verdict: reuse COMP-QMF-RISK, no new component). The design is ratified; implementation authorization still arrives only through the factory pipeline.

| Field | Value |
|---|---|
| Mode | Change mode — fold the ratified risk increment |
| Authority snapshot | 16 new ledger decisions (DEC-0143–DEC-0158); GAP-0039–GAP-0046 answered (44 answered, 0 open); DEC-0095 superseded by DEC-0143, DEC-0067 (the last live conflict) resolved by DEC-0147, DEC-0070 confirmed and subsumed by DEC-0149, DEC-0072 by DEC-0152, DEC-0075 by DEC-0153, DEC-0094 by DEC-0155 |
| Provenance | Memlog entries 85–124 of the architecture sitting workspace; the re-finalized spine; the risk-sitting deep-study briefs and QML dig under `research-risk/`; the risk increment gate applied at desk (adversarial 54, rubric 45, rulings-reconcile 10, currency 1; lint clean twice; three operator-ruling-over-reviewer tensions filed in Deferred) |
| Contracts filled | [CT-22](contracts/ct-22-book-charter.yaml) v1 (Book definition template), [CT-23](contracts/ct-23-risk-evaluation.yaml) v1 (bot-to-Book door), [CT-24](contracts/ct-24-book-mode.yaml) v1 (Book mode + binding transition), [CT-25](contracts/ct-25-risk-journal.yaml) v1 (entity journals as projections) |
| Contracts minted | [CT-27](contracts/ct-27-bms-definition.yaml) (BMS definition template), [CT-28](contracts/ct-28-book-binding.yaml) (Book binding record + identity trinity), [CT-29](contracts/ct-29-exit-record.yaml) (exit record per virtual-position close), [CT-30](contracts/ct-30-control-action.yaml) (kill switch, kill line, suspend_new/drain/flatten/resume), [CT-31](contracts/ct-31-control-window.yaml) (news, daily_dead_zone, session_handover_buffer), [CT-32](contracts/ct-32-performance-result.yaml) (performance-result container); CT-19 gains the fifth venue command amend_protection (DEC-0148) |
| New laws | L36 authority order bot → book → BMS → operator (DEC-0143); L37 corpus precedence for risk sources (DEC-0156); L38 configurable-means-UI-editable (DEC-0157); L39 the exit-preservation invariant (DEC-0150) |
| Registry | risk-sitting figures recorded as configurable UI-editable variables with recorded evidence and no ratified spine value (DEC-0157): SQS per-class thresholds/band/outlier guard, bench `q`/`bench_consecutive_loss_threshold`, protection-window widths (news buffer withdrawn; disagreeing 1h/~3h dead-zone widths recorded unmerged; ~45min handover buffer as recollection), breakeven-ratchet parameters, paper starting balance |
| Still open | None blocking. Deferred: GAP-0016/GAP-0017 (backtesting sitting, DEC-0121) and consumers GAP-0047–GAP-0049 (QML, backtesting, and research-threshold sittings) |

Touched docs: the [gap report](gap-report.md) (44 answered / 0 open / 5 deferred; the last conflict and the last three open ledger entries closed); [qmf-risk](components/qmf-risk.md) rewritten from AD-29..41 (fenced-stub posture dropped) plus ripple updates to [qmf-core](components/qmf-core.md) (Position/Order shared nouns with the venue-vs-virtual split, canonical numeric form and per-value-class storage scales, unit-kind vocabulary), [qmf-registry](components/qmf-registry.md) (nine risk record kinds onto AD-16, continues-performance / carries-ledger / enacts edges), the [qmf-data family](components/qmf-data.md) ([qmf-data](components/qmf-data.md) journals-as-projections and the command-fingerprint join), [qmf-venue](components/qmf-venue.md) (amend_protection fifth command, CT-18 protection/margin/settlement fields), [ctrader](components/ctrader.md) (amend-mechanics and margin/venue_liquidation-level facts), and [calendar-feed](components/calendar-feed.md) (protection-window news source); contracts CT-22–CT-25 filled and CT-27–CT-32 minted, with CT-01/CT-05/CT-06/CT-07/CT-13/CT-18/CT-19/CT-20 amended (canonical numeric form, per-value-class scales, risk record wrapping, enacts edges, projection surface, protection/margin/settlement capability fields, amend_protection, venue-authored event join); the [constitution](constitution.md) (L36–L39); the [glossary](glossary.md) (BMS as account-facing supervising layer, kill switch vs kill line, qualifying_loss_exit vs venue_liquidation, seat active|benched vs Book LIVE|PAPER vs binding live|paper|stood-down, admission_bar, ExitLogicRef, exit-preservation invariant, and the other risk terms); [variables.yaml](registry/variables.yaml); scenarios [SCN-0005](scenarios/SCN-0005-uncertain-venue-submission.md) through [SCN-0010](scenarios/SCN-0010-risk-boundary-conflicts.md) (the risk subset — paper transition, instrument-scoped news windows, same-tick arbitration refreshed to ratified state) plus the new [SCN-0011 qualifying-loss bench](scenarios/SCN-0011-qualifying-loss-bench.md); the security, observability, ops, performance, testing, data, and bug-triage lens docs; [overview](architecture/overview.md), [stack](architecture/stack.md), and [dependencies.yaml](architecture/dependencies.yaml) (risk contracts under COMP-QMF-RISK, no new edge); [traceability](knowledge/traceability.md); the [feature inventory](../_docwork/feature_inventory.yaml) (FEAT-0027 re-traced to DEC-0143–DEC-0158, now an implementation feature); and [index](index.md), [AGENTS.md](AGENTS.md), and this changelog. Node-runtime material stays out per DEC-0142 — `tracker/trading-node-notes.md` is the standing cross-session node ledger, referenced as a pointer only.

## 2026-08-20 — Venue increment absorption (change mode)

Absorbed the 2026-08-20 venue sitting — spine AD-26 through AD-28 plus the increment gate's cross-AD amendments to AD-7, AD-8, AD-9, AD-12, AD-15, the dependency direction, and the Stack register — into the knowledge base. ADR: [ADR-0007](decisions/ADR-0007-venue-neutral-integration.md) (rewritten in place, superseding its GAP-defined placeholders; preflight verdict: reuse COMP-QMF-VENUE, no new component). The design is ratified; implementation authorization still arrives only through the factory pipeline.

| Field | Value |
|---|---|
| Mode | Change mode — fold the ratified venue increment |
| Authority snapshot | 8 new ledger decisions (DEC-0135–DEC-0142); GAP-0035–GAP-0038 answered; DEC-0123 superseded by DEC-0135 — the cTrader research is ratified as `ctrader-venue-facts.md` with corrected evidence grades: the 2013-forum-grade claims (17:00-NY daily boundary, BID-derived trendbars) were demoted and replaced by measure-per-broker adapter obligations |
| Provenance | Memlog entries 63–83 of the architecture sitting workspace; the re-finalized spine; the ratified venue-facts sheet and its research companions (primary-source verification, rate limits, tick/spot mechanics, depth/connectivity, Spotware org inventory); the 49-finding venue increment gate applied at desk |
| Contracts filled | [CT-18](contracts/ct-18-venue-capabilities.yaml) v1 (capability declaration vs venue-observation profile), [CT-19](contracts/ct-19-venue-command.yaml) v1 (four command kinds, four-outcome law), [CT-20](contracts/ct-20-venue-event.yaml) v1 (recording precedes interpretation, read-time fold, reconciliation), [CT-21](contracts/ct-21-venue-secret-session.yaml) v1 (SecretRef/SecretValue lifecycle) |
| New laws | L34 secret references never values (DEC-0136); L35 four-outcome law — a timeout is never a rejection (DEC-0137) |
| Registry | `venue_trendbar_price_basis` → measured-per-broker, never hardcoded; new `venue_daily_bar_boundary` (measured-per-broker, calendar-identity mint), `venue_broker_identity` (deployment configuration, DEC-0139), `venue_protocol_artifact` (Spotware proto tag 91, DEC-0141) |
| Still open | Risk (GAP-0039–GAP-0046, risk sitting — qmf-risk stays a stub); deferred GAP-0016/GAP-0017 (backtesting sitting, DEC-0121) and consumers GAP-0047–GAP-0049 |

Touched docs (41 in the drafting pass plus desk fixes from the consistency review): the [gap report](gap-report.md) (36 answered / 8 open / 5 deferred); [qmf-venue](components/qmf-venue.md) rewritten from AD-26..28 (reserved-unwired posture dropped) plus ripple updates to [qmf-core](components/qmf-core.md) (SecretRef/SecretValue, sink protocols), [qmf-data](components/qmf-data.md) and [qmf-data-ingest](components/qmf-data-ingest.md) (venue market-data intake at CT-10/CT-15, venue journal production through the injected JournalSink), [ctrader](components/ctrader.md) (venue-facts home), [dukascopy](components/dukascopy.md) and [qmf-calendar-forex](components/qmf-calendar-forex.md) (stale GAP-0037 forward-references retired); contracts CT-18–CT-21 filled and CT-01–CT-07, CT-10, CT-13, CT-15 amended (foreign-float law, venue-scoped calendar identity mint, platform-vs-broker, denied-locally-is-an-outcome, command fp1 identity, venue WriterId granularity, out-of-sequence and command-id-binding records, venue-as-source, journal cardinality law, no-silent-sibling-failover); the constitution (L34, L35); the glossary (38 venue terms; stale venue-gap markers on Bar/Fill/Order/Tick/Venue resolved); [variables.yaml](registry/variables.yaml); [SCN-0005](scenarios/SCN-0005-uncertain-venue-submission.md) (ratified uncertain-submission behavior); [stack](architecture/stack.md) (Spotware proto tag 91, protobuf runtime, OpenApiPy reference-only), [overview](architecture/overview.md), and [dependencies.yaml](architecture/dependencies.yaml) (venue-sink note, no new edge); the security, observability, ops, performance, testing, data, and bug-triage lenses; traceability; the feature inventory (FEAT-0023–FEAT-0026 re-traced to DEC-0135–DEC-0140); index and AGENTS.md; and this changelog. ADR-0013 deliberately keeps its point-in-time "cTrader evidence, not adoption" record under the immutable-ADR convention; the supersession chain is carried by the gap report, traceability, and ADR-0007. Node-runtime material stays out per DEC-0142 — `tracker/trading-node-notes.md` is the standing cross-session node ledger, referenced as a pointer only.

## 2026-08-20 — Indicators/structure increment absorption (change mode)

Absorbed the 2026-08-20 indicators/structure sitting — spine AD-22 through AD-25 plus the increment gate's amendments to AD-2, AD-7, AD-8, AD-12, AD-14, AD-16, AD-17, and AD-21 — into the knowledge base. ADR: [ADR-0006](decisions/ADR-0006-indicators-and-structure.md) (rewritten in place, superseding its GAP-defined placeholders; preflight verdict: reuse, no new component). Scope stops before the venue sitting: GAP-0035 and later stayed open and untouched at this entry's date. (The venue increment entry above subsequently closed GAP-0035–GAP-0038; this sentence is a dated record, not current state.)

| Field | Value |
|---|---|
| Mode | Change mode — fold the ratified indicators/structure increment |
| Authority snapshot | 9 new ledger decisions (DEC-0126–DEC-0134); GAP-0031–GAP-0034 answered (GAP-0033 was the catalog's last nonblocking gap); DEC-0056 superseded by DEC-0128, DEC-0124 by DEC-0134 |
| Provenance | Memlog entries 50–62 of the architecture sitting workspace; the re-finalized spine; the increment gate's reviews (adversarial-3, two school-spanning edge-case lenses) as CT-16/CT-17's conformance input register |
| Contracts filled | [CT-16](contracts/ct-16-indicator.yaml) v1 (two-mode indicator, identity = entire declared configuration) and [CT-17](contracts/ct-17-causal-structure.yaml) v1 (causal structure lifecycle) |
| New laws | L32 school-neutral vocabulary (DEC-0132); L33 plain-Python escape hatch + graduation path (DEC-0133) |
| Registry | `canonical_indicator_reference` = TA-Lib 0.7.1 + 0.7.1 as lockfile artifact hashes + reference-configuration record; new enums `barspec_kinds`, `presence_map_states`, `evidence_classes`, `structure_seed_family_candidates` |
| Still open | Venue (GAP-0035–GAP-0038), risk (GAP-0039–GAP-0046); deferred GAP-0016/GAP-0017 (backtesting sitting, DEC-0121) and consumers GAP-0047–GAP-0049 |

Touched docs: the [gap report](gap-report.md) (32 answered / 12 open); component specs [qmf-indicators](components/qmf-indicators.md) and [qmf-structure](components/qmf-structure.md) (rewritten from AD-22..25, GAP markers resolved) plus ripple updates to [qmf-core](components/qmf-core.md), [qmf-data](components/qmf-data.md), and [qmf-registry](components/qmf-registry.md); contracts CT-16, CT-17, CT-07, CT-12, and CT-05 (result label gains producer contract identity and evidence class per DEC-0131 — the "five-part" wording corrected here, in the glossary, in SCN-0001, and in the registry note); the constitution (L32, L33); the glossary (BarSpec — bare "timeframe" retired — presence map, knowable-at, evidence class, anchor span, interaction record, exact rational, PriceDelta, derived-series identity, standing object, structure family); [variables.yaml](registry/variables.yaml); [stack](architecture/stack.md) (TA-Lib row, roster roles); the performance-budget, observability, and testing lenses (new AD-13 rungs; AD-14 component definition + correlation exemption; equality-law and emission-invariant test rows); ADR-0003 and SCN-0001 (freeze-choice count now four-of-six, DEC-0134); [dependencies.yaml](architecture/dependencies.yaml); traceability; the feature inventory (FEAT-0019–FEAT-0022 notes re-grounded); index, overview, and AGENTS.md counts; and this changelog.

## 2026-08-20 — Foundation architecture-sitting absorption (change mode)

Absorbed the ratified foundation architecture spine (AD-1 through AD-21, ledger DEC-0099 through DEC-0125) from the 2026-08-19/20 sitting into the existing knowledge base; the rulings are operator-ratified, and every absorbing document stays `provisional` until the knowledge base is re-ratified.

| Field | Value |
|---|---|
| Mode | Change mode — absorb a ratified architecture sitting |
| Authority snapshot | 27 new ledger decisions (DEC-0099–DEC-0125); 28 gaps answered (GAP-0001–GAP-0015, GAP-0018–GAP-0030); GAP-0016/GAP-0017 deferred to the backtesting sitting (DEC-0121) |
| New ADRs | 5: [ADR-0012](decisions/ADR-0012-runtime-packaging-quality.md), [ADR-0013](decisions/ADR-0013-exact-values-and-identity.md), [ADR-0014](decisions/ADR-0014-performance-observability-concurrency.md), [ADR-0015](decisions/ADR-0015-registry-records-and-promotion.md), [ADR-0016](decisions/ADR-0016-data-rooms-splits-journal.md) |
| New component spec | [qmf-calendar-forex](components/qmf-calendar-forex.md) — first market-hours calendar extension, outside the roster on its own SemVer ladder |
| Corpus | 88 files: 60 Markdown and 28 YAML (was 82: 54 Markdown and 28 YAML) |
| Still open | Indicators/structure (GAP-0031–GAP-0034), venue (GAP-0035–GAP-0038), risk (GAP-0039–GAP-0046); deferred consumers GAP-0047–GAP-0049 |

Foundation now ratified: exact money (AD-7), exact time and calendar rule sets (AD-8), instrument/venue/account identity (AD-9), the fp1 fingerprint (AD-10), typed refusals (AD-11), the result label and worlds (AD-12), runtime matrix and packaging (AD-1/AD-2), toolchain and gates (AD-3/AD-4), version ladders (AD-5), dependency tiers (AD-6), performance/observability/concurrency (AD-13/AD-14/AD-15), registry records and promotion (AD-16/AD-17/AD-18), data rooms/migrations/backup (AD-19/AD-20), splits/journal/adapters (AD-21), and the default-deny dependency direction with the one ratified qmf-registry→qmf-data edge (DEC-0120).

Touched doc groups in this pass: contracts CT-01–CT-07, CT-09–CT-15, and CT-26 (reserved shapes bound to the ratified rules); the registry YAML artifacts; all component specifications plus the new qmf-calendar-forex spec; the constitution (new laws L30 default-deny dependencies, L31 everything-built-with-QMF); the glossary (three-calendar naming, worlds vocabulary, WriterId, taint money path); the active lenses; the golden scenarios; the feature inventory; and this changelog, the [documentation index](index.md), the [gap report](gap-report.md), and [AGENTS.md](AGENTS.md).

## 2026-08-18 — Fresh documentation-factory build

| Field | Value |
|---|---|
| Mode | Fresh documentation from two transcript sources |
| Authority snapshot | 98 sequential decisions; 49 gaps; 431 source extractions |
| Documentation corpus | 82 files: 54 Markdown and 28 YAML |
| Public QMF roster | Five libraries and two modules |
| Component registry | 14 public, internal-seam, and external component records |
| Contracts | CT-01 through CT-26 |
| Component specifications | 14 |
| ADRs | 11 |
| Golden scenarios | 10, deliberately blocked where source rulings are missing |
| Active lens documents | 10 across data, testing, bugs, operations, security, observability, and performance |
| Feature handoff | 27 planned features in 14 dependency waves; none ratified |
| Mode status | Provisional; not implementation-ready or live-operation-ready |

Created the authority ledger, gap catalog, constitution, architecture maps, typed contract placeholders, component specifications, ADR set, variable registry, glossary, active lens documentation, scenario bank, agent entry point, traceability map, and ratification packet.

Independent consistency and source-blind adversarial reviews identified wiring and authority defects. The documentation pass corrected contract ownership and routing, added CT-26 for the Store-to-Backup seam, separated active from intended consumers, removed invented journal, restore, secret, and command assumptions, and preserved all true source gaps as explicit non-buildable gates.

The remaining human gate is intentional: the two conflicts, open decisions, and blocking gaps must be ruled on and the provisional packet signed before strict release validation can pass.
