# Backtesting / Examination Engine — BMAD Status and Recovery Evidence

> Scope: documentation-only recovery scout of the BMAD planning and delivery record in the old QMX repository. This report distinguishes the intended Backtesting/Examination Engine from adjacent proof mechanisms that were actually completed. Agentic workflow internals are excluded except where they define a direct certification boundary.
>
> Evidence window: planning artifacts through 2026-07-24; sprint status through 2026-07-28; reconciliation audit through 2026-08-10.

## Executive finding

The old repository did **not** contain a completed Backtesting or Examination Engine. BMAD deliberately put the engine in **Deferred D1**, to be rebuilt in-house in a dedicated design session on the **backend node**. No D1 epic or story was cut, and no exam/backtest implementation story appears in `sprint-status.yaml`.

What BMAD did build was a proof-shaped substrate around the future engine:

- immutable MIS-Archive emission storage;
- deterministic, bounded CT-MIS-02 replay-query serving;
- an offline labeler-materialization lane;
- data-acquisition, provenance, and curation proof contracts;
- backend-node topology and storage boundaries that reserve an examination host;
- trading-side plans for certificate consumption, parity invalidation, admission, and promotion.

Those adjacent surfaces are useful recovery material, but they are **not** evidence that a backtest runner, fill simulator, statistical battery, certificate generator, or end-to-end certification flow was built. The repository's own 2026-08-10 reconciliation calls the implemented system “design/proof-shaped” and “not a wired running trading node.”

## 1. Authority and chronology

Use this order when the sources disagree:

1. `planning-artifacts/architecture/architecture-QMX-2026-07-20/ARCHITECTURE-SPINE.md` — final topology-v2 architecture, including AD-5, AD-13..20, AD-27/28, AD-35, AD-39/40 and the explicit Deferred section.
2. `planning-artifacts/prds/prd-QMX-2026-07-20/prd.md` — current functional and non-functional requirements after the 2026-07-24 update.
3. `planning-artifacts/epics.md` — topology-v2 epic re-derivation; explicitly supersedes the pre-v2 epic document.
4. `implementation-artifacts/sprint-status.yaml` — delivery status as of 2026-07-28.
5. Ratified `standards/*.json` and story specifications — authoritative only within each story's deliberately narrow proof boundary.
6. `implementation-artifacts/reconciliation-report.md` — read-only truth audit dated 2026-08-10; strongest evidence of what “done” meant in the old repository.
7. `architecture/.../research/examination-lineage-coverage-audit.md` — 2026-07-20 coverage audit, useful for gaps and recovered-only mechanics; explicitly a research artifact, not a design authority.

Do not treat the reverted agentic run under `_bmad-output/attic/2026-07-22-agentic-run-reverted/` as authority. `epics.md` SR-2 says it was fully skipped.

## 2. Intended system boundary

### 2.1 Name and product role

The current planning language is **Examination Engine** or **examination pipeline**, not a general-purpose backtesting product. The PRD explicitly says replay serves examination and possible future read-only research; it is not a V1 strategy-development playground.

The engine's purpose is to certify a candidate bot **against a specific book profile**, never in the abstract. It answers two questions:

1. Is the edge real after modeled costs?
2. Is the candidate statistically honest rather than an overfit fiction?

Its outputs are evidence:

- **CT-EXAM-01** exam certificate;
- **CT-EXAM-02** cohort-correlation certificate.

The engine has no trading or admission authority. A passing certificate cannot authorize live trading, mutate a book profile, bypass parity, or seat a bot. The Book's entrance-exam/admission path consumes the evidence, and the operator's promotion click remains the human ratification act.

### 2.2 Placement and process model

The host placement was closed in topology v2:

- the Examination Engine belongs on the **backend node**;
- the backend node is the durable evidence home;
- replay is off the hot path;
- exam jobs are **process-per-run** under the backend-node supervisor;
- exam runners read Class-3 Parquet data through their own DuckDB process and never share a writable DuckDB file;
- the backend-node service is the sole Parquet writer/finalizer; exam jobs are read-only consumers.

The certification area is intended to be replaceable behind CT-EXAM-01, CT-EXAM-02, and CT-MIS-02. This replaceability does not license alternate policy semantics: fill simulation and door/refusal evaluation must use shared in-house logic consistent with live behavior.

