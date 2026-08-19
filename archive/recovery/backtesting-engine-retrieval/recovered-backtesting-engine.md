# Recovered Backtesting / Examination Engine

## 1. Recovery verdict

The former repository supports recovery of this target:

> **A backend-node Examination Engine using an in-house, deterministic, book-specific replay harness.**

It does not support copying an already-built engine. The actual engine remained **Deferred D1** and had no story set or executable runner. The working code stopped at replay-input infrastructure.

Use the names deliberately:

- **Examination Engine** — the book-specific certification component, job lifecycle, battery, evidence and certificates.
- **Replay harness** — the deterministic execution mechanism used by an examination run.
- **Backtest Engine** — historical/recovered vocabulary; acceptable conversationally, but the old WF2-embedded component must not be restored wholesale.
- **Replay Service** — a recovered proposal for an API/module seam, not a ratified deployable microservice.

## 2. Status model

| Class | Meaning in this recovery |
| --- | --- |
| `KEEP` | Binding architecture/requirement from the old project's later active layer. |
| `SUBSTRATE` | A real verifier-backed prerequisite, not the engine. |
| `RECONFIRM` | A useful recovered mechanic or old-project value that needs a new-project decision. |
| `DESIGN` | Required seam with no complete authoritative old design. |
| `DROP` | Superseded WF/authority/lifecycle mechanics or a false implementation claim. |

## 3. Recovered responsibility and authority

The engine answers one question:

> Does this immutable bot specification retain a cost-adjusted edge under production-equivalent behavior when evaluated against this exact Book profile and its pinned policy versions?

The engine may:

- request bounded, version-pinned historical evidence from MIS-Archive;
- execute/evaluate QML-authored bot logic through an explicit Python boundary;
- replay Book policy, protection effects, costs and refusals;
- simulate broker execution through in-house fill physics;
- calculate the registry-governed examination battery;
- emit immutable CT-EXAM-01 and CT-EXAM-02 evidence;
- produce per-run evidence and CT-EXAM payloads for publication through Backend-owned writer/finalizer boundaries; the worker-to-publisher seam remains `DESIGN`;
- preserve passing, failing and invalidated evidence.

The engine may not:

- authorize trading, admission or promotion;
- mutate a bot specification, signal logic, Book profile or registry value;
- mutate or optimize the frozen candidate during a certifying run;
- write authoritative Trading Node state;
- become another BMS Records writer;
- bypass labeler, data, configuration, Book-policy or stop-policy parity;
- omit live refusals or inconvenient production behavior;
- run in or block the Trading Node hot path.

The former design did not settle whether D1 may expose a **separate** optimization-orchestration facility. That is `RECONFIRM`/`DESIGN`; it must never blur the immutable candidate boundary or own fill, Book, door or refusal semantics.

## 4. Placement and process model

| Decision | Recovered state |
| --- | --- |
| Host | `KEEP`: Backend Node, the always-on evidence home. |
| Runtime isolation | `KEEP`: exam jobs are process-per-run workers under the Backend Node supervisor. |
| Hot-path relationship | `KEEP`: completely off the Trading Node hot path; Backend/Exam failure does not block trading. |
| Class-3 access | `KEEP`: each runner reads manifested Parquet through its own read-only DuckDB/process context. |
| Archive writes | `KEEP`: the Backend service is sole Parquet writer/finalizer; exam workers are not archive writers. |
| Engine implementation | `KEEP`: in-house rebuild. Donor engines are lenses only. |
| Service/API topology | `DESIGN`: no ratified queue, RPC, scheduler, REST API or central Replay Service boundary exists. |
| Resource policy | `DESIGN`: concurrency, CPU/memory budgets, cancellation, retry and prioritization are unset. |

The certification area is replaceable behind CT-MIS-02 and CT-EXAM-01/02. Replaceability does not permit different fill, Book, door or refusal semantics.

## 5. Logical flow

