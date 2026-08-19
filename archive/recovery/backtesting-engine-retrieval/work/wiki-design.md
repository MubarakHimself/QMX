# Backtesting Engine retrieval — wiki and design evidence

## Retrieval verdict

The old Backtest Engine is recoverable as a **deterministic, book-specific replay and examination capability**, but it is not recoverable as a ready-to-build subsystem by copying the old specification.

The durable center is strong:

- certification is against a particular bot specification **and** a particular book profile;
- replay is outside the trading hot path and is hosted on the backend node;
- only historical market input and simulated execution may replace their live counterparts;
- live policy, costs, refusals, state transitions, and evidence behavior must otherwise remain equivalent;
- runs must be pinned to immutable inputs and be reproducible;
- the Examination Engine measures and certifies but never admits a bot, changes a book, or authorizes live trading;
- the statistical battery and its registry values survive;
- the result of examination is CT-EXAM-01 and, where applicable, CT-EXAM-02 evidence for a later Book/admission decision.

What does **not** survive is the old engine's embedding in the WF2 mutation pipeline, its old six-clamp/multiplier/equity-band/slot-cap authority table, or its automatic registration/paper/live progression. Current planning explicitly defers the Examination Engine as **D1**, to be redesigned and rebuilt in-house. The later old-repository implementation proves only bounded CT-MIS-02 archive reads; it does not prove a Backtest Engine, an Examination Engine, fill simulation, certification, or book-aware policy replay.

The safest recovered name is therefore:

> **Backend-node Examination Engine with an in-house deterministic replay harness**

`Replay Service` is useful proposal vocabulary, but it is not a ratified deployable service boundary.

## Source-authority ladder

| Rank | Source family | Authority for this retrieval | Treatment |
| --- | --- | --- | --- |
| 1 | Final Architecture Spine, especially AD-5, AD-13, AD-14, AD-17, AD-19, AD-28, AD-35, AD-39 and AD-40 | Current architecture and mechanics | Binding unless a later operator ruling supersedes it. |
| 2 | Current PRD/addendum and `epics.md` | Requirements, scope, terminology, deferred-work status and acceptance intent | Binding. `epics.md` is especially important because it marks FR-4..FR-7 as Deferred D1. |
| 3 | Current wiki pages | Reconciled operator-facing model | Current summary, but planning artifacts win on conflict. |
| 4 | Story 3.6 implementation artifacts | Later proof of CT-MIS-02 bounded archive-query serving only | Evidence that one prerequisite exists in the old repository; never evidence that the engine exists. |
| 5 | GitBook capture | Earlier core contracts and examination concept | Retain where compatible with ranks 1–4. |
| 6 | Recovered `backtest-engine-spec.md` and clash reports | Old-system detail and donor mechanics | Unratified baseline. Re-anchor before use. |
| 7 | Recovered microservice proposal | Possible service/API decomposition | Proposal only; not deployment truth. |

Chronology matters:

1. The old-vault Backtest Engine export is dated 2026-07-18 and labels itself `UNRATIFIED baseline` despite an old “Canonical v1.0” caption.
2. The wiki ingested the recovered design artifacts on 2026-07-20 and explicitly preserved WF/slot/DPR mechanics as unratified.
3. The July planning run became the higher authority on 2026-07-21 through 2026-07-24.
4. Story 3.6 was completed on 2026-07-26. It deliberately stops at CT-MIS-02 bounded query serving.

## Current intended boundary

### Responsibility

The Examination Engine answers:

> Does this immutable bot specification retain a cost-adjusted edge, under replay behavior equivalent to production, when evaluated against this exact book profile and its registered policy versions?

It receives historical evidence from MIS-Archive, executes the examination battery through the replay harness, and emits certification evidence to the Book boundary.

It may:

- request bounded, version-pinned archive emissions;
- execute/evaluate QML-authored bot behavior through explicit Python adapters;
- replay the book-specific decision policy and protection effects;
- simulate broker fills honestly;
- calculate examination statistics;
- emit immutable exam and cohort-correlation certificates;
- write its own backend-node certificate corpus and run artifacts under a single owner;
- attach passing and failing evidence immutably to the bot dossier.

It may not:

