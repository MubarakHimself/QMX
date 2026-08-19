# Backtesting / Examination implementation archaeology

Status: read-only evidence report  
Inspected root: `C:\Users\Mubarak\Documents\QMX`  
Scope: backend-node and adjacent source, storage, standards, verification, CI, and operations surfaces  
Inspection date: 2026-08-17

## Executive verdict

The old repository did **not** contain an executable Backtesting Engine or Examination Engine.

What actually existed was a narrow, verifier-backed **MIS archive and bounded replay proof** plus supporting acquisition and storage-boundary work:

1. A real Dukascopy acquisition CLI downloaded and decoded historical tick data into Parquet, but those partitions were still raw acquisition evidence and were explicitly refused for canonical use because Dukascopy licensing posture remained unresolved.
2. `mis_archive_storage.py` could publish synthetic/proof-shaped CT-MIS-01 archive emissions, materialize caller-supplied historical feature rows, and serve deterministic bounded CT-MIS-02 queries over those proof artifacts.
3. Story 3.6 explicitly recorded `exam_engine_implemented: false`. Its machine-readable non-goals excluded the Examination Engine, certificate generation, a complete replay-run schema, book-aware parity, fill simulation, Records/veto replay, and bot validation.
4. The backend service entry point remained an inert scaffold. The systemd service ran a wrapper that called `describe_scaffold()` once and then slept; it did not host replay, examination, certificate, database, API, or job-runner functionality.
5. PostgreSQL certificate and dossier tables existed only as validated DDL plans. There was no live PostgreSQL migration executor, connection, certificate writer, certificate reader, or operative certificate index.
6. The verification scripts exercised proof helpers in temporary directories and CI enforced their deliberately narrow boundaries. They were not production runtime integration tests.

The most important recovery distinction is therefore:

> Recover the archive/replay boundary, determinism rules, provenance gates, and acquisition evidence as useful implementation evidence. Do not describe them as a recovered backtest engine. The engine itself still had to be designed and built.

## Confidence and method

- **Observed:** direct statement or executable/static evidence in the inspected files.
- **Deduced:** necessary conclusion from multiple observed surfaces.
- No Git command was run.
- No old-repository file was changed.
- No verifier or acquisition command was executed.
- The scan covered all Python source outside generated/site/cache/trash trees, filenames and definitions matching backtest/exam/certificate/replay terms, backend operations wiring, CI wiring, relevant machine-readable standards, and the current `data/` artifact shape.

## 1. What executable functionality existed

### 1.1 Real historical-data acquisition

**Observed.** The only production-shaped backend executable in the recovered area was:

```text
backend-node/qmx_backend_node/acquisition/pipeline.py
```

Its module CLI exposed two commands:

```text
cd backend-node
python -m qmx_backend_node.acquisition.pipeline --rate 2 validate --pair EURUSD --date YYYY-MM-DD
python -m qmx_backend_node.acquisition.pipeline --rate 4 --retries 6 run --pairs all --resolution tick --max-history
```

It implemented:

- Dukascopy HTTP acquisition of hourly `.bi5` tick files;
- LZMA decoding of real bid/ask ticks;
- per-day sanity checks;
- Parquet output through pyarrow;
- immutable preservation of raw `.bi5` files;
- per-partition acquisition manifests and validation results;
- resumable checkpoints, retry/backoff, rate limiting, and run logging;
- refusal to fabricate or interpolate missing market data.

Its separate runtime dependencies were `requests`, `numpy`, and `pyarrow`, declared in `backend-node/qmx_backend_node/acquisition/requirements-acquisition.txt`. The root `requirements.txt` was documentation-only, and the repository had no `pyproject.toml`, `setup.py`, or `setup.cfg` application packaging surface.

**Observed repository state.** The old root contained a large acquisition corpus under:

```text
data/raw/external-deep-history/
```

At inspection time the `data/` tree contained approximately:

- 257,631 files total;
- 215,068 `.bi5` files;
- 10,640 `.parquet` files;
- 21,281 `.json` files;
- no `.jsonl`, `.duckdb`, `.db`, `.sqlite`, or `.sqlite3` replay/certificate store artifacts found in the data tree;
- an empty `data/_runs/` directory;
- a large `data/_state/checkpoint.json` recording completed EURUSD/USDJPY tick partitions;
- two acquisition log files dated August 2026.

