# Packet vs Decision Register — Delta

Baseline: `transcript-decision-register.md`. Compared: packet v0.1 docs 00, 02–10 + manifest.

---

## 1. New in the packet, absent from the register

**Answers to register open questions**

- **Graphs as plugins — answered "yes".** `07 · Graphs as plugins`: "Strong candidate: yes." Adds two guardrails the register has no equivalent for: graph definitions "versioned and validated against stable graph APIs", and "Avoid letting graph plugins own the scheduler implementation." Names three graph packs: `research-discovery`, `strategy-validation`, `backtest-investigation`. (Register open Q4 = "Never answered.")
- **Mission-scoped hooks authored by agents.** `07 · Mission-scoped hooks`: agents may author hooks "from approved templates/schemas", bounded by six constraints — schema validated, permission bounded, visible in UI, auditable, removable with the Mission, "incapable of silently escalating privileges". Four worked examples (reject task completion unless test script passes; require artifact schema; validate cross-agent message fields; block backtest promotion without validation outputs). (Register open Q14 = "raised, unexamined".)
- **Hooks + ledger fusion.** `07 · Hooks + ledger`: a `TaskCompleted` hook requires a structured ledger append with a fixed field set — what was done, what changed, evidence/artifacts, unresolved issues, next recommendation. (Register open Q13 = "Never worked through.")
- **Skill/Loop containment rule.** `07 · Skill`: "Skill != Loop. A Skill may invoke a Loop; a Loop may use multiple Skills." Register carries this only as unratified boundary (open Q11).

**New enumerations and field lists**

- **21 in-house lifecycle hooks** (`07 · Candidate in-house lifecycle hooks`) — QMX's own set, not Claude's. New beyond the Claude surface: `before ledger append`, `before memory write`, `before skill write`, `before graph transition`, `agent idle`, `mission start/end`, `workspace create/remove`.
- **Six-entry initial loop registry** (`07 · Loop`): Act→Observe→Verify; Generate→Critique→Revise; Search→Evaluate Coverage→Expand or Stop; Hypothesis→Test→Learn→Mutate→Gate; Plan→Execute→Verify→Replan; Discover→Extract→Normalize→Rank. Plus five candidate QMX loops incl. "Book/BMS construction loops" and "Research evidence saturation loops". Register carries only #4.
- **Graph node types** (`07 · Graph`): tasks, conditional nodes, parallel branches, joins, approval gates, human gates, deterministic scripts, loops, agents/bots, artifact dependencies.
- **Plugin manifest — 17 candidate fields** and a **plugin directory layout** (`05`): `manifest / daemon / ui / worker / skills / tools / hooks / loops / graphs / migrations / assets`. Register has the daemon/worker/ui/skills split but no `migrations`, `assets`, `hooks`, `tools` dirs.
- **Capability contract namespace** (`05 · Capability model`): `memory.provider`, `model.provider`, `tool.provider`, `compute.provider`, `browser.provider`, `artifact.renderer`, `graph.definition`, `loop.definition`, `ui.navPanel`, `ui.settingsSection`.
- **Cordis-derived plugin lifecycle states** (`05 · Lifecycle`): mount → dependencies pending → activate → register reversible effects → disable → unload → reload → upgrade → rollback, with "Every contribution should have a disposer/unregistration path."
- **8-point upgrade compatibility checklist** (`05 · Upgradeability`), plus install-failure behavior in `10 · Install/update flow`: "previous version remains/rolls back where feasible; UI shows diagnostic; daemon remains healthy."
- **Context Engine input list — 12 items** (`08 · Context Engine`), incl. two the register never names: **model context budget** and **prompt-cache strategy**.
- **Compaction durability rule** (`08 · Compaction`): "Full transcripts may remain durable even when compacted context is used for subsequent model calls."
- **Ledger index dimensions** (`08 · Ledger`): Bot, Agent, Mission, Task, experiment, date.
- **RLM handle list** (`08 · RLM`) adds `knowledge` and `memories` as handles — the register's handle list stops at experiments/backtests/trades/strategies/papers/market_data.
- **Seven-level environment hierarchy** (`09 · Environment hierarchy`): native/API → CLI → local process → Docker/container → remote container/host → browser → computer/desktop. Register's ladder has four rungs.
- **Per-desk tool assignment concretes** (`09 · Tool assignment`): Research = browser/search, knowledge retrieval, filesystem, analysis, research MCPs; Developer = filesystem, git, shell, tests, backtesting tools; Trading = market, portfolio, execution, risk.
- **UI visibility contract** (`10 · UI visibility of backend state`): 12 things that must be inspectable — agents/bots, missions/tasks, graphs, **loops currently active**, **hook blocks/approvals**, ledgers, traces/logs, provider health, worker/compute state, plugin versions, tools/MCPs, memory/context diagnostics.
- **Settings-panel workflow list** (`10 · Plugin Settings`): install an MCP, enable a tool, add a model provider, configure a memory backend, **attach a capability to a Role**, **enable a graph**, add a UI panel — "without manually editing QMX internals."
- **10 machine-readable `core_principles` keys** (`packet_manifest.json`).

