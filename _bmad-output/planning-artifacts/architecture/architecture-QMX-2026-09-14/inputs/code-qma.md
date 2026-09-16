# QMA (QuantMind Agents) — integration source investigation

**Sitting:** architecture only (QMX 2026-09-14).  
**Checkout:** `main` (planning). **Product tip inspected:** `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` (verified `git rev-parse`).  
**Method:** `git ls-tree` / `git show integration:<path>` plus docs on this checkout. No implementation, commit, or branch switch.  
**Lead:** `workroom/research/2026-09-14-qma-understanding.md` — verified; corrections called out below.

Evidence levels: `user-intent` | `documented-design` | `source-inspected` | `behavior-demonstrated`  
Class: `reuse` | `connect` | `extend` | `new` | `undecided`

---

## Classification table

| Capability | Class | Evidence | Integration path(s) | Note |
|---|---|---|---|---|
| Ontology (Desk→Role→Quant→Agent→Subagent; Mission/Task) | **reuse** | source-inspected | `qmx-agents/packages/qma-core/src/qma/core/ontology/` | Definitions-only; matches COMP-QMA-CORE / AD-7 |
| Mission Compiler + Task Graph | **reuse** | source-inspected | `qma-daemon/.../taskgraph/compiler.py`, `dispatcher.py`, `execution.py`, `state.py`, `records.py` | Deterministic compiler; no LLM compile |
| Control primitives (Graph Template / Loop / Skill) | **reuse** | source-inspected | `qma-core/.../control/primitives.py` | Skill ≠ Loop; GAP-0084/0086 deferred |
| Plugins + desk packs | **reuse** | source-inspected | `qma-core/.../plugins/`, `qma-daemon/.../plugins/`, `qmx-agents/plugins/*` | Five seed packs with `activate()` |
| Tool Registry + capability ladder | **reuse** | source-inspected + behavior-demonstrated (unit tests) | `qma-core/.../ports/tools.py`, `barriers/capability.py`, `qma-daemon/.../tools/registry.py`, `tests/test_money_path_denial.py` | Deny before `check_fn` |
| MemoryProvider port + admission | **reuse** | source-inspected | `ports/memory.py`, `daemon/memory/admission.py`, `plugins/research-corpus` in-process provider | External backend GAP-0072 still deferred |
| KnowledgeSource + plain-file adapter | **reuse** | source-inspected | `ports/knowledge.py`, `daemon/knowledge/plain_file.py`, `service.py` | Literal search; GAP-0073 indexing deferred |
| Compute / ExecutionEnvironment / JobHandle | **reuse** | source-inspected | `ports/execution.py`, `ports/compute.py`, `daemon/envs/*` | Desktop GAP-0070 |
| Wire envelope / initialize / principals / host_request | **reuse** | source-inspected | `qma-wire/src/qma/wire/*`, `schemas/*.schema.json` | Protocol types + schemas; **no live WS server found** |
| Laptop-off: loopback listener posture, dial-out, durable outbox | **reuse** | source-inspected | `wire/listener.py`, `wire/reachability.py`, `wire/outbox.py`, `ports/deployment.py` | Library + validation; not a running daemon process |
| Routines + continuation | **reuse** | source-inspected | `ontology/routine.py`, `ontology/continuation.py`, `daemon/scheduler/routines.py`, `continuation.py` | Operator-authored; machine principal on fire |
| ExperimentSpec + Experiment Ledger + lineage | **reuse** | source-inspected | `ports/experiments.py`, `daemon/experiments/service.py`, `daemon/ledgers/experiment.py` | CT-47 docs still say `defined-unwired` — **stale** vs source |
| QMB door / Backtesting Service | **reuse** / **connect** | source-inspected + unit tests | `ports/qmb.py`, `daemon/backtest/service.py`, `plugins/analysis-backtest/` | Connect = runtime CLI/MCP to QMB; **no `import qmb`**; transport is recording stub by default |
| Money-path barrier (no execution tool, paper included) | **reuse** | source-inspected + behavior-demonstrated | `barriers/money_path.py`, `barriers/reachability.py`, tool registry, QMB `world=replay` | Standing law intact |
| `qma-ui-contract` | **reuse** (as deferred stub) | source-inspected | `qmx-agents/packages/qma-ui-contract/STUB.md` only | Not a workspace member; GAP-0081 |
| Long-running asyncio daemon process (WS bind, compose services) | **extend** / **undecided** | source-inspected (absence) | No `asyncio.run` / websockets server under `qma-daemon`/`qma-wire` src | Function pieces exist; process composition missing |
| Non-source-reader extensibility (skills/templates/packs/UI vars) | **reuse** + **extend** | source-inspected + documented-design | Plugin packs + AD-26 variables + wire human-gate commands | UI editing deferred with stub; wire binds now |
| Strategy-mechanism nouns on ExperimentSpec | **undecided** / deferred | documented-design + source-inspected | `GAP_0085_STRATEGY_MECHANISMS` refused in `ports/experiments.py` | Owned by QML/registry; QMA must not mint |

