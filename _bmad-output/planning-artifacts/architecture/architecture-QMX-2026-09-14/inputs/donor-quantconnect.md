# Donor investigation — QuantConnect Cloud + Lean CLI

**Donor:** QuantConnect (cloud platform and Lean CLI).  
**Date:** 2026-09-14.  
**Mode:** architecture only. No implementation. Shapes, not engines.  
**QMB note:** QMB was reverse-engineered from Lean *shapes*, not Lean code. This sitting does not reopen that. It only extracts product mechanisms that still transfer onto existing QMX owners.

## Standing bans (apply to every row)

- No donor engine adoption (LEAN, QuantBook, `QCAlgorithm`, `quantconnect/lean` / `quantconnect/research` images).
- QMA never executes the money path, including paper (DEC-0315, DEC-0341; CT-47).
- QMB never imports `qmf-venue`.
- Ordinary Python stays legal (L33; QML QL-2; QMB B-9).
- QC Research Pipeline stages are **not** a required QMX lifecycle.
- Do not copy vendor UI (Algorithm Lab, Ask Mia, Research Pipeline kanban chrome) or vendor engines.

## Evidence sources (official docs first)

Workroom/research notes were leads only. Primary evidence is official QuantConnect / Lean documentation fetched 2026-09-14:

| Area | Official URL |
|---|---|
| Projects | https://www.quantconnect.com/docs/v2/cloud-platform/projects |
| Project getting started | https://www.quantconnect.com/docs/v2/cloud-platform/projects/getting-started |
| Project structure | https://www.quantconnect.com/docs/v2/cloud-platform/projects/structure |
| Research (cloud) | https://www.quantconnect.com/docs/v2/cloud-platform/research |
| Research getting started | https://www.quantconnect.com/docs/v2/cloud-platform/research/getting-started |
| Research deployment / nodes | https://www.quantconnect.com/docs/v2/cloud-platform/research/deployment |
| Research engine | https://www.quantconnect.com/docs/v2/research-environment/key-concepts/research-engine |
| Research Pipeline | https://www.quantconnect.com/docs/v2/cloud-platform/research-pipeline |
| Optimization parameters (cloud) | https://www.quantconnect.com/docs/v2/cloud-platform/optimization/parameters |
| GetParameter (algorithm API) | https://www.quantconnect.com/docs/v2/writing-algorithms/optimization/parameters |
| Organization resources / node types | https://www.quantconnect.com/docs/v2/cloud-platform/organizations/resources |
| Object Store | https://www.quantconnect.com/docs/v2/cloud-platform/object-store |
| AI agents | https://www.quantconnect.com/docs/v2/ai-assistance/getting-started |
| Agent configuration / tools | https://www.quantconnect.com/docs/v2/ai-assistance/agents |
| MCP server tools | https://www.quantconnect.com/docs/v2/ai-assistance/mcp-server/key-concepts |
| Lean CLI | https://www.quantconnect.com/docs/v2/lean-cli |
| Lean CLI getting started | https://www.lean.io/docs/v2/lean-cli/key-concepts/getting-started |
| Cloud sync | https://www.lean.io/docs/v2/lean-cli/projects/cloud-synchronization |
| Project files / config.json | https://www.lean.io/docs/v2/lean-cli/projects/structure , https://www.lean.io/docs/v2/lean-cli/projects/configuration |
| CLI research | https://www.lean.io/docs/v2/lean-cli/research |
| CLI parameters / optimize | https://www.lean.io/docs/v2/lean-cli/optimization/parameters , https://www.lean.io/docs/v2/lean-cli/optimization/deployment |
| CLI workflows | https://www.lean.io/docs/v2/lean-cli/projects/workflows |
| Private Cloud | https://www.quantconnect.com/docs/v2/local-platform/private-cloud |

QMX mapping evidence is from ratified docs (`docs/components/qmb.md`, `qml.md`, `qma-core.md`, `qma-daemon.md`, `trading-node.md`, CT-33/CT-46/CT-47) and a reconcile of CT-47 `defined-unwired` docs against `git show 1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` (integration).