- authorize trading or promotion;
- change the book profile or registry;
- mutate signal logic or optimize parameters as part of certification;
- write into authoritative trading-node state;
- become a second BMS Records writer;
- bypass labeler, stop-policy, data-snapshot or configuration parity;
- omit live refusals or known production behavior to make the replay easier;
- execute in, or block, the trading hot path.

### Placement

Current topology places the certification pipeline on the **backend node**, the always-on evidence home. The architecture enumerates examination job runners as process-per-run workers under one supervisor. They are read-only over manifested Class-3 Parquet. The backend service is the sole Parquet writer/finalizer; a job runner must not create a shared writable DuckDB or a second archive writer.

The backend node also holds:

- the full certificate corpus and per-bot dossiers;
- MIS-Archive and the captured canonical feed;
- Class-1 and Class-2 read replicas used as evidence;
- dataset catalog and provenance metadata.

The operative certificate-validity truth does **not** live in the corpus. The trading-node certificate index is the Class-1 authority for admitted certificate validity; labeler version changes invalidate it through the L10 cascade. The corpus preserves evidence as issued.

### Logical flow

```text
immutable bot spec + target book profile + pinned policy/config versions
                                  |
                                  v
                 CT-MIS-02 bounded archive request
                                  |
                                  v
             deterministic book-aware replay harness
               | live-equivalent policy/refusals
               | in-house fill simulation
               | reproducible evidence trace
                                  |
                                  v
                  registry-backed exam battery
                                  |
                       +----------+----------+
                       |                     |
                       v                     v
                 CT-EXAM-01            CT-EXAM-02
                 bot evidence        cohort evidence
                       |                     |
                       +----------+----------+
                                  |
                                  v
                  Book/admission consumes evidence
                                  |
                   operator promotion remains separate
```

## Lifecycle reconstruction

### Current lifecycle that should be recovered

1. **Candidate identity is frozen.** A candidate is referenced by stable `bot_id` and immutable `bot_spec_version`; a spec change creates a new version rather than mutating the certified artifact.
2. **Target contract is frozen.** The run binds the specific Book definition/profile, registry state, attributes and all policy versions that can change observed behavior.
3. **Evidence identity is frozen.** The run selects a named immutable data snapshot/source class and exact labeler versions. Live-recorded and materialized-backfill emissions remain disjoint and explicitly selected.
4. **CT-MIS-02 requests archive evidence.** Exam sends exactly `query_id`, `pair`, `start_utc`, `end_utc`, and `labeler_versions`; MIS-Archive returns a deterministic result over manifest-visible emissions.
5. **Replay executes shared production policy.** Historical input substitutes for the live feed and the in-house fill simulator substitutes for the broker adapter. The Book decisions, policy order, refusal behavior and evidence semantics stay production-equivalent.
6. **Battery executes.** Walk-forward, Monte Carlo and PBO evidence are computed from cost-adjusted out-of-sample behavior using registry-owned thresholds.
7. **Certificates are emitted.** CT-EXAM-01 records book-specific candidate evidence; CT-EXAM-02 records cohort correlation evidence when measurable. Failed as well as passed runs remain dossier evidence.
8. **Certification-side paper may follow.** AD-28 relocates birth-in-paper, warm-up and examination-to-paper to this side, but their exact state machine is not designed yet. This is not license to restore the old WF2 state machine.
9. **WF2 ends at paper-complete.** The operator's promotion click is separate. A valid certificate is evidence at the gate, never self-promotion authority.
10. **Admission and live activation happen elsewhere.** The trading node pulls and revalidates artifacts at the click, writes admitted artifacts to Class-1 stores, and lands the unit in `ADMITTED`. Activation timing remains a separate proposed ruling.

### Old lifecycle that must not be restored

The recovered engine was WF2's evaluation spine:

```text
Stage G retest via WF1 contracts
  -> Stage H unspecified scenario stress
  -> Stage I.0 exactly-once registry write
  -> Stage I.1 paper wait / fail / re-paper
  -> Stage I.2 operator A1 live gate
```

That orchestration, including weakness buckets, typed reviewer mail, registry-write ownership, old paper redemption and mutation-pipeline customer, is donor history only. The modern customer is the Examination Engine/Book admission boundary, not a workflow stage list.