This is genuine data-acquisition evidence, not examination evidence. A sampled partition validation returned:

```json
{
  "accepted": false,
  "refusal_codes": ["SOURCE_LICENSE_NOT_CANONICAL_USABLE"],
  "structurally_valid_except_licensing_gate": true
}
```

The corresponding manifest was `source_class: external_deep_history`, `stage: download`, `partition_namespace: raw/external-deep-history`, with a proposed—not ratified—canonical JSON hash algorithm.

**Deduced.** The acquired tick corpus could eventually feed a backtest system, but it was not legally/governance-ready for canonical use and was not wired into replay or examination.

### 1.2 MIS archive publication proof

**Observed.** `backend-node/qmx_backend_node/mis_archive_storage.py` implemented the following public proof helpers:

- `load_archive_standard`
- `validate_archive_standard`
- `derive_partition_key`
- `publish_archive_emission`
- `evaluate_archive_visibility`

The Story 3.5 path could:

- derive partitions ordered as `source_class / venue_triple / pair / date / resolution`;
- accept only `self_recorded` and `materialized_backfill` source classes;
- temp-write and rename an emission artifact;
- fsync the directory;
- publish a manifest only after the final artifact;
- gate visibility on manifest presence, artifact SHA-256, row count, snapshot version, publication cycle, identity, source class, and partition key;
- refuse overwrite or duplicate emission identities;
- require the backend-node service role as sole writer and finalizer.

The important implementation caveat is encoded directly in the standard:

```text
artifact_kind: parquet_shaped_jsonl_proof_bytes
implementation_form: dependency_free_backend_node_storage_proof
```

The artifacts were JSONL proof bytes with a Parquet-shaped contract, not real Parquet archive writes. The standard also explicitly excluded a live backend service, PostgreSQL integration, DuckDB readers, UI/API/CLI/config surfaces, Records writes, registry writes, trading decisions, and Book/KSA/BMS logic.

### 1.3 CT-MIS-02 bounded replay proof

**Observed.** The closest thing to replay execution was:

```python
serve_bounded_replay_query(
    query_request,
    archive_root,
    replay_standard=None,
    archive_standard=None,
    archive_locator=None,
)
```

It accepted the exact CT-MIS-02 request fields:

```text
query_id
pair
start_utc
end_utc
labeler_versions
```

It could:

- validate the ratified Story 3.6 standard;
- require explicit archive partitions supplied through an internal locator;
- read only manifest-visible Story 3.5 proof artifacts;
- filter by pair, UTC interval, and exact labeler identity/version/parameter-set bindings;
- report hidden, missing, orphaned, or corrupt partitions without returning their data;
- order results by partition key, emission time, and emission identity;
- compute deterministic SHA-256 hashes over explicit query scope and returned evidence;
- produce the same hash for identical bounds and unchanged archive evidence;
- remain read-only and filesystem-local.

The direction was explicitly encoded as:

```text
request: Exam -> MIS-Archive
result:  MIS-Archive -> Exam
```

This direction label did not imply that an Exam caller existed.

### 1.4 Historical labeler materialization proof

**Observed.** Story 3.7 added:

```python
materialize_labeler_backfill_emissions(...)
```

It accepted a caller-provided canonical merged-history manifest and explicit historical feature rows, preserved `data_snapshot_id` and lineage, derived CT-MIS-01-shaped evidence using Story 3.1 labeler identities, and published through the Story 3.5 proof writer as `materialized_backfill`.

It did not read the recovered Parquet corpus itself. The caller had to supply already-shaped rows containing integer feature inputs such as spread points, gap duration/count, feed age, liquidity depth, and sensor freshness.

Its standard explicitly excluded:

- real DuckDB/Parquet/pyarrow readers;
- timed jobs and schedulers;
- model training or refitting;
- canonical-feed binding;
- the Examination Engine;
- certificate generation;
- a complete replay-run schema;
- Book/KSA/BMS decisions and trading behavior.

### 1.5 Feature-stack boundary proof

**Observed.** `backend-node/qmx_backend_node/feature_stack.py` was a ratification validator and degradation-boundary model, not an indicator or examination engine. Its own module header says: “This module is not an indicator engine.”

