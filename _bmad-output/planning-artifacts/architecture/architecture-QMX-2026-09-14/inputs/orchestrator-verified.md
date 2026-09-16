# Orchestrator-verified findings (2026-09-14)

Planning checkout: `main` `430fb7d`. Implementation: `integration` `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. Source inspected via `git show`/`ls-tree` only. Donor pages fetched live. Not runtime-demonstrated.

## Existing product (source-inspected)

| Area | Exists | Wiring status |
|---|---|---|
| QMB library + CLI public surface | Broad: config, data (catalog/download/verify/gap_check/convert/generate/licensing), execution ports, host/QML adapter, ledger, optimize, orchestrator/study, registryread, results/CT-32, robustness ladder, runloop, sweep | Library source complete enough to call reuse. MCP door `MCP_SHIPPED=False`. |
| QML two-artifact bot | declaration, protocol, conformance, families, footprint, logic; `admit_ungoverned_tunnel` | Source present. `.qml` DSL not revived. |
| QMA daemon | experiments service, backtest service, sqlite writer, scheduler/continuation, plugins (analysis-backtest, research-corpus, …) | ExperimentSpecService uses in-memory `_specs` plus ledger store; BacktestingService default transport is `RecordingQmbDoorTransport` (records CLI/MCP invocations, does not spawn `qmb`). CT-47 still `defined-unwired` in docs. |
| qma-ui-contract | `STUB.md` only | Explicit deferred GAP-0081. |
| QMN | paper/, promotion/, loop (QMB run_slice), doors | Operational paper soak ≠ research paper. |

## Donor mechanisms (official docs, 2026-09-14 fetch)

**StrategyQuant.** Random generation of entry/exit rules from building-block pool; genetic evolution; templates with RandomCondition placeholders and NegatedCondition pairing. Custom Projects = ordered task workflows (build → retest markets → WF matrix → databank), restartable until full. Distinct from QMB parameter TPE.

**QuantAnalyzer What-if.** Filter existing trade lists by hours/days/max-trades; snippet-extensible. Vendor page does not claim path-dependent Book replay. Money-management / portfolio advertised separately.

**QuantDataManager.** Dukascopy (+ others) download, CSV import, gap/spike/incorrect-candle review, timezone clones that auto-update from source, timeframe recompute, MT4/MT5 export. Pro CDN/verified-download is a vendor speed claim.

**QuantConnect.** A Project holds files for backtests, notebooks, optimizations, live deploy. Research Pipeline is a kanban (Ideas→Research→Backtest→Paper→Live) plus specialized agents. Not a required QMX lifecycle. Paper trading is a live brokerage simulation, not QMB replay.

**OpenResearch.** Local-first; parallel agents in isolated git worktrees; immutable run archives tied to commits; local/SSH/remote compute. Git-worktree-per-experiment is Cut in QMA (DEC-0376). Borrow lineage+compute placement, not git-branch-per-parameter.

**Delphi.** Local MCP index of repos/papers/datasets; PostgreSQL+pgvector; context packs. Maps to QMA KnowledgeSource port (GAP-0073 still deferred). Not a replacement store.

**RoboQuant.dev.** Fetch of homepage returned session-check only this sitting. Keep commercial AI IDE distinct from Kotlin `neurallayer/roboquant`. Treat as weak/supplemental until a successful page fetch.

## Classification seed (to be reconciled with agent files)

| Capability | Class | Owner |
|---|---|---|
| Event-slice backtest, optimize, sweep, robustness, CT-32 | reuse | QMB |
| Data download/verify/gap/catalog | reuse (connect UI) | QMB fronts qmf-data |
| Ungoverned ordinary Python in the tunnel | reuse | QML `admit_ungoverned_tunnel` + QMB `run()` |
| QMA mission/task/plugin/skill/routine | reuse | QMA |
| QMA→QMB real process door | connect | replace Recording transport; persist ExperimentSpec through daemon journal |
| Candidate databank | connect | query over QMB ledger + registry as-of; no second store |
| Custom-project procedures | connect | QMA Graph Template / Skill / Routine calling QMB studies |
| Notebook as research host | connect | QMB Python API + QMA ExecutionEnvironment kernel lifecycle |
| Shared Library | connect | qmf-registry kinds + CT-32 + ExperimentSpec projections |
| What-if trade-list filter | extend | named QMB analysis view over CT-29/CT-32; claim-class `projection` |
| Path-dependent what-if / MM / Book policy | reuse via re-run | QMB new resolved-config, not a filter |
| Structure generation (SQ templates, GAP-0085) | new | QML authors CT-33/34 candidates; QMB only runs them |
| Knowledge indexing (Delphi-class) | undecided/deferred | QMA KnowledgeSource; GAP-0073 |
| UI contribution SDK | deferred | GAP-0081 |
| Laptop-off continuation | connect | QMA daemon must not die with the laptop; QMB processes are job-lifetime |
| Research paper-before-promotion | connect | QMB governed replay + Book paper evidence; forbidden in QMA; not node soak |
