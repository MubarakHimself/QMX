---
id: SCN-0015
title: Three Door-Derived Experiment Lanes
type: scenario
status: ratified
component: COMP-QMB
depends_on: [COMP-QMB, COMP-QML, COMP-QMA-CORE, COMP-QMA-DAEMON, COMP-QMF-REGISTRY]
decisions: [DEC-0270, DEC-0275, DEC-0276, DEC-0285]
sources: [docs/decisions/ADR-0022-workbench-expansion.md, docs/contracts/ct-32-performance-result.yaml, docs/contracts/ct-47-qma-experiment-spec.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md, _docwork/workbench-increment-brief.md]
generated: 2026-09-14
verified: 2026-09-14
stale_after: 30d
---

# SCN-0015: Three Door-Derived Experiment Lanes

This scenario pins the three experiment lanes of the strategy-experimentation workbench: the lane is selected by which door the caller uses, never by a payload flag. Ungoverned returns values only; governed writes one QMB ledger line plus one CT-32; coordinated places QMB through the QMA Backtesting Service under a registered ExperimentSpec. [DEC-0270]

## Given

A registered bot definition is resolvable by fingerprint `fp1` through the single registry-read port. The workspace has the `qmb` library and CLI available, and the QMA daemon (when present) exposes its Backtesting Service door. No caller-declared `lane` / `workbench_lane` field exists on CT-32, on B-4 role, or on QMF AD-12 evidence class — `workbench_lane` is metadata derived from the door. [DEC-0270] [DEC-0285]

## When

The same bot `fp1` is invoked through each door in turn:

1. **Ungoverned** — ordinary Python calls `qmb.run(...)` (or imports `qml` for authoring values) with no orchestrator spawn and no CT-47 placement.
2. **Governed** — the QMB orchestrator spawns an isolated process for a CLI/MCP backtest that is **not** placed by a CT-47 ExperimentSpec (the SCN-0012 research-paper shape).
3. **Coordinated** — the QMA Backtesting Service places at most one `qmb` CLI/MCP run invocation per ExecutionEnvironment under a registered ExperimentSpec; the daemon never `import qmb`. [DEC-0270] [DEC-0276]

## Then

**(1) Ungoverned returns values only.** The call returns library values. It writes no QMB ledger line, no CT-32 **registry record**, and no ExperimentSpec / Experiment Ledger entry. A returned CT-32-shaped value, if any, is not a Library object and is not governed evidence. [DEC-0270]

**(2) Governed writes one ledger line and one CT-32.** The orchestrator spawns the run (not a CT-47 placement), appends exactly one WriterId-scoped QMB ledger line carrying metadata `workbench_lane = governed`, and the run's canonical artifact is one CT-32. This is **research-paper**: QMB governed replay (`world = replay`) outside the trading node. The run is **not** an ExperimentSpec and creates no Experiment Ledger entry unless a later act places the same work through CT-47. [DEC-0270] [DEC-0275]

**(3) Coordinated still writes QMB evidence and a second label on the Experiment Ledger.** QMA places the run only when a registered ExperimentSpec (CT-47) exists. The spawned run still writes one QMB ledger line with metadata `workbench_lane = governed` and one CT-32 — that is the evidence, reached by `_ref`; QMA does not copy it. The Experiment Ledger entry carries `workbench_lane = coordinated` (QMA placed it). The two labels are not the same field and must not be collapsed. Occupancy is one `qmb` **run** invocation per ExecutionEnvironment. [DEC-0270] [DEC-0276]

## Failure branches

**Branch A — caller-declared lane flag.** A caller attempts to select the lane by setting a `lane` / `workbench_lane` / `analysis_method` field on the payload, on CT-32, or on a B-4 role. The design refuses that path: the **door** selects the lane; a flag does not. Extending CT-32 or B-4 with such a field is a spine amendment, not a connect fix. [DEC-0270]

## Worked numbers

This scenario pins a control-and-identity flow. The load-bearing chain:

- **door → lane** — ungoverned / governed / coordinated are mutually exclusive outcomes of which surface was called (DEC-0270);
- **`workbench_lane = governed`** rides the QMB ledger line metadata for every orchestrator spawn, including those QMA placed (DEC-0270);
- **`workbench_lane = coordinated`** rides the Experiment Ledger entry when QMA placed the run; that entry cites the QMB ledger line and CT-32 by `_ref` (DEC-0270);
- research-paper is the governed replay noun; it is not node-paper and not QMA-paper (DEC-0275).