It validated the intended DuckDB + pyarrow + deterministic Python-kernel stack, exact-number boundaries, and `INSUFFICIENT_DATA` degradation. It did not calculate the examination statistical battery or consume historical market data.

## 2. Machine-readable proof that the engine was absent

### 2.1 `exam_engine_implemented: false`

**Observed.** `standards/ct-mis-02-bounded-replay-query-serving.json` contains:

```json
"direction": {
  "request_from": "Exam",
  "request_to": "MIS-Archive",
  "result_from": "MIS-Archive",
  "result_to": "Exam",
  "exam_engine_implemented": false
}
```

This is the strongest direct answer to whether an Examination Engine existed.

### 2.2 Story 3.6 non-goals

**Observed.** The same standard marks all of these as non-goals:

- `examination_engine`
- `certificate_generation`
- `complete_replay_run_schema`
- `book_aware_replay_parity`
- `fill_simulation`
- `records_veto_replay`
- `bot_validation`
- API/CLI/UI/config transport
- DuckDB runtime query
- PostgreSQL integration
- cache and scheduler
- BMS/Book/KSA decisions
- trading behavior

The Story 3.6 implementation spec is even more explicit: it says “Never” build the Examination Engine, certificate generation, book-aware replay parity, fill simulation, Records/veto replay, or bot validation in that story.

### 2.3 No engine source surface

**Observed.** Across application Python roots (`backend-node`, `trading-node`, `console`, and `tools`):

- there was no `backtest`, `backtesting`, `exam`, `examination`, `certificate`, or replay-service module;
- there was no `ExaminationEngine`, `BacktestEngine`, replay server, certificate generator, job scheduler, or exam runner class/function;
- the only source definition representing bounded historical replay was `serve_bounded_replay_query`;
- statistical-battery terms appeared only in registry-validation data, not algorithms;
- fill-simulator terms appeared only as prohibited/non-goal strings;
- no executable implementation existed for walk-forward, Monte Carlo permutations, CSCV/PBO, Sharpe, profit factor, equity curves, MAE/MFE, slippage models, spread models, partial fills, or rejection probability.

### 2.4 No CT-EXAM implementation contract

**Observed.** The repository had Markdown pages for CT-EXAM-01 and CT-EXAM-02, but no corresponding machine-readable standard/schema or Python producer/consumer implementation under `standards/`, `backend-node/`, or `trading-node/`.

The documented fields were therefore design evidence only:

- CT-EXAM-01: bot/book profile, labeler versions, EV by regime, mean loss, fire-rate band, breaker expectation, and cost ratio;
- CT-EXAM-02: cohort/book IDs, correlation observations, expected loss shape, and certification time.

No code generated, validated, persisted, invalidated, or consumed either certificate.

## 3. Actual backend entrypoints and operational wiring

### 3.1 Backend `main.py` was inert

**Observed.** `backend-node/qmx_backend_node/main.py` contains only `describe_scaffold()`. It returns metadata including:

```text
process_layout: one Python backend-node service plus PostgreSQL and exam job-runners
behavior: inert scaffold only
```

The phrase “plus PostgreSQL and exam job-runners” described intended layout. No job-runner implementation accompanied it.

`backend-node/qmx_backend_node/__init__.py` exports only `describe_scaffold`.

### 3.2 The systemd backend service did not run replay

**Observed.** `ops/systemd/qmx-backend-node.service` starts:

```text
tools/supervised_node_runner.py --node backend
```

The runner maps `backend` to:

```python
("backend-node", "qmx_backend_node.main", "describe_scaffold")
```

It calls that function, prints the resulting JSON once, and enters a sleep loop. It does not start PostgreSQL, an RPC/HTTP endpoint, MIS archive serving, a replay worker, an exam worker, a queue, or a scheduler.

### 3.3 Replay had no deployable entrypoint

**Observed.** `serve_bounded_replay_query` was called only by Story 3.6 and 3.7 verifier scripts. No application module imported it. There was no:

- console script;
- command-line subcommand;
- HTTP/RPC route;
- queue consumer;
- scheduled job;
- systemd worker;
- backend package export;
- production caller.