## Load-bearing invariants

### Binding/current

1. **Book-specific, never abstract.** There is no generic “certified bot”; certification is for one immutable bot spec against one Book contract/profile.
2. **Off hot path.** Replay load or backend failure cannot block the trading node.
3. **Exam is non-authoritative.** It measures and certifies. It cannot admit, promote, change registry values, change book profiles, or trade.
4. **Shared policy path.** Door/refusal evaluation must execute through the same in-house code path used live. A third-party engine may not own fill physics or policy evaluation; current planning chooses an in-house rebuild rather than a wrapped engine.
5. **Refusal parity.** Every live refusal that matters to an outcome must be reproduced as replay evidence, including its ordering and reason.
6. **Version parity.** A labeler mismatch invalidates CT-EXAM-01 and blocks live use until recertification. Every other policy affecting measured loss, especially the future stop-policy version, must be pinned as the certification design is completed.
7. **Immutable input evidence.** Replay reads manifest-visible immutable archive emissions. It never silently falls back to partial labeler matches or live-updating data.
8. **Deterministic run identity.** No ambient clock or randomness. `seed` is explicit; configuration identity covers resolved registry and attribute bindings.
9. **Exact financial arithmetic.** Money, price, equity and sizing use platform-scaled integers or `Decimal`. Floats are allowed only for replay-stable statistics and labeler features.
10. **Evidence ownership.** Exam workers write their own corpus/run artifacts only. BMS Records remains the sole authoritative trading-journal writer.
11. **Evidence survives failure.** Failed examinations and invalidated certificates remain immutable historical evidence in the dossier/corpus; validity is read from the index, not inferred from corpus presence.
12. **Clock is context, not permission.** Session/overlap reconstruction may characterize results but may not restore time-window authorization that the current architecture explicitly rejects.

### Strong recovery candidates requiring a replay-run contract

The recovered four-part reproducibility key is:

```text
bot_spec_version + data_snapshot_id + config_hash + seed
```

Current planning uses this quadruple as a replay reproducibility test shape, but there is still no ratified replay-run schema. It should be retained as the minimum identity, then extended explicitly rather than silently. At minimum, the future schema must decide how it binds:

- `bot_id` and target Book definition/profile identity;
- policy versions, including stop policy and ordered door implementation;
- `labeler_versions`, data source class and input-availability tier;
- fill-model identity and cost schedule;
- replay engine/code version;
- UTC bounds and pair/symbol scope;
- result/evidence-pack hashes and run status.

## Contract recovery

### CT-MIS-02 — bounded archive replay query

**Current status:** request/result direction is resolved, request fields are fixed, and Story 3.6 proves a bounded read helper in the old repository.

| Direction | Party | Meaning |
| --- | --- | --- |
| Request | Exam → MIS-Archive | Select immutable replay evidence bounded by pair, UTC interval and exact labeler versions. |
| Result | MIS-Archive → Exam | Return deterministic, manifest-visible matching emissions and archive identity evidence. |

Exact request fields:

- `query_id`
- `pair`
- `start_utc`
- `end_utc`
- `labeler_versions`

Story 3.6 adds implementation evidence for stable ordering/hash, manifest visibility, strict bounds, structured refusal and read-only behavior. Its internal archive locator is not a CT-MIS-02 field. It explicitly forbids adding bot, Book, configuration, seed, fill, or policy-trace fields to CT-MIS-02.

**Important seam:** CT-MIS-02 retrieves inputs. It is not the future replay-run submission/result contract.

### CT-EXAM-01 — book-specific exam certificate

**Current status:** draft contract inherited from GitBook and treated as a required consuming surface in current planning.

| Field | Meaning |
| --- | --- |
| `bot_id` | Candidate identity. |
| `book_profile` | Exact target profile; certification is not abstract. |
| `labeler_versions` | Live/exam parity binding. |
| `ev_by_regime` | Regime-conditioned expected value. |
| `mean_loss_r` | Measured `Lbar`, used downstream by Book money rules. |
| `fire_rate_band` | Certified activity envelope. |
| `breaker_expectation` | Expected breaker behavior. |
| `cost_ratio` | Cost-adjusted edge evidence. |