### 2.3 In-house ruling

The wrapped-OSS-engine option was explicitly narrowed off. The engine was to be rebuilt **in-house** in its own design session. Named donor projects—backtesting.py, QuantDinger, Blankly, and AutoTrader—were lenses for mechanics only, never engines to wrap or current authority.

This matters for recovery: donor mechanics may be mined as candidates, but no recovered donor behavior should be promoted as QMX architecture without a fresh decision.

## 3. Binding examination semantics

### 3.1 Book-specific certification

FR-4 requires every run and certificate to name the target book profile. There is no portable, abstract “certified bot” status. A bot may be certified for one book profile and not another.

Replay input is bounded through CT-MIS-02 by:

- `pair`;
- UTC start and end;
- exact `labeler_versions`;
- a request `query_id` in the later ratified proof standard.

### 3.2 Registry-backed battery

The PRD carries these current battery values from DEC-0036:

- walk-forward: 6 months in-sample / 1 month out-of-sample;
- at least 200 OOS trades per window;
- at least 0.15R OOS expectancy after modeled costs;
- 1,000 Monte Carlo shuffles;
- PBO pass below 0.25;
- PBO dead above 0.50.

These values were current requirements, but the **procedures** were not fully current. The coverage audit says the following method detail survived only in a recovered, non-authoritative backtest spec:

- Monte Carlo as 1,000 permutations of OOS trades with 5th/50th/95th equity envelopes;
- PBO via CSCV with 16 sub-periods;
- the choice and exact mechanics of expanding versus rolling walk-forward.

Disposition: preserve those as design candidates, not as automatically ratified semantics.

### 3.3 Certificate content and parity

CT-EXAM-01 is expected to carry at least:

- target book/profile identity;
- bot identity and immutable `bot_spec_version`;
- bound labeler versions;
- EV by regime;
- mean loss, `Lbar`;
- fire-rate band;
- breaker expectation;
- cost ratio;
- data-source class and input-availability tier under AD-17;
- eventually every policy version that shapes measured loss, especially the stop-policy version.

CT-EXAM-02 carries cohort-correlation observations and expected loss shape. The chorus/correlation threshold remains unresolved (`GAP-0012`); the engine may record observations but must not invent a promotion threshold.

The L10 parity rule is binding:

- a labeler-version mismatch voids the certificate;
- affected bots stay blocked from live until recertified;
- the future stop-policy version must behave the same way once position-safety design is ratified.

PE-8 is the explicit blocker for extending CT-EXAM-01 with stop-policy pinning.

### 3.4 Reproducibility and parity

NFR-3 defines a replay identity tuple:

`bot_spec_version + data_snapshot_id + config_hash + seed`

Replay/live parity permits exactly two substitutions:

1. historical data replaces live ticks;
2. a fill simulator replaces the real adapter.

Everything else must follow the shared live path: Book policy, door ordering, formulas, costs, protection rules, and refusals. Refusal/veto parity is part of the obligation. Reproducibility therefore requires explicit time and randomness; ambient clocks and ambient random seeds are forbidden.

The exact replay-run schema was still deferred to the engine design session. The tuple and two-substitution rule were binding principles, not a completed run contract.

### 3.5 Arithmetic

Money, prices, equity, and sizing remain exact across replay:

- platform-scaled integers at boundaries;
- fixed-context Python `Decimal` for derived money math;
- no binary float on money/equity/sizing paths.

Floats are allowed only for examination statistics and labeler feature computation, and then only in replay-stable formulations.

### 3.6 Honesty acceptance

SM-6 requires a battery-honesty proof:

- multiple overfit archetypes must fail;
- a known-good control must pass;
- a mismatched-labeler certificate must block live.

This success metric deferred with D1. It was never delivered.

## 4. Data and evidence dependencies

### 4.1 Dataset identity

Every historical dataset carries a provenance manifest. The manifest hash is `data_snapshot_id`. Canonical, derived, synthetic, shadow, captured-feed, self-recorded, and materialized-backfill data must remain in distinct namespaces and cannot silently mix.