```text
frozen bot spec + target Book/profile + pinned policies/configuration
                                  |
                                  v
                 ReplayRunSpec / candidate submission
                         [currently DESIGN]
                                  |
                                  v
                    CT-MIS-02 bounded query
                  Exam -> MIS-Archive -> Exam
                                  |
                                  v
             deterministic book-aware replay harness
                historical data for live feed
                fill simulator for real adapter
                everything else production-equivalent
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
                Backend corpus + per-bot dossier
                                  |
                                  v
           later human promotion pull and Trading-side gate
```

Certificates are evidence. They are not permission to trade.

## 6. Load-bearing invariants

| ID | Invariant | Status |
| --- | --- | --- |
| INV-01 | Certification is for one immutable bot specification against one specific Book contract/profile. No abstract “certified bot” state exists. | `KEEP` |
| INV-02 | Replay/live parity permits exactly two substitutions: historical data for live ticks, and an in-house fill simulator for the Adapter. | `KEEP` |
| INV-03 | Book policy, ordered doors, formulas, protection, costs and refusal behavior use the same in-house semantics as live. | `KEEP`; shared seam still `DESIGN` |
| INV-04 | Every relevant refusal is reproduced, ordered and visible in replay evidence. Easier-than-production evidence is invalid. | `KEEP` |
| INV-05 | Run identity contains no ambient time or randomness. Clock, bounds and seed are explicit inputs. | `KEEP` |
| INV-06 | Minimum reproducibility identity is `bot_spec_version + data_snapshot_id + config_hash + seed`. | `KEEP` principle; full schema `DESIGN` |
| INV-07 | `config_hash` represents resolved registry values and attribute/policy bindings in force for the run. | `KEEP` |
| INV-08 | Exact financial arithmetic uses scaled integers/Decimal; binary float is allowed only for replay-stable statistics and labeler features. | `KEEP` |
| INV-09 | Labeler-version mismatch invalidates a certificate and blocks live use until recertification. Any stop policy shaping measured loss must eventually pin and invalidate the same way. | `KEEP`; PE-8 open |
| INV-10 | Replay reads immutable, manifested data and explicitly selects source class/input-availability tier. No partial-version or live-updating fallback is allowed. | `KEEP` |
| INV-11 | Exam runners are read-only over Class-3 Parquet. The Backend service is the sole Class-3 writer/finalizer; one registered exam-host writer owns each certificate-corpus/dossier table family; BMS Records remains the sole writer of authoritative trading streams. The worker→publication seam is `DESIGN`. | `KEEP` ownership; seam `DESIGN` |
| INV-12 | Failed runs and invalidated certificates remain immutable evidence; corpus presence never means current validity. | `KEEP` |
| INV-13 | Sessions/overlap may be measured context but never restored as clock-window permission. | `KEEP` |
| INV-14 | The engine evaluates. It does not generate signal logic, mutate candidates, self-register, self-promote or decide live entry. | `KEEP` |

## 7. Run and certification lifecycle

The following lifecycle reconstructs the current intent. Items marked `DESIGN` are required seams, not claims about old implementation.

1. **Candidate identity freezes.** Stable `bot_id` plus immutable `bot_spec_version`; mutation creates a new version.
2. **Target contract freezes.** Exact Book definition/profile, registry state, attributes and behavior-shaping policy versions are selected.
3. **ReplayRunSpec is accepted.** `DESIGN`: submission, validation, run id, status and idempotency contract do not exist yet.
4. **Historical evidence freezes.** Select immutable `data_snapshot_id`, source class, input-availability tier, UTC bounds, pair/resolution and labeler versions.
5. **CT-MIS-02 retrieves inputs.** The bounded query returns only manifest-visible, exact-version emissions.
6. **Replay executes shared physics.** Historical input and simulated fills are the only substitutions; decisions and refusals remain production-equivalent.
7. **Battery executes.** Cost-adjusted OOS evidence drives walk-forward, Monte Carlo and PBO results.
8. **Evidence pack seals.** `DESIGN`: trace, fills, refusals, metrics, artifacts and hashes require a new schema.
9. **Certificates issue.** CT-EXAM-01 and, where measurable, CT-EXAM-02 are written to the Backend corpus/dossier.
10. **Certification-side paper belongs to D1.** Birth-in-paper, warm-up, CT-BOOK-02 flip, exam-to-paper and paper-complete mechanics must be designed; their placement survived, not their old workflow.
11. **Human promotion remains separate.** The Trading Node later pulls and revalidates evidence at the operator click. No exam result self-promotes.

