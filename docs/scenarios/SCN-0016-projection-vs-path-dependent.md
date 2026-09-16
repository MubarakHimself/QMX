---
id: SCN-0016
title: Projection Saved View Versus Path-Dependent Rerun
type: scenario
status: ratified
component: COMP-QMB
depends_on: [COMP-QMB, COMP-QMF-RISK, COMP-QMF-REGISTRY]
decisions: [DEC-0273, DEC-0274, DEC-0283]
sources: [docs/decisions/ADR-0022-workbench-expansion.md, docs/contracts/ct-32-performance-result.yaml, docs/contracts/ct-29-exit-record.yaml, docs/contracts/ct-22-book-charter.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md, _docwork/workbench-increment-brief.md]
generated: 2026-09-14
verified: 2026-09-14
stale_after: 30d
---

# SCN-0016: Projection Saved View Versus Path-Dependent Rerun

This scenario pins the two named analysis methods: `analysis.project` produces a saved-view JSON over an existing CT-32 and its CT-29 stream; `analysis.rerun` produces a new QMB run and a new CT-32. Projection never rescales size, R, Book, ports, or `starting_capital`. [DEC-0273]

## Given

A completed governed (or coordinated) run has produced one CT-32 performance-result artifact and a paired CT-29 exit-record stream under that run's replay binding. The registry holds the Book charter (CT-22) cited by the original run. A second complete Book definition exists in the registry `dev` zone as a distinct fingerprinted candidate — not a patch on the first. [DEC-0273] [DEC-0274]

## When

Two analysis calls run against that evidence:

1. **`analysis.project`** — with a predicate that filters the CT-29 stream (for example an hours-of-day filter) over the cited `source_ct32` and `source_ct29`.
2. **`analysis.rerun`** — with a new Book `fp1` (the complete `dev`-zone candidate) as the path-dependent input, spawning a new QMB run. [DEC-0273] [DEC-0274]

## Then

**(1) Projection yields saved-view JSON, not a CT-32.** The durable body is the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`. It is a saved view, not a run: it writes no new CT-32, consumes no ExecutionEnvironment occupancy, and never reads as B-4 `role = confirmation` evidence. Homes: ungoverned return value; governed-without-QMA JSON sidecar in the **source** run-dir; coordinated daemon-persisted plus `analysis.published`. [DEC-0273] [DEC-0283]

**(2) Path-dependent rerun yields a new CT-32.** `analysis.rerun` is a new QMB run. Its artifact is a new CT-32 under the new Book binding. A proposed Book/BMS variant is a complete new fingerprinted CT-22/CT-27, not a field patch. [DEC-0273] [DEC-0274]

**(3) `compare_runs` stays readout only.** Comparing the original CT-32 to the rerun CT-32 is a readout function; it invents neither a third method nor a confirmation label. [DEC-0273]

## Failure branches

**Branch A — size rescale presented as projection.** A caller asks `analysis.project` to rescale size, R, Book, ports, or `starting_capital` (or any money-path counterfactual) while keeping the same CT-32 identity. That request is forbidden as projection: those changes are path-dependent and require `analysis.rerun` (a new run, a new CT-32). Labels stay parent-shaped — CT-32 and B-4 gain no `analysis_method` field. [DEC-0273] [DEC-0283]

## Worked numbers

This scenario pins a control-and-identity flow. The load-bearing chain:

- **projection body** = `{method: projection, source_ct32, source_ct29, predicate, as_of}` — the canonical saved-view JSON, never a CT-32 (DEC-0273);
- **rerun artifact** = new CT-32 from a new QMB run (DEC-0273);
- **Book/BMS variant** = complete new `fp1` in `dev`, never a patch (DEC-0274);
- forbidden projection axes: size, R, Book, ports, `starting_capital` (DEC-0273).