---

## 1. Ontology, missions/task graph, plugins, tools, memory/knowledge, compute, wire

### Ontology

`qma-core` is definitions-only (`git show integration:qmx-agents/packages/qma-core/src/qma/core/ontology/__init__.py`). Chain and work vocabulary match docs: Desk → Role → Quant → Agent → Subagent; Goal → Mission → Task; Session as run container; Worker not an ontology object. Five desk slugs (`research`, `trading`, `dev`, `analysis`, `pm`) and `ActorId` grammar `quant:<desk_slug>/<quant_slug>` live under `ontology/desks.py`, `actor_id.py`, `records.py`, `creation.py`.

**Correction to research lead:** lead is accurate here.

### Missions / Task Graph

Daemon owns deterministic `MissionCompiler` (`taskgraph/compiler.py`): Goal + optional Graph Template → one `MissionRecord` + initial `TaskGraph`. LLM is not the compiler. Dispatcher grants `dispatch_lease` and asks Compute Router for environment leases. Node kinds and task-emitting set (`task`/`agent`/`loop`) are in `control/primitives.py` and vocabulary enums. Graph engine choice remains GAP-0086 (`DEFERRED_GRAPH_EXCLUSIONS`).

### Plugins

Contribution surface in `qma-core/plugins/` (`PluginManifest`, `PluginContext`, hooks). Cardinality law in `ports/cardinality.py`: seven ports; eight multi points (`tool`, `tool_adapter`, `hook`, `skill`, `graph_template`, `model_deployment`, `toolset`, `worker_template`); retired `ui_view`/`command`/`mission_template`. Daemon loader + reversible exit stack under `qma-daemon/plugins/`. Five first-party packs under `qmx-agents/plugins/` with `manifest.json` + `daemon/plugin.py` (`analysis-backtest`, `trading-readonly`, `research-corpus`, `dev-factory`, `pm-coordination`). Packs import `qma-core` only (never `qma-daemon` / `qmb` / `qmf-venue`).

### Tools

Unified `ToolRegistry` (`daemon/tools/registry.py`) spans native/CLI/plugin/MCP/browser/computer-use/backtest. Money-path deny-list evaluated **before** `check_fn`. Subagent leaf blocked from delegation/memory-write tags (`LEAF_BLOCKED_TOOL_TAGS`). Skills do not grant capability (`skill_grants_tool_or_capability() -> False`).

### Memory / knowledge

- Memory: port in `ports/memory.py`; daemon `MemoryAdmissionGate` / registry; `admission_confidence` gate-owned; no `promote`. `research-corpus` ships an **in-process** `ResearchDeskMemory` (not GAP-0072 external). Unbound desk → `NoMemoryProvider`, candidates stage via AD-22.
- Knowledge: port in `ports/knowledge.py`; `PlainFileLibrarySource` adapter; literal/locator search; cite copies into artifact store (service layer). Hybrid indexing GAP-0073 refused in port helpers.