Labeler mismatch invalidates the certificate. PE-8 requires future stop-policy version pinning; that extension is not yet ratified.

### CT-EXAM-02 — cohort correlation certificate

**Current status:** draft contract; method and threshold remain incomplete.

Fields are `cohort_id`, `book_id`, `correlation_observations`, `expected_loss_shape`, and `certified_at_utc`. The chorus threshold remains null under GAP-0012; the engine must not invent one when cohort measurement is absent.

### CT-BMS-05 / replay journal seam

The recovered specification says replay writes the “same journal schema” with replay/demo mode. The current architecture says BMS Records is the only writer for authoritative trading streams, while the exam host owns its corpus outputs. Those statements are compatible only if “same schema” means **behaviorally equivalent replay evidence**, not writes into the live Records tables.

The future replay-run contract must define a replay-owned trace/evidence artifact that:

- preserves the accepted/refused decision ordering and fields needed for parity;
- is clearly marked as replay/certification evidence;
- never appears as live/paper accounting evidence;
- does not create a second CT-BMS-05 writer;
- can be compared contractually to the production trace.

## Examination battery

### Current registry authority

| Input | Current value | Status |
| --- | --- | --- |
| Walk-forward in-sample window | 6 months | Binding registry value. |
| Walk-forward out-of-sample window | 1 month | Binding registry value. |
| Minimum OOS trades/window | 200 | Binding registry value. |
| OOS expectancy floor | 0.15R after modeled costs | Binding registry value. |
| Monte Carlo permutations | 1,000 | Binding registry value. |
| PBO pass threshold | `< 0.25` | Binding registry value. |
| PBO dead threshold | `> 0.50` | Binding registry value. |

### Recovered method detail — useful, unratified

- Walk-forward may use expanding or rolling windows, with OOS as the primary evidence and below-minimum-trade windows excluded.
- Monte Carlo permutes completed OOS trade sequences and reports 5th/50th/95th distributions for final equity, drawdown, Sharpe and profit factor.
- PBO uses CSCV with 16 subperiods and ranks each IS selection against its OOS complement.
- Aggregate evidence includes the OOS equity curve, MAE/MFE distributions, PBO scalar, Monte Carlo envelope and regime breakdown.

The **numbers** are current. The exact method, window aggregation, annualization, exclusion rules, percentile fields and CSCV `S=16` are donor mechanics until D1 ratifies them.

## Recovered fill-simulation model

### Logic worth recovering

Per-symbol configuration candidates:

- historical/fixed spread model;
- slippage distribution;
- commission schedule;
- partial-fill probability;
- rejection probability, including widened-news conditions.

Recovered per-bar intent:

1. reconstruct and check protection state;
2. replay Book/risk authority and refuse with evidence when unauthorized;
3. apply spread, slippage and commission;
4. produce simulated fill/partial/rejection evidence;
5. replay post-entry protection policy on later market evidence;
6. close with gross result, fees, slippage, achieved R and reason.

### Required re-anchoring

The sequence must be redesigned against:

- the seven ordered doors and the Book's current money ladder;
- breaker/leash effects and KSA levels;
- current Book profile/attribute bindings;
- current news and feed/SQS refusal rules;
- platform-blind Adapter command semantics;
- the unresolved stop-policy and position-fate decisions.

Do not inherit the old exact SL/TP behavior, “BE at +1R,” old kill-switch order, six-clamp risk engine, multiplier stack, equity bands, slot caps, old circuit breaker, or `mode=demo` representation as current facts.

## Disposition register