**New rules and framings**

- **Task transcript-independence** (`04 · Task`): "A task may be reassigned or resumed by another Agent without requiring the previous Agent's full transcript." Stronger than the register's "infrastructure owns the state".
- **Session promoted to an ontology object** (`00 · Packet Map`, `04 · Session`): the chain is stated as "Desk, Role, Bot, Agent, Session, Mission, Task" — Subagent and Worker drop out of the headline list.
- **Worker as an addressable execution slot** (`04 · Worker`): "Research Bot spawns Agent A. Agent A is placed on remote Worker W-17."
- **Role fields** (`04 · Role`) add three the register lacks: `default prompt sections`, `allowed mission types`, `agent/subagent policy`.
- **`Role != Prompt`** as an explicit statement (`07 · Prompt`).
- **Daemon owns three things the register never lists** (`03 · Daemon responsibilities`): **artifact registry**, **durable queues**, **workspaces**.
- **Language-choice rule** (`03 · Language consequence`): "Do not choose the daemon language based on UI convenience. Do not choose the UI architecture based on scientific/Python convenience." Widens the open question with two new options: "compare this against an **all-Rust or Rust+Python daemon**".
- **VPS as a registered provider** (`09 · Persistent computer`): "A persistent Windows/Linux VPS can be registered as a capability/provider" — not just a machine with one agent on it.
- **Backtesting framework is not the CLI** (`09`): "Do not reduce the framework to the CLI. CLI is one client surface over the same contract." Plus a naming directive: "Use this exact name in later packets."
- **Six-question reference study protocol** (`02`, opening) turning the operator's extract-don't-clone rule into a checklist, and a **primary-reference-by-subsystem index** (`02 · Primary reference by subsystem`) assigning one owner per subsystem. New candidate named there and in `08`: **LangMem** as a memory provider.
- **Four-bucket epistemic classification** (`00 · Status`): Agreed principles / Reference extractions / Candidate designs / Open questions — plus the reading rule "prefer latest explicit revisions over earlier brainstorms."

---

## 2. Contradictions

1. **Loops vs graphs — inverted emphasis.** Register #27, operator L4954: *"we have to have a few graphs noted down, not loops. I think I was wrong."* Packet `07` enumerates **eleven loops** (six-entry registry + five candidates) against **three** graph names. The packet obeys the letter of "graphs as plugins" while re-centring loops.
2. **Trust tiers — revived after being written off.** Register §8.2: *"Extension Trust Levels and a QMX extension marketplace … A single-operator system with no third-party publishers has no untrusted extension problem; it was floated and never returned to."* Packet `05 · Trust tiers`: *"Recommended design: Tier 1 — Declarative … Tier 4 — Worker/host plugin."*
3. **`provides`/`requires`/`optional` capability solver — revived.** Register §8.3 calls it *"a package-manager dependency solver for a plugin set that will realistically number in single digits."* Packet `05 · Plugin manifest` keeps *"provides capabilities / requires capabilities / optional capabilities."*
4. **Memory taxonomy — revived after being superseded.** Register §2: *"Eight-type kernel taxonomy → A single narrow definition plus provenance-gated candidates, then externalised to a provider."* Packet `08 · Memory`: *"Candidate memory types: episodic, semantic, procedural, decision, preference/policy, entity/relationship."*
5. **Cross-reference field names differ.** Register #37: *"an optional `trace_ref` / `artifact_ref` / `experiment_ref`."* Packet `08 · Cross-references`: *"`trace_id` / `experiment_id` / `artifact_id`."*
6. **Desk ledger count.** Register #36: *"Research Ledger, Development Ledger, Analysis Ledger, Trading Ledger."* Packet `08 · Ledger` adds a fifth: *"PM Ledger."*
7. **Mission field list.** Register #21: *"intent, scope, constraints, evidence requirements, available capabilities, success criteria, outputs, verification, budget, escalation, termination criteria."* Packet `04 · Mission` drops `constraints` and `outputs`, adds *"non-goals"*, *"allowed models/compute"*, *"expected artifacts"*.
8. **Buzz and external A2A stay on the comparison list.** Register open Q6, operator L4954: *"Buzz, I did not agree to use Buzz by the way. I just told you to look into it"*; external A2A *"possibly unnecessary internally."* Packet `02 · Primary reference by subsystem`: *"Agent communication: compare Grok Bot, Buzz, Claude teams/subagents, Prime Agent, and relevant A2A protocols."*
9. **`qmx.` blanket prefix vs the naming rule.** Register #73, operator L3968: *"Don't blanket-prefix with QMX … I don't like QMX because QMX is assuming the entire platform."* Packet `06` prefixes **all 37 daemon surfaces and 13 UI surfaces** with `qmx.` (the register's exception for *QMX Backtesting Framework* is an operator ruling and stands; the SDK namespace is not covered by it).
10. **ModelClass enum dropped.** Register #54 names four values — `REASONING_HIGH`, `WORKHORSE_GENERAL`, `CODING_HIGH`, `FAST_CHEAP`. Packet `09` keeps only the principle: *"The harness/Role decides the model class/capability required."* Loss, not disagreement, but the vocabulary is gone.
11. **Environment ladder depth.** Register #60: four rungs (CLI/API → Docker → browser → computer). Packet `09`: seven, inserting *native/API* vs *CLI* as separate rungs and *local process* and *remote container/host*.

