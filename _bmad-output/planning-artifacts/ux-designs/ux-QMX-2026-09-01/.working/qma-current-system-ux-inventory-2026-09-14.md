# QMX Agentic System UX Inventory — Current Platform-Wide Grounding

Status: working inventory for UI grounding, not a design proposal.

Source basis: current filesystem on 2026-09-14, while QMA/workbench docs are actively modified. Parent saved the source hashes and timestamps in `_bmad-output/planning-artifacts/ux-designs/ux-QMX-2026-09-01/.working/qmx-agentic-source-snapshot-2026-09-14.json`; primary QMA files were modified around 2026-09-14 10:43-10:44 UTC, ADR-0022 at 10:42 UTC, and the latest QMX expansion spine at 08:13 UTC. The latest expansion spine and ADR-0022 are untracked/new relative to HEAD, so this inventory cites filesystem state, not HEAD.

## Scope

This is a platform-wide agentic-system inventory, not a QMA-only note. QMA is the organizer, runtime, wire, identity, memory, procedure, and coordination layer. QMB, QML, QMF Registry/Data/Risk, and QMN are the platform systems it coordinates, queries, references, or is barred from controlling.

The UI question should therefore be framed as "how does the user see and steer the platform's agentic work?" rather than "where does one chat thread live?". The docs now contain enough object/state vocabulary to support departments, work states, and cross-system evidence, but they explicitly defer screen composition, departments/chrome, and the UI SDK to a later UI track (`GAP-0081`, screen composition/chrome deferred) [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:269](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L269), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:278](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L278).

## Authority Level

Normative / ratified design:

- QMA's ontology, ports, wire, daemon, contracts CT-40..CT-51, and refusal laws are ratified design. `qma-core` is definitions-only and runs/writes nothing; `qma-daemon` is the only process that runs anything and is the sole writer; `qma-wire` is the cross-boundary package [docs/components/qma-core.md:17](../../../../../docs/components/qma-core.md#L17), [docs/components/qma-core.md:19](../../../../../docs/components/qma-core.md#L19).
- The platform workbench spine from 2026-09-14 is adopted by ADR-0022 as DEC-0269..DEC-0287, reusing existing components rather than minting a new experiment service [docs/decisions/ADR-0022-workbench-expansion.md:35](../../../../../docs/decisions/ADR-0022-workbench-expansion.md#L35), [docs/decisions/ADR-0022-workbench-expansion.md:56](../../../../../docs/decisions/ADR-0022-workbench-expansion.md#L56).
- The workbench is not a sixth application. New capabilities must name an existing component owner or explicit connect/extend of one; a permanent experiment daemon beside `qma-daemon` is a spine amendment [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:59](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L59), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:63](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L63).

Planned / deferred:

- UI presentation architecture, Rust extension technology, UI SDK surfaces, UI contribution points, UI plugin packaging, and `qma-ui-contract` beyond a stub are deferred under `GAP-0081` [docs/gap-report.md:237](../../../../../docs/gap-report.md#L237), [docs/components/qma-wire.md:110](../../../../../docs/components/qma-wire.md#L110).
- Concrete always-on host for laptop-off continuation is `GAP-0062`; the property is decided, the machine is not [docs/gap-report.md:217](../../../../../docs/gap-report.md#L217), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:287](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L287).
- Memory backend and knowledge indexing are ports now, deferred backend/index choices later (`GAP-0072`, `GAP-0073`) [docs/gap-report.md:228](../../../../../docs/gap-report.md#L228), [docs/gap-report.md:229](../../../../../docs/gap-report.md#L229).
- Graph engine, external agent-to-agent transport, desktop ExecutionEnvironment provisioning, and RLM performance envelope remain deferred [docs/gap-report.md:226](../../../../../docs/gap-report.md#L226), [docs/gap-report.md:232](../../../../../docs/gap-report.md#L232), [docs/gap-report.md:235](../../../../../docs/gap-report.md#L235), [docs/gap-report.md:242](../../../../../docs/gap-report.md#L242).

Implementation evidence reported by the documentation (not independently exercised in this study):

- Current docs use `wiring_status: source-inspected` for CT-40..CT-51 and related source on `integration@1b451a8`, but class/test existence is explicitly not end-to-end proof [docs/contracts/ct-40-qma-wire-envelope.yaml:9](../../../../../docs/contracts/ct-40-qma-wire-envelope.yaml#L9), [docs/decisions/ADR-0022-workbench-expansion.md:23](../../../../../docs/decisions/ADR-0022-workbench-expansion.md#L23).
- The QMA→QMB default transport is still `RecordingQmbDoorTransport`, which records and does not spawn `qmb`; a real CLI transport and composed asyncio daemon process are connect work [docs/components/qma-daemon.md:221](../../../../../docs/components/qma-daemon.md#L221), [docs/contracts/ct-47-qma-experiment-spec.yaml:42](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L42).

## Organization And Hierarchy

The core hierarchy is Desk -> Role -> Quant -> Agent -> Subagent, with Session, Worker, Mission, Task, and Task Graph around it [docs/components/qma-core.md:23](../../../../../docs/components/qma-core.md#L23), [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53). This is the strongest grounding for a department-aware UI.

Key distinctions:

- Desk is the organizational/workspace unit. There are exactly five desk slugs: `research`, `trading`, `dev`, `analysis`, and `pm` [docs/components/qma-core.md:55](../../../../../docs/components/qma-core.md#L55).
- Role is a declarative, stateless behavioral contract close to a system prompt [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53).
- Quant is the persistent named organizational actor instantiated from a Role. It carries memory scope, missions, routines, preferences, WakePolicy, mailbox, and sometimes a Quant Ledger [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53).
- Agent is a running reasoning/execution instance. Subagent is spawned by an Agent, cannot exceed parent capabilities, and is a leaf: it cannot delegate further [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53).
- Session is the run container; Worker is an addressable execution slot, deliberately not an ontology object [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53).
- Profile is presentation only: client-side grouping of desk slugs, never daemon state or a routing/permission key [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53).

Department mapping:

- The docs currently map departments to the five Desks. "Department" is a UI term, not a backend object unless the UI aliases Desk. A desk consolidation is display-only and cannot rename/retire a desk slug, ActorId, plugin prefix, memory scope, or ledger index key [docs/components/qma-core.md:55](../../../../../docs/components/qma-core.md#L55).
- Exactly one lead Quant per Desk and the lead mailbox catch-all are not fully ruled: until `GAP-0071` is answered, a second lead flag is a hard startup error and undeliverable mail resolves to `dead_letter` rather than lead fallback [docs/components/qma-core.md:55](../../../../../docs/components/qma-core.md#L55), [docs/gap-report.md:227](../../../../../docs/gap-report.md#L227).

UI hypothesis: left navigation can safely expose departments/desks and persistent Quants as stable user addressees. It should avoid making Role names look like destinations and avoid showing Profile as if it were permission-bearing backend state.

## User Addressee Vs Executing Agents

The user addresses a Quant, Desk, Mission, or Task scope more naturally than a transient Agent. The wire `scope_path` order is desk, quant, mission, task, session, agent, subagent; Session sits between Task and Agent because a Task outlives the session that runs it [docs/contracts/ct-40-qma-wire-envelope.yaml:31](../../../../../docs/contracts/ct-40-qma-wire-envelope.yaml#L31).

This has UI consequences:

- A "chat with the department" affordance should probably target a Desk lead Quant or a Mission scope, not a specific Agent process. That is a UI hypothesis; the backend only names `ActorId` and `scope_path`.
- A running Agent can disappear, resume, be reassigned, or be replaced while the Task and its ledger remain the durable work record. Task state lives in the daemon Task Graph; a Task is transcript-independent and carries intent, inputs, refs, acceptance criteria, and Task Ledger [docs/components/qma-daemon.md:110](../../../../../docs/components/qma-daemon.md#L110).
- Closing a client must not stop an agent. Attach/detach are client state; replay is read-only over the durable stream [docs/contracts/ct-40-qma-wire-envelope.yaml:28](../../../../../docs/contracts/ct-40-qma-wire-envelope.yaml#L28), [docs/components/qma-wire.md:67](../../../../../docs/components/qma-wire.md#L67).

## Work Objects And Lifecycles

Mission and Task:

- A Mission is an executable organizational contract owned by exactly one Quant. There is no global mission [docs/components/qma-daemon.md:110](../../../../../docs/components/qma-daemon.md#L110).
- A deterministic Mission Compiler turns a Goal plus optional Graph Template into a Mission and initial Task Graph. Where decomposition needs reasoning, it emits a decomposition Task whose Agent acts as Mission Director; Mission Director is not a new ontology object [docs/components/qma-daemon.md:112](../../../../../docs/components/qma-daemon.md#L112).
- Task/Mission states are `pending`, `ready`, `running`, `blocked`, `unknown`, `done`, `failed`, and `cancelled`; terminal states are `done`, `failed`, `cancelled` [docs/components/qma-daemon.md:114](../../../../../docs/components/qma-daemon.md#L114).
- `unknown` is not failure. A Task whose handle is `unknown` may enter only `unknown`, holds both `dispatch_lease` and `environment_lease`, and blocks completion until explicit recorded resolution; a Mission containing an unknown Task is itself `unknown`, never `failed` [docs/components/qma-daemon.md:114](../../../../../docs/components/qma-daemon.md#L114).

Task Graph / procedure:

- Graph Template is authored, versioned topology with no runtime state. Loop is an executable cycle. Skill is reusable procedure/knowledge and is not the same as Loop [docs/components/qma-daemon.md:135](../../../../../docs/components/qma-daemon.md#L135).
- Node kinds include `task`, `conditional`, `parallel_branch`, `join`, `approval_gate`, `human_gate`, `deterministic_script`, `loop`, `agent`, and `artifact_dependency`; only `task`, `agent`, and `loop` emit Tasks [docs/components/qma-daemon.md:135](../../../../../docs/components/qma-daemon.md#L135).
- Workbench procedures live in QMA as Graph Templates, Skills, and operator Routines. QMB does not grow a task graph [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:107](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L107), [docs/components/qma-daemon.md:229](../../../../../docs/components/qma-daemon.md#L229).

Execution jobs:

- ExecutionEnvironment kinds are `local`, `docker`, `remote_container`, `remote_host`, `browser`, and `desktop`; Docker-per-worker ephemeral is default [docs/contracts/ct-46-qma-execution-environment-job.yaml:30](../../../../../docs/contracts/ct-46-qma-execution-environment-job.yaml#L30).
- JobHandle states are `queued`, `running`, `done`, `failed`, `cancelled`, `aborted`, and `unknown`; terminal states are `done`, `failed`, `cancelled`, `aborted`; `unknown` is non-terminal [docs/contracts/ct-46-qma-execution-environment-job.yaml:34](../../../../../docs/contracts/ct-46-qma-execution-environment-job.yaml#L34), [docs/contracts/ct-46-qma-execution-environment-job.yaml:35](../../../../../docs/contracts/ct-46-qma-execution-environment-job.yaml#L35).
- Mapping from JobHandle to Task state is fixed: queued/running -> running, done -> done, failed -> failed, aborted -> failed with reason, cancelled -> cancelled, unknown -> unknown [docs/components/qma-daemon.md:211](../../../../../docs/components/qma-daemon.md#L211).

Routine:

- Routine is a Quant-owned scheduled trigger, declarative daemon state, UI-editable by operator-principal command, never agent-authored [docs/components/qma-daemon.md:167](../../../../../docs/components/qma-daemon.md#L167), [docs/contracts/ct-49-qma-routine.yaml:30](../../../../../docs/contracts/ct-49-qma-routine.yaml#L30).
- Missed fires while daemon is down are recorded, not automatically replayed; catch-up is explicit operator action [docs/contracts/ct-49-qma-routine.yaml:34](../../../../../docs/contracts/ct-49-qma-routine.yaml#L34).
- Continuation is an Agent-run property, not a Routine record property. An Agent continues across ready Tasks while `agent_stop` returns `block_stop`, bounded by continuation configurables, then escalates to the Quant mailbox and stops [docs/contracts/ct-49-qma-routine.yaml:36](../../../../../docs/contracts/ct-49-qma-routine.yaml#L36).

## Coordination, Delegation, Messages

Coordination is Task Graph plus ledger plus mailbox, not chat alone.

- Parallel workers synchronize through the Task Graph, never chat [docs/components/qma-daemon.md:112](../../../../../docs/components/qma-daemon.md#L112).
- Every Task has one Task Ledger across every Agent that ever holds it. Append rights follow `dispatch_lease`; reassignment writes a daemon-authored `reassigned` entry and increments `attempt_no`; resume from `defer` keeps the lease and does not increment attempt [docs/components/qma-daemon.md:153](../../../../../docs/components/qma-daemon.md#L153).
- Three ledger stores exist: Task Ledger, Quant Ledger, and Experiment Ledger. Desk ledgers are read-time views, not stores [docs/components/qma-daemon.md:157](../../../../../docs/components/qma-daemon.md#L157), [docs/contracts/ct-51-qma-task-ledger-entry.yaml:62](../../../../../docs/contracts/ct-51-qma-task-ledger-entry.yaml#L62).
- Mailbox lives per Quant. Message kinds are `handoff`, `reply`, `notify`, `review_request`, `status`, `question`, and `approval_request`; delivery states are `delivered`, `queued`, `woke`, `deferred`, `dead_letter` [docs/components/qma-daemon.md:161](../../../../../docs/components/qma-daemon.md#L161), [docs/contracts/ct-48-qma-mailbox-envelope.yaml:30](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L30).
- A message may request work but can never be the work. A handoff becomes real only when it writes a Task [docs/contracts/ct-48-qma-mailbox-envelope.yaml:28](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L28).

UI hypothesis: "inbox/messages" and "work/tasks" must be visually distinct. A message thread can explain why work exists, but the Task/ledger is the accountable object.

## Memory, Knowledge, Context

Memory:

- MemoryProvider is a per-desk singleton with no default binding; no provider returns `NoMemoryProvider`, and proposed candidates stage under RefinementProposal as memory edits [docs/contracts/ct-43-qma-memory-provider.yaml:30](../../../../../docs/contracts/ct-43-qma-memory-provider.yaml#L30), [docs/contracts/ct-43-qma-memory-provider.yaml:31](../../../../../docs/contracts/ct-43-qma-memory-provider.yaml#L31).
- MemoryCandidate lifecycle states are `proposed`, `validated`, `admitted`, `superseded`, `invalidated`, `expired`, `contradicted` [docs/contracts/ct-43-qma-memory-provider.yaml:33](../../../../../docs/contracts/ct-43-qma-memory-provider.yaml#L33), [docs/contracts/ct-43-qma-memory-provider.yaml:62](../../../../../docs/contracts/ct-43-qma-memory-provider.yaml#L62).
- A memory candidate is admitted, never promoted. `promote` is reserved for the live-zone human act outside QMA [docs/contracts/ct-43-qma-memory-provider.yaml:36](../../../../../docs/contracts/ct-43-qma-memory-provider.yaml#L36).

Knowledge:

- KnowledgeSource is read-only; QMX adapts to the library and does not impose a QMX schema/layout or write back to it [docs/contracts/ct-44-qma-knowledge-source.yaml:29](../../../../../docs/contracts/ct-44-qma-knowledge-source.yaml#L29).
- A Mission pins one CorpusSnapshot at start; citations carry source, locator, evidence label, and six evidence-confidence dimensions [docs/contracts/ct-44-qma-knowledge-source.yaml:31](../../../../../docs/contracts/ct-44-qma-knowledge-source.yaml#L31), [docs/contracts/ct-44-qma-knowledge-source.yaml:32](../../../../../docs/contracts/ct-44-qma-knowledge-source.yaml#L32).
- Search is literal and locator-based; no ranking, no embedding, no v1 index [docs/contracts/ct-44-qma-knowledge-source.yaml:36](../../../../../docs/contracts/ct-44-qma-knowledge-source.yaml#L36).

Context:

- Context is written by nobody, never persisted, and discarded with invocation; Context Compiler is a singleton default binding replaceable by exactly one plugin [docs/components/qma-daemon.md:103](../../../../../docs/components/qma-daemon.md#L103), [docs/components/qma-core.md:61](../../../../../docs/components/qma-core.md#L61).
- Handles are daemon-resolved references whose contents never enter the context window. Known handle kinds include BacktestHandle, ExperimentHandle, TradeLogHandle, StrategyHandle, KnowledgeHandle, and MarketDataHandle; live/writable money-path handles cannot be minted [docs/components/qma-daemon.md:213](../../../../../docs/components/qma-daemon.md#L213), [docs/contracts/ct-47-qma-experiment-spec.yaml:34](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L34).

UI hypothesis: Memory, Knowledge, and Context should not be merged into one "context" drawer. They have different trust, persistence, and mutability rules.

## Extensions, Tools, Models, Execution

QMA-specific term: "plugin" is adopted only inside the QMA scope for desk extension packages. Outside QMA prose, the platform still prefers "extensions" except where QMA docs explicitly say plugin.

Extensions / plugin surface:

- Contribution points: singleton MemoryProvider, KnowledgeSource, ExecutionEnvironment, ComputeProvider, ContextCompiler; multi tool, tool_adapter, hook, skill, graph_template, model_deployment, toolset, worker_template [docs/components/qma-core.md:59](../../../../../docs/components/qma-core.md#L59), [docs/contracts/ct-42-qma-plugin-manifest-context.yaml:61](../../../../../docs/contracts/ct-42-qma-plugin-manifest-context.yaml#L61).
- There is no `ui_view` contribution point in v1 [docs/components/qma-core.md:59](../../../../../docs/components/qma-core.md#L59), [docs/contracts/ct-42-qma-plugin-manifest-context.yaml:63](../../../../../docs/contracts/ct-42-qma-plugin-manifest-context.yaml#L63).
- Activation registers contributions through scoped PluginContext; unload disposes them LIFO. Missing dependency, duplicate singleton, duplicate multi id, unresolved cardinality/scope, required unbound singleton, manifest-declared operator fields, or forward-only upgrade without operator confirmation are load refusals [docs/contracts/ct-42-qma-plugin-manifest-context.yaml:32](../../../../../docs/contracts/ct-42-qma-plugin-manifest-context.yaml#L32), [docs/contracts/ct-42-qma-plugin-manifest-context.yaml:68](../../../../../docs/contracts/ct-42-qma-plugin-manifest-context.yaml#L68).

Tools:

- One Tool Registry spans native, CLI, plugin, MCP-adapter, browser, computer-use, and backtest tools [docs/components/qma-daemon.md:179](../../../../../docs/components/qma-daemon.md#L179).
- The capability ladder is API/structured tool, CLI, containerized program, browser automation, visual browser or computer-use, persistent remote desktop [docs/components/qma-daemon.md:179](../../../../../docs/components/qma-daemon.md#L179).
- There is no QMA execution tool at any account role, research-paper/node-paper included. Prohibited acts include order submission/amend/cancel, opening/closing/hedging positions, protection changes, sizing, bot-to-book binding changes, Book/BMS parameter changes, kill switch/control actions, or registry zone transitions [docs/components/qma-daemon.md:181](../../../../../docs/components/qma-daemon.md#L181), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:95](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L95).
- Reachability barrier: no QMA worker/environment/browser/computer-use session may reach venue, broker, exchange, trading-node, or platform-registry control surfaces; violations are refused at placement/registration [docs/components/qma-daemon.md:183](../../../../../docs/components/qma-daemon.md#L183).

Models:

- ModelClass has four values: `REASONING_HIGH`, `WORKHORSE_GENERAL`, `CODING_HIGH`, `FAST_CHEAP`; the harness picks a class and an agent never names a vendor [docs/contracts/ct-45-qma-model-deployment-broker.yaml:31](../../../../../docs/contracts/ct-45-qma-model-deployment-broker.yaml#L31).
- Router never crosses class boundaries; empty eligible pool returns `NoEligibleDeployment` [docs/contracts/ct-45-qma-model-deployment-broker.yaml:32](../../../../../docs/contracts/ct-45-qma-model-deployment-broker.yaml#L32), [docs/contracts/ct-45-qma-model-deployment-broker.yaml:33](../../../../../docs/contracts/ct-45-qma-model-deployment-broker.yaml#L33).
- Credentials are references, never values; broker allowlist excludes venue, broker, exchange, trading-node, and platform-registry credentials [docs/contracts/ct-45-qma-model-deployment-broker.yaml:41](../../../../../docs/contracts/ct-45-qma-model-deployment-broker.yaml#L41), [docs/contracts/ct-45-qma-model-deployment-broker.yaml:42](../../../../../docs/contracts/ct-45-qma-model-deployment-broker.yaml#L42).

Execution:

- Default environment is Docker-per-worker, ephemeral, no shared dirty filesystem [docs/components/qma-daemon.md:189](../../../../../docs/components/qma-daemon.md#L189).
- RLM kernel is the persistent Python interpreter inside the Analysis worker's Docker container, not in the daemon process; it reaches host functions via `host_request` over qma-wire [docs/components/qma-wire.md:102](../../../../../docs/components/qma-wire.md#L102), [docs/components/qma-daemon.md:213](../../../../../docs/components/qma-daemon.md#L213).

## QMA Across The Platform

QMB:

- QMB is the experimentation/backtesting product: one pure library plus `qmb` CLI, application-layer product built on QMF [docs/architecture/overview.md:291](../../../../../docs/architecture/overview.md#L291), [docs/components/qmb.md:17](../../../../../docs/components/qmb.md#L17).
- In the workbench, there are exactly three experiment lanes, selected by door: ungoverned `qmb.run()`/ordinary Python/import qml; governed QMB orchestrator spawn; coordinated QMA Backtesting Service placement [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:65](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L65), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:69](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L69).
- QMA places at most one `qmb` CLI/MCP run invocation per ExecutionEnvironment, never imports qmb, and reaches QMB run ledger/CT-32 by refs from the Experiment Ledger [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:101](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L101), [docs/contracts/ct-47-qma-experiment-spec.yaml:38](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L38).
- QMB owns intra-run parallelism, run ledger, and artifact contract; QMA never copies/merges that ledger [docs/components/qma-daemon.md:215](../../../../../docs/components/qma-daemon.md#L215).

QML:

- QML authors bot-domain registry artifacts: CT-33 Bot definition, CT-34 confluence, plus runtime protocol/conformance. QML is pure and built on QMF, not QMA [docs/architecture/overview.md:325](../../../../../docs/architecture/overview.md#L325).
- Generation, if built, authors CT-33/CT-34 and/or logic-source bytes through QML; search is QMB parameter variation. QMA never assembles CT-33/CT-34 JSON or fills deferred mechanism nouns [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:77](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L77), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:81](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L81).

QMF Registry / Library:

- Shared Library is a projection over existing `fp1` kinds; there is no new COMP and no second store [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:71](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L71), [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:75](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L75).
- Library objects include CT-33, CT-34, strategy-family, CT-22 Book, CT-27 BMS, CT-28 binding, CT-12 split, CT-10 observation, CT-32 result, and CT-47 ExperimentSpec. Not Library objects: QMA staging/RefinementProposals, JobHandles, Graph Templates, Skills, Routines, saved views, analysis publications, derived datasets [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:75](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L75).

QMF Risk:

- Book/BMS variants are complete new fingerprinted CT-22/CT-27 candidates in registry `dev` zone, then evaluated through QMB replay; QMA may emit them only as `money_path_relevant` candidates with field-level diffs, never filling unset money-path fields [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:89](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L89), [docs/contracts/ct-47-qma-experiment-spec.yaml:36](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L36).

QMN:

- QMN is the trading node: one product with two modes `paper | live`, no operator command line; control surface is desktop UI over node doors [docs/components/trading-node.md:99](../../../../../docs/components/trading-node.md#L99), [docs/components/trading-node.md:101](../../../../../docs/components/trading-node.md#L101).
- QMA does not execute against accounts and does not write the hub; research-paper is QMB governed replay, node-paper is Book-level demo routing + soak, QMA-paper does not exist [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:95](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L95), [docs/components/qma-daemon.md:233](../../../../../docs/components/qma-daemon.md#L233).

## User-Visible Waiting, Failure, Approval, Intervention

Waiting and background work:

- Client attach/detach is not run control. Closing a UI tab cancels nothing [docs/components/qma-wire.md:69](../../../../../docs/components/qma-wire.md#L69), [docs/components/qma-wire.md:120](../../../../../docs/components/qma-wire.md#L120).
- `defer` parks work durably, releases `environment_lease`, retains `dispatch_lease`, and reruns hooks on resume [docs/components/qma-daemon.md:145](../../../../../docs/components/qma-daemon.md#L145).
- Quiet hours suppress wakes only: messages still deliver and ack; they do not suppress Routine firing, pause runs, or delay approval replies [docs/components/qma-daemon.md:163](../../../../../docs/components/qma-daemon.md#L163), [docs/contracts/ct-48-qma-mailbox-envelope.yaml:33](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L33).

Failures:

- Hook timeout is generally fail-closed to `deny`, with carve-outs for ledger append, `agent_stop`, and after-events [docs/components/qma-daemon.md:143](../../../../../docs/components/qma-daemon.md#L143).
- Unknown environment/job outcome is durable non-terminal `unknown`, not failure; no component retries, assumes outcome, or invents terminal state [docs/components/qma-daemon.md:211](../../../../../docs/components/qma-daemon.md#L211).
- Plugin load-time refusal does not terminate a running daemon or discard pending evidence append; it refuses the load/install/enable/reload and leaves running leases/tasks untouched [docs/contracts/ct-42-qma-plugin-manifest-context.yaml:39](../../../../../docs/contracts/ct-42-qma-plugin-manifest-context.yaml#L39).

Approvals:

- `ask` emits one approval_request into a mailbox or operator approval queue, with timeout/escalation semantics [docs/components/qma-daemon.md:145](../../../../../docs/components/qma-daemon.md#L145).
- `approval_request` is the single human approval channel every gate raises [docs/components/qma-daemon.md:161](../../../../../docs/components/qma-daemon.md#L161).
- Operator approval queue can be read/answered only by an `operator` principal; no headless, scripted, scheduled, or agent-initiated path can answer an approval [docs/contracts/ct-48-qma-mailbox-envelope.yaml:35](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L35).
- Human-gate commands include admission approval, forward-only migration confirmation, unknown resolution, plugin install/enable/reload, desk/quant creation, role base writes, model family assignment, Routine writes, ExecutionEnvironment declaration, Mission approval route writes, and other high-authority changes [docs/components/qma-wire.md:108](../../../../../docs/components/qma-wire.md#L108).

Intervention:

- `JobHandle.cancel` is coordinated cancel authority for QMA-placed work; for QMB it maps to QMB abort and the QMB ledger writes `aborted` [docs/components/qma-daemon.md:231](../../../../../docs/components/qma-daemon.md#L231).
- Node promotion/live acts remain outside QMA and are human acts. QMA can hold candidate refs only [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:99](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L99).

## Compact State / Object Matrix

| Object | Documented States / Key Lifecycle | Relationships | User Needs To See / Control | Source |
|---|---|---|---|---|
| Desk | Five fixed slugs; consolidation display-only; lead flag unresolved | Hosts Roles and Quants; desk ledgers are read-time views | Department grouping; lead ambiguity; avoid renaming backend desk | [qma-core.md:55](../../../../../docs/components/qma-core.md#L55), [gap-report.md:227](../../../../../docs/gap-report.md#L227) |
| Role | Declarative, stateless behavioral contract; `role.base` operator-authored, overlay editable through proposal | Instantiates many Quants; grants ceiling capabilities | Understand "behavior contract" vs person/addressee | [qma-core.md:53](../../../../../docs/components/qma-core.md#L53), [ct-50...yaml:39](../../../../../docs/contracts/ct-50-qma-refinement-proposal.yaml#L39) |
| Quant | Persistent named actor with memory, missions, routines, WakePolicy, mailbox; may have Quant Ledger while lead | Belongs to Desk and Role; owns Mailbox/Missions/Routines | Primary addressee, department member, wake/quiet-hour controls | [qma-core.md:53](../../../../../docs/components/qma-core.md#L53), [ct-48...yaml:32](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L32) |
| Agent | Running reasoning/execution instance | Runs under Quant/Mission/Task/Session; holds leases | Show as active worker, not durable identity | [qma-core.md:53](../../../../../docs/components/qma-core.md#L53), [qma-daemon.md:153](../../../../../docs/components/qma-daemon.md#L153) |
| Subagent | Leaf spawned by Agent; no wider capabilities; cannot delegate | Child of Agent | Show only within task execution, never as department contact | [qma-core.md:53](../../../../../docs/components/qma-core.md#L53) |
| Mission | `pending/ready/running/blocked/unknown/done/failed/cancelled`; terminal computed from Tasks | Owned by one Quant; contains Task Graph | Mission board/status; success criteria, budget, approvals | [qma-daemon.md:110](../../../../../docs/components/qma-daemon.md#L110), [qma-daemon.md:114](../../../../../docs/components/qma-daemon.md#L114) |
| Task | Same state vocabulary; terminal done/failed/cancelled; unknown blocks | Owns Task Ledger; outlives sessions/agents | Work item detail, resume/reassign/cancel, evidence trail | [qma-daemon.md:110](../../../../../docs/components/qma-daemon.md#L110), [qma-daemon.md:114](../../../../../docs/components/qma-daemon.md#L114) |
| Session | Run container; client replay attach read-only | One Task can have many Sessions across resumes | Replay/inspect without implying control | [qma-core.md:53](../../../../../docs/components/qma-core.md#L53), [qma-wire.md:67](../../../../../docs/components/qma-wire.md#L67) |
| JobHandle | `queued/running/done/failed/cancelled/aborted/unknown`; terminal done/failed/cancelled/aborted | ExecutionEnvironment job maps to Task state | Progress, cancel, attach/reattach, explicit unknown resolution | [ct-46...yaml:34](../../../../../docs/contracts/ct-46-qma-execution-environment-job.yaml#L34), [qma-daemon.md:211](../../../../../docs/components/qma-daemon.md#L211) |
| Routine | Enabled/disabled; missed fires recorded; no automatic replay | Quant-owned scheduled trigger into Mission Compiler | Schedule, enable, catch-up, max concurrency, owner | [ct-49...yaml:31](../../../../../docs/contracts/ct-49-qma-routine.yaml#L31), [ct-49...yaml:34](../../../../../docs/contracts/ct-49-qma-routine.yaml#L34) |
| Mailbox Envelope | Delivery: delivered/queued/woke/deferred/dead_letter | Per Quant; message may request work but is not work | Inbox, approval requests, dead letters, wake state | [ct-48...yaml:30](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L30), [ct-48...yaml:31](../../../../../docs/contracts/ct-48-qma-mailbox-envelope.yaml#L31) |
| MemoryCandidate | proposed/validated/admitted/superseded/invalidated/expired/contradicted | Per desk MemoryProvider; stages if no provider | Inspect proposed/admitted memory, validation/conflicts | [ct-43...yaml:33](../../../../../docs/contracts/ct-43-qma-memory-provider.yaml#L33) |
| Knowledge Citation | Pinned CorpusSnapshot; six evidence-confidence dimensions | Read-only KnowledgeSource; copied cited bytes retained | Source/citation viewer, freshness/provenance warnings | [ct-44...yaml:31](../../../../../docs/contracts/ct-44-qma-knowledge-source.yaml#L31), [ct-44...yaml:32](../../../../../docs/contracts/ct-44-qma-knowledge-source.yaml#L32) |
| RefinementProposal | validation -> verification -> optional review -> staged -> approval -> applied | Edits definitions only; operator apply | Review/apply/rollback candidate changes | [ct-50...yaml:35](../../../../../docs/contracts/ct-50-qma-refinement-proposal.yaml#L35), [ct-50...yaml:56](../../../../../docs/contracts/ct-50-qma-refinement-proposal.yaml#L56) |
| ExperimentSpec | Content-addressed fp1; lineage via CT-07; no Project/Workspace kind | Coordinated QMA research identity; links QMB evidence by ref | Research undertaking continuity, branches/successors | [ct-47...yaml:31](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L31), [ct-47...yaml:32](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L32) |
| QMB run | Ungoverned returns values; governed writes QMB ledger+CT-32; coordinated adds ExperimentSpec/Experiment Ledger refs | QMA places at most one qmb run per ExecutionEnvironment | Lane clarity, occupancy, evidence refs | [ARCHITECTURE-SPINE.md:69](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L69), [ct-47...yaml:38](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L38) |
| Analysis projection | Saved view, no CT-32, no occupancy | Reads CT-32/CT-29; may be persisted by QMA in coordinated lane | Distinguish saved view from rerun/result | [ARCHITECTURE-SPINE.md:87](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L87) |
| Analysis rerun | New QMB run; artifact is new CT-32 | Path-dependent method via QMB | Treat as run with occupancy/evidence | [ARCHITECTURE-SPINE.md:87](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L87) |
| Library object | Existing fp1 kinds only | Registry/QMB/QMA projections; no new store | Shared searchable objects by fingerprint | [ARCHITECTURE-SPINE.md:75](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L75) |
| Node/QMN | Node lifecycle separate; one product, modes `paper | live`; no CLI | Desktop UI over node doors; QMA cannot control money path | Separate node control/status from QMA candidate work | [trading-node.md:99](../../../../../docs/components/trading-node.md#L99), [trading-node.md:101](../../../../../docs/components/trading-node.md#L101) |

## September 14 Expansion Changes That Matter To UI

1. Workbench is now composition over existing applications, not a new app/package/service. UI should avoid implying "Experiment Service" or a sixth app [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:59](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L59), [docs/decisions/ADR-0022-workbench-expansion.md:78](../../../../../docs/decisions/ADR-0022-workbench-expansion.md#L78).

2. Three experiment lanes are now door-derived, not payload flags. A QMA-placed run has QMB evidence labeled governed and QMA Experiment Ledger labeled coordinated; collapsing those into one badge would be misleading [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:69](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L69).

3. Library identity is a projection over existing fp1 objects. Saved views, routines, skills, staging, and JobHandles are not Library kinds, even if the UI lets users find them [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:75](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L75).

4. Generation and search are split. QMB search varies parameters; QML owns future generation writes; QMA may reference/register candidates but must not assemble CT-33/CT-34 JSON [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:81](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L81).

5. Projection and path-dependent rerun are now named analysis methods. Projection is saved view/no occupancy/no CT-32; rerun is a new run/new CT-32 [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:87](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L87).

6. Research-paper / node-paper / no QMA-paper is now explicit. UI should avoid a generic mode switch for paper-like activity near agents [architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md:99](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md#L99).

7. QMA→QMB door is connect work, not proven implementation. Any UI that assumes live coordinated runs must account for the recording transport until connect work lands [docs/components/qma-daemon.md:221](../../../../../docs/components/qma-daemon.md#L221).

8. Laptop-off continuation is decided as a property but has no named always-on host yet. UI copy should not promise "keeps working while laptop sleeps" unless it can show the actual daemon/remote environment satisfying `GAP-0062` [docs/components/qma-daemon.md:231](../../../../../docs/components/qma-daemon.md#L231), [docs/gap-report.md:217](../../../../../docs/gap-report.md#L217).

## Contradictions / Ambiguities To Guard Against

- PM terminology needs reconciliation: the current component explicitly names the Role **Product Manager**, while the user has repeatedly described **Portfolio Manager** as a core QMX work perspective. Preserve both facts; do not silently rename the documented role or assume the portfolio responsibility is already represented by it [docs/components/qma-core.md:55](../../../../../docs/components/qma-core.md#L55). The five backend desk slugs do not settle the final user-facing environment roster.

- "Agent" is not the durable addressee. Quant is persistent; Agent is running instance; Bot is a trading-strategy/platform object, not an agentic actor [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53), [docs/components/qma-wire.md:94](../../../../../docs/components/qma-wire.md#L94).
- "Department" is a likely UI alias over Desk/Profile, but Desk is backend, Profile is client-side display only, and desk consolidation is deferred/display-only [docs/components/qma-core.md:53](../../../../../docs/components/qma-core.md#L53), [docs/gap-report.md:239](../../../../../docs/gap-report.md#L239).
- "Run" is overloaded: Agent run, JobHandle execution, QMB run, node loop/run_slice, Routine firing. The UI should qualify run-like nouns by object.
- "Project" and "Workspace" are UX aliases only; coordinated continuity is ExperimentSpec fp1 [docs/contracts/ct-47-qma-experiment-spec.yaml:32](../../../../../docs/contracts/ct-47-qma-experiment-spec.yaml#L32), [docs/decisions/ADR-0022-workbench-expansion.md:54](../../../../../docs/decisions/ADR-0022-workbench-expansion.md#L54).
- "Plugin" is allowed in QMA for desk extension packages, but broader platform prose still treats "extensions" as the safe general term.
- `source-inspected` contradicts older "defined-unwired/no code exists" wording where matching source exists, but it still is not end-to-end demonstration [docs/components/qma-wire.md:118](../../../../../docs/components/qma-wire.md#L118), [docs/decisions/ADR-0022-workbench-expansion.md:88](../../../../../docs/decisions/ADR-0022-workbench-expansion.md#L88).

## UI Implications As Hypotheses

These are interpretations, not backend facts:

1. Left navigation likely needs at least three axes available somewhere: Departments/Desks/Quants, Work/Missions/Tasks, and Library/Research Undertakings. Collapsing all into chat threads would hide the durable Task Graph and ExperimentSpec objects.

2. The primary conversational target should be a Quant, Mission, Task, or department/Desk alias, not an Agent process. Agent status still matters as execution telemetry.

3. Work status should use backend object labels: Task state, JobHandle state, DeliveryState, Routine state, Experiment lane, QMB run/query, and node state. A single generic spinner/status pill will blur important distinctions.

4. Approvals need their own first-class queue because `approval_request` is the single channel for human gates and cannot be answered by machine principals.

5. Background/autonomous work needs two visible truths: "client detached does not cancel" and "laptop-off continuation depends on actual daemon/remote environment availability."

6. Library search should show what kind of thing each hit is: registry fp1 object, ExperimentSpec, saved view, analysis publication, Knowledge citation, or Task evidence. Only some are Library objects in the architecture sense.

7. Trading/node controls should remain visually and permission-wise separate from QMA candidates. QMA can suggest/reference candidates; QMN/node UI controls promotion, soak, node-paper/live surfaces.

## Unresolved Questions For The Next UI Pass

1. Should "Department" be a visible alias for Desk, a Profile grouping of desks, or a higher-level UI construct over both? The backend gives Desk and Profile but leaves display consolidation deferred.

2. How should the UI represent the lead Quant ambiguity while `GAP-0071` remains open? It can show dead-letter behavior and avoid assuming a desk catch-all.

3. What is the minimal visual distinction between Mission, Task, Session, Agent, JobHandle, and QMB run so users understand resumption and evidence without seeing backend clutter?

4. How should the UI label the three experiment lanes without implying a payload flag or one universal "run" object?

5. Where should approvals live: per Quant mailbox, global operator approval queue, or both with the same underlying requests surfaced by scope?

6. What should the UI promise about continuation before `GAP-0062` names a concrete always-on host?

7. How should future UI contribution packaging be represented while `qma-ui-contract` is only a stub and no `ui_view` contribution point exists?

8. Does the documented Product Manager role match the user's intended Portfolio Manager perspective, or does portfolio work need a different role/display mapping? This is a reconciliation question, not authorization to modify the backend ontology.

## Parent Review

The main agent checked the central organization, transcript-independent Task definition, Task/Mission states and the latest experiment/procedure/continuation/extension rules against the current source. Relative links to architecture sources were corrected. Primary sources in the saved 12-file hash snapshot were unchanged at the end of this study. This does not freeze ongoing Grok work or verify integration behavior.

The previous layout recommendations remain paused. A fresh visual study should first demonstrate departmental ownership, persistent work, delegated execution, attention/approval states and shared evidence. It should not expose every internal type as another sidebar level. Performance cards remain relevant to bot/result work, but cannot serve as the universal representation of every departmental activity.