### Compute / environments

`ExecutionEnvironment` kinds + required `network` ∈ {`none`,`allowlist`}; Compute Router placement; `JobHandle` states including mandatory `unknown`. Deployment envelope: `DEFAULT_DAEMON_HOST = "operator_workstation"`, `DEFAULT_WORKER_ISOLATION = "docker_on_host"` (`ports/deployment.py`). Reachability barrier refuses trading-node hosts / `qmf-venue` images (`barriers/reachability.py`, `envs/boundary.py`).

### Wire continuation

`qma-wire` carries envelope, families, initialize, attach/replay, idempotency, principals, `host_request`, money-path field diff schemas, **listener bind validation** (`DEFAULT_BIND_HOST = "127.0.0.1"`), dial-out reachability validation, and **durable remote outbox** (`RemoteOutbox` JSONL + fsync, depth/spool bounds, `unknown_tail` on lost env). JSON-RPC WebSocket / HTTP GET are declared transport kinds in `families.py` / `initialize.py`.

**Gap (source-inspected):** no websockets/aiohttp/uvicorn server module and no composed asyncio process entry under `qma-daemon`/`qma-wire` `src/`. Examples expose library `main()` demos only. Wire is implemented as **contract library + posture validators**, not a live listener process yet.

---

## 2. Experiment ledger / experiments service / backtest service / QMB door

### ExperimentSpec (core)

`qma/core/ports/experiments.py`: content-addressed `ExperimentSpec` via `fp1`; `code_ref` only as `git:commit:<40-hex>` when code changes; parameter changes via `resolved_config_ref`; git-branch-per-parameter refused (DEC-0376); GAP-0085 mechanism nouns refused.

### ExperimentSpecService (daemon)

`qma/daemon/experiments/service.py`: register (identical fp1 collapses), `create_successor` with CT-07 `branches-from` edge via `qmf-registry` `EdgeLog`, `append_evidence` through Experiment Ledger under registering Task’s `dispatch_lease`, `mutate_in_place` always refused.

### Experiment Ledger

`qma/daemon/ledgers/experiment.py`: one notebook per Experiment (`spec_fp1`); append-only; lease-gated; quarantine/announcement hooks.

### QMB door + Backtesting Service

- Definitions: `qma/core/ports/qmb.py` — route `agent → qma_backtest_tool → backtesting_service → qmb_door → qmb`; tool id `analysis-backtest:qmb`; `world=replay` only; venue/account/paper fields refused; one job per environment occupancy; no package-import edge; QMB keeps parallelism/run ledger/artifact contract.
- Runtime: `qma/daemon/backtest/service.py` — installs one Tool Registry BACKTEST entry; `RecordingQmbDoorTransport` records CLI/MCP invocations **without importing `qmb`**; refuses Compute Router for the QMB compute leg; refuses second job / QMB-owned concerns.
- Plugin: `plugins/analysis-backtest/` registers tool `qmb`, skill `replay`, graph template `notebook`, toolset `replay-tools`.

### CT-47 reconciliation (required)

| Claim | Status |
|---|---|
| Docs/CT-47 `wiring_status: defined-unwired` / “no code exists” | **Stale documentation** relative to integration tip |
| Integration source for ExperimentSpec, ledger, lineage, QMB door, analysis-backtest | **Present** (`source-inspected`) |
| End-to-end live spawn of real `qmb` CLI against real evidence | **Not demonstrated** — default transport records invocations; unit tests exercise door law |
| Same staleness pattern | CT-40..CT-51 on integration still stamp `defined-unwired` while matching packages exist under `qmx-agents/packages/` |

**Architectural reading:** treat CT-47 as **defined and library-wired in source**, with **process/product wiring** (live door transport, journal-persisted experiments in a long-running daemon, UI) still incomplete. Do not silently pick “no code” from the contract stamp.

---

## 3. Implemented in source vs defined-unwired in contracts

