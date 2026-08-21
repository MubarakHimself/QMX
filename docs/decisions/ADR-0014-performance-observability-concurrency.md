---
id: ADR-0014
title: Measured performance, loud failure, and application-owned concurrency
type: adr
status: ratified
component: COMP-QMF-CORE
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK]
decisions: [DEC-0111, DEC-0112, DEC-0113]
sources: [DEC-0111, DEC-0112, DEC-0113, DEC-0102, DEC-0106, DEC-0119, EXT-2013, EXT-2014, EXT-2015, EXT-2028, "_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md", "archive/qmf-3.txt"]
generated: 2026-08-20
verified: 2026-08-20
stale_after: 1y
---

# ADR-0014: Measured performance, loud failure, and application-owned concurrency

Date: 2026-08-20. status: ratified — AD-13 and AD-14 are operator-ratified 2026-08-19 and AD-15 on 2026-08-20 in the foundation architecture sitting; this document stays provisional until the knowledge base is re-ratified.

## Context

Three cross-cutting stances had no home before the foundation architecture sitting, and each failure mode was already visible. Performance: a factory that optimizes against numbers nobody measured produces confident regressions, and a scalping-oriented node makes slow rot expensive. Diagnosis: a solo operator cannot afford multi-hour what-broke hunts, so every component must fail loudly and traceably. Concurrency: without one stance, two packages would disagree on whether QMF is safe to use simultaneously, and an async decision in one library would spread through every signature in the workspace. The sitting ratified the three as AD-13, AD-14, and AD-15.

## Options considered

1. **Numeric performance budgets stated up front** — rejected on the operator's "no invented numbers" ruling: budgets asserted before measurement become the thing the factory optimizes toward, and they cannot be attributed to any real machine. Measure-then-budget was selected, which leaves numeric budgets deferred until the first baselines exist (DEC-0111).
2. **Speed as the only benchmark axis** — rejected at the sitting's close: peak memory is a first-class budget, and a memory regression fails the gate exactly as a slowdown does (DEC-0111).
3. **One global load ladder in bot counts** — rejected: load is expressed in framework-native units per package — calls per second, series length, artifact count — with the `registry:design_bot_concurrency` node scenario and its 10, 100, and 200 marks as the motivating reference for sizing each ladder (DEC-0111).
4. **Shipped mock market data or fixture products for benchmarks** — rejected: benchmark and test data are generated at runtime or held as controlled fixtures, never shipped as product artifacts, and synthetic data stresses infrastructure without ever validating trading edge (L6, L20, DEC-0111).
5. **Choosing the monitoring stack now** — rejected as node and ops territory; the binding obligation is that emitted signals be exportable to Prometheus-class stacks, with the stack choice and the full monitoring design owned by the later data and ops sitting (DEC-0112).
6. **Logs and journals as one stream** — rejected at the reviewer gate: operator-facing log text renders UTC ISO-8601 with an explicit Z, while journals and evidence streams store int64 UTC nanoseconds plus writer and sequence, with ISO-8601 admitted only as a display-only field excluded from identity (DEC-0112, DEC-0106).
7. **Async-first public APIs** — rejected: async would contaminate every signature in the workspace; async exists only at the venue network edge and never in core or the libraries (DEC-0113).
8. **QMF owning threads, schedulers, or background work** — rejected: the application owns all concurrency, which is what keeps unlimited parallel experimentation safe (DEC-0113).
9. **Purity required of every package** — rejected as unimplementable for components that own an external resource; a stateful class was carved out explicitly (DEC-0113).

## Decision