The materialized labeler lane must run the same versioned labeler code used live over cleaned backfilled history. Certificates must name:

- source class (`self_recorded` or `materialized_backfill`);
- input-availability tier;
- input dataset manifest identity;
- exact labeler versions.

### 4.2 Archive layout

The ratified Story 3.5 proof uses this partition order:

`source_class / venue_triple / pair / date / resolution`

Publication is temp-write then final rename, with a manifest required before reader visibility. Visible emissions are immutable; corrections receive new identities.

### 4.3 Certificate storage split

The architecture separates certificate authority from certificate evidence:

- the full CT-EXAM-01/02 corpus and per-bot dossier live on the backend node;
- the operative certificate index lives as Class-1 authority on the trading node;
- validity has one truth: the index and its CDC replica;
- the corpus preserves evidence as issued and must not be interpreted as current validity.

The proposed index columns were `cert_id`, `bot_spec_version`, bound labeler versions, and validity. However, the story that would build this index—Story 9.6—remained backlog.

## 5. Pre-live paper and promotion boundary

Topology v2 moved all **pre-live** paper phases out of the trading node and into the certification side:

- birth-in-paper;
- warm-up ramp;
- CT-BOOK-02 warm-up flip;
- exam-to-paper.

The trading node retained only fail-mechanism paper: kill-line stand-down and breaker bench.

This relocation did not produce a completed certification-side state machine. `warm_up_days` was retired from trading-node registry scope, and its meaning was deferred to the exam design session. The coverage audit confirms there was no current, fully defined post-exam paper/promotion pipeline.

Live promotion was planned as:

1. the engine produces evidence on the backend node;
2. the operator clicks promote;
3. the trading node initiates a manifest-verified pull;
4. it re-runs admission preconditions server-side against fresh trading-node state;
5. on success it atomically writes the definition, certificate references, and placement into Class-1 stores as `ADMITTED`;
6. `ADMITTED` has no intents and no ledger;
7. birth and LIVE later land atomically at the activation boundary.

Neither the promotion epic nor the certificate-index story was implemented. The proposed “next rollover” activation boundary also remained an operator-confirmation assumption.

## 6. What BMAD actually completed

The following items were marked done and audited as real but narrowly scoped deliverables.

| Item | Status | What exists | What it expressly does not mean |
|---|---|---|---|
| Story 3.5 — MIS-Archive immutable storage | Done, verifier-backed proof | Backend storage/finalization discipline, disjoint partitions, manifest-gated immutable visibility | Not a live Parquet pipeline, not an exam runner |
| Story 3.6 — bounded CT-MIS-02 replay query | Done, verifier-backed proof | Read-only query validation and stable evidence/hash for identical explicit bounds | No examination engine, replay-run schema, fill simulation, Book-aware parity, certificate generation, or bot validation |
| Story 3.7 — labeler materialization lane | Done, verifier-backed proof | Validates offline use of the same labeler identities over manifested history and publishes materialized-backfill-shaped evidence | No actual scheduled materialization service, model training, exam run, certificate, or real Parquet/DuckDB runtime |
| Epic 2 data acquisition stories | Marked done at proof/design altitude | Source posture, acquisition/clean/maintain manifest rules, curation gates, join validation, actual-depth evidence requirements | No real five-year history acquisition, external downloader, real market-data files, canonical Parquet dataset, or production curation service |
| Backend topology/storage foundation | Done at design/proof altitude | Reserved backend process/storage roles, Postgres migration discipline, sync proof mechanisms | Does not make the backend a wired examination host |

The ratified Story 3.6 standard explicitly sets `exam_engine_implemented: false` and lists all of these as non-goals:

- examination engine;
- certificate generation;
- complete replay-run schema;
- Book-aware replay parity;
- fill simulation;
- Records/veto replay;
- bot validation.

This is the clearest machine-readable status statement in the old repository.

## 7. What remained planned or unstarted

### 7.1 D1 itself

`epics.md` names D1 as:

> Examination Engine, now including the relocated pre-live paper phases.

It includes FR-4 through FR-7 plus birth-in-paper, warm-up, the CT-BOOK-02 flip, and exam-to-paper. Its next step was “in-house rebuild in its own design session, then build.” No design session artifact or D1 story set landed in the active plan.