| Capability or mechanic | Disposition | Reason |
| --- | --- | --- |
| Book-specific certification | **KEEP** | Current FR-4 and Examination boundary. |
| Historical data + simulated execution as the two replay substitutions | **KEEP / formalize** | Current parity and fill-honesty rule; needs exact contract wording. |
| Shared in-house live/replay door and refusal path | **KEEP** | AD-35 requirement. |
| Statistical battery numeric values | **KEEP** | Registry/FR-5 authority. |
| Reproducibility quadruple | **KEEP / extend** | Current test shape, but replay-run schema remains open. |
| Immutable named data snapshots | **KEEP** | Current data identity/provenance doctrine. |
| Manifest-visible CT-MIS-02 bounded query | **KEEP** | Contract plus completed Story 3.6 prerequisite. |
| CT-EXAM-01/02 boundaries | **KEEP / evolve by ratification** | Current consuming surfaces; PE-8 and method details remain open. |
| Independent jobs, no shared mutable state | **KEEP** | Fits deterministic/process-per-run backend topology. |
| Failed-run evidence and dossier linkage | **KEEP** | AD-13 corpus/dossier model. |
| Fill simulator parameters | **RE-ANCHOR** | Useful donor mechanics; exact distributions and semantics unratified. |
| Expanding-vs-rolling WF, MC percentile suite, CSCV S=16 | **RECONFIRM** | Detailed method exists only in recovered baseline. |
| Replay trace mirroring production evidence | **RE-ANCHOR** | Preserve semantic parity without becoming another Records writer. |
| Central Replay Service API | **PROPOSAL** | Useful module seam; service boundary/API/transport not ratified. |
| Research/agent runs sharing the certification engine | **OUT OF THIS BUILD / PROPOSAL** | Agentic customer is outside deterministic D1 recovery. Do not let it drive authority or topology. |
| Certification queue vs exploration queue and caller budgets | **PROPOSAL** | No ratified queue, quota or transport design. |
| Scenario stress for news shocks/spread blowouts/gaps | **DESIGN NEW OR DEFER** | Old Stage H intent exists, but criteria never existed. |
| Old WF2 Stages G–I orchestration | **DROP** | Wrong customer and superseded lifecycle. |
| Old automatic registry write/paper redemption/live progression | **DROP** | Conflicts with unified human promotion and `ADMITTED`. |
| Six-clamp/multiplier/equity-band/slot-cap parity table | **DROP** | Dead authorities replaced by Book/BMS model. |
| Old QML cross-component coupling | **DROP** | QML ends at Book; certification glue is Python. |
| Parameter optimization and signal generation inside certification | **DROP / forbid** | Examination evaluates; it does not create or optimize bot logic. |

## Unresolved decisions and conflicts

### D1 design blockers

1. **Replay-run contract:** submission, status, cancellation, result and evidence-pack schema are absent.
2. **Book/profile binding:** exact identity for Book definition, instance registry, attributes and policy code/version is absent.
3. **Candidate submission:** no current contract explains how a candidate enters the certification pipeline.
4. **Stop-policy parity (PE-8):** the policy version affecting `mean_loss_r`, breaker expectations and position behavior must be pinned into CT-EXAM-01.
5. **Stop-out taxonomy (PE-3):** what counts toward breaker behavior and measured loss is unresolved.
6. **Position fate (PE-7):** open-position treatment at rollover, sweep, kill line and paper transitions is unresolved.
7. **Adapter amendment semantics:** `amend_order`, close/amend priority, idempotency and confirmation remain unratified.
8. **Certification-side paper:** birth-in-paper, warm-up, examination-to-paper and paper-complete semantics were relocated here but not designed.
9. **Data snapshot identity:** canonical manifest serialization and final `data_snapshot_id` derivation remain open.
10. **Archive source selection:** the run must explicitly choose self-recorded versus materialized-backfill and input-availability tier; exact contract placement is open.
11. **Battery procedure:** rolling/expanding policy, MC output schema, CSCV details, insufficient-window behavior and metric definitions need ratification.
12. **Scenario stress:** news shock, spread blowout and gap-open criteria never existed in the old system.
13. **Session/overlap reconstruction:** must be context-only and cannot reintroduce clock authority.
14. **Dual-input reconstruction:** the precise relationship between direct-feed bot input and CT-MIS-01 snapshot evidence is unresolved.
15. **Cohort correlation:** measurement method and `F_CHORUS` threshold are unresolved.
16. **Multi-pair scope:** CT-MIS-02 is pair-bounded; pair-specific boards and cross-pair certification have no current or recovered design.
17. **Synthetic data:** no source defines synthetic exam data; adding it would be fresh design, not recovery.
18. **Artifact retention and storage schema:** certificate corpus placement is fixed; run-artifact layout, retention and indexing are not.
19. **Process/API mechanics:** process-per-run placement is fixed, but submission transport, concurrency, queueing, quotas, failure recovery and cancellation are not.
20. **Evidence equivalence:** the rule for comparing replay traces with production Records without writing into production streams needs an explicit contract.

