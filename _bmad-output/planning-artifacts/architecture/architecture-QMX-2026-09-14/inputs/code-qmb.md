# Code inventory — QMB (`integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`)

Evidence: `source-inspected` via `git ls-tree` / `git show integration:<path>` unless noted. Docs cited for design intent. Class/test existence ≠ end-to-end runtime proof. Lead only: `workroom/research/2026-09-14-qmb-understanding.md`.

## Capability classification (compact)

| Capability | Class | Evidence | Primary home on integration |
|---|---|---|---|
| Pure `run()` / `run_slice()` (values, no evidence) | **reuse** | source-inspected | `qmb/src/qmb/runloop/loop.py` |
| Impure orchestrator (spawn, logs, one ledger line) | **reuse** | source-inspected | `qmb/src/qmb/orchestrator/{spawn,ledger,log,governor,study}.py` |
| Python API door (`import qmb` / `doors.api`) | **reuse** | source-inspected | `qmb/src/qmb/__init__.py`, `doors/api/__init__.py` |
| CLI door (`qmb` console script) | **reuse** | source-inspected | `doors/cli/__init__.py`, `doors/cli/tree.py` |
| MCP door | **extend** (scaffold → ship) | source-inspected | `doors/mcp/__init__.py` (`SHIPPED=False`, `serve()` refuses) |
| Door parity (CLI↔API derived) | **reuse** | source-inspected | `doors/parity.py` |
| Config compiler / resolved run-config | **reuse** | source-inspected | `config/{compiler,fragments,replay,qml_compile}.py` |
| Registry-read as-of port | **reuse** | source-inspected | `registryread/{port,hub,as_of}.py` |
| Data download / verify / gap-check / list / catalog / generate | **reuse** | source-inspected | `data/*`; CLI `DATA_COMMANDS` |
| Provider→exact price conversion | **reuse** (library-only) | source-inspected | `data/convert.py` — not a CLI command |
| Claim class / store taint / licensing | **reuse** | source-inspected | `data/{claim_class,store_taint,licensing,policy}.py` |
| Execution ports (fill/slippage/cost/financing/spread) | **reuse** | source-inspected | `execution/*` |
| Optimize sampler (TPE parameter search) | **reuse** | source-inspected | `optimize/sampler.py` (`SAMPLER_FAMILY=tpe-class`) |
| Strategy-structure / template generation | **new** (absent) | source-inspected (negative) | no module; sampler searches declared CT-33 params only |
| Optimize objective / splits / sensitivity / resume | **reuse** | source-inspected | `optimize/{objective,splits,sensitivity,resume,space}.py` |
| Sweeps (axes, admit, batch, rank) | **reuse** | source-inspected | `sweep/*`; CLI exposes `sweep.count` only |
| Robustness ladder (WF, trade-shuffle MC, candle MC, significance) | **reuse** | source-inspected | `robustness/*` — library-only, no CLI group |
| Results CT-32 / measures / charts / render / compare | **reuse** | source-inspected | `results/{ct32,measures,charts,render,interpret}.py` |
| Host QL-7 adapter (QML conformant bots) | **reuse** | source-inspected | `host/adapter.py` |
| Plain-Python `SliceHandler` bridge | **reuse** | source-inspected | `runloop/loop.py` `SliceHandler`; host package optional |
| Host Layer-2 sandbox runner | **reuse** | source-inspected | `host/runner.py` (`run_sandbox`; not re-exported from top-level `qmb`) |
| Study stop + resume | **reuse** | source-inspected | `orchestrator/study.py::stop_study`; `optimize/resume.py` |
| Notebook / Jupyter runtime lifecycle | **new** (product) / **connect** (API already) | documented-design + source | B-9 = pure import; no notebook host in QMB |
| What-if (filter/rescale existing trades / day-hour rules) | **new** | source-inspected (negative) | `results.interpret` compares CT-32 fields only; no scenario refilter |
| Candidate databanks (persistent filtered candidate stores) | **new** (QMB) / **connect** (QMA candidates) | source + CT-47 | QMB has ledger/sweep ranks, not databank collections |
| Custom-Project-like procedure graphs (chained stages/loops) | **new** (product) / **connect** (library rungs) | source-inspected | procedures exist as callable functions, not a workflow graph |
| QMA→QMB door (CT-47 ExperimentSpec path) | **connect** (defined-unwired) | docs + QMA source | contract `wiring_status: defined-unwired`; QMA port/service source exists |

---

## Source-linked findings

### 1. Pure run vs orchestrator evidence

Standing law matches source.