| Layer | Contracts (docs on integration) | Source @ 1b451a8 |
|---|---|---|
| CT-40 wire | `defined-unwired` | Types, schemas, outbox, listener validation, principals — **no live server** |
| CT-41 hooks | `defined-unwired` | Core + daemon hook registry, timeouts, verifiers, agent-authored bounds — **library** |
| CT-42 plugins | `defined-unwired` | Loader, packs, five desk plugins |
| CT-43 memory | `defined-unwired` | Port + admission + research in-process provider |
| CT-44 knowledge | `defined-unwired` | Port + plain-file adapter + service |
| CT-45 model/broker | `defined-unwired` | Proxy/router/broker/opencodex modules present |
| CT-46 envs/jobs | `defined-unwired` | Registry, router, jobs, boundary |
| CT-47 experiment/QMB | `defined-unwired` | Spec service, ledger, backtest service, plugin |
| CT-48 mailbox | `defined-unwired` | `daemon/bus/mailbox.py` + wake |
| CT-49 routine/continuation | `defined-unwired` | Core defs + scheduler modules |
| CT-50 refinement | `defined-unwired` | `daemon/staging/*` |
| CT-51 task ledger | `defined-unwired` | `daemon/ledgers/task.py` (+ quant/experiment) |

**Verdict:** factory shipped a **large library + unit/example surface** that realizes the contracts’ types and refusal laws. Contracts’ `defined-unwired` / “no code exists” provenance notes are **out of date**. What remains “unwired” in the product sense is primarily: (a) one composed long-running daemon process over the wire, (b) real remote workers dialing a live listener, (c) non-recording QMB transport, (d) UI beyond stub, (e) deferred backends (memory vendor, desktop env, graph engine, knowledge index).

---

## 4. Money-path barrier

Standing law holds in source:

1. **Act-level deny-list** (`barriers/money_path.py`): orders, positions, protection, sizing, bindings, book/BMS mode/params, kill switch/control, zone transition, promotion — including paper_/live_/demo_ prefixes stripped then matched. Not liftable by role/mission/hook/toolset/adapter/`check_fn`.
2. **Tool Registry** refuses matching tools at registration with `ProhibitedMoneyPathTool` before `check_fn` (`daemon/tools/registry.py`; `tests/test_money_path_denial.py` parametrizes denied acts and every `ToolKind` including paper-only).
3. **Reachability** refuses venue/broker/trading-node hosts and `qmf-venue` images; paper is account role not sandbox (`PAPER_IS_SANDBOX = False`).
4. **QMB door** forces `world=replay` and refuses venue/account request fields.
5. **Promotion:** `QMA_MINTED_PROMOTION_COMMAND = None`; human promotion outside QMA; daemon may only record artifact refs.

Class: **reuse** (barrier already built). No architecture change needed to keep the barrier; any new experiment UI/workflow must exit through candidate + human promotion, never an execution tool.

---

## 5. Laptop-off continuation

| Mechanism | Source evidence | Product readiness |
|---|---|---|
| Daemon default host | `DEFAULT_DAEMON_HOST = "operator_workstation"`; Docker workers on host | Documented + encoded |
| Listener default | `DEFAULT_BIND_HOST = "127.0.0.1"`; non-loopback needs TLS + operator-recorded config | Validation only |
| Remotes dial out | `wire/reachability.py`; daemon never dials in | Validation only |
| Durable outbox | `wire/outbox.py` fsynced JSONL; blocks dispatch on bound; telemetry before evidence; `unknown_tail` | Library ready |
| Routines | Operator `routine.write`; scheduler fires as `machine`; missed fires recorded not auto-replayed | Library + tests/examples |
| Continuation | Verifier-gated completion; `agent_stop`/`block_stop`; registry caps; escalate to Quant mailbox; refuse invented tasks | Library |
| Closing client harmless | Documented wire attach/detach semantics | Needs live event stream to demonstrate |

**Architectural implication for strategy experimentation:** unattended overnight work is **designed and partially coded** as daemon-owned scheduler + continuation + dial-out outbox. The missing piece is the **always-on process** that binds the listener and keeps the journal writer alive when the laptop UI is closed — not a new ontology.