The proof function was executable when imported manually, but it was not a deployed service.

## 4. Storage and contracts that existed

### 4.1 Archive proof storage

The proof archive used filesystem partitions and paired emission/manifest files. Visibility was fail-closed and content-addressed. This is useful recovery material because it establishes:

- immutable evidence publication;
- verify-before-read behavior;
- deterministic partition/query scope;
- labeler-version parity;
- separation of writer and read-only roles;
- stable result hashing;
- no ambient clock or randomness inside replay proof code.

It should be recovered as a boundary pattern, not assumed to be the final backtesting storage engine.

### 4.2 Actual acquisition storage was a different substrate

The downloaded data lived under `raw/external-deep-history` as real Parquet plus raw `.bi5` evidence. The Story 3.6 query only understood Story 3.5 archive proof artifacts in `self_recorded` or `materialized_backfill` partitions.

There was no adapter that:

1. read acquired Parquet;
2. cleaned and canonically merged it;
3. resolved the licensing refusal;
4. calculated materialization features;
5. called `materialize_labeler_backfill_emissions`;
6. exposed the resulting archive to a live replay service.

This substrate mismatch is the main reason the code was not end-to-end.

### 4.3 PostgreSQL certificate corpus was a DDL plan only

**Observed.** `standards/backend-postgresql-discipline.json` defines table-family ownership and baseline `CREATE TABLE` SQL for:

```text
bn_certificates_corpus
bn_per_bot_dossier_assembly
```

The planned certificate table fields were:

```text
certificate_id
bot_id
certificate_contract
evidence_json
manifest_sha256
observed_at_utc
```

The planned dossier table fields were:

```text
dossier_id
bot_id
artifact_kind
artifact_ref
lineage_json
assembled_at_utc
```

Ownership was assigned to `exam-host`.

However, the discipline also explicitly says:

```text
live_server_required_for_validation: false
backend_authoritative_certificate_index_created: false
certificate_corpus_presence_means_validity: false
```

`postgresql_migrations.py` provided only:

- standard loading;
- SQL hashing;
- DDL-plan validation;
- applied-history validation;
- returning a validated plan.

It had no database driver import, connection, transaction, SQL execution, or migration-application function. No PostgreSQL artifact was found in the data tree.

**Deduced.** The schema names capture useful evidence-home intent, but they do not prove any certificate was ever written.

## 5. Verification and CI evidence

### 5.1 What the verifiers tested

The relevant executable verifiers were:

- `tools/verify-story-3-5.py`
- `tools/verify-story-3-6.py`
- `tools/verify-story-3-7.py`

They imported `mis_archive_storage.py`, created temporary scratch directories, constructed explicit fixture manifests/rows, called the proof helpers, and checked:

- archive publication and manifest visibility;
- hidden/orphan/corrupt artifact handling;
- request shape and bounds validation;
- labeler-version exact matching;
- deterministic ordering and result hashing;
- refusal behavior and no filesystem mutation on invalid reads;
- materialization lineage and replay visibility;
- static absence of network transports, ambient time/randomness, float literals, database runtimes, engine classes, and other prohibited surfaces;
- syntax compilation;
- consistency with story progress/acceptance ledgers and sprint status.

The `.github/workflows/qmx-foundation.yml` workflow ran the three verifier scripts and corresponding `py_compile` checks.

### 5.2 What passing verification did not mean

The acceptance ledger for Story 3.6 says the story passed specifically because it was a dependency-free read-only proof and **not** an Exam Engine, certificate generator, runtime query service, materialization lane, replay-run schema, or trading path.

The Story 3.6 verifier additionally searched changed source for prohibited tokens such as:

- replay server;
- Examination Engine;
- certificate generator;
- fill simulator implementation;
- DuckDB and pyarrow runtime access;
- PostgreSQL integration;
- scheduler and transport surfaces.

Therefore “Story 3.6 done” means the bounded query proof was complete inside its intentionally tiny scope. It must not be translated into “replay engine done.”

### 5.3 Test-suite limitations

**Observed.** There was no conventional pytest/unittest suite or application packaging configuration for the engine. The verifier scripts were bespoke acceptance programs tied to story documents, static allowlists, and repository evidence ledgers.

They did not test:

- actual downloaded Parquet through replay;
- a real backend service endpoint;
- concurrent replay jobs;
- queue priority or budgets;
- a live PostgreSQL certificate corpus;
- bot/book loading;
- fill simulation;
- statistical-battery algorithms;
- certificate production or invalidation;
- Book admission or promotion consumption.

## 6. End-to-end wiring assessment

### Intended flow versus recovered implementation

| Intended stage | Recovered implementation state | Verdict |
| --- | --- | --- |
| Acquire historical market data | Real Dukascopy CLI and large raw tick corpus | Implemented, but canonical use refused |
| Clean/merge into approved immutable snapshot | Proof validators/design exist; no observed runtime bridge for this corpus | Not end-to-end |
| Materialize replay labelers/features | Helper accepts caller-supplied rows; no Parquet reader or scheduler | Proof only |
| Publish MIS archive | Filesystem JSONL proof writer with manifest gate | Proof only |
| Serve CT-MIS-02 | Importable read-only query helper | Proof only; no service/runner |
| Load bot spec and book profile | No implementation | Absent |
| Reproduce live authorities/doors/KSA/Records | Explicit Story 3.6 non-goal | Absent |
| Simulate fills and costs | Explicit Story 3.6 non-goal | Absent |
| Run walk-forward / MC / PBO battery | Registry values only | Absent |
| Produce CT-EXAM-01 / CT-EXAM-02 | Markdown contracts only | Absent |
| Persist certificate/dossier | PostgreSQL DDL plan only | Absent |
| Consume certificate for admission | No producer/consumer wiring | Absent |

**Conclusion:** the recovered path stopped at an isolated archive-query proof. It was not wired end-to-end from acquired ticks to an examination verdict.

## 7. Exact implementation debt

### Engine core

- Define and implement the replay-run contract. Story 3.6 deliberately refused bot ID, book profile, configuration, seed, fill-simulator, and policy-trace fields in CT-MIS-02.
- Implement the deterministic event/tick/bar loop.
- Decide tick-versus-bar execution physics and multi-resolution behavior.
- Load a versioned bot specification and a specific book profile.
- Reproduce current doors, money ladder, breaker/leash, KSA, stop/target policy, and Records/refusal semantics in the exact live order.
- Define how known live gaps and versioned authority changes are replayed.

### Execution simulation

- Implement spread, slippage, commission, partial-fill, rejection, amendment, stop, target, and close behavior.
- Bind fill assumptions to immutable versioned configuration.
- Establish price/money precision and deterministic random-stream rules.
- Emit a replay journal compatible with the chosen live Records contract without writing to live authority stores.

### Statistical examination

- Implement expanding/rolling walk-forward windows.
- Implement out-of-sample aggregation and minimum-trade handling.
- Implement Monte Carlo permutations with explicit seed and reproducible RNG ownership.
- Implement CSCV/PBO and threshold behavior.
- Implement cost-adjusted expectancy, drawdown, Sharpe, profit factor, regime/session breakdowns, MAE/MFE, and survival evidence.
- Resolve which old recovered metrics remain current and which require new ratification.

### Data plane

- Resolve Dukascopy canonical-use/licensing posture or choose another approved source.
- Ratify the manifest serialization/hash scheme used by the acquisition pipeline.
- Implement clean/canonical merge and platform-continuity lineage.
- Implement real Parquet/DuckDB/pyarrow reads.
- Convert tick data into the explicit inputs needed by MIS materialization and bot execution.
- Implement scheduling, concurrency limits, caching policy if any, retention, and replay-result sealing.

### Service/runtime plane

- Choose whether replay is an in-process exam worker or a separate service.
- Add a deployable entrypoint, job runner, queue, status/result API, cancellation, retries, timeouts, and resource budgets.
- Replace the backend scaffold loop with a real backend host without granting it trading authority.
- Ensure live MIS publication cannot depend on replay load.
- Add observability, failure registration, and recovery semantics.

### Certificate plane

- Ratify machine-readable CT-EXAM-01 and CT-EXAM-02 schemas.
- Implement certificate generation, hashing/signing, storage, invalidation, and labeler-version parity checks.
- Apply real PostgreSQL migrations or select a revised evidence store.
- Implement certificate and per-bot dossier writers/readers.
- Keep corpus presence separate from operative validity.
- Implement the Book-side consumer and the boundary from certification to admission/promotion.