- **Pure library:** `run_slice` / `run` / `reproduce_run` in `qmb/src/qmb/runloop/loop.py`. Docstring on `run_slice`: “Pure: no log, no ledger write.” Six pinned sub-phases; forming bars non-actionable; warm-up is in-loop with trading locked.
- **Impure owner:** `qmb/src/qmb/orchestrator/__init__.py` module docstring: library `run()` writes nothing; orchestrator owns sinks, process-per-run spawn, `min(cpu, memory)` governor, abort. Symbols: `start_run`, `spawn_run`, `spawn_governed`, `spawn_concurrent`, `collect_run`, `abort_run`, `finish_run`, `stop_study`.
- **Study stop:** `orchestrator/study.py::stop_study` — one ledger line per already-spawned run (`completed` or `aborted`); `resumable=True`; resume via `optimize.plan_study_resume` / `resume_stepper`.
- **Ledger roles:** `confirmation | trial | replicate | aborted` (`ledger/line.py`); bar verdict is reader-derived fold, never frozen in the line (`docs/components/qmb.md`, spine B-4).

**Class:** **reuse** both modes. Exploratory notebooks/UI call pure API; governed evidence requires orchestrator composition.

### 2. Python API vs CLI vs MCP

| Door | Status | Notes |
|---|---|---|
| Python API | Shipped | Thin re-export; “Direct calls return values and produce no governed evidence” — `doors/api/__init__.py` |
| CLI | Shipped product face | Groups: `backtest`, `data`, `optimize`, `sweep`, `ledger`, `config` — `doors/cli/tree.py` `COMMAND_GROUPS` / `_COMMAND_TREE`. Entry `qmb = qmb.doors.cli:main` in `pyproject.toml`. Orchestrator entry for backtest: `qmb.orchestrator.spawn_run`. |
| MCP | Scaffold only | `doors/mcp/__init__.py`: `SHIPPED=False`, `POST_CLI_V1=True`, `serve()`/`main()` → `unsupported capability`. Not in door-set (`parity.py` `MCP_IN_DOOR_SET=False`). |
| Parity | Shipped | `doors/parity.py` derives CLI↔API capability surfaces programmatically (fixes prior hand-catalog gap on `data.generate`). |

CLI does **not** expose robustness, results/charts, host/sandbox, or full sweep batch/rank — those are library (and examples/tests) surfaces. Missing CLI coverage is **missing wiring**, not missing function.

### 3. Data catalog / download / verify / gap_check / convert

`DATA_COMMANDS = ("download", "verify", "gap-check", "list", "catalog", "generate")` — `data/__init__.py`. CLI mirrors that set.

- Thin fronts over `qmf-data` (B-11 / DEC-0166); runs never provider-fetch (`refuse_run_provider_fetch`).
- Dukascopy adapter #1, license tags, coverage catalog, integrity verify, interior gap report (never fill), synthetic `generate` with claim-class / store-taint law.
- **`convert`:** `data/convert.py::provider_price_to_exact` — named AD-22/AD-7 boundary for provider floats. Library helper, **not** a `DATA_COMMANDS` entry / CLI subcommand.
- Multi-scenario generation: `data/scenarios.py` (`generate_scenarios`, fanout admission) — synthetic infra-stress, not edge.

**Class:** **reuse** acquisition/QA fronts; **extend** only if product needs a first-class convert CLI or richer transform UX (function already exists).

### 4. Optimize sampler — parameter search vs strategy-structure generation

- Default adapter: Optuna TPE-class, `n_jobs=1`, pin `registry:qmb_sampler_pin` — `optimize/sampler.py` (`SAMPLER_FAMILY="tpe-class"`, `SAMPLER_GENERATOR="TPESampler"`).
- Generation-stepped: `StudyStepper.ask()` → immutable `ParameterBatch`; second ask before `tell()` refused for TPE (`refuse_parallel_ask`). History is ledger view, not Optuna store.
- Space is CT-33 Bot parameter schema (`optimize/space.py`, `parameter_space_from_bot`) — **numeric/categorical parameter search over a declared bot**, not structural AST/template mutation.
- Objective/constraints/winner set: `optimize/objective.py` (`compute_winner_set` makes no edge/bar verdict — deferred GAP-0049).
- Sensitivity: `build_sensitivity_report` — distributions/slices/clusters; `refuse_search_quality_verdict`.
- Resume/cost: `plan_study_resume`, `estimate_study_cost`.

**Class:** parameter optimize = **reuse**. StrategyQuant-like structure/template generation = **new** (belongs with QML/structure authoring + search product, not present in QMB optimize).

