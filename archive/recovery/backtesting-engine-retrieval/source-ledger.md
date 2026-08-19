# Backtesting Engine source ledger

## Old-repository root

`C:\Users\Mubarak\Documents\QMX`

The search began with the Backend Node, then followed explicit references through the active wiki, BMAD planning and implementation artifacts, machine-readable standards, verifier scripts, and recovered local-cleaned design exports.

## Authority order

| Rank | Source | Treatment |
| --- | --- | --- |
| 1 | Final Architecture Spine | Governs topology, placement, authority, data/evidence ownership, parity, and supersessions. |
| 2 | Current PRD/addendum and topology-v2 `epics.md` | Governs requirements, deferred status, acceptance intent, and scope. |
| 3 | Active wiki | Reconciled operator-facing model, evaluated claim by claim. |
| 4 | `sprint-status.yaml`, reconciliation report, ratified standards, and completed-story evidence | Governs what was actually completed within each deliberately narrow proof boundary. |
| 5 | GitBook capture | Earlier Examination contracts and conceptual baseline where compatible with later rulings. |
| 6 | Recovered `backtest-engine-spec.md` and clash report | Unratified old-system mechanics. Mine for durable intent; never copy old authority or lifecycle. |
| 7 | Reverted agentic attic and recovered service proposal | Non-authority/proposal only. |

## Primary documents

### Active architecture and wiki

- `C:\Users\Mubarak\Documents\QMX\wiki\topics\backtest-and-replay.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\components\examination-engine.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-mis-02-mis-archive-replay-query.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-exam-01-exam-certificate.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\contracts\ct-exam-02-cohort-correlation-certificate.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\registry\variables.md`
- `C:\Users\Mubarak\Documents\QMX\wiki\registry\formulas.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\ARCHITECTURE-SPINE.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\prds\prd-QMX-2026-07-20\prd.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\epics.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\planning-artifacts\architecture\architecture-QMX-2026-07-20\research\examination-lineage-coverage-audit.md`

### Recovered design donors

- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\backtest-engine-spec.md`
- `C:\Users\Mubarak\Documents\QMX\raw\local-cleaned\2026-07-20-recovered-design-artifacts\clash-report-backtest-replay.md`

The first file declares itself an `UNRATIFIED baseline` despite its older “Canonical v1.0” caption. Its parity principle and statistical ideas are useful; its WF2 embedding, six-clamp/multiplier/equity-band/slot authority, and automatic registry/paper/live progression are not current.

### Implementation/status evidence

- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\sprint-status.yaml`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\reconciliation-report.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-3-6-bounded-replay-query-serving-ct-mis-02.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-3-5-mis-archive-immutable-emission-storage.md`
- `C:\Users\Mubarak\Documents\QMX\_bmad-output\implementation-artifacts\spec-3-7-labeler-materialization-lane.md`
- `C:\Users\Mubarak\Documents\QMX\standards\mis-archive-immutable-emission-storage.json`
- `C:\Users\Mubarak\Documents\QMX\standards\ct-mis-02-bounded-replay-query-serving.json`
- `C:\Users\Mubarak\Documents\QMX\standards\labeler-materialization-lane.json`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\mis_archive_storage.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\acquisition\pipeline.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\acquisition\README.md`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\acquisition\requirements-acquisition.txt`
- `C:\Users\Mubarak\Documents\QMX\data\_state\checkpoint.json`
- `C:\Users\Mubarak\Documents\QMX\data\raw\external-deep-history\venue=FOREX\platform=CTRADER\instrument=EURUSD\resolution=tick\date=2003-05-22\_manifest.json`
- `C:\Users\Mubarak\Documents\QMX\data\raw\external-deep-history\venue=FOREX\platform=CTRADER\instrument=EURUSD\resolution=tick\date=2003-05-22\_manifest.validation.json`
- `C:\Users\Mubarak\Documents\QMX\tools\verify-story-3-5.py`
- `C:\Users\Mubarak\Documents\QMX\tools\verify-story-3-6.py`
- `C:\Users\Mubarak\Documents\QMX\tools\verify-story-3-7.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\main.py`
- `C:\Users\Mubarak\Documents\QMX\backend-node\qmx_backend_node\postgresql_migrations.py`
- `C:\Users\Mubarak\Documents\QMX\standards\backend-postgresql-discipline.json`

The clearest status evidence is machine-readable: the Story 3.6 standard sets `exam_engine_implemented: false` and lists examination, certificates, replay-run schema, book-aware parity, fill simulation, Records/veto replay, and bot validation as non-goals. The Story 3.5/3.7 standards further identify their artifacts as dependency-free proof shapes and exclude real Parquet/DuckDB/pyarrow runtime, scheduling, Examination and certificate generation. `data/_runs/` was empty, so no completed authoritative acquisition-run summary or `actual_pair_set` was observed.

## Chronology and status boundary

1. The old-vault Backtest Engine export was recovered on 2026-07-18 as an unratified baseline.
2. The wiki reconciled it against the newer Book system on 2026-07-20–21.
3. Topology v2 placed the future Examination Engine on the Backend Node, process-per-run, and explicitly deferred its internals as D1.
4. Stories 3.5–3.7 later completed archive storage, bounded CT-MIS-02 query serving, and labeler materialization proofs.
5. The old sprint ended with D1 still deferred, the engine without stories or implementation, a large raw Dukascopy corpus not admitted as canonical because of the licensing gate, no bridge from that corpus into the replay archive, and many shared live-path dependencies still backlog.

The data tree and acquisition logs include activity from August 2026, later than the July sprint ledger. They are current filesystem evidence in the former repository, not proof that the July “Epic 2 done” label represented a usable canonical dataset.

No live web research was needed for this retrieval. It reports the former repository's state rather than validating current third-party APIs or licenses.