Status vocabulary: `reuse` | `connect` | `extend` | `new` | `undecided`.  
`qmx_home` is an existing owner only: QMB, QMA, QML, QMF, QMN, UI, undecided.

## Compact table

| Mechanism | What transfers | qmx_home | Status |
|---|---|---|---|
| Project continuity | One durable identity that carries declaration, logic, parameters, research notes, and result lineage across local/remote edits — **not** a QC Project folder | QML | connect |
| Interactive research notebooks | Hypothesis testing that imports strategy code and inspects results **before** a governed run; Jupyter is optional, QuantBook is not | QMB | extend |
| Declared parameters | Typed space outside code; inject at compile/deploy; freeze while running; retune mints a new identity | QML | reuse |
| Research pipeline board | Operator-visible work tracking with specialist assignment — **not** Ideas→Research→Backtest→Paper→Live as product law | QMA | extend |
| Specialist agents and tools | Role-scoped agents that *do* work via tools, skills, memories; never paper/live execution | QMA | connect |
| Typed compute placement | Place research, backtest, agent, and live work on different hosts; agents never name a machine | QMA | connect |
| Research-to-run artifact handoff | Persist research outputs (models, reports) for later QMB runs — **not** QC Object Store | QMF | extend |
| Mixed author/execute workflow | Write locally, execute on declared compute, same library surface | QMB | connect |

---

## 1. Project continuity

### Donor (official)