### 5. Robustness (walk-forward, MC, significance)

Library package `robustness/` implements B-14 ladder as pure functions with versioned `procedure_contract`:

| Procedure | Entry points | Claim class |
|---|---|---|
| Trade-shuffle MC | `run_trade_shuffle`, `shuffle_scenarios`, `governed_scenario_requests` | robustness / infra-stress; no edge |
| Candle-perturbation MC | `run_candle_perturbation`; persist → `world=simulated` | ephemeral stays replay-legal; persisted synthetic refused as evidence |
| Rule-significance | `run_signal_only_pass`, `run_significance_gate` | advisory; `refuse_gate_auto_merge`, `refuse_live_result_world` |
| Walk-forward | `plan_walk_forward`, `admit_walk_forward`, `aggregate_walk_forward` | ordered split-manifest runs; OOS bar `not-yet-ruled`; battery thresholds deferred |

Shared: return-space float carve-out (`carveout.py`), distribution summary without pass/fail (`summary.py`). Thresholds/pass batteries → GAP-0048/0049 (**Deferred** content, not missing procedure mechanics).

**Class:** **reuse** procedures; **extend** when wiring CLI/UI/orchestrator fan-out for scenario batches; threshold content stays deferred AD/GAP.

### 6. Sweeps, studies, resume

- **Sweep:** declarative axes (instruments/timeframes/parameters) → `expand_sweep` / `preflight_run_count`; `admit_sweep` freezes one registry as-of; `run_sweep_batch` one line per combo; `rank_sweep` publishes ranked list, `refuse_rank_act` (no promote/bench).
- **CLI today:** `sweep.count` only — batch/rank are library.
- **Study:** optimize Study + `stop_study` + `plan_study_resume` / `resume_stepper`.
- Orchestrator concurrency: process-per-run; explicitly not Ray/Docker daemon (`orchestrator` identity constants).

**Class:** **reuse** library; **extend**/connect UI and fuller CLI for batch/rank/study lifecycle.

### 7. Results / CT-32 / charts

- Canonical artifact **is** CT-32: `results/ct32.py` (`mint_run_performance_result`, `assemble_run_performance_result`, `load_stored_ct32`, `require_reproduced_fingerprint`).
- Measures: `assemble_v1_measure_set` / `emit_measure`.
- Charts: `assemble_v1_chart_set` — series data (not PNG-as-identity); `downsample_chart_series` display-only.
- Render: HTML/markdown token substitution (`render_*`, `write_run_renders`); agents must not parse HTML.
- Interpret: `explain_run`, `compare_runs`, `flag_refusal_heavy` — field readout/diff of stored CT-32; forbids allocate/bench/bind/promote/size.

**Class:** **reuse** for reports/charts/compare. Interactive chart UI is a **connect** consumer of chart-series payloads (Simulator/UI later per ADR-0017).

### 8. Host adapter — QML bots vs plain Python

- **QL-7:** `host/adapter.py` — `construct_conformant_bot`, `drive_instant`, `ConformantSliceHandler`. Injects declared-footprint evidence only; no Book/clock/venue commands.
- **QL-8 sandbox:** `host/runner.py::run_sandbox` — AST scan + capability starvation + subprocess isolation; OS confinement deferred. Not re-exported from top-level `import qmb` (`host/__init__.py` documents this).
- **Plain Python:** first-class `SliceHandler` protocol on the run loop; ungoverned bots never require `qmb.host` (module docstring).

**Class:** **reuse** both bridges. Node later reuses same QL-7 seam (documented in `docs/components/qmb.md`).

### 9. Gaps vs donor-shaped product asks

| Ask | In QMB today? | Classification |
|---|---|---|
| Notebooks / Jupyter | Same pure library importable (B-9); no notebook kernel/lifecycle/project binder | **connect** API; **new** host/lifecycle if product owns notebooks |
| What-if on closed trades (day/hour/count filters, snippet rules) | Absent. Closest: `compare_runs` / robustness shuffles (different semantics) | **new** analysis procedure (distinguish path-dependent re-sim vs post-hoc trade filter) |
| Money-management / sizing simulator over past trades | Absent in QMB (Book/BMS own sizing on money path) | **new** or **connect** to Book/BMS analysis — AD needed |
| Candidate databanks | No persistent “databank” collection type. Ledger lines + sweep rankings + QMA `StrategyHandle` candidates (CT-47) | **new** store/UX in experimentation product **or** **connect** to QMA/registry candidate zone |
| Custom Projects (chained tasks, loops, waits, filters until databank full) | Ladder rungs callable; no DAG/workflow runner inside QMB | **new** procedure-orchestration product layer; QMB remains callable wind tunnel (**reuse** rungs) |
| Strategy structure generation | Not in optimize | **new** (QML/authoring + search), not QMB sampler extend |
| MCP day-to-day agent door | Scaffold | **extend** post CLI v1 |
| Fidelity calibration / `world=simulated` unlock | Seams present; content open | GAP-0048 **Deferred** |
| Search-quality / registration gate | Prevention delivered; gate deferred | GAP-0049 / GAP-0016/0017 **Deferred** |