The old WF2 Stage G→H→I pipeline is not this lifecycle.

## 8. ReplayRunSpec — minimum recovered design input

No authoritative schema existed. A fresh design must at least decide explicit bindings for:

| Field group | Required meaning |
| --- | --- |
| Candidate | `bot_id`, immutable `bot_spec_version`, bot-code repository/commit/path or equivalent code identity. |
| Target | Book type/definition/profile/instance identity and schema version. |
| Configuration | `config_hash`, resolved registry version/values, attribute bindings and policy versions. |
| Market evidence | `data_snapshot_id`, source class, input-availability tier, venue/platform/instrument, pair/resolution, UTC bounds. |
| Intelligence | Exact labeler ids, versions and parameter-set identities. |
| Protection | Door implementation/version, KSA policy/effects, news behavior, breaker/leash rules, stop-policy version. |
| Execution | Fill-model id/version, cost schedule, spread/slippage/commission/partial/rejection configuration. |
| Determinism | Explicit seed, replay-engine/code version, canonical serialization version. |
| Control | Run id, submitter class, idempotency key, resource budget, cancellation/retry policy. |

These fields belong to a replay-run contract, not CT-MIS-02.

## 9. CT-MIS-02 input boundary

Story 3.6 fixes exactly five request fields:

- `query_id`
- `pair`
- `start_utc`
- `end_utc`
- `labeler_versions`

Direction is Exam→MIS-Archive request and MIS-Archive→Exam result. The completed proof:

- validates explicit UTC bounds with `end_utc > start_utc` and canonical pair/version identity; the proof helper selects `[start_utc, end_utc)`, but that interval convention is substrate behavior pending contract ratification;
- reads only manifest-visible Story 3.5 artifacts;
- refuses hidden, corrupt, unsafe or extra-authority inputs;
- orders results deterministically;
- hashes results using canonical JSON and SHA-256;
- performs no archive mutation.

CT-MIS-02 is the **input retrieval seam**, not an engine submission/result contract. Its internal archive locator does not become a CT field.

## 10. Examination battery

### 10.1 Old-project registry authority

| Input | Old-project value | Fresh-restart treatment |
| --- | --- | --- |
| Walk-forward in-sample window | 6 months | `RECONFIRM` while preserving its prior binding status. |
| Walk-forward out-of-sample window | 1 month | `RECONFIRM`. |
| Minimum OOS trades per window | 200 | `RECONFIRM`. |
| OOS expectancy floor | 0.15R after modeled costs | `RECONFIRM`. |
| Monte Carlo permutations | 1,000 | `RECONFIRM`. |
| PBO pass threshold | `< 0.25` | `RECONFIRM`. |
| PBO dead threshold | `> 0.50` | `RECONFIRM`. |

FORM-0009 and FORM-0010 remain the cost-aware examination formulas:

- expectancy: `EV = p * W - (1 - p) * L - c`
- break-even condition: `p > (L + c) / (W + L)`

### 10.2 Recovered method candidates

The old-vault spec adds valuable but unratified mechanics:

- expanding or rolling walk-forward, with aggregated OOS as primary evidence;
- exclusion/explicit handling of windows below the minimum trade count;
- Monte Carlo permutations of completed OOS trades, reporting 5th/50th/95th distributions for final equity, drawdown, Sharpe and profit factor;
- PBO through CSCV with 16 subperiods;
- OOS equity curve, MAE/MFE, regime breakdown, PBO scalar and Monte Carlo envelope.

All method definitions, annualization, percentile schema, insufficient-window treatment and CSCV `S=16` are `RECONFIRM`, not recovered authority.

### 10.3 Honesty acceptance

The old project's SM-6 requires:

- multiple overfit archetypes fail;
- a known-good control passes;
- a mismatched-labeler certificate blocks live use.

This acceptance obligation is `KEEP`. It was never implemented.