### Testing

- Add unit/property tests for statistical and fill algorithms.
- Add golden replay fixtures with immutable market snapshots.
- Add determinism tests across process/machine boundaries.
- Add end-to-end acquisition-to-certificate tests.
- Add corruption, interruption, concurrency, partial-write, and restart tests.
- Add parity tests proving replay and live decision pipelines share the intended code/contract surfaces.

## 8. Recovery disposition

### Keep as strong implementation evidence

- CT-MIS-02 exact request fields and request/result direction.
- `exam_engine_implemented: false` as historical status truth.
- manifest-gated archive visibility and immutable publication pattern.
- deterministic result ordering and result hashing.
- labeler identity/version/parameter-set parity.
- explicit no-ambient-time/no-ambient-randomness boundary in replay proof code.
- sole-writer/read-only-role separation.
- acquisition pipeline's no-synthetic-data rule and preserved raw provenance.
- backend evidence-home intent and certificate/dossier ownership names.

### Reconfirm before rebuilding

- filesystem partition layout;
- JSONL proof artifact shape versus real Parquet;
- CT-MIS-02 keeping only five fields versus a separate replay-run envelope;
- one shared Replay Service versus an in-process Examination Engine worker;
- PostgreSQL table schemas and `exam-host` ownership label;
- current labeler set and materialization feature inputs;
- book-aware parity surface and current live authority ordering.

### Do not recover as implemented fact

- any claim that the Backtesting Engine was operational;
- any claim that the Examination Engine existed;
- any claim that CT-EXAM certificates were generated or persisted;
- any claim that downloaded Dukascopy data was canonically admitted;
- any claim that Story 3.6 implemented a replay server;
- any claim that PostgreSQL certificate tables were applied;
- any claim that walk-forward, Monte Carlo, PBO, fill simulation, or live-parity execution code existed.

## 9. Primary evidence index

### Application and operations

- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\main.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\__init__.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\mis_archive_storage.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\feature_stack.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\postgresql_migrations.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\acquisition\pipeline.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\acquisition\README.md`
- `C:\Users\Mubarak\Documents\QMX\ops\systemd\qmx-backend-node.service`
- `C:\Users\Mubarak\Documents\QMX\tools\supervised_node_runner.py`

### Machine-readable standards

- `C:\Users\Mubarak\Documents\QMX\standards\ct-mis-02-bounded-replay-query-serving.json`
- `C:\Users\Mubarak\Documents\QMX\standards\mis-archive-immutable-emission-storage.json`
- `C:\Users\Mubarak\Documents\QMX\standards\labeler-materialization-lane.json`
- `C:\Users\Mubarak\Documents\QMX\standards\backend-postgresql-discipline.json`
- `C:\Users\Mubarak\Documents\QMX\standards\indicator-feature-computation-stack.json`

### Verification and acceptance evidence

- `C:\Users\Mubarak\Documents\QMX\tools\verify-story-3-5.py`
- `C:\Users\Mubarak\Documents\QMX\tools\verify-story-3-6.py`
- `C:\Users\Mubarak\Documents\QMX\tools\verify-story-3-7.py`
- `C:\Users\Mubarak\Documents\QMX\.github\workflows\qmx-foundation.yml`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-3-6-bounded-replay-query-serving-ct-mis-02.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\story-3-6-progress.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\story-3-6-acceptance.json`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-3-7-labeler-materialization-lane.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\sprint-status.yaml`

### Design-only cross-checks

- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\backtest-engine-spec.md`
- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\clash-report-backtest-replay.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\topics\backtest-and-replay.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\components\examination-engine.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-exam-01-exam-certificate.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-exam-02-cohort-correlation-certificate.md`

## Final implementation-state statement

The recovered old repository had a meaningful start on the **data and evidence substrate** for future examination: real historical acquisition, immutable archive publication rules, exact replay-query bounds, deterministic hashing, labeler parity, and proof-heavy refusal behavior. It did not have the Backtesting/Examination Engine that consumed those inputs and produced certification. The repository itself repeatedly and machine-readably says so.