---

## 6. `qma-ui-contract`

**Stub only.** Tree is solely `qmx-agents/packages/qma-ui-contract/STUB.md` (GAP-0081 / DEC-0333). Explicitly: no `pyproject.toml`, no `src/`, excluded from uv workspace members and pyright include. Wire + AD-26 variables bind now; presentation/SDK later. Class: **reuse** the deferral; do not invent UI contribution points in this sitting.

---

## 7. Routines, skills, graph templates as reusable procedures

| Artifact | Owner | Authoring | Runtime |
|---|---|---|---|
| **Graph Template** | Plugin multi contribution | Authored, versioned, stateless topology | Compiler expands into Task Graph |
| **Loop** | Node kind inside templates | Runtime-owned stopping/budget/escalation | Emits one Task per iteration |
| **Skill** | Plugin multi contribution | Reusable procedure/knowledge; may invoke a Loop | Knowledge only — not a capability grant |
| **Routine** | Quant-owned definition-store record | Operator-principal only; UI-editable; **no** AD-22 `routine` edit kind | Scheduler → Mission Compiler with named `graph_template` |

Seed examples: `analysis-backtest:notebook`, `analysis-backtest:replay` skill; `research-corpus:survey`; `pm-coordination:standup`; `trading-readonly:tape-read`; `dev-factory:factory` + worker template. Daemon ships **no** built-in graph templates in v1 (plugin-contributed only).

---

## 8. Extensibility a non-source-reading user could use

Already shaped for operator-facing extension **without reading daemon internals**:

1. **Desk plugin packs** — drop a `{desk}-*` folder with `manifest.json` + `daemon/plugin.py` `activate(ctx)` registering tools/skills/templates/hooks/providers through `PluginContext` (types from `qma-core` only).
2. **Skills + graph templates + toolsets** — named reusable procedures referenced by Routines and Missions.
3. **Ordinary Python** — still legal outside QMA (QML / plain experiments); graduation into governed evidence is separate (L33). QMA does not replace Python authoring.
4. **Operator wire commands** (when process exists) — human-gate list includes plugin install, desk/quant create, routine write, env declaration, variable.set, human_gate answers.
5. **AD-26 registry variables** — configurable ≡ UI-editable once UI exists; values are evidence not constants.

**Not available yet to a non-source reader:** a UI to edit those surfaces (`qma-ui-contract` stub); a published plugin store (first-party only); Mission Template registry (GAP-0084); typed strategy-mechanism palette on ExperimentSpec (GAP-0085 — QML/registry).

---

## Research lead verification

`workroom/research/2026-09-14-qma-understanding.md` is largely correct on ownership splits (core/daemon/wire; QMB door; money path; dial-out). **Corrections / sharpenings:**

1. CT docs saying `defined-unwired` / “no code” are **stale**; integration has substantial source — reconcile as **library-implemented, process-uncomposed**.
2. Lead understates that the daemon today is a **service library + tests/examples**, not an observed long-running asyncio listener.
3. Memory: lead correctly notes GAP-0072 deferred; note also that `research-corpus` already contributes a **first-party in-process** MemoryProvider (not the deferred external backend).
4. QMB door transport in daemon defaults to **recording stub**, preserving “no import qmb” — connect to real CLI/MCP is the remaining product edge.

---

## Synthesis required by brief

### (1) What already exists

Three packages under `qmx-agents/` (`qma-core`, `qma-wire`, `qma-daemon`) plus five desk plugins; ontology; ports; barriers; mission/taskgraph; hooks; ledgers (task/quant/experiment); mailbox; scheduler (routines/continuation); model proxy modules; tool registry with money-path denial; envs/compute; staging; telemetry; persistence/journal substrate; ExperimentSpec + QMB door library; wire contract library with outbox/dial-out/loopback posture; comprehensive unit tests and usage examples.

### (2) Missing wiring vs missing function