### 10. CT-47 reconciliation (do not pick one silently)

- **Docs:** `docs/contracts/ct-47-qma-experiment-spec.yaml` — `wiring_status: defined-unwired`, `consumers: []`, provenance says “no code exists.”
- **Integration source (QMA side):** port/service implementations exist (`qma.core.ports.qmb`, `qma.daemon.backtest.service` per lead audit) defining the Agent→tool→Backtesting Service→qmb door route and forbidding `import qmb` from QMA.
- **Reconciled reading:** contract is ratified and marked unwired; QMA has **source-shaped** door/service code that is not proven end-to-end against a live QMB process; QMB itself already exposes CLI/API doors the contract intends to call. Treat as **connect** with **missing wiring/deployment proof**, not missing QMB backtest capability.

---

## (1) What already exists

A full B-1..B-15 shaped library+CLI on `integration`: pure event-slice loop; config compiler; registry-read port; data fronts; execution ports; CT-32/results/charts; ledger; orchestrator spawn/governor/logs; optimize (TPE parameter Study + resume); sweeps; robustness ladder; QL-7 host + plain-Python handler; thin API+CLI doors; MCP scaffold. Ordinary Python exploration and governed orchestrated evidence are both intentional.

## (2) Missing wiring vs missing function

| Missing wiring (function present) | Missing function |
|---|---|
| Robustness / sweep batch+rank / study lifecycle not on CLI | Strategy-structure generation |
| MCP not shipped | What-if trade-filter / sizing-simulator procedures |
| CT-47 QMA↔QMB end-to-end deployment | Candidate databank collection type inside QMB |
| UI/Simulator consumption of chart-series | Custom-Project workflow graph runner |
| Notebook lifecycle host (if product-owned) | GAP-0048 fidelity content; GAP-0049 thresholds; registration gate |

## (3) Recommended architectural ownership

| Concern | Owner |
|---|---|
| Wind tunnel, evidence minting, validation ladder, data fronts, sampler, CT-32 | **QMB** (reuse/extend in place) |
| Bot definition, parameter schema, structure/templates, QL-7 protocol | **QML** (+ qmf-structure/indicators) |
| Book/BMS/risk/CT-32 definitions | **qmf-risk** (QMB wires in replay) |
| Rooms/splits/journal | **qmf-data** (QMB thin front) |
| Records/lineage/as-of delivery | **qmf-registry** + QMB `registryread` |
| Agent ExperimentSpec, candidates, tool placement to qmb door | **QMA** (connect; does not import QMB) |
| Live venue / node host of same loop | **QMN** (not QMB) |
| Notebooks, What-if workbench, databanks, Custom-Project graphs, Simulator UI | **New product/UX layers** that **call** QMB; do not fork a second tunnel |

## (4) Open questions — AD vs Deferred

**Need an AD (architecture sitting):**

1. Where do What-if / MM-simulator live — QMB analysis procedures vs separate analysis app — and how they label non-path-dependent results vs re-sim?
2. Who owns candidate databanks — QMB ledger extensions, registry collections, or QMA candidate zone UX?
3. Is Custom-Project-like orchestration a QMA Skill/Loop concern, a QMB study graph, or a new experimentation-app layer?
4. Does strategy-structure search enter QML authoring only, or does QMB gain a non-parameter sampler family?
5. Notebook lifecycle: QMX-hosted kernels vs external Jupyter using `import qmb` only (B-9 already allows the latter)?

**Can stay Deferred (already ticketed):**

- GAP-0048 fidelity taxonomy/calibration / simulated unlock
- GAP-0049 search-quality thresholds / pass batteries
- GAP-0016/0017 registration gate (prevention already in loop/splits)
- MCP tool-list/details post CLI v1
- Hardened OS sandbox confinement (named deferred on `host/runner.py`)

---

*Checkout: `main` (planning only). Product cited: `git show integration:<path>` at `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. No implementation or branch switch performed.*