## 11. Fill simulator recovery

### 11.1 Valuable candidates

Per-symbol configuration candidates from the recovered engine:

- historical or fixed spread model;
- slippage distribution;
- commission schedule;
- partial-fill probability;
- rejection probability, including widened-news conditions.

Candidate execution sequence:

1. reconstruct current market/protection evidence;
2. evaluate the shared Book/door/protection policy and record any refusal;
3. apply spread, slippage and commission;
4. produce fill, partial-fill, reject and attribution evidence;
5. replay the current post-entry protection policy against later evidence;
6. close with gross outcome, fees, slippage, achieved R and close reason.

### 11.2 Mandatory re-anchoring

The simulator must be redesigned against the new:

- seven doors and Book money ladder;
- breaker/leash effects and KSA levels;
- Book/profile/attribute bindings;
- current news, feed and SQS refusal rules;
- platform-blind Adapter command and fill semantics;
- stop-policy, amendment, close-priority and position-fate decisions.

Do not inherit the old exact `BE at +1R`, old SL/TP service, old kill-check ordering, six-clamp, multiplier stack, equity bands, slot caps or circuit-breaker behavior.

## 12. Output evidence and certificate boundaries

### 12.1 ReplayEvidencePack (`DESIGN`)

A new immutable evidence-pack contract should decide:

- run identity and status;
- input/manifests/policy/code hashes;
- ordered decision/refusal trace;
- simulated command/fill/cost trace;
- trade-level OOS evidence;
- equity, drawdown, MAE/MFE and regime artifacts;
- walk-forward, Monte Carlo and PBO output schemas;
- failure/cancellation/insufficient-data evidence;
- content hashes and storage references.

“Same journal schema” must mean semantic comparability with production evidence. It must not mean writing replay rows into authoritative BMS Records tables or misusing live/paper modes.

### 12.2 CT-EXAM-01

The draft inherited contract contains:

- `bot_id`
- `book_profile`
- `labeler_versions`
- `ev_by_regime`
- `mean_loss_r`
- `fire_rate_band`
- `breaker_expectation`
- `cost_ratio`

Later architecture also expects immutable bot-spec identity, data-source/input-availability evidence and eventually every policy version shaping loss—especially stop policy. Those extensions require ratification.

Labeler mismatch invalidates the certificate. PE-8 blocks complete parity until stop-policy pinning is designed.

### 12.3 CT-EXAM-02

Draft fields are:

- `cohort_id`
- `book_id`
- `correlation_observations`
- `expected_loss_shape`
- `certified_at_utc`

The correlation method and `F_CHORUS` threshold remain open under GAP-0012. Missing measurement must remain explicit rather than producing an invented threshold.

## 13. Data and evidence placement

| Evidence | Placement/authority |
| --- | --- |
| Canonical/materialized history | Backend Class-3, manifested and immutable. |
| Archive partition order | `source_class / venue_triple / pair / date / resolution`. |
| Replay artifacts | Backend Class-3. Exam runners read; the Backend service is the sole Parquet writer/finalizer. Exact worker→publication handoff is `DESIGN`. |
| Full CT-EXAM-01/02 corpus | Backend PostgreSQL evidence corpus, with one registered exam-host writer for its table family. |
| Per-bot dossier | Backend evidence assembly under its registered table-family writer; passing and failing artifacts remain linked. |
| Operative certificate validity | Trading Node Class-1 certificate index only; Backend corpus presence never implies validity. |

Every source class remains distinct. A run must not silently combine self-recorded, materialized-backfill, synthetic, derived or shadow evidence.

## 14. What actually existed in the old repository