A QuantConnect **Project** is the unit of continuity. Official project docs: projects contain files to run backtests, launch research notebooks, perform parameter optimizations, and deploy live strategies ([Projects](https://www.quantconnect.com/docs/v2/cloud-platform/projects)). Structure: code files (`.py`/`.cs`) plus notebook files (`.ipynb`); settings, results, attached libraries, and parameters live on the project; clone copies files but not backtest results or live history; migrate copies files but not Object Store content; recycle bin holds deletes 30 days ([Getting Started](https://www.quantconnect.com/docs/v2/cloud-platform/projects/getting-started), [Structure](https://www.quantconnect.com/docs/v2/cloud-platform/projects/structure)).

Lean CLI materializes the same unit locally: `lean project-create` / `lean cloud pull` write `config.json`, `main.py`, `research.ipynb` ([CLI structure](https://www.lean.io/docs/v2/lean-cli/projects/structure)). `config.json` holds `description`, `parameters`, `cloud-id`, `local-id`, `libraries`, `organization-id`, `algorithm-language` ([CLI configuration](https://www.lean.io/docs/v2/lean-cli/projects/configuration)). Continuity across machines is `lean cloud pull` / `lean cloud push`; pulling a cloud project overwrites local config values, and vice versa on push ([Cloud synchronization](https://www.lean.io/docs/v2/lean-cli/projects/cloud-synchronization)).

### QMX already

QMX does **not** have a Project service and must not grow one. Continuity is already split across three identity objects:

- **QML CT-33 Bot definition** + versioned logic distribution (`docs/components/qml.md` QL-2/QL-3): declaration + plain-Python logic; identity is content (`fp1` + source-manifest), `branches-from` version graph.
- **QMA ExperimentSpec** (CT-47): `code_ref` only when code changes, `resolved_config_ref` for parameter/config changes, plus data/environment/seed/harness and a CT-07 lineage DAG — never a git branch per parameter (`docs/contracts/ct-47-qma-experiment-spec.yaml`).
- **QMB resolved run-config** (`docs/components/qmb.md` B-3): one fingerprinted artifact per run; registry as-of sets (B-15) freeze identity for a sweep.

### Mapping

**Status: connect. Home: QML.**  
Transfer the *job* of QC's Project (one thing an operator can name that still means the same strategy after local edits and remote runs). Do not transfer the folder, `config.json`, cloud-id, or IDE. Wire CT-33 (strategy identity) to ExperimentSpec (experiment identity) to QMB run-config (execution identity) so a UI workspace can present them as one continuity unit without minting a fourth service.

UI may *display* a workspace. It does not own identity.

---

## 2. Interactive research notebooks

### Donor (official)

Cloud Research Environment is Jupyter-based; data is accessed through `QuantBook` instead of `QCAlgorithm`; Python may import project code files; recommended before backtests; ML models may be trained in research, saved to Object Store, then loaded in backtest/live ([Research](https://www.quantconnect.com/docs/v2/cloud-platform/research), [Getting Started](https://www.quantconnect.com/docs/v2/cloud-platform/research/getting-started), [Research Engine](https://www.quantconnect.com/docs/v2/research-environment/key-concepts/research-engine)). New projects ship `research.ipynb`. Cells time out after 15 minutes. Research nodes are typed SKUs (R1-4 … R8-16, GPU variants); launch uses the best-performing node by default ([Research deployment](https://www.quantconnect.com/docs/v2/cloud-platform/research/deployment)). Simultaneous peer editing is not supported.

The research engine page is explicit about **batch vs stream**: backtests are event-based and slow; research is for statistical hypothesis testing first; look-ahead bias is easier in notebooks because all data is available at once.

Lean CLI: `lean research "<project>"` starts JupyterLab in the `quantconnect/research` Docker image on port 8888, mounting the project directory; VS Code / PyCharm can attach to that kernel ([CLI research](https://www.lean.io/docs/v2/lean-cli/research)). Local notebooks can read `backtests/<timestamp>/*.json` and, if logged in, cloud backtest stats via the QC API.

MCP/agent tools operate *on the cloud notebook*: `jupyter_create_cell`, `jupyter_execute_cell`, `jupyter_execute_notebook`, etc. ([MCP tools](https://www.quantconnect.com/docs/v2/ai-assistance/mcp-server/key-concepts)).

### QMX already

- QMB B-9: research surface **is the library's own pure functions**, importable from a bare uv-installed package — no server, no Docker, no daemon required (`docs/components/qmb.md` ~99–101). Direct library calls return values and produce **no governed evidence** (B-4).
- Ordinary Python is first-class forever (QML QL-2; L33).
- QMA's "scientist's notebook" is the **Experiment Ledger** (one append-only ledger per Experiment), not a Jupyter file (`docs/glossary.md`; CT-47).
- Docs contain no `.ipynb` product and no QuantBook analogue.

### Mapping

**Status: extend. Home: QMB.**  
Transfer: interactive analysis that imports strategy/logic modules and can read CT-32 / journal outputs *before* a governed orchestrator run.  
Do not transfer: `QuantBook`, LEAN research image, 15-minute cell timeout as product law, or notebooks as a required lifecycle stage.

A `.ipynb` is legal ordinary Python over B-9. If the UI opens notebooks, they remain a thin host of the QMB library. Governed evidence still requires the orchestrator (B-4). QMA agents may *propose* notebook cells only as ordinary Python against B-9; they must not gain a QuantBook-class data engine.

Whether V1 ships a Jupyter UX at all is an AD (see Open questions). The *mechanism* (research-before-backtest, import code, inspect results) already exists.

---

## 3. Declared parameters

### Donor (official)

Parameters are project variables stored **outside** algorithm code. Cloud: add name + default in the Project panel; optimizer injects values when an optimization job launches; `GetParameter` / `get_parameter` reads them ([Cloud parameters](https://www.quantconnect.com/docs/v2/cloud-platform/optimization/parameters), [Project structure § Parameters](https://www.quantconnect.com/docs/v2/cloud-platform/projects/structure)). Algorithm API: values are injected when you run a backtest, deploy live, or launch an optimization; **cannot change while the algorithm runs** ([Writing algorithms — Parameters](https://www.quantconnect.com/docs/v2/writing-algorithms/optimization/parameters)). Live workaround: a scheduled download of a remote file (not a first-class mutate-in-place).

CLI: parameters live in `config.json` as string key/value; `GetParameter(name, default)` in code ([CLI parameters](https://www.lean.io/docs/v2/lean-cli/optimization/parameters)). Local `lean optimize` offers Grid Search or Euler Search, objective min/max, per-parameter min/max/step, and constraints; results under `optimizations/<timestamp>` ([CLI optimize deployment](https://www.lean.io/docs/v2/lean-cli/optimization/deployment)). Cloud optimizer is **grid search only, max three parameters**; more than three requires local CLI. Cloud node types O2-8 / O4-12 / O8-16; parallel node count 1–12; cost estimate before start.

Overfitting guidance (Research Guide): parameter detection heuristics; walk-forward recommended when adding/tuning parameters. That is advice, not a QMX lifecycle.

### QMX already

This is already stricter and more complete than QC:

- **One authoritative schema** on CT-33: name; type ∈ exact integer | exact rational | categorical | boolean; bounds; step; mandatory default; unit-kind; optional hard constraint filters (`docs/components/qml.md` QL-3; `docs/components/qmb.md` B-8).
- Canonical assignment vs B-3 run-spec override; `assignment_is_canonical` stamp; promoting a tuned assignment **mints a new Bot version**, never a silent new default.
- Governed live/paper seats execute the **canonical assignment only**.
- QMB sampler is a pure generation-stepped function; default TPE-class adapter; trial history from the ledger view; walk-forward and permutation sweeps are first-class runs (`docs/components/qmb.md` B-8, B-12, B-14).
- Node config is sealed per boot epoch; identity-bearing values do not hot-reload (`docs/components/trading-node.md`).

### Mapping

**Status: reuse. Home: QML.**  
Do not add `GetParameter`, stringly `config.json` parameters, or a 3-parameter grid-search quota. QMB already consumes the CT-33 space. QC's only transferable reminder: **inject at compile/deploy, freeze for the life of the run** — already B-3 / node-seal law.

QC live "download a file to mutate parameters" is **rejected**: QMX retune = new Bot version + human promotion.

---

## 4. Research pipeline board

### Donor (official)

The Research Pipeline is a **kanban** of project cards: Stage 0 Ideas → Stage 1 Research → Stage 2 Backtest → Stage 3 Paper Trading → Stage 4 Live Trading, plus an archive ([Research Pipeline](https://www.quantconnect.com/docs/v2/cloud-platform/research-pipeline)). Agents can be assigned to a stage so a card landing there auto-deploys that agent. Predefined specialists: Ideas, Research, Research Validation, Backtest, Paper Testing, Live Monitoring, plus Mia and a Conductor. Paper Testing Agent deploys algorithms, compares paper to backtest, and **edits/redeploys**. Live Monitoring Agent reads positions and news and notifies. Quotas ride Agent Nodes.

QMA already retired the word "Kanban" to **Task Graph** (`docs/decisions/ADR-0020-qma-agentic-system.md` / DEC-0348).

### QMX already

- Paper-before-promotion happens **outside the node** (DEC-0261). The node has no per-bot paper lane.
- QMA Missions / Tasks / Task Graph / Routines / Experiment Ledger (`docs/components/qma-core.md`, `qma-daemon.md`).
- Human promotion then separate activation (`docs/components/trading-node.md`).
- QMA money-path deny-list includes paper (`docs/components/qma-daemon.md` AD-16).

### Mapping

**Status: extend. Home: QMA.**  
Transfer: an operator-visible board of work (cards = Missions/Tasks/Experiments) and the idea that a specialist Quant can be assigned.  
Do **not** transfer the five QC stages as QMX lifecycle, auto-promotion down a paper/live chute, or agents that deploy/redeploy paper.

UI may render the Task Graph. QMA owns the work records. QMN owns live after a human promotes.

---

## 5. Specialist agents and tools

### Donor (official)

Agents are recursive tool-users with a standing system prompt and a per-task prompt; tools are granted by permission groups (files, backtest, optimization, research/jupyter, live, object store, kanban, notifications, data) ([Agents](https://www.quantconnect.com/docs/v2/ai-assistance/agents)). Structured JSON outputs; chained vs callable orchestration; custom skills / memories / templates in Object Store `.agent/{skills,memories,templates}`. MCP server is a bridge to the QuantConnect API: `create_project`, `create_backtest` (async, do not poll), `create_optimization`, **`create_live_algorithm`**, `stop_live_algorithm`, `liquidate_live_algorithm`, jupyter_* ([MCP](https://www.quantconnect.com/docs/v2/ai-assistance/mcp-server/key-concepts)).

### QMX already

QMA is the existing agentic system: daemon, desks/Quants/Roles, Tool Registry, capability ladder, skills as a multi contribution, MemoryProvider, ExperimentSpec, money-path deny-list and reachability barrier (`docs/components/qma-core.md`, `qma-daemon.md`). The QMB door is specified: one `qmb` job per environment via `analysis-backtest`; QMB owns parallelism and the run ledger (CT-47; DEC-0316, DEC-0348).

**Reconcile CT-47 wiring (do not pick one silently):**  
- Docs: `docs/contracts/ct-47-qma-experiment-spec.yaml` `wiring_status: defined-unwired`, `consumers: []`, "no code exists".  
- Integration `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` **does** have source: `qmx-agents/packages/qma-core/src/qma/core/ports/experiments.py` (`class ExperimentSpec`) and `qmx-agents/packages/qma-daemon/src/qma/daemon/experiments/service.py` (`class ExperimentSpecService` — register, ledger, CT-07 `branches-from`).  
That is **missing wiring / unverified end-to-end**, not missing function.

### Mapping

**Status: connect. Home: QMA.**  
Transfer: specialist roles with *selective* tools, skills/memories as organization files, structured outputs, async job handles (do not poll — CT-46 `JobHandle` already).  
Do not transfer: Mia, Conductor branding, Agent Teams, live/paper MCP tools, Object Store `.agent` layout as a storage product.

Connect the existing QMA tool registry to the existing QMB CLI/MCP door (one job per environment). Any QC tool that submits, amends, cancels, sizes, binds, or deploys paper/live is `ProhibitedMoneyPathTool` at registration.

---

## 6. Typed compute placement

### Donor (official)

Cloud organizations subscribe to **typed shared nodes**: Backtesting (B-MICRO … B8-16), Research (R1-4 … R8-16), Live (L-MICRO … L8-16-GPU), Agent (A-MICRO … A16-32). Concurrent work scales with node count. Backtesting nodes **cannot** be used for optimizations. GPU nodes are for ML-ish parallel work; transferring data to GPU can make non-ML jobs look slower. Live: one node per simultaneous algorithm; no sub-algorithms sharing a server ([Resources](https://www.quantconnect.com/docs/v2/cloud-platform/organizations/resources)).

Lean CLI local execution uses Docker (`quantconnect/lean` for backtest/optimize, `quantconnect/research` for notebooks). Mixed workflows: write locally, `lean cloud backtest --push --open` for cloud compute/data ([Workflows](https://www.lean.io/docs/v2/lean-cli/projects/workflows)).

Private Cloud: thin-client laptops submit research/backtest/optimize/live jobs to a master/slave server cluster with centralized data and GPU; `lean private-cloud start --master|--slave` ([Private Cloud](https://www.quantconnect.com/docs/v2/local-platform/private-cloud)).

### QMX already

- **QMB orchestrator:** process-per-run, governor `min(cpu, memory)`, no required Docker (`docs/components/qmb.md` B-4/B-5).
- **QMA CT-46:** `ExecutionEnvironment` kinds `local | docker | remote_container | remote_host | browser | desktop`; `ComputeRequirement` (cpu, memory, disk, optional gpu); Compute Router places; agents never name a machine; `network` is `none | allowlist`; trading-node hosts are deny-listed (`docs/contracts/ct-46-qma-execution-environment-job.yaml`; `docs/components/qma-daemon.md`). Docs mark CT-46 `defined-unwired`; treat like CT-47: design exists, end-to-end placement unverified.
- **QMN:** VPS live/paper product; QMA must not run workloads on the trading-node VPS (`docs/components/qma-daemon.md`).
- Daemon default: workstation + Docker workers; remote workers dial **out** to the daemon.

### Mapping

**Status: connect. Home: QMA.**  
Transfer: typed placement by *workload class* (research vs backtest vs agent vs live) and "author here, run there".  
Do not transfer: QC SKU names, fair-use token caps, LEAN Docker images, or a LEAN private-cloud master/slave.

Connect:

| Workload | Placement owner | Execute |
|---|---|---|
| Agent reasoning / tools | QMA Compute Router | local/docker/remote_host (never QMN) |
| Governed backtest / optimize / WF | QMA places **one** `qmb` job; QMB governor owns intra-job parallelism | QMB orchestrator |
| Ungoverned research (ordinary Python / optional notebook) | Operator workstation or QMB research host | QMB library (no ledger) |
| Paper (pre-promotion) | Outside the node (DEC-0261) | not QMA; not a QMN per-bot lane |
| Live / node paper (soak, protective demotion) | QMN | `qmn.service` |

QC's "don't share a live node across algorithms" maps to QMN's existing one-loop-per-`(VenueId, account)` — already law, not a new mechanism.

---

## 7. Research-to-run artifact handoff

### Donor (official)

Object Store is an organization-wide key-value cache used to (1) move data between research and backtesting and (2) train ML in research then load in live. Paid-only; live access is slower; keep objects < 50 MB ([Object Store](https://www.quantconnect.com/docs/v2/cloud-platform/object-store)). Reserved `.agent/` holds skills, memories, templates. Lean CLI has local and `lean cloud object-store *` counterparts.

### QMX already

- `COMP-OBJECT-STORAGE` is the **off-machine encrypted backup bucket** (CT-14), not a research cache (`docs/components/object-storage.md`). Do not overload it.
- QMF rooms / CT-11 evidence / CT-13 journals are the governed stores.
- QMB research returns values; governed evidence requires the orchestrator.
- QML graduation: ungoverned experiment → CT-33/CT-34 with a lineage edge back to the originating research artifact (`docs/components/qml.md` QL-8).

### Mapping

**Status: extend. Home: QMF.**  
Transfer: a named place to persist research outputs (serialized models, intermediate tables) that a later QMB run can read through declared footprint/data refs.  
Do not transfer: QC Object Store product, `.agent` folder layout, or live-trading in-process mutation of that store.

Extend QMF rooms (or a declared research-artifact role inside existing rooms) with content-addressed blobs cited by ExperimentSpec `data_ref` / Bot logic. QMA skills/memories stay on QMA ports (MemoryProvider, contribution files), not on the backup bucket.

---

## 8. Mixed author/execute workflow

### Donor (official)

Lean CLI documents three mixes: cloud-focused (local edit, cloud execute), locally-focused (local data + Docker), mixed (local debug, cloud backtest) ([Workflows](https://www.lean.io/docs/v2/lean-cli/projects/workflows)). `lean cloud pull/push` is the file sync; `--push` on `lean cloud backtest` / `lean cloud optimize` / `lean cloud live deploy` uploads then runs.

### QMX already

`qmb` CLI is the single command-line surface (DEC-0159, DEC-0185). QMA remote deploy is first-class on the wire (workers dial out). QMN has no operator CLI.

### Mapping

**Status: connect. Home: QMB.**  
Transfer: author on the workstation, execute on declared compute, same library.  
Do not transfer: QC cloud as a runtime, pull/push of a Project tree as identity, or `lean cloud live`.

Connect QMB CLI (governed runs) to QMA ExecutionEnvironment (where the process is placed) without QMA importing QMB. File identity stays QML/QMF fingerprints, not cloud-id.

---

## Do not copy

- LEAN engine, `QCAlgorithm`, `QuantBook`, ToolBox programs, `quantconnect/lean` and `quantconnect/research` Docker images.
- Algorithm Lab / web IDE / Ask Mia / Research Pipeline kanban chrome.
- QC Project / `config.json` / `cloud-id` as a QMX identity.
- `GetParameter` / stringly project parameters as a QMX contract.
- Cloud optimizer (grid search, 3-parameter cap) as QMX optimizer law.
- Research Pipeline stages Ideas → Research → Backtest → Paper → Live as required lifecycle.
- Paper Testing Agent, Live Monitoring Agent, `create_live_algorithm`, `stop_live_algorithm`, `liquidate_live_algorithm`.
- QC Object Store product and `.agent/` folder as storage architecture (backup bucket is a different component).
- Private Cloud master/slave LEAN cluster.
- Agent Teams / Conductor / Mia names and vendor prompt packs.
- Hostname sniffing to detect "local vs cloud" (`platform.node()` example in CLI sync docs).
- Synthetic `lean data generate` as governed evidence (QMB already refuses store-tainted simulated data for edge claims).

---

## 1. What already exists

- QMF contracts/toolbox, rooms, journals, fingerprints.
- QML: CT-33 declaration + plain-Python logic; parameter space; graduation lineage.
- QMB: run loop, orchestrator, TPE optimize, walk-forward, sweeps, data commands, CT-32; B-9 research surface; no engine.
- QMA: daemon, missions/tasks, tools, ExperimentSpec (docs defined-unwired; integration source present), CT-46 placement ports, money-path deny-list.
- QMN: paper|live node; promotion then activation; no operator CLI.
- UI: later consumer of identity and evidence; not an identity owner.

## 2. Missing wiring vs missing function

| Gap | Kind |
|---|---|
| CT-47 ExperimentSpec → single `qmb` job per environment | **Wiring.** Source exists on integration (`experiments.py`, `ExperimentSpecService`); docs still `defined-unwired`; end-to-end placement unverified. |
| CT-46 Compute Router actually placing jobs | **Wiring** (same docs/source split). Function specified; not a new compute product. |
| Present Task Graph / Experiments as one operator workspace | **Wiring + UI.** Identities exist (QML/QMA/QMB). |
| Optional Jupyter host over B-9 | **Function only if V1 wants notebooks.** Not required for research; ordinary Python already legal. |
| Research-artifact blob role in QMF rooms | **Small extend** of existing rooms, not a new store. |
| QC-style paper agent / live MCP | **Not missing.** Banned. |

## 3. Recommended architectural ownership

- **QML** owns strategy continuity and the parameter schema.
- **QMB** owns the research library surface, governed runs, optimize/WF/sweeps, and the CLI door.
- **QMA** owns agents, missions/tasks (the only "pipeline"), tool grants, and compute *placement policy*.
- **QMF** owns rooms/journals and any research-artifact persistence.
- **QMN** owns live (and node paper). Unreachable from QMA.
- **UI** presents workspace, board, and optional notebooks; owns no identity and no engine.

No new service is required to absorb this donor.

## 4. Open questions

Need an AD:

- Is a Jupyter UX in V1, or is ordinary Python + Experiment Ledger enough? (mechanism extend vs defer)
- How does pre-promotion paper (DEC-0261, outside the node) show on a QMA board without becoming a QC Paper stage or a QMA execution tool?
- Who writes the ExperimentSpec `environment_ref` when the operator runs `qmb` directly (no agent)? Default local orchestrator vs explicit QMA placement.

Can stay Deferred:

- GPU research-node SKUs (CT-46 already has optional `gpu`; GAP-0075 vendors).
- Simultaneous notebook editing (QC itself does not support it).
- Agent-authored live notifications (QC MCP `send_*`); QMN already owns operator notify on the node.
- Custom project templates as Object Store JSON (QMA already has `worker_template` / graph templates).