**Measure-then-budget performance.** QMF invents no performance numbers. Every component ships a benchmark harness carrying the same status as its unit tests, measuring speed and peak memory at a load ladder expressed in framework-native units for that package. First real measurements are recorded as fingerprinted baselines scoped to a declared (OS, CPU-class) tuple; each benchmark's regression threshold is stated when its baseline is recorded, as a multiple of measured run-to-run variance; thereafter a regression beyond threshold fails the tier-2 merge gate (DEC-0102), memory equally with speed. One design constraint is stated rather than measured: `qmf-core` imports in well under one second (`registry:core_import_time_budget`), because disposable sandboxes pay that cost on every run. Server sizing and scaling are node and compute decisions made later with these numbers. (DEC-0111)

**Loud failure, traceable behavior.** Errors and refusals always carry context and are never swallowed. Structured logging carries a correlation id under the field name `correlation_id`, propagated across every package boundary, so one event can be followed across components. Every component exposes a no-argument `health()` returning a typed health report. Logs are not journals: log text is display, journals and every evidence stream are evidence encoded per DEC-0106. Emitted signals must be exportable to Prometheus-class monitoring stacks. (DEC-0112)

**Concurrency stance.** QMF values are immutable and therefore safe to share by construction. Purity binds the pure-computation libraries — `qmf-core`, `qmf-indicators`, `qmf-structure`. Components that own an external resource — stores, recorders, adapters — are the stateful class and follow one-writer-per-stream with unlimited readers, where a writer is the holder of a `WriterId` (DEC-0106). QMF never spawns threads or background work; the application owns all concurrency. Async APIs exist only at the venue network edge. (DEC-0113)

## Consequences

A benchmark harness becomes part of the definition of done for every component, which raises the cost of shipping a package and makes performance regressions attributable to a machine class and a commit instead of to a feeling. Until the first baselines are recorded there are no numeric budgets at all — the gate can only compare against a baseline that exists, so early components pass on correctness and record their numbers rather than being judged by them. `correlation_id` must be threaded through every public boundary, including boundaries that have no other reason to know about it, and it is explicitly excluded from `fp1` identity by versioned declaration so a linking annotation never changes an artifact's fingerprint (DEC-0119). The one-writer-per-stream rule means a second process cannot append to a stream that already has a writer, which is the constraint that makes gapless per-writer sequences meaningful. Because QMF spawns nothing, any scheduling, supervision, retry, or parallel-run behavior is the consuming application's to build — and since everything downstream is built with QMF libraries, that work is real and lands in the node, backtesting, and ops sittings.

## Blast radius

- **Component specs (all seven roster packages):** COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK each ship a benchmark harness with a package-native load ladder, expose `health()`, propagate `correlation_id`, and declare whether they are pure or stateful.
- **Data seams:** COMP-QMF-DATA-STORE, COMP-QMF-DATA-INGEST, COMP-QMF-DATA-BACKUP are stateful components under one-writer-per-stream; their store and network failures surface as `storage failure` and `transient venue failure` refusals rather than swallowed exceptions.
- **Venue boundary:** COMP-QMF-VENUE is the only place async APIs may appear; COMP-CTRADER, COMP-DUKASCOPY, COMP-CALENDAR-FEED, and COMP-OBJECT-STORAGE are reached through it or through the ingest and backup seams.
- **Contracts:** CT-13 journal (writer, sequence, event types, `correlation_id` as a non-identity annotation), CT-11 evidence persistence and CT-26 store backup input (stateful writer discipline), CT-04 typed refusal (context always carried).
- **Registry:** `registry:design_bot_concurrency`, `registry:core_import_time_budget`.
- **Gates:** the tier-2 merge gate gains benchmark comparison alongside integration and contract tests (DEC-0102).

## Architecture preflight

Verdict: **reuse**. No new component, no authority shrink. The ruling adds obligations to components that already exist and does not move ownership: COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA with its seams COMP-QMF-DATA-STORE, COMP-QMF-DATA-INGEST and COMP-QMF-DATA-BACKUP, COMP-QMF-INDICATORS, COMP-QMF-STRUCTURE, COMP-QMF-VENUE, COMP-QMF-RISK. The monitoring stack itself is named at the node and ops sitting and is not a QMF component.