### 7.2 Direct upstream dependencies still missing

- Real canonical history was not acquired. Epic 2 produced governance/proof helpers only.
- Story 3.8 canonical-feed binding was backlog.
- Story 3.9 raw canonical-feed capture and backend shadow readiness was backlog.
- CT-MIS-02 has an open timestamp-contract defect: Story 3.5 manifests do not require `emission_utc`, while Story 3.6 interval replay needs timestamp evidence to classify legacy visible artifacts. `deferred-work.md` says this needs a contract decision, not a fallback invented in the reader.

### 7.3 Shared live-path dependencies still missing

The intended engine must share production policy code, but the relevant production mechanisms were not complete:

- Story 4.1 platform-blind adapter: backlog; the reconciliation audit says there was no adapter at all.
- Story 4.2 amend command: backlog.
- Story 4.3 startup gates: backlog.
- Epic 6 Book doors, sizing, refusal path, bot identity, and protection projection: entirely backlog.
- Epic 7 KSA: entirely backlog.
- Epic 8 QML bot-authoring layer: entirely backlog.
- Epic 9 admission, promotion, certificate index, parity cascade, and identity completion: entirely backlog.

Therefore no honest claim can be made that replay was exercising the same current live Book/door/refusal codepath. That codepath did not yet exist as a wired system.

## 8. Explicit open gates and design questions

| Gate / question | Status in old corpus | Recovery disposition |
|---|---|---|
| Complete replay-run schema | Undefined; deferred with D1 | Fresh design, preserving NFR-3 tuple and two-substitution rule |
| Fill simulator | Recovered-only mechanics; no current implementation | Fresh design; must remain cost-honest and shared-policy compatible |
| Candidate submission contract | Absent | Fresh design |
| Ordered end-to-end examination pipeline | Only implied by contracts; no current narrative/process contract | Fresh design using current boundaries |
| Exact Monte Carlo procedure | Recovered-only | Reconfirm; do not silently ratify |
| Exact PBO/CSCV procedure | Recovered-only (16 sub-period candidate) | Reconfirm |
| Expanding vs rolling walk-forward | Not ruled | Fresh decision |
| Cohort correlation method | Thin | Fresh design |
| Chorus/correlation gate threshold | Null, GAP-0012 | Keep null until evidence and ratification |
| Stop-policy version pin | PE-8 blocked on position-safety design | Must resolve before certificate parity is complete |
| Position-fate effects on simulation | PE-7/position-safety cluster not part of D1 completion | Must align with the new architecture before fill/replay semantics lock |
| Warm-up duration and semantics | Retired from trading-node registry; deferred to D1 | Fresh certification-side decision |
| Post-exam paper state machine | Not designed current | Fresh design; do not revive old WF/probation machinery automatically |
| Activation boundary | Next rollover was only an assumption | Operator decision required |
| Full bot registry/lineage | Out of V1; current minimal identity only | Exclude from engine core beyond stable bot id + immutable spec version |
| Session/pair-specific exam boards | Absent everywhere | Fresh design only if still wanted |
| Synthetic exam data | Absent everywhere | Fresh design; not recoverable |
| Alpha-decay math | Never written down | No retrieval possible; future design |
| General replay-for-research | Proposed, unratified | Do not expand V1 scope automatically |

## 9. Do-not-revive list

The examination-lineage coverage audit warns that recovered specs contain old authority mechanics that conflict with the later Book/BMS/doors/leash architecture. Do not import these as current engine behavior:

- DPR/PRS merit ranking and tiers;
- global bot pools and slot auctions;
- WF1 mechanics;
- six-clamp or old circuit-breaker authority;
- paper-redemption/probation loops;
- continuous tiers;
- old WF2 live-promotion authority;
- identifier recycling or in-place revival;
- session windows as authority;
- synthetic-data behavior that was never documented.

The stage name WF2 survived only as agentic-driven backtest-to-paper iteration, ending at paper-complete. It does not decide live promotion. Because the current recovery is for the Backtesting Engine rather than agentic workflow design, the name is not needed to specify the engine boundary.

## 10. Recovery classification

### KEEP — binding architecture or requirements