| Missing | Kind |
|---|---|
| Composed asyncio daemon process binding WS/HTTP and owning one writer loop | **Wiring / composition** (functions exist as modules) |
| Live QMB CLI/MCP transport (beyond `RecordingQmbDoorTransport`) | **Wiring** to existing QMB product |
| Contract YAML `wiring_status` refresh | **Docs drift** (not a code gap) |
| External memory backend, knowledge index, graph engine, desktop env, UI SDK | **Deferred function** (GAP-0070/72/73/81/86) |
| Second host / external A2A relay | **Deferred** (GAP-0079) |

### (3) Recommended architectural ownership (for strategy-experimentation sitting)

| Concern | Owner |
|---|---|
| Experiment identity, lineage, scientist notebook | **QMA** ExperimentSpec + Experiment Ledger (`analysis` desk) |
| Backtest execution, intra-node parallelism, run artifacts | **QMB** via single door; QMA places one job/env |
| Bot/strategy authoring & mechanism nouns | **QML** + `qmf-registry` (GAP-0085); QMA holds handles/candidates |
| Money-path / promotion | **Human outside QMA**; node/Book/BMS untouched |
| Unattended overnight continuation | **qma-daemon** scheduler + wire dial-out (compose process) |
| Operator UX for experiments | **Future UI** over existing `qma-wire`; not `qma-ui-contract` invention now |

Class recommendation for this sitting’s strategy-experimentation architecture: **reuse** QMA experiment/QMB-door/ledger/mission machinery; **connect** live QMB door + composed daemon; **extend** only where operator-facing experiment workflows need new wire nouns or analysis graph templates; **new** only if a capability is absent from ports/plugins (none identified for core experiment loop beyond deferred GAPs).

### (4) Open questions — AD vs Deferred

| Question | Disposition |
|---|---|
| Refresh CT-40..51 `wiring_status` / consumers to match integration source | **AD / docs reconciliation** (cheap; prevents false “no code” architecture) |
| Compose long-running daemon entry (listener + journal writer + pack roster) | **AD build-order** (implementation via factory; architecture already specifies it) |
| Real QMB door transport adapter (CLI vs MCP first) | **Deferred product choice** under existing CT-47 door kinds — not a new paradigm |
| GAP-0085 strategy-mechanism on specs | **Stay Deferred** — QML/registry owned |
| GAP-0086 graph engine | **Stay Deferred** |
| GAP-0081 UI contract beyond stub | **Stay Deferred** |
| GAP-0071 lead Quant catch-all mailbox | **Stay Deferred** (interim: `dead_letter`) |
| Whether experiment UI needs new wire families beyond seed 26 nouns | **Undecided** — inspect seed commands/queries first; prefer reuse `artifact.created` / ledger inspect / mission start |

---

## Absolute paths cited (integration)

- `qmx-agents/packages/qma-core/src/qma/core/ontology/`
- `qmx-agents/packages/qma-core/src/qma/core/ports/{qmb,experiments,tools,memory,knowledge,cardinality,deployment}.py`
- `qmx-agents/packages/qma-core/src/qma/core/barriers/money_path.py`
- `qmx-agents/packages/qma-core/src/qma/core/control/primitives.py`
- `qmx-agents/packages/qma-daemon/src/qma/daemon/{backtest,experiments,ledgers,taskgraph,tools,scheduler,envs,plugins,memory,knowledge,bus}/`
- `qmx-agents/packages/qma-wire/src/qma/wire/{outbox,listener,reachability,envelope,host_request,initialize}.py`
- `qmx-agents/packages/qma-ui-contract/STUB.md`
- `qmx-agents/plugins/{analysis-backtest,trading-readonly,research-corpus,dev-factory,pm-coordination}/`
- Docs (checkout): `docs/components/qma-{core,daemon,wire}.md`, `docs/decisions/ADR-0020-qma-agentic-system.md`, `docs/contracts/ct-47-qma-experiment-spec.yaml`, `_bmad-output/.../architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md`