| Surface | What existed | Verdict |
| --- | --- | --- |
| Backend entrypoint | `main.py` returns an inert scaffold description, including the planned exam-runner process layout. | Not an engine or service. |
| Backend supervision | The systemd unit invokes a scaffold function, prints its metadata and sleeps; it starts no replay worker, query endpoint, PostgreSQL process or scheduler. | Operational placeholder only. |
| Historical acquisition | A real Dukascopy CLI downloaded and decoded `.bi5` ticks into raw Parquet with manifests/checkpoints; a large raw corpus exists. | Useful evidence, but sampled validation refuses canonical use with `SOURCE_LICENSE_NOT_CANONICAL_USABLE`. |
| Story 3.5 | Dependency-free immutable archive publication/visibility proof. | `SUBSTRATE`; not a production Parquet service. |
| Story 3.6 | Dependency-free `serve_bounded_replay_query` helper, ratified standard and CI verifier. | `SUBSTRATE`; replay input only. |
| Story 3.7 | Dependency-free labeler-materialization proof publishing replay-visible evidence. | `SUBSTRATE`; not a scheduler or real materialization service. |
| Backend PostgreSQL | Migration-plan/DDL discipline reserves certificate corpus and dossier table families for `exam-host`. | `SUBSTRATE`; no certificate generator/corpus writer/runtime database integration. |
| Examination Engine | No runner, module, entrypoint, scheduler, fill simulator, battery executor or run lifecycle. | Unbuilt, Deferred D1. |
| Certificate generation | No CT-EXAM-01/02 issuer existed. | Unbuilt, Deferred D1 with no engine story. |
| Certificate validity consumer | No Trading-side certificate index or L10 cascade existed. | Unbuilt; Story 9.6 backlog. |
| Shared live/replay physics | No complete Adapter, Doors, KSA or QML runtime to share. | Unavailable in the former build. |
| Historical data bridge | Real raw Dukascopy acquisition exists, but canonical admission/licensing, clean merge, feature materialization, and conversion into Story 3.5/3.6 replay-visible evidence are not wired. | Insufficient to run honest examination. |

The Story 3.6 standard is explicit: `exam_engine_implemented: false`. Its non-goals include examination, certificates, complete replay-run schema, Book-aware parity, fill simulation, Records/veto replay and bot validation.

## 15. Completion and dependency traps

The following old story statuses must not be mistaken for engine readiness:

- “Story 3.6 done” means the bounded archive reader proof passed—not that backtesting worked.
- “Epic 2 done” did not itself prove that canonically usable history was ready. Separately inspected filesystem evidence shows a real large multi-year raw Dukascopy corpus, but it is incomplete/unsealed as an authoritative run, its licensing gate refuses canonical use, and no replay bridge exists.
- Story 3.8 canonical-feed binding and Story 3.9 raw capture/shadow readiness were backlog.
- Adapter Stories 4.1–4.3 were backlog.
- all Book Doors/protection projection work in Epic 6 was backlog.
- all KSA work in Epic 7 was backlog.
- all QML work in Epic 8 was backlog.
- admission, promotion, certificate index and parity cascade in Epic 9 were backlog.

Because the required production policy code was not wired, the old repository could not prove live/replay parity end to end.

## 16. Open design register