- backend-node hosting and process-per-run isolation;
- in-house engine ruling;
- book-specific certification;
- engine non-authority;
- CT-MIS-02 / CT-EXAM-01 / CT-EXAM-02 boundaries;
- reproducibility tuple and two permitted substitutions;
- shared live Book/door/refusal semantics;
- labeler and stop-policy parity/invalidation principle;
- exact-money discipline;
- immutable manifested input data and source-class separation;
- certificate corpus/index separation;
- evidence-only output followed by a human promotion click;
- SM-6 battery-honesty obligation.

### KEEP AS IMPLEMENTED SUBSTRATE, NOT AS AN ENGINE

- Story 3.5 immutable archive publication proof;
- Story 3.6 bounded deterministic replay-query proof;
- Story 3.7 materialization proof;
- acquisition/curation manifest standards;
- backend storage and sync boundaries.

### RECONFIRM

- every exact statistical battery value, despite being current in DEC-0036, because the project is being restarted and the method was never completed;
- recovered Monte Carlo, CSCV/PBO, walk-forward, fill/cost, and evidence-pack mechanics;
- proposed pre-live paper/warm-up lifecycle;
- activation timing;
- certificate schema beyond the binding minimal content;
- cohort-correlation computation and gate threshold.

### FRESH DESIGN

- runner/API/job lifecycle;
- candidate submission;
- replay-run schema and evidence pack;
- fill simulator and order sequencing;
- failure and cancellation behavior;
- resource isolation/concurrency limits;
- complete certification-side paper state machine;
- certificate generation/persistence transaction;
- operator-facing run status and diagnostics.

### DROP / EXCLUDE

- reverted agentic-run internals;
- old WF/DPR/PRS/slot/probation authority;
- general-purpose strategy-playground scope;
- any claim that the old repository already had an engine;
- any claim that “Epic 2 done” means real historical data was acquired;
- any claim that “Story 3.6 done” means backtesting was implemented.

## 11. Recommended restart sequence

This is a dependency sequence, not an implementation plan:

1. Re-ratify the engine boundary: book-specific certification, backend host, non-authority, in-house build.
2. Resolve the data truth: actual acquired datasets, manifests, real Parquet publication, and the `emission_utc` replay-visibility defect.
3. Define the shared replay seam only after the new Book/door/protection interfaces are stable enough to share with live.
4. Ratify the replay-run identity/schema, explicit clock/seed, fill simulator, cost model, and evidence pack.
5. Reconfirm the statistical battery values and formally specify each method.
6. Resolve stop-policy pinning and other policies that shape `Lbar` before locking CT-EXAM-01.
7. Define the certification-side paper/warm-up lifecycle separately from trading-node fail-mechanism paper.
8. Implement the engine and prove SM-6 honesty with multiple overfit archetypes plus a known-good control.
9. Only then connect certificates to the trading-side index, L10 invalidation, AD-40 promotion pull, and human promotion flow.

## 12. Evidence index

Primary sources inspected:

- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\ARCHITECTURE-SPINE.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\prds\prd-QMX-2026-07-20\prd.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\epics.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\epics-v2-verification-2026-07-24.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\sprint-status.yaml`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\reconciliation-report.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\deferred-work.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\epic-3-context.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\research\examination-lineage-coverage-audit.md`
- `C:\Users\Mubarak\Documents\QMX\standards\ct-mis-02-bounded-replay-query-serving.json`
- `C:\Users\Mubarak\Documents\QMX\standards\mis-archive-immutable-emission-storage.json`
- `C:\Users\Mubarak\Documents\QMX\standards\labeler-materialization-lane.json`
- `C:\Users\Mubarak\Documents\QMX\standards\testing-doctrine.md`
- `C:\Users\Mubarak\Documents\QMX\standards\data-source-licensing-and-acquisition-manifest.json`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-2-6-deep-history-acquisition-external-sources-merged-with-platform-continuity.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-2-7-flow-governance-and-curation-ownership-design.md`

## Final status sentence

The recoverable BMAD asset is a **precise intended boundary plus several narrow backend evidence/replay proofs**. The Backtesting/Examination Engine itself remained a deferred, uncut, unbuilt design effort.