### Authority collisions to close deliberately

- **Old `same journal schema` vs Records sole writer:** recover semantic equivalence, not a second journal writer.
- **Old WF2 customer vs current Examination/Book customer:** certificates gate later admission; the engine does not register or promote.
- **Old paper lifecycle vs AD-28:** only the fact that pre-live paper belongs certification-side survives; old state transitions do not.
- **Old stop/kill order vs current Book/KSA/Adapter authorities:** no old ordering can be inherited before PE-3/PE-7/PE-8 and amendment priority are ruled.
- **Global bot evaluation vs Book-specific certification:** every run must bind a Book profile and instance values.
- **Recovered central microservice vs adopted node topology:** backend placement is binding, but service-ification is optional design, not current deployment.

## What actually existed in the old repository

### Proven prerequisite

Story 3.6 is marked done and proves a dependency-free backend-node helper that:

- validates the exact CT-MIS-02 request fields;
- reads only manifest-visible Story 3.5 archive artifacts;
- filters by pair, half-open UTC interval and exact labeler identities;
- returns stable ordered identities and a SHA-256 result hash;
- surfaces hidden/corrupt evidence without returning it;
- rejects bad bounds, unsafe partitions, extra authority fields and mutation attempts;
- has no dependency on MIS-Live or trading behavior.

### Explicitly not built by Story 3.6

- Examination Engine;
- certificate generation;
- replay-run schema;
- Book-aware parity;
- fill simulator;
- Records/veto replay;
- bot validation;
- materialized backfill generation;
- API, CLI, UI, scheduler or runtime service transport;
- DuckDB/PostgreSQL query runtime integration;
- BMS/Book/KSA decisions or any trading behavior.

This distinction is essential. The old repository contained a replay **input-serving proof**, not the recovered Backtesting Engine itself.

## Recommended clean-restart kernel

The smallest coherent D1 design session should ratify six seams before implementation:

1. `ReplayRunSpec` — immutable identities for bot, Book/profile, data, labelers, configuration, policy versions, fill model, engine version and seed.
2. `ReplayEvidencePack` — result identity, replay trace, refusal trace, fills/costs, OOS trades, MAE/MFE, battery outputs and content hashes.
3. `ExamRun` lifecycle — submitted, validated, running, completed/failed/cancelled, with deterministic retry semantics and no live authority.
4. Production-policy adapter — the exact in-house functions shared with live door, refusal, money, protection and evidence evaluation.
5. Certificate issuance — CT-EXAM-01/02 evolution, failure evidence, stop-policy pinning and certificate invalidation triggers.
6. Certification-side paper boundary — define its states and evidence separately from the trading node, without restoring WF2's dead registration/promotion mechanics.

Only after those are ratified should the recovered fill and battery methods be selected and written as build requirements.

## Evidence index

### Current wiki

- `C:\Users\Mubarak\Documents\QMX\wiki\topics\backtest-and-replay.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\components\examination-engine.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-mis-02-mis-archive-replay-query.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-exam-01-exam-certificate.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-exam-02-cohort-correlation-certificate.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\architecture\runtime.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\architecture\components.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\architecture\data-and-contracts.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\architecture\proposed-service-boundaries.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\system\lifecycle.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\lenses\quality-and-testing.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\lenses\data-and-ml.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\knowledge\gap-report.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\open-questions.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\sources\local-cleaned-recovered-design-artifacts.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\sources\bmad-planning-run-2026-07.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\log.md`

### Current planning authority

- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\ARCHITECTURE-SPINE.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\prds\prd-QMX-2026-07-20\prd.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\prds\prd-QMX-2026-07-20\addendum.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\epics.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\research\examination-lineage-coverage-audit.md`

### Later prerequisite proof

- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-3-6-bounded-replay-query-serving-ct-mis-02.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\story-3-6-progress.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\story-3-6-acceptance.json`

### Recovered donor evidence

- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\backtest-engine-spec.md`
- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\clash-report-backtest-replay.md`
- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\clash-report-sltp-vs-book.md`
- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\deterministic-coverage-map.md`
- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\microservices-proposal.md`