| ID | Unresolved seam | Required treatment |
| --- | --- | --- |
| O-01 | Candidate-submission contract | `DESIGN` |
| O-02 | ReplayRunSpec, run state, idempotency, retry and cancellation | `DESIGN` |
| O-03 | Exact Book/profile/config/policy identity | `DESIGN` |
| O-04 | Shared live/replay policy adapter | `DESIGN` after new Book/Doors interfaces stabilize |
| O-05 | Fill physics and cost-model calibration/versioning | `RECONFIRM` candidates, then `DESIGN` |
| O-06 | Stop-out taxonomy (PE-3) | `DESIGN` |
| O-07 | Position fate at boundaries (PE-7) | `DESIGN` |
| O-08 | Stop-policy version pinning (PE-8) | `DESIGN` before CT-EXAM-01 is complete |
| O-09 | Adapter amend/partial-close/priority/idempotency | `DESIGN` with execution boundary |
| O-10 | Exact battery methods and metric definitions | `RECONFIRM` |
| O-11 | Cohort-correlation computation and `F_CHORUS` | `DESIGN`; threshold stays null |
| O-12 | Scenario stress for news, spread blowout and gaps | No criteria existed; `DESIGN` or defer |
| O-13 | Session overlap and dual-input reconstruction | `DESIGN`; context only, never authority |
| O-14 | Multi-pair/cross-pair certification | No recoverable design; `DESIGN` only if required |
| O-15 | Synthetic exam data | No source; not a recovered feature |
| O-16 | Certification-side paper/warm-up/paper-complete lifecycle | `DESIGN`; old WF2 mechanics do not fill it |
| O-17 | Activation timing after `ADMITTED` | Operator decision |
| O-18 | Replay artifact storage, retention and indexing | `DESIGN` within fixed Backend placement |
| O-19 | Certificate issuance transaction and invalidation crossing | `DESIGN`; Trading validity remains one truth |
| O-20 | Process scheduling, concurrency, quotas, cancellation and recovery | `DESIGN` |
| O-21 | CT-MIS Story 3.5/3.6 `emission_utc` contract mismatch | Resolve in contract; no reader fallback invention |
| O-22 | Actual canonical market data and source/license validity | Acquire and prove; old governance is not data |
| O-23 | Canonical manifest serialization before hashes become durable identity | `DESIGN`/ratify |
| O-24 | Evidence equivalence without a second Records writer | `DESIGN` replay trace contract |
| O-25 | CT-MIS-02 interval inclusion (`[start,end)` is helper behavior, not yet contract authority) | `RECONFIRM`/ratify |
| O-26 | Exam-worker output handoff to the sole Class-3 finalizer and registered corpus/dossier writers | `DESIGN` without adding writers |
| O-27 | PE-4 Kelly-input registration required for parity with final live `take` sizing | Resolve before honest certification |
| O-28 | PE-5 KSA trigger→level/effects matrix, including fail-closed unknown/unmapped behavior | Resolve before protection parity |
| O-29 | CT-QML-01, compiler and runtime boundary used to execute the pinned bot specification | `DESIGN`; Epic 8 backlog is a hard dependency |
| O-30 | Separate optimization-orchestration scope, if any | `RECONFIRM`/`DESIGN`; never mutate the certifying candidate |

## 17. Do not recover

| Old mechanic | Disposition |
| --- | --- |
| WF1 mechanics and old WF2 Stages G–I orchestration | `DROP` |
| Weakness buckets, typed reviewer mail and workflow-owned registration | `DROP` |
| Six-clamp, multiplier stack, equity bands, slot caps and old circuit breaker | `DROP` |
| DPR/PRS ranking, tiers, global pools and slot auctions | `DROP` |
| Automatic registry write, paper redemption, probation and automatic live progression | `DROP` |
| Session windows as trading authority | `DROP` |
| Identifier recycling or in-place revival | `DROP` |
| Reverted agentic architecture, queues, budgets and shared research-service claims | `DROP` from this recovery |
| General-purpose strategy-development playground scope | `DROP` for V1 |
| A claim that the former repository already had a Backtesting Engine | `DROP` as false |

WF2 survives only as a boundary name for an agentic-driven backtest→paper iteration ending at paper-complete. Its internal workflow is outside this recovery and cannot authorize live promotion.

## 18. Smallest coherent fresh design

Before implementation, ratify seven seams:

1. **ReplayRunSpec** — immutable bot, Book, data, labeler, configuration, policy, fill-model, engine and seed identities.
2. **ReplayEvidencePack** — decisions, refusals, fills/costs, OOS trades, artifacts, battery outputs and hashes.
3. **ExamRun lifecycle** — accepted/refused, validated, queued/running, completed/failed/cancelled, retry and resource semantics.
4. **Production-policy adapter** — exact functions shared with live Book/doors/money/protection/refusal evaluation, including resolved PE-4 Kelly inputs and the PE-5 KSA matrix.
5. **Certificate issuance** — CT-EXAM evolution, failure evidence, stop-policy pinning, corpus transaction and invalidation triggers.
6. **Certification-side paper boundary** — states and evidence distinct from Trading Node fail-mechanism paper and without old WF2 promotion authority.
7. **QML execution boundary** — CT-QML-01, compiler/runtime identity, deterministic invocation and failure behavior for the pinned bot specification.

Only after those seams are explicit should the recovered fill model and statistical procedures be selected as build requirements.