---

## 3. Proposed SDK surfaces and contract names (06, with 05/07)

**Daemon SDK — `qmx.*` (37 surfaces)**

- Core: `role` (declarative behavioral contract) · `bot` (persistent named actor) · `agent` (running instance) · `session` (interaction/history container)
- Orchestration: `mission` (organizational contract) · `task` (bounded unit) · `graph` (topology/dependencies) · `loop` (control cycle) · `hook` (lifecycle interception) · `scheduler` (cron/routines)
- Cognition: `prompt` (invocation-time content) · `context` (what this call sees) · `memory` (provider-backed adaptive state) · `knowledge` (evidence corpus) · `skill` (reusable procedure) · `rlm` (programmatic over-context operation)
- Models: `model` (aliases/classes) · `provider` (vendor adapter) · `auth` (credential broker) · `proxy` (deterministic router)
- Tools/environments: `tool` (registry) · `mcp` (adapter source) · `workspace` · `environment` · `sandbox` · `browser` · `computer` · `compute` (fabric placement)
- State/evidence: `ledger` (agent-authored) · `artifact` · `experiment` · `trace` · `log` · `metrics` · `eval`
- Communication: `mailbox` (per-actor address) · `message` · `bus` (durable transport)
- Domain: `backtest` (+ "later QMX market/trading domain contracts")

**UI SDK — `qmx.ui.*` (13, independently versioned from the daemon SDK; "should not import daemon internals")**
`command · activity · sidebar · view · panel · editor · artifactRenderer · status · settings · notification · contextMenu · dashboard · theme`

**Plugin capability contract ids (05)**
`memory.provider · model.provider · tool.provider · compute.provider · browser.provider · artifact.renderer · graph.definition · loop.definition · ui.navPanel · ui.settingsSection`

**UI contribution functions (10)**
`registerCommand() · registerActivityItem() · registerSidebarView() · registerWorkspaceView() · registerPanel() · registerBottomPanel() · registerStatusItem() · registerSettingsSection() · registerArtifactRenderer() · registerContextMenu() · registerDashboardWidget() · registerTheme()`

---

## 4. Daemon/UI wire contract as stated (03)

- **Commands (9 named):** start mission · send message · steer agent · stop run · approve hook action · install/enable plugin · update configuration · launch task · retry task
- **Queries (7 named):** get bot · list missions · get graph state · inspect ledger · inspect trace · list installed plugins · get provider health
- **Events (10 named):** `agent.started` · `message.delta` · `tool.started` · `task.completed` · `hook.blocked` · `ledger.updated` · `mission.updated` · `worker.detached` · `provider.cooldown` · `artifact.created` — a dotted `noun.verb` convention, applied consistently but never stated as a rule.
- **Transport:** explicitly not frozen — "HTTP + WebSocket/SSE, local sockets, gRPC, or another transport can be evaluated."
- **Versioning rule: asserted, not specified.** `03` says only "They are connected by a versioned protocol"; there is no version-negotiation, deprecation, or compatibility-window rule anywhere for the wire. The only concrete compatibility machinery in the packet is for **plugins/SDK** (`05 · Plugin manifest` field "QMX SDK compatibility"; `05 · Upgradeability` items 5–7 "daemon compatibility / UI-bundle compatibility / worker compatibility"). This is the packet's largest under-specification against register #6, which calls the versioned wire contract "architectural law".
- **Attachment:** "Attachment is a client state" — an agent survives desktop close, browser close, laptop sleep, another UI connecting, and migration to a remote worker.
- **Boundary rule:** "The UI must not own authoritative execution state"; the protocol is the decoupling boundary, so neither side's language may be chosen for the other's convenience.

---

## 5. Verdict

**Faithful?** Substantially yes on the boundaries, the ontology, and the state-system separations — but it is a *normalization plus re-expansion*: it resolves four register open questions with real answers, and simultaneously revives three ideas the register had recorded as dropped or overcooked (trust tiers, the capability solver, the memory-type taxonomy), and re-centres loops against the operator's last word.

**Under-weighted by the register, worth keeping:** (1) `07`'s **mission-scoped hooks with the six safety constraints plus the `TaskCompleted`→ledger fusion** — this is the only place the operator's determinism preference, his hooks-and-ledger idea, and agent-authored ledger semantics are made to work together mechanically. (2) `04`'s **task transcript-independence rule** — one sentence that makes reassignment, resumption and detached work implementable rather than aspirational. (3) `03`'s **named command/query/event vocabulary** — 26 concrete wire nouns the register reduces to "commands + queries + durable event stream".

**Caveat for the spine:** adopt the wire vocabulary only alongside a versioning rule the packet does not supply, and treat the `qmx.` prefix on all 50 SDK surfaces as unresolved against the operator's desk-scoped naming ruling.
