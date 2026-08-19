# Fresh-session handoff — Backtesting / Examination Engine

## Mission

Design and build the deferred Backend Node Examination Engine from recovered requirements and invariants. Do not transplant the old WF2 Backtest Engine or mistake the completed CT-MIS-02 reader proof for a runner.

## Ground truth

- The target is a **book-specific Examination Engine with an in-house deterministic replay harness**.
- It runs off the hot path on the Backend Node as process-per-run work.
- It measures and certifies; it cannot admit, promote, trade or mutate bot/Book/registry state.
- Replay/live parity allows only historical data for the live feed and a fill simulator for the Adapter.
- Book policy, doors, formulas, protection, costs and refusals must use shared production-equivalent semantics.
- Minimum reproducibility identity is `bot_spec_version + data_snapshot_id + config_hash + seed`.
- CT-MIS-02 retrieves replay inputs. CT-EXAM-01/02 carry certification evidence. A separate ReplayRunSpec/EvidencePack is required.
- Full certificate evidence lives on the Backend; operative validity belongs to the Trading Node index.
- Exam runners are read-only over Class-3 Parquet. The Backend service alone finalizes Class-3 files; registered exam-host writers own certificate/dossier table families. The worker-to-publication seam still needs design.

## What can be reused conceptually

1. Backend placement and process-per-run isolation.
2. Book-specific certification and non-authority.
3. Exact two-substitution parity plus refusal parity.
4. Immutable manifested data, explicit source class, labeler identity and deterministic run identity.
5. Registry-backed battery values and FORM-0009/0010, subject to fresh confirmation.
6. CT-MIS-02's exact five-field request, explicit UTC bounds with `end > start`, manifest visibility and stable hash behavior. The helper's `[start,end)` selection is not yet contract authority.
7. Recovered fill-model dimensions and statistical procedures as design candidates.
8. Passing/failing evidence retained in a per-bot dossier.

## What actually exists in the old repository

- an inert Backend Node scaffold;
- a real Dukascopy acquisition CLI and large raw tick/Parquet corpus that was refused for canonical use by the licensing gate;
- immutable MIS-Archive publication/visibility proof;
- bounded CT-MIS-02 replay-query proof;
- labeler-materialization proof;
- PostgreSQL DDL/migration discipline reserving certificate-corpus and dossier tables;
- verifier/CI evidence around those slices.

It does **not** contain an Examination runner, fill simulator, battery executor, certificate generator, run lifecycle, candidate-submission API, certification paper flow, or end-to-end shared live/replay policy path.

## Design order

1. Stabilize the new Book/door/protection/execution interfaces that replay must share, including PE-4 Kelly inputs and the PE-5 KSA trigger→level/effects matrix.
2. Ratify ReplayRunSpec identities, canonical serialization and job lifecycle.
3. Resolve real historical data, source/license evidence, Parquet runtime and the Story 3.5/3.6 `emission_utc` mismatch.
4. Design the in-house fill simulator against current Adapter, stop, close and position-fate semantics.
5. Ratify exact walk-forward, Monte Carlo and PBO procedures—not just their numeric thresholds.
6. Define ReplayEvidencePack and evidence equivalence without writing into live Records.
7. Evolve CT-EXAM-01/02, including stop-policy pinning and cohort-correlation rules.
8. Define exam-worker publication, certificate issuance/corpus writes and the later Trading-side validity/index crossing without creating extra Class-3 or Records writers.
9. Design certification-side paper/warm-up separately from Trading fail-mechanism paper.
10. Implement and prove battery honesty with several overfit archetypes, a known-good control and mismatch invalidation.

## First decisions to force

- Candidate submission and immutable code/spec identity.
- Exact Book/profile/config/policy bindings.
- Job states, idempotency, retry, cancellation and resource limits.
- Fill/cost model identities and calibration evidence.
- PE-3 stop-out taxonomy, PE-7 position fate and PE-8 stop-policy certificate pin.
- PE-4 Kelly-input registration and PE-5 KSA trigger→level/effects parity.
- CT-QML-01 plus the compiler/runtime identity and deterministic bot-execution seam.
- CT-MIS-02 interval inclusion; `[start,end)` is only the old helper's behavior until ratified.
- Exam-worker output handoff to the sole Class-3 finalizer and registered certificate/dossier writers.
- Whether a separate D1 optimization orchestrator exists; a certifying run must never mutate its frozen candidate.
- Walk-forward rolling versus expanding behavior, insufficient-window rules, Monte Carlo outputs and CSCV method.
- Cohort-correlation method and whether `F_CHORUS` remains null.
- Replay trace schema and comparison with production Records.
- Certification-side paper states and the boundary of WF2.
- Actual data availability versus proof-only manifests.

## Never import

- WF1 or old WF2 Stages G–I;
- six-clamp, multiplier, equity-band, slot-cap or old circuit-breaker authority;
- DPR/PRS ranking, global pools or slot auctions;
- automatic registry writes, probation, paper redemption or self-promotion;
- session windows as permission;
- reverted agentic internals or general-purpose strategy-playground scope;
- the assumption that a verifier-backed archive query is a Backtesting Engine.

## Documentation acceptance

The new specification is ready to drive code only when it identifies, without consulting the old repository:

- every immutable input and version identity;
- the exact live functions reused by replay and the two permitted substitutions;
- order/fill/stop/refusal sequencing and failure semantics;
- run states, resource/cancellation/retry behavior and deterministic idempotency;
- battery procedures and metric formulas;
- evidence-pack and certificate schemas;
- corpus ownership versus Trading validity authority;
- the certification-side paper and human-promotion boundary;
- explicit outcomes for every unresolved item in the recovered design register.

Use `recovered-backtesting-engine.md` as the consolidated recovery source and the `work/` reports as evidence, not as files to copy wholesale.
