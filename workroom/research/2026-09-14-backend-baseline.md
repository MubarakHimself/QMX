# QMX backend baseline for UI planning

Read-only inspection on 2026-09-14. This is a starting inventory, not a runtime audit or a release claim.

## The intentional branch split matters

The operator confirmed on 2026-09-14: planning happens on `main`, and implementation belongs on `integration`. The split itself is expected. The issue to guard against is consulting only one branch and misclassifying capability status.

The active checkout is `main` at `430fb7d`. It contains documentation, planning and factory tooling; absence of product packages there does not prove the backend is absent. The local `integration` ref is `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` (commit dated 2026-09-04). Its tree contains `packages/`, `qmb/`, `qml/`, `qmn/`, `qmx-agents/`, product tests and QA records. No fetch was performed: this is the locally available implementation revision, not a claim about the current remote or deployed version.

Inspection used `git ls-tree`, `git show` and `git log`, without switching branches or altering existing work. The UI worktree also exists at `.worktrees/ui`; neither its existence nor its name proves a usable UI has shipped.

## What was actually inspected

Paths below belong to the pinned `integration` revision, not necessarily the current working directory.

| Area | Source evidence | What it establishes and what it does not |
|---|---|---|
| QMB Python access | `qmb/src/qmb/doors/api/__init__.py` | In-process re-export surface exists for research/UI consumers. Its documented contract distinguishes pure calls from governed evidence. Do not add a new HTTP service merely because UI contracts are needed. |
| Parameter optimization | `qmb/src/qmb/optimize/sampler.py` | Inspected source includes Optuna TPE imports and generation-based trial machinery. This is evidence of parameter optimization source, not arbitrary strategy-logic generation or StrategyQuant parity. |
| Walk-forward | `qmb/src/qmb/robustness/walkforward.py` | Source defines split-manifest runs and aggregation; it explicitly leaves some thresholds/verdict conditions unresolved. A function's presence is not proof of accepted operational verdicts. |
| Experiment records | `qmx-agents/packages/qma-daemon/src/qma/daemon/experiments/service.py` | Inspected registration, fingerprints, ledger/lineage references and internal maps. This disproves a blanket assumption of no experiment source. It does not prove restart persistence, remote continuation or complete QMA-to-QMB wiring. |
| Other candidate reuse | Tree lists `qmb/src/qmb/data/{catalog,convert,download,gap_check,verify}.py`, `sweep/`, `results/`, `robustness/`; QML, QMN and QMA packages/tests | These are audit targets. Only their presence was checked here; no detailed completeness or behavior claim. |
| Historical QA | `FINAL-REPORT.md` on integration | A prior report describes fixed defects and passing checks at its recorded commits. These are historical claims, not checks rerun by this session. |

`docs/contracts/ct-47-qma-experiment-spec.yaml` still labels the contract `defined-unwired` and says no code exists. The inspected source means that statement must be reconciled with actual wiring and revision history. It would be equally wrong to assume full wiring from a class name.

## Consequential questions for architecture

1. **Strategy generation:** distinguish varying declared parameters from generating condition/logic structure. Existing F01 and GAP-0085 identify a semantic question, not merely a missing UI control.
2. **Laptop-off continuation:** QMA documentation defaults the daemon to the workstation. A remote worker alone does not show that orchestration, state and follow-on task scheduling survive the workstation sleeping.
3. **Book/BMS assistance:** user intent includes proposing versions; QMA documents prohibitions on authoring/mutating Book/BMS records as well as money-path operations. Establish the exact candidate-authoring boundary and necessary amendment; do not label all non-live writes automatically allowed.
4. **Paper testing:** user wants it before promotion. Current QMA ExperimentSpec permits recorded-evidence/QMB replay, not execution on any account, paper included. Existing node and research responsibilities need reconciliation before assigning this workflow.
5. **What-if/sizing:** filtering or rescaling past trades may be useful analysis, but it is not equivalent to rerunning a path-dependent Book/BMS. Name the method and its limitations in both the backend and UI.
6. **Knowledge retrieval:** QMA evidence custody and literal lookup do not automatically provide Delphi-style indexing and retrieval. Reuse existing owners before proposing another store.
7. **Extensions:** executable backend extensions do not establish a runtime UI contribution system or a no-code authoring guarantee. Clarify the promised user-facing scope separately.

These are focused investigation/amendment candidates, not an approved replacement architecture. Existing component specs, the dependency manifest, registry variables, gaps and authority rules remain the baseline. Reconcile newer CONNECT planning against the selected implementation revision as part of the Grok audit.
