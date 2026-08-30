# QMA Options Sheet — spine invariants D1..D22

Synthesis input for the agentic-system spine (`architecture-QMA-2026-08-28`). Sources: `inputs/transcript-decision-register.md` (§4 operator words BIND; §8 over-engineering), `inputs/packet/.../01_QMX_CONSTITUTION.md` (P1..P12), `inputs/packet-delta.md`, the parent platform spine `architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md` (inherited read-only), `docs/constitution.md` (L1..L39), and the 12 studies in `research/`.

**Component name used throughout: QMA** — the agentic system, sibling to QMF (framework), QML (bot library), QMB (backtesting). Already the name in `research/research-compute-experiments.md#Q6`. It resolves the operator's naming ruling (register row 73) against the packet's blanket `qmx.*` prefix (packet-delta §2.9).

**Reading rule.** "SETTLED by operator (register row N)" = do not reopen; only the contract shape below is new. "Operator must rule? yes" = the options differ materially in cost, vocabulary, or irreversibility.

---

### D1 — Design paradigm (name it; map to namespaces)

**Without it:** independently built units invent their own composition style — one team writes a service container, another a message bus, a third direct imports — and nothing can be unloaded, versioned, or reasoned about as one system. Namespaces drift into the blanket `qmx.` prefix the operator rejected.

- **A. Contract-hub daemon with reversible plugin scopes.** A definitions-only `qma-core` (ontology nouns, wire schemas, QMA refusal *variants*) that depends on nothing but `qmf-core`; every runtime concern enters through a port the core defines (MemoryProvider, ModelDeployment, ExecutionEnvironment, KnowledgeSource, ToolAdapter, ComputeProvider); every contribution registers through a scoped handle that returns a disposer, so deactivation replays the inverses. Mirrors the parent spine's hexagonal contract-hub exactly one level up. Cost: discipline, not machinery. `research/cordis-plugin-lifecycle.md#Q4`, `research/pi-agent.md#Q6`.
- **B. Actor/organization paradigm.** Desks and persistent actors first-class, coordination by message-passing between addressable mailboxes. Reads well organizationally but tempts the bus into being the record, which register row 33 forbids ("Ledger = truth, Messages = collaboration"). `research/grok-bot-and-buzz.md#Q1`.
- **C. Event-sourced control plane.** Everything is an append-only stream; all state is a read-time fold. True and inherited from the parent spine — but it is a persistence law (D4), not a composition paradigm; alone it says nothing about ports or plugins.

**LEAN: A, carrying C as a state law inside it.** It is the same paradigm the platform already ratified, so one house style covers QMF and QMA. It gives the reversible-activation invariant that answers the operator's stated upgrade fear directly (register rows 69, 72). It keeps every third-party thing (Hindsight, OCX, Docker, MCP) behind a QMX-owned port per Constitution P3 / L10. Namespaces: `qma-core` (definitions) · `qma-daemon` · `qma-wire` (contract package, the only cross-boundary import) · `qma-ui-contract` · plugins named by desk (`research-*`, `trading-*`, `analysis-*`) — never a blanket product prefix.

**Inherited-invariant row (L31/DEC-0122), binding on every downstream unit.** QMA mints **no parallel error, identity or canonicalization model**. QMA refusal types are *variants* of `qmf-core`'s typed-refusal base; ids and `correlation_id` are `qmf-core` types; `fp1` is imported, never re-derived. `qma-core` may add nouns and refusal variants — it may **not** define a second base for anything `qmf-core` already defines, and no unit may re-mint one "for wire convenience".

**Port cardinality is part of the contract.** Without it, two first-party plugins that each obey this lean to the letter — `research-corpus` calling `register_memory_provider` and a D13 candidate store binding the same port — produce two owners of Memory with two mutation paths and no defined winner. `singleton-per-scope`: **MemoryProvider**, **KnowledgeSource** (per `source_id`), **ExecutionEnvironment** (per `kind`), **ContextCompiler**. `multi`: tool, hook, skill, graph, model_deployment, command, ui_view. A second binding of a singleton is a **hard startup error naming both plugin ids and the port** — never last-write-wins, never a runtime override.

**Operator must rule?** **Yes** — it fixes the vocabulary and the namespace convention against the packet's 50 `qmx.*` surfaces.

---

### D2 — Daemon ≠ UI wire contract

**SETTLED by operator (register rows 6, 7):** two products joined by a versioned wire contract of commands + queries + a durable event stream; closing the UI must not stop an agent; attachment is a client state and never changes an agent's identity. Contract shape only below.

**Without it:** the UI grows authoritative state, a detached overnight run becomes unobservable, and a separately built Rust UI breaks on every daemon change.

- **Shape (not optional).** Envelope `{v, type, id, correlation_id, scope_path, seq?, payload}`; `scope ∈ desk|steward|session|mission|task|agent|subagent` — D15 gives every Steward a durable mailbox and register row 39 makes a Session replayable, and neither was addressable in the transcript's five-value vocabulary. **Commands** mutate, are acked immediately, side effects settle asynchronously. **Queries** read durable state. **One-journal law:** a **single** append-only journal with a global monotonic `journal_seq` is the only durable append target; every event carries a full scope-path `{desk, mission?, task?, steward?, session?, agent?, subagent?}`; a per-scope stream is a **filtered projection** whose `seq` is a derived index the daemon maintains, **never an independent append target** — otherwise one tool call, which belongs to an agent, a task, a mission and a desk at once, becomes four `seq` for one fact with no dedupe. *This is the daemon's internal event journal and is explicitly **not** a ledger:* desk ledgers stay per-desk and agent-authored (register row 36), and nothing here revives the QMX-wide event ledger the operator refused. `attach(scope, since_seq)` resolves against the projection while **replay authority remains the journal**; `detach` changes nothing; **session replay is `attach(since_seq=0)` read-only** (register row 39). Interaction requests queue durably — never reject an inbound message while blocked (bb ships that bug). Authoritative snapshots vs explicitly non-authoritative progress events. `research/bb-control-plane.md#Proposed QMX daemon↔UI wire contract SHAPE`, `research/pi-agent.md#Q6`.
- **Versioning (the packet's largest gap, delta §4).** semver `protocolVersion` + capability negotiation at attach (MCP `initialize` shape); **additive-only within a major**; unknown types and fields ignored by older clients; deprecations live N minors then drop. The contract package is the compatibility authority.
- **Transport A (JSON-RPC 2.0 over WebSocket + HTTP GET queries).** Transport-agnostic spec; QMF typed refusals serialize into the `error` object; JSON matches `fp1` canonical-JSON identity. **`id` and `correlation_id` are two fields, never one.** Commands, events, job records, ledger appends and telemetry spans each need their own unique id, so a per-message wire `id` cannot also be the thing that propagates unchanged: `id` is unique per message/record, minted by its producer; `correlation_id` is minted **once** at the originating operator command or scheduled trigger and copied **verbatim** onto every downstream command, event, JobHandle, ledger append, memory candidate and telemetry span. **No QMA component may regenerate, derive or truncate a `correlation_id`, and a record without one is refused at the gate.** `research/daemon-stack-options.md#(c) Wire contract`.
- **Transport B (Connect/gRPC protobuf).** Typed codegen for Rust + Python from one `.proto`, first-class streaming — but protobuf field-number identity fights `fp1` and adds a codegen toolchain.
- **Transport C (MCP-style stdio + Streamable HTTP/SSE).** Right model for the *handshake*; wrong as the daemon's own contract — MCP is a tool adapter inside the registry (register row 58).

**LEAN: A, with C's `initialize` handshake and JSON-Schema-described families.** Language-neutral for a Rust UI over a Python daemon; identity-consistent with `fp1`; no new toolchain; the durable event stream is just a replay of the journal D4 already requires.

**Operator must rule?** No — the boundary is his law already; transport is an engineering pick behind it.

---

### D3 — Daemon language

**Without it:** every other contract is written twice. A non-Python daemon must re-serialize QMF frozen dataclasses and re-implement `fp1`, money scaling and typed refusals — the exact thing L31/DEC-0122 forbids.

- **A. Python 3.14 asyncio daemon.** Composes `qmf-*` natively at the composition root; money/time/`fp1`/`correlation_id` never cross a language boundary. 3.14 ships `TaskGroup`, `asyncio.timeout`, subprocess supervision, live asyncio introspection of a running daemon, `concurrent.interpreters` and `forkserver` for worker isolation. Same toolchain as the existing factory (uv/ruff/pyright/pytest). Cost: the Claude **Python** SDK exposes fewer in-process hook events than the TS one — **[UNVERIFIED]**, two studies give 10 vs 7 for the same source checked the same day (item 1 below). `research/daemon-stack-options.md#(a) Daemon language`.
- **B. TypeScript/Node daemon.** Every studied reference (Pi, Prime host, bb, Cordis, OpenCodex) is TS, and the Claude TS SDK exposes ~20 more lifecycle events (**[UNVERIFIED]**; the TS SDK page was never independently opened). But that gap only bites if the daemon *embeds* the Claude SDK to drive workers; QMA authors its own hooks in any language, and a Claude worker runs as a subprocess behind a QMA provider adapter. Cost: schema export + re-implemented `fp1`, or a Python sidecar — a DEC-0122 violation either way. Tagged inherited fashion ("TS because the references are TS").
- **C. Hybrid — Python daemon, language-specific workers.** Prime Agent is exactly this (TS host + Python kernel), inverted. `connect-py` proves a Python server can serve a polyglot wire today, so a Rust UI and an occasional TS worker attach as clients. This is the escape hatch under A, not a third base.

**LEAN: A (Python 3.14), with C as the standing escape hatch.** L31 is dispositive: everything downstream of QMF must be built with QMF and must not re-implement its contracts. The single TS advantage is a *worker* concern solvable by adapter. The Rust UI stays Rust and attaches over the wire (register row 9, operator). One language for the daemon also keeps the RLM kernel, the hook callables and the verifier scripts in one runtime.

**Operator must rule?** **Yes** — he named this "the make or break" (register §3.1); it is the least reversible choice on the sheet.

---

### D4 — Persistence / event model and store

**Without it:** units invent mutable stored state, two writers corrupt a journal, and "session replay" and folds become impossible after the fact.

- **A. SQLite (WAL) + JSONL append journals behind `qmf-data` sinks.** Append-only evidence, read-time folds, no database server — the platform's existing convention (DEC-0114/0117; parent spine Stack). WAL: readers never block the writer, exactly one writer, same host only. The daemon is that single writer; UI and folds are readers. **Sole-writer invariant — an invariant, not a property of the store:** no process other than the daemon opens the journal, the SQLite file or the artifact store — not a worker, not a plugin's worker half, not the UI, not a fold job. Every write from anywhere else is a **wire command to the daemon**. Read-only folds may open the store **only on the daemon's host**. External stores that legitimately live elsewhere (QMB's own run ledger, D12) are reached by `_ref` and never merged into QMA's journal. Unstated, D20's workers on three hosts mount one WAL path and silently corrupt the journal the whole spine rests on. `research/daemon-stack-options.md#(b) Persistence / event model`.
- **B. PostgreSQL.** Real MVCC and many writers — but it is a database server, contradicting the ratified stack and the single-operator/single-host reality. Tagged inherited fashion (multi-tenant write concurrency).
- **C. DuckDB as the journal.** One read-write process or many read-only; cross-process writes only via a beta protocol. Confirms the parent ruling: DuckDB holds **rebuildable analytics views only** (fold outputs), never evidence.

**LEAN: A.** It is inherited, not chosen — the parent spine already ratified JSONL evidence + SQLite metadata + DuckDB rebuildable views, and every QMA fold (mission state, task state, seat state, provider health) declares a fold contract exactly like the platform's. Note the coupling: if D13 selects Hindsight, Postgres arrives as that *provider's* isolated dependency, never as the QMA journal.

**Operator must rule?** No — inherited from the parent spine.

---

### D5 — Ontology + vocabulary (incl. the replacement for "Bot")

**SETTLED by operator (register rows 10, 11, 15, 16, 20):** Desk/Profile → Role → persistent actor → Agent → Subagent; Role is a declarative behavioral contract ≈ system prompt, stateless; the five quant roles stand; Profile is presentation, Role is responsibility; Goal → Mission → Task. Only the **name of the persistent actor** and the Session/Worker placement are open.

**Without it:** two units mean different things by "agent", the UI models identity where the daemon models runs, and "bot" collides with the platform's most load-bearing authority word.

- **The collision that decides it.** `docs/constitution.md` L36: *"Bots trade; books control bots; BMS accounts for and constrains books."* **Bot is taken** and it is the money-path authority term. The parent spine also reserves **Seat** (`seat active|benched`, `BENCHED` is a bot-seat state only). Both candidates from the transcript are unusable.
- **Candidates and the case for each** (`research/grok-bot-and-buzz.md#Names for the persistent named organizational actor`): **Steward** — names end-to-end ownership of a desk's area, which is exactly Grok's stable "distinct area of ownership" rule made into a noun; no collision. **Operative** — mission-carrying, fits the quant/ops register and the trading-terminal feel; no collision. **Persona** — idiomatic and UI-legible, but collides conceptually with Profile-as-presentation. **Principal** — precise if identity-as-authority carries the design, but overloads the security word. **Teammate** — Grok's own framing; too generic, imports marketplace softness.
- **Chain proposed:** Desk (workspace) → Role (contract) → **Steward** (durable named actor: name, memory scope, desk ledger, missions, routines, mailbox) → Agent (a running instance) → Subagent (an Agent spawned by an Agent). **Session** = the run container carrying the three axes (D9); **Worker** = an addressable execution slot, deliberately not an ontology object.
- **Cardinality and address grammar (stated, because D15's `steward:research/lead` otherwise smuggles register row 18's undefined "Role Lead" back in).** Role:Steward is **1:N**; Desk:Steward is **1:N**. Exactly **one** Steward per Desk carries the `lead` flag, and its mailbox is the address for desk-scoped inbound and for any envelope whose more specific recipient no longer exists. `ActorId` grammar is fixed as `steward:<desk_slug>/<steward_slug>`, where the steward slug is **operator-minted, stable, never a Role name and never reused**. **Agents and Subagents have no mailbox and are never a `to:` address** — D12's `wake` resolves to the owning Steward at submit time and stores that `owner_actor` on the JobHandle.

**LEAN: Steward** (runner-up: Operative, if the operator wants a harder register). It is the only candidate that is both accurate to the Bot-holds-identity semantics and free of a collision with `bot`, `seat`, `book` or `BMS`. Constitution P1: name for one operator's quant desk, not for a general teammate product.

**Operator must rule?** **Yes** — pure vocabulary, and it propagates into every UI label, ledger name and SDK surface.

---

### D6 — State ownership

**SETTLED by operator (register rows 23, 33, 35, 36, 37, 40, 43, 47):** the infrastructure owns the task graph; ledgers are agent-authored and per-desk; ledger ≠ observability, separate contracts and stores; `MEMORY ≠ LEDGER ≠ KNOWLEDGE ≠ ARTIFACTS ≠ CONTEXT`. Contract shape only.

**Without it:** the same fact is written to three stores with three meanings, and a lost mailbox or compacted transcript takes real state with it.

| State | Owner | Who may write | Crossing rule |
|---|---|---|---|
| Mission / Task graph | daemon | daemon only (agents *propose* transitions as commands) | id reference |
| Desk Ledger (Research/Development/Analysis/Trading/PM) | daemon store, **agent-authored** | the agent, through a schema-validated gate hook | may carry `trace_ref` / `artifact_ref` / `experiment_ref` / `knowledge_ref` — references, never shared semantics |
| Memory | MemoryProvider, scoped per desk/role | agent *proposes*; daemon gate promotes | recalled into Context only |
| Knowledge | external corpus (STRATS et al.) | **nobody** — read-only; agent output re-enters as a new source | `Citation{source_id, locator, snapshot_id}` |
| Artifacts | daemon registry, content-addressed | producing agent via the registry | ref only |
| Telemetry (logs/traces/metrics/trajectories) | daemon, **harness-authored** | harness only | separate store; `correlation_id` shared |

Keep the register's `_ref` suffixes over the packet's `_id` (delta §2.5) — the suffix is what says "reference, not join". Ledger indexes by Steward, Agent, Mission, Task, experiment, date, so the operator's "per-agent ledger" ask is served as a view over the per-desk store (register §3.12).

**Clock law — stated here because every row above is timestamped and the daemon no longer runs on the operator's machine.** Every persisted QMA timestamp is **UTC**, obtained from `qmf-core`'s clock protocol **via the daemon**: no component reads host local time and no worker timestamps its own evidence. Any operator-facing wall-clock policy — `quiet_hours` (D15), routines/cron (D16), daily ledger rollups, the ledger's `date` index, D12 timeouts, D18 retention — carries an explicit **IANA timezone** field resolved at policy-evaluation time in the daemon. The UI renders in the viewer's zone and **never persists a local-time value**. Unstated, "quiet hours 22:00–07:00" means two different things on the always-on host (D15) and the Windows workstation (D20).

**Operator must rule?** No — every row is already his ruling.

---

### D7 — Hooks: HookEvent vocabulary, HookResult, where they run, ReviewPolicy

**SETTLED by operator (register rows 29, 30, 31):** hooks are a first-class QMA primitive modelled on the Claude surface; deterministic verifier scripts at task completion instead of LLMs judging themselves; ReviewPolicy `author_family != reviewer_family` enforced by hooks, and the review must update the task.

**Without it:** each unit invents its own interception point, "done" means whatever the model says, and the review is a chat message nobody can audit.

- **A. B's ten events plus five lifecycle extras — restated as a strict superset of B** (`research/claude-agent-sdk-hooks.md#QMX-owned contract`): everything in B, plus `after_tool_failed · agent_start · agent_idle · before_compact · prompt_submit`. The study's own 15-event list was **not** a superset — it lacked `before_ledger_append` — so A-vs-B was not a monotone sizing choice until now.
- **B. Ten-event v1 closed set, addable via registry.** `before_tool · after_tool · agent_stop · task_created · before_task_complete · review_required · before_ledger_append · before_memory_write · env_create · env_remove`, with `mission_start/complete` added the moment the Mission Compiler ships. **`before_memory_write` is required, not optional** — D19 names it one of the five enforcement points and D6 requires a daemon gate to promote memory, so its absence was a hole, not a sizing decision. Everything else waits for a named consumer — the register's own §8.10 warns about five overlapping control abstractions.
- **C. Adopt Claude's ~31-event TS surface.** Rejected: most of it is display, elicitation, settings-file and marketplace plumbing for a general-public IDE.

**Contract (any option).** `HookResult` is one tagged union: `decision ∈ observe|allow|deny|ask|defer|block_stop`, plus `reason`, `updated_input` (before_tool only), `updated_output` (after_tool only), `injected_context` (→ Context Compiler, **never** the Ledger), `ledger_entry` (gated), `stop`, `verifier_ref`. **Total precedence order — all six values, no unordered pairs:** `block_stop > deny > defer > ask > allow > observe`; parallel hooks, most-restrictive wins. **`observe` never participates in resolution** and may not carry `stop`, `updated_input` or `updated_output`. **Fail closed on timeout** (Hermes `pre_tool_call`) now names its value: a hook timeout resolves to **`deny` with `reason="hook_timeout"`** plus a telemetry record carrying the `correlation_id`. Every hook is a deterministic Python callable or subprocess — no prompt-type or agent-type handlers (Constitution P2). Hooks run **in the daemon**; a worker-side tool interception may execute in the worker but the *decision* is the daemon's. Registry keys by `(event, matcher, source)` with `source ∈ desk|role|mission|plugin`. `before_task_complete` and `review_required` are **required** gates, not optional. Agent-authored hooks are mission-scoped only, from approved templates, under the six packet constraints, and removable with the Mission.

**LEAN: B.** The operator's determinism preference needs the *gates*, not the surface area; a closed-and-addable enum satisfies Constitution P5 without enumerating events that have no consumer. `research/claude-agent-sdk-hooks.md#Verified fact B`, `research/hermes-agent.md#Q4`.

**Operator must rule?** No — the ruling exists; this is sizing.

---

### D8 — Graph / Loop / Skill: keep three or collapse Loop into Graph

**Without it:** three registries with overlapping semantics, and the packet re-centres loops (eleven of them) against the operator's last word that only graphs need enumerating.

- **A. Keep three.** Skill = reusable procedure/knowledge; Loop = executable control cycle with runtime-owned stopping conditions and budgets; Graph = topology across actors. Containment rule: a Skill may invoke a Loop; a Loop may use Skills. Faithful to register row 25, but the operator himself asked "how do loops differ from skills… seems like I was wrong" (§3.11).
- **B. Two primitives — Skill + Graph; Loop folds into Graph.** **Name split, stated as law.** One word over two entities with different owners is why a plugin author would build a graph engine holding node state while the daemon holds task state — two mutation paths over one work item. So: the authored, plugin-contributed, versioned artifact is a **Graph Template** and holds **no runtime state**; the daemon-owned runtime structure keeps the name **Task Graph** and is the **only** place work state lives. **Compilation law:** instantiating a Graph Template emits **Tasks (and only Tasks)** into the daemon's Task Graph; a template is never mutated by a run. **Cycle form is picked, not left ambiguous:** `cycle` is a **node kind** wrapping a named subgraph and carrying the runtime-owned `stopping_condition`, `budget` and `escalation`; **back-edges in the topology are invalid and the validator rejects them at registration** — otherwise one team builds a wrapping node, another a back-edge, and the two disagree on where those three fields attach. Other template node kinds stay as the packet lists them (task, conditional, parallel branch, join, approval gate, human gate, deterministic script, cycle, agent, artifact dependency). The six named cycles (Act→Observe→Verify; Hypothesis→Test→Learn→Mutate→Gate; repair/refill/promote/stop; …) become authored Graph Templates, not a second registry. Templates are validated against a stable graph API; **graph plugins never own the scheduler and never hold node state**. v1 = authored templates only, no self-invented ones — register row 28 survives intact.
- **C. Collapse Skill into Loop.** Reject: a Skill is documentation with progressive disclosure and its own promotion lifecycle; a control cycle is executable state. Different lifecycles, different gates.

**LEAN: B.** The operator's last word (register row 27) demoted loops and asked for graphs as plugins ("I would prefer it"); the register's §8.10 flags the five-abstraction stack as overcooked; two primitives are the smallest set that still expresses the quant workflow. The runtime keeps owning stopping conditions and budgets either way — that property belongs to the runtime, not to a noun, which is exactly why the `cycle` **node kind** rather than a back-edge is the attachment point. `research/research-compute-experiments.md#Q4`, `research/pi-agent.md#Q6`. **[UNVERIFIED]** — no graph-engine candidate was studied anywhere; B is a contract with no implementation evidence behind it.

**Operator must rule?** **Yes** — it deletes a vocabulary word and a registry surface.

---

### D9 — Two runtimes (Dialogue, RLM): v1 scope, shared services, session axes

**SETTLED by operator (register rows 41, 42):** Dialogue and RLM are a clean split with different engineering; the axes are orthogonal and there is no separate "background session" type. Shape and v1 scope only.

**Without it:** RLM leaks into dialogue-shaped work, or dialogue prompt-stuffing is used for 800-variant backtest aggregation and quietly fails.

- **v1 = Dialogue Runtime for all desks; RLM Runtime v1 scoped to the Analyst desk.** RLM is the engine for the stated OG use case (mass backtesting, 3y of results, 40 MC reports). Ship the *engineering* — persistent Python kernel, typed `host_request` bridge, async spawn returning an admission handle, depth cap 2, kernel **inside the worker's Docker container** — not the research paradigm (RL-trained recursion, unbounded depth). **[UNVERIFIED]**: whether that kernel sustains the parallel-backtest fan-out, whether `dill` snapshots hold QMA's large handles, and the cost/latency at "800 variants" are all unmeasured. `research/prime-agent-rlm.md#Q6`.
- **Alternative: RLM deferred to v1.1 entirely.** Cheaper, but the Analyst desk then has no credible path for its actual load, and the operator's overnight-autonomy case is largely Analyst work.
- **Shared services (identical for both runtimes):** model proxy, credential broker, tool + capability registry, hooks/policy, desk ledgers, memory, knowledge, context compiler, compaction, mission/task graph, compute router, agent bus, telemetry.
- **Session axes:** execution model `dialogue|rlm` × attachment `attached|detached` × autonomy `interactive|semi|autonomous`. Attachment is a client state only.
- **Handles are the QMA contribution:** `BacktestHandle`, `ExperimentHandle`, `TradeLogHandle`, `StrategyHandle`, `KnowledgeHandle`, `MarketDataHandle` — daemon-resolved references whose contents never enter a context window.
- **`StrategyHandle` is bounded (L17, L33) — it is not "typed component mutation".** It may create and mutate only QMA-zone **candidate** artifacts in the registry's **dev zone**. It may **never** mutate a registered artifact: a change to one produces a **new content-addressed candidate carrying a `lineage[]` edge** back to the original, per L33. **Strategy and Bot semantics are QML / `qmf-registry`-owned**; QMA holds references and candidates only, and no QMA contract redefines either noun. Unbounded, the handle hands a QMA agent a mutation path onto the noun that feeds the bot→book→BMS authority chain (L36) and contradicts D20's own "a candidate artifact a human promotes".

**LEAN: v1 = Dialogue everywhere + RLM on the Analyst desk only**, both behind one loop/state contract so a session's execution model is a field, not a fork in the code.

**Operator must rule?** No — the split is his; the scoping follows from his own "backtesting first" ruling.

---

### D10 — Model Proxy / Router: ModelClass → Deployment Registry → Credential Broker

**SETTLED by operator (register rows 51, 52, 53, 54, 56):** the router is a deterministic availability-aware load balancer, never an LLM; OpenCodex is *the* reference; the credential broker is a separate subsystem; the harness picks the class.

**Without it:** callers name vendors, credentials scatter into config files, and the Context Compiler has no trustworthy context budget.

- **Contract.** `ModelClassRequest{model_class, min_context_tokens, needs{tools,vision,reasoning_effort,parallel_tool_calls}, affinity_key, budget_hint, exclude[]}` → `RoutingPolicy{strategy: failover|weighted_round_robin|quota_lowest|fill_first, sticky_limit, targets}` over a `Deployment` registry (provider, protocol, base_url, `credential_ref`, account_ref, capabilities, health, quota, rate-limit state, latency, cost, weight) → `CredentialBroker.resolve(ref) → {auth_mode: oauth|api_key|forward|local, secret}`. `ModelCapabilities` returns to the Context Compiler. **Re-mint the ModelClass enum the packet dropped** (delta §2.10) **exactly as register row 54 names it — four values, not five**: `REASONING_HIGH · WORKHORSE_GENERAL · CODING_HIGH · FAST_CHEAP`. **`VISION` is deleted**: neither the register nor the delta ever contained it, and it double-encodes eligibility `needs.vision` already carries. **Eligibility is encoded once:** `needs` is the **sole** eligibility input; `ModelClass` is a pure cost/difficulty tier. Otherwise caller A asks `WORKHORSE_GENERAL + needs.vision=true`, caller B asks `VISION`, and two conforming routers compute different eligible sets with neither wrong. **An unsatisfiable request returns a typed refusal `NoEligibleDeployment{model_class, unmet_constraint}`** — the router **never substitutes** a deployment failing `min_context_tokens` or any `needs` flag (a silent downgrade to a 128k deployment breaks the Context Compiler's budget guarantee this lean's first guardrail exists to protect), and the Context Compiler never receives a capability record the request did not qualify. `research/opencodex-model-proxy.md#(6) The QMX-owned Model Proxy contract`.
- **A. OpenCodex behind the contract as first implementation, for the OAuth/subscription-pool providers only.** Each OCX combo becomes one QMA Deployment with a **QMA-owned** capability record. Gains multi-account OAuth pooling, quota-aware routing and protocol translation that work today, for zero build. **[UNVERIFIED]**: combos, pool strategy and the routing-history store were read from this machine's install, not published docs.
- **B. In-house router from day one, API keys only.** Full determinism and full routing telemetry; loses the subscription pooling the operator's model pool assumes.
- **C. OCX as the whole model plane.** Reject: capabilities go opaque (OCX synthesizes placeholder 128k/text rows for combos), routing decisions and their audit live in OCX's own SQLite, credentials sit in plaintext home-dir JSON, and the product is built to masquerade as another harness.

**LEAN: A with three guardrails** — QMA keeps its own per-deployment capability map (never trust a combo's placeholder for context budgeting), QMA emits its own routing-decision telemetry, and credentials for QMA-owned deployments resolve from **Windows Credential Manager** per L34, not from `~/.opencodex`. **[UNVERIFIED]** and needing a governance ruling: whether multi-account pooling is acceptable under each provider's ToS — OCX's own README disclaims protection against enforcement. That keeps `ModelClass` swappable later without touching a caller.

**Operator must rule?** **Yes** — a third-party single-maintainer npm dependency in the model path, an explicit account-pooling ToS disclaimer, and credential custody.

---

### D11 — Tool Registry / Toolsets / MCP-as-adapter / capability ladder

**SETTLED by operator (register rows 57, 58, 59, 60):** the Tool Registry is QMA's internal representation and everything resolves through it; "MCP is not the tool system, it's part of"; assignment is per Role narrowed by Mission; the capability ladder stands.

**Without it:** MCP becomes the tool system by default, every agent gets every tool, and models call tools that cannot run.

- **Shape.** One registry over native · CLI · plugin · **MCP adapter** · browser · computer · backtest tools. Each entry carries a **`check_fn` availability preflight**: a tool that cannot run is *silently excluded before its schema reaches the model* (`research/hermes-agent.md#Q2`). Toolsets are named bundles. Assignment: Role grants a toolset → Mission narrows (never widens) → Subagent inherits ≤ parent and is blocked from delegation/memory-write tools at the leaf (`research/hermes-agent.md#Q4`). MCP servers are configured per desk/role from Settings and upgradeable there (row 58).
- **Ladder.** Keep the Constitution's six rungs: API/structured tool → CLI → containerized program → browser automation → visual browser/computer-use → persistent remote desktop. The packet's seven-rung version splits native/API from CLI for no consumer; the register's four is too coarse to express the Docker default.
- **Per-desk concretes** (packet, worth keeping): Research = browser/search, knowledge retrieval, filesystem, analysis, research MCPs; Developer = filesystem, git, shell, tests, backtest tools; Trading = market data (**read**), portfolio/positions (**read**), risk **calculation** (read-only, **no sizing authority**). **There is no execution tool, at any account role.** The packet's "execution (paper only)" is deleted: D20's own words say QMA's money-path output is "never a binding, a sizing decision or an **order**", and L36 puts nothing above a bot on the market — a Steward sits above a bot. "Paper" does not rescue it, because under the parent spine paper validation is an **account role on a real venue**, so an execution tool is a live venue command path opened to an agent. This is a **registry-level prohibition, not a permission policy**: no `check_fn` may make an order-submit, amend or cancel tool available, because none exists in the QMA Tool Registry. The only QMA write path toward the node is a candidate artifact the operator promotes (D20).

**LEAN: as above, six rungs, `check_fn` mandatory.** "Do not spawn a computer when a CLI can do the job" is already law (P10); the preflight is what makes narrowing real rather than advisory.

**Operator must rule?** No.

---

### D12 — ExecutionEnvironment + Compute Router + JobHandle

**SETTLED by operator (register rows 61, 62, 63, 64, 65; §4 Compute):** Docker container per worker is the default; one purchased Windows VPS with one dedicated computer-use agent; vendors deferred until the environment contract exists; backtesting is the reason workspaces exist.

**Without it:** agents name vendors, a detached overnight job is orphaned when the supervisor's turn ends, and two governors fight over the same CPU.

- **Contracts** (`research/research-compute-experiments.md#Q6`): `ExecutionEnvironment{kind: local|docker|remote-container|remote-host|browser|desktop, provider_ref, image?, mounts[], env_allowlist[], capabilities, lifecycle: ephemeral|persistent}` — env is a declared allowlist, never a control channel. `ComputeRequirement{cpu, memory, disk, gpu?, capabilities_needed, timeout, max_memory, isolation}` — the agent declares, the router places. `JobHandle{job_id, state: queued|running|done|failed|cancelled|aborted|UNKNOWN, environment_ref, spec_ref, reason?}` with `submit` (queues and returns immediately) · `attach` · `wait` · `reattach` · `wake` (terminal state → the owning Steward's mailbox, D5) · `cancel` · `stream`. Single-in-flight lease per node unless forced. **`UNKNOWN` is mandatory.** QMA *adopts* L35/DEC-0137's discipline here — L35 literally binds QMF **venue submissions**, so this is an adopted rule rather than an inherited one, but the failure it prevents is identical: a timeout, a lost supervisor or an unreachable environment resolves to **`UNKNOWN`, never `failed`**, because writing `failed` for a detached overnight job whose supervisor died is a **fabricated terminal outcome**. An `UNKNOWN` job **holds its environment's single-in-flight lease and blocks further placement on that node** until an explicit recorded resolution (reconciliation evidence or an operator ruling). **No component retries, assumes an outcome, or invents terminal state.** `wake` fires on `UNKNOWN` like any other terminal transition. `wait` is a sleep-until-change signal; the durable job store is truth.
- **`ExperimentSpec`** is content-addressed: `code_ref` only when *code* changes, `config_ref` (resolved-config fingerprint) for parameter/config changes, plus `data_ref`, `env_ref`, seed, model/harness version, cost assumptions, `lineage[]` as a DAG. This is the explicit rejection of git-branch-per-parameter.
- **QMB is the backtesting path, unchanged:** agent → QMA SDK backtest tool → Backtesting Service → the `qmb` CLI/MCP door → QMB. **QMA places exactly one `qmb` job per environment; QMB owns intra-node parallelism, its own run ledger and its artifact contract.** No second governor, no second data layer, no second registry inside QMA.

**LEAN: the contracts above, Docker-per-worker ephemeral default, the Windows VPS registered as a persistent provider** (not merely a machine with an agent on it), vendors still deferred.

**Operator must rule?** No — every load-bearing choice here is already his.

---

### D13 — MemoryProvider contract + first backend

**SETTLED by operator (register row 43):** QMA does **not** build memory in-house at v1; the SDK owns a `MemoryProvider` contract; Hindsight leads, Mem0 compares, Honcho is out.

**Without it:** arbitrary agent text becomes trusted memory, and memory silently becomes the ledger.

- **Contract (owned regardless of backend).** `propose(MemoryCandidate) → promote(id, ValidationResult) → recall(RecallQuery) → get/list/history → supersede/invalidate/expire → scopes()`; `reflect` optional and **off** (cognition is QMA's). `MemoryCandidate` carries provenance, supporting artifacts, **`promotion_confidence`** (QMA-owned scalar — see D14's name split), scope, proposed_by, occurred_at, supersedes. `Memory.validation_state ∈ proposed|validated|promoted|superseded|invalidated|expired|contradicted`. Recall is **token-budgeted**, not result-count. `research/memory-providers.md#QMX-owned contract`.
- **A. Hindsight as first backend.** MIT, self-hostable on Windows, retain/recall/reflect maps near 1:1, consolidation with exact quotes + proof count, reversible invalidate with reason and audit archive, temporal + graph retrieval. Costs: Postgres 14+ with pgvector, an LLM call per retain, and no native confidence or TTL field. **[UNVERIFIED]**: its SOTA claims are unevaluated against QMA's load, and whether its LLM extraction preserves structured provenance faithfully is unknown.
- **B. Mem0 OSS.** Apache-2, lighter — but ADD-only accumulation, no supersession (**[UNVERIFIED]** — Mem0's docs and README conflict on whether v3 supersedes or only accumulates), and **graph memory was removed from OSS**, which was the transcript's reason for naming it.
- **C. Ship the contract + a QMA-owned candidate store; defer any external backend — bounded so it is defensibly not a memory implementation.** The store persists **candidates and their `validation_state` only**: **no embeddings, no consolidation, no reflection, no ranking**. `recall` over it is **exact-match on scope + tag + time window and is explicitly not semantic retrieval**; any ranked or semantic recall is **unavailable until a MemoryProvider is registered**. This keeps the promotion pipeline and the provenance model alive while leaving "memory" itself unbuilt — which is precisely what row 43 protects.

**LEAN: C now, A next — and this is an amendment request to register row 43, not an application of it.** Stated plainly because the earlier framing hid it: row 43 is **[OPERATOR]** and says "**not building memory in-house at v1**"; a QMA-owned candidate store *is* in-house code, so the operator is being asked to **narrow his own ruling** to "no memory *engine* in-house", not to confirm it. The case for the narrowing: there is no trajectory or experience corpus yet — the same argument that defers the promotion pipeline (register §8.12) applies to the backend. Bounded C costs a small table and unblocks every dependent contract; A adds a database server and a per-write LLM call to a system that has nothing to remember yet. Re-evaluate A against QMA's own eval once desks have run.

**Operator must rule?** **Yes — on two things.** (1) The **row-43 amendment** above: C is in-house code against his recorded words, bounded to candidates + `validation_state` only. (2) A introduces a database server and per-write model cost; he deferred the backend choice explicitly (register §3.7).

---

### D14 — Knowledge contract (ingests the STRATS library unchanged) + separation from Memory

**Without it:** the STRATS library gets QMX fields written into it, provenance collapses to one confidence number, and Knowledge quietly becomes Memory.

- **The binding external constraint:** STRATS is *"a folder structure, not software"*, must stay readable without any tool, and **"QMX will adapt to the library — the library is NOT built around QMX"**. Writing back, adding QMX folders/fields, or hardcoding its layout is barred; its layout and serialization are still unratified; its root is currently **empty** — so **[UNVERIFIED]** by construction: the contract is designed against a spec, not a corpus, and 9 duplicate entry IDs are unresolved upstream. `research/knowledge-corpus-boundary.md#Q1`, `#Forbidden assumptions QMX must NOT make`.
- **A. Own the Knowledge contract now, ship a read-only file adapter.** `KnowledgeSource{kind, source_id, adapter}` · `PlainFileLibrarySource{root_path, read_only=true, impose_schema=false}.snapshot() → CorpusSnapshot{snapshot_id = content-addressed tree digest, file_digests[]}` · `Provenance{source_id, snapshot_id, locator, evidence_label (6 values), evidence_confidence (6 orthogonal dimensions), transfer_caveat}` carried **opaquely** — stored and surfaced, never averaged or reinterpreted · query surface `search / retrieve / cite`, returning handles and locators so the RLM works over the corpus instead of dumping it into context. **Name split, stated as law — one field called `confidence` cannot mean both things.** Knowledge carries **`evidence_confidence`**: six named dimensions, corpus-owned, opaque — never averaged, never compared across sources, never mapped to a scalar (`research/knowledge-corpus-boundary.md#Q2`, §4.6). Memory carries **`promotion_confidence`**: a QMA-owned scalar on the candidate (D13). **No QMA component may derive one from the other**, and a memory candidate that cites knowledge stores the `Citation` **plus the six dimensions verbatim** alongside its own scalar. Otherwise a UI citation renderer and the memory promotion gate both read "confidence" and collapse the wrong one — the exact failure the source corpus rejects.
- **B. No Knowledge subsystem.** The Analyst's RLM plus filesystem tools read the corpus directly. Cheapest, and it is the operator's own doubt ("RLM… makes it better without the need for actual knowledge bases… I don't know"). Loses citation reproducibility and the Memory/Knowledge separation law's enforcement point.
- **C. Full Delphi-shaped indexed corpus** (Postgres/pgvector, hybrid retrieval, context packs by token budget). The right end state; premature against an empty corpus with an unratified layout.

**LEAN: A without an index, with the query surface in the Tool Registry.** The contract is cheap, the separation law needs an enforcement point, and content-addressed snapshots are what make a citation reproducible (P11). **The query surface is a desk-agnostic Tool Registry entry (D11)**, available to every Role D11 grants knowledge retrieval: `search` (literal/locator over the `CorpusSnapshot`, **no index**, grep-class semantics) · `retrieve` (handle + locator) · `cite` (emits `Citation{source_id, locator, snapshot_id}`). **The RLM read path cannot be v1's retrieval mechanism**, as an earlier draft of this lean claimed: D9 scopes the RLM Runtime to the Analyst desk, so under that wording the Research desk — whose entire job is the corpus — would have had no retrieval mechanism at all. RLM is an **additional** programmatic access path on Analyst, never the only one. The v1 retrieval guarantee is **snapshot + locator reproducibility, not ranking**; indexing waits for a populated corpus. **Separation rule, stated as law:** flow is Knowledge → Context and Knowledge → cited in Memory/Ledger/Artifact; agent experience never silently becomes Knowledge — a QMA report re-enters only as a distinct source kind with its own snapshot.

**Operator must rule?** **Yes** — "is a knowledge base even needed at all" is his open question (register §3.10), and A commits to a subsystem.

---

### D15 — Agent Bus (mailbox, durable, non-authoritative) + where the daemon runs

**Without it:** messages become the record, parallel workers synchronise through chat, and every mailbox dies with the workstation.

- **Bus contract.** `ActorId` (stable, e.g. `steward:research/lead`) · one durable `Mailbox` per Steward · `Envelope{msg_id, from, to, kind, mission_ref?, task_ref?, correlation_id, reply_to?, causation_id?, body, artifact_refs[], priority, created_at}` · `MessageKind ∈ handoff|reply|notify|review_request|status|question|approval_request` · `DeliveryState ∈ DELIVERED|QUEUED|WOKE|DEFERRED|DEAD_LETTER` · `WakePolicy{wake_on, quiet_hours, max_wakes_per_window}` decided by the **deterministic** scheduler, never a model. At-least-once with idempotent `msg_id` dedup, per-actor ack cursor, **bounded retention** — the bus is not institutional memory. **Non-authoritative invariant:** a message may request work but cannot *be* the work; a handoff becomes real only when it writes a Task; the reviewer's authoritative act is the task update, the message is only the ping. `research/grok-bot-and-buzz.md#Q6`.
- **Where the daemon runs — A. A separate always-on host** (small Linux VPS or the existing research node). Mailboxes and the journal survive the workstation being off for days; the workstation is a pure client. Cost: one host.
- **B. Co-locate on the trading-node VPS.** No new host — but it puts agent workloads on the money path's machine, against the authority order (L36) and the clean framework/node split.
- **C. Daemon on the workstation.** Free; messages queue and deliver on next boot — which fails the operator's single most-wanted use case ("I want to be away for maybe the night and the agents continue working") whenever the box is off.

**LEAN: A.** Overnight autonomy is the stated primary requirement; an off-workstation daemon is the only shape that delivers it, and it needs **no external relay** — the mailbox lives in the daemon's own durable store. External A2A stays a later adapter behind the same `ActorId` contract; Nostr/Buzz signing is not adopted.

**Operator must rule?** **Yes** — it buys a host and decides whether the trading VPS is shared.

---

### D16 — Plugin model: manifest, contribution points, reversible activation, trust

**Without it:** unloading a plugin leaves dangling tools, hooks and timers; the operator's "will it upgrade cleanly" fear stays unanswered; and the existing in-house primitives (the threading node — **[UNVERIFIED]**, named in the transcript and nowhere specified) have nowhere to live.

- **A. Full Cordis-derived lifecycle** — reactive dependency re-mount, isolate/intercept scopes, HMR file watching, five event dispatch modes. Rejected as general-framework machinery for a handful of first-party plugins.
- **B. Reversible scope + topo load (lean).** `PluginManifest{id, version, qma_api range, desk, depends[], provides[], permissions[], entrypoint, migrations, rollback}`. `activate(ctx)` registers everything through a scoped `PluginContext`, and **each contribution point carries D1's cardinality** — `multi`: `register_tool / register_hook / register_skill / register_graph / register_model_deployment / register_command / contribute_ui_view`; `singleton-per-scope`: `register_memory_provider / register_knowledge_source / register_execution_environment / register_context_compiler`. Each returns a disposer pushed onto a per-plugin `AsyncExitStack`; **unload closes the scope LIFO and every contribution disappears together**. Missing dependency = hard startup error, not a silent PENDING; a second binding of a singleton likewise. Explicit `reload(plugin_id)` command; **no file watcher**. **Data is the one thing LIFO disposal cannot undo, so the manifest carries it:** every migration declares a `down`, **or** the manifest declares `rollback: forward_only`; migrations run inside a **daemon-held transaction preceded by a recorded journal checkpoint** (checkpoint id written as evidence with the `correlation_id`); the load flow **refuses** an upgrade whose migration is `forward_only` unless the operator confirms it in that session; a `forward_only` plugin may be **disabled** (scope disposed, data left intact) but never **rolled back**, and the UI must show which of the two it is *before* install. Load flow: manifest validation → `qma_api` compatibility → permissions → dependencies → migrations → topo activate → publish contributions → the UI learns new contribution points over the wire. `research/cordis-plugin-lifecycle.md#Q6`.
- **C. No plugin model in v1.** Cheapest, but Constitution P5 makes extensibility a first-class requirement and the operator's existing primitives must be accommodated (register row 72).
- **Trust: first-party only in v1.** Cut trust tiers, the capability solver and the plugin store that the packet revived (delta §2.2, §2.3) — one operator, no third-party publishers, no untrusted-extension problem. Keep *upgrade* machinery, drop *marketplace* framing.
- **Plugin shape:** one logical bundle spanning daemon / worker / UI / skills+graphs, whose halves communicate **only over the daemon contract**, never shared process memory (register row 67). UI contributions cross the wire; a daemon plugin never renders.

**LEAN: B.** One invariant — reversible activation — buys clean unload, clean upgrade and clean rollback **for code**, which is the whole reason Cordis was studied. It does **not** by itself answer the upgrade fear "end to end": a migration mutates D4's durable store and no `AsyncExitStack` LIFO can undo it, so the `down` / `forward_only` declaration above is what extends the invariant to **data** — the only genuinely irreversible half of the path the operator was afraid of (register rows 69, 72).

**Operator must rule?** No.

---

### D17 — Self-improvement / promotion gate as law

**Without it:** an agent's stray sentence becomes a trusted memory, a skill rewrite lands live, and the harness engineers itself into loops the operator explicitly forbade for v1.

- **Law (Constitution P9 + register rows 28, 45, 49).** Nothing agent-produced automatically becomes durable runtime state — memory, skill, tool, hook, graph, role or prompt. Pipeline: `RefinementProposal{summary, rationale, edits[], expected_outcome}` where an edit is `{action: create|update|delete, kind: prompt|memory|skill|worker_template|hook|graph|role, id, content, reference}` → deterministic `validate` (schema + **immutable base** + optimistic-concurrency conflict check). **Role splits, because "immutable base prompt" and an editable `kind: role` cannot both be enforced against D5's Role ≈ system prompt:** `role.base` is operator-authored and **immutable to the pipeline**, versioned only by a human commit; `role.overlay` is proposal-editable (appended prompt sections, added skills, narrowed toolsets). `kind: role` and `kind: prompt` edits may target the **overlay only**, and the validator rejects any edit whose path resolves into a base. **`subagent` is removed from the enum** — D5 defines a Subagent as a *running instance*, so nothing coherent can be staged under it; the durable definition is **`worker_template`** (register row 17). **Only definitions are promotion targets; no runtime-instanced object is ever an edit kind.** → deterministic verification/evaluation (verifier script, test or backtest replay — never an LLM judging itself) → optional cross-model review under ReviewPolicy → **staged candidate**, never live → operator/policy approval → promotion. Rollback via recorded before/after snapshots per applied edit. `research/prime-agent-rlm.md#Q4`.
- **A. Full pipeline in v1.** Infrastructure for evidence that does not exist yet (register §8.12).
- **B. Invariants + staging + the data model in v1; evaluation gates switched on when trajectories accumulate (lean).**
- **C. No self-improvement surface at all.** Loses the operator's stated eventual direction ("we do that eventually… this is the first stable version").

**LEAN: B.** The immutable-base invariant and the staging store cost almost nothing and are impossible to retrofit honestly; the gates need real trajectories to be meaningful. Reject the reference pattern of a single LLM review auto-firing on a timer.

**Operator must rule?** No — P9 already binds; this is the mechanism.

---

### D18 — Observability: OTel-exportable telemetry, separate from ledgers

**SETTLED by operator (register rows 37, 38):** logs/traces/metrics/trajectories are harness-authored, OpenTelemetry-exportable, and a different system from the ledger with different contracts and stores.

**Without it:** the ledger becomes a log, evaluation has nothing to read, and the operator's Langfuse-vs-ledger distinction collapses.

- **A. OTel SDK export from the daemon core, day one.** Standard-conformant immediately; adds a vendor SDK to the core before there is anything to view.
- **B. QMA-owned trace/metric records with an OTel exporter behind a port (lean).** Records carry the inherited `correlation_id` propagated across every boundary (parent spine convention) and the wire `id`; export is an adapter, swappable, and the daemon core stays dependency-light.
- **C. No telemetry in v1.** Reject — session replay, evaluation and router-decision audit all read from it.

Streams that are telemetry, not evidence: routing decisions and usage, job/log streams from the compute router, tool call traces, agent trajectories. The desk ledger may carry a `trace_ref` to them; never the reverse.

**Retention exemption, stated here so a not-yet-written policy cannot pre-empt it.** Agent **trajectories** and the **session-replay journal** are **retention-exempt**: never trimmed by any policy until the D21 deferred rows that revisit *on* them — external memory backend ("once desks have run"), self-improvement evaluation gates ("a trajectory corpus exists"), RLM beyond Analyst ("measured need from Analyst runs") — have been **evaluated and recorded**. Otherwise the eventual retention rule is free to destroy the corpus those three deferrals depend on, and register row 39's session replay with it. Any trim is a **recorded, reason-carrying operator action**, never a background job.

**LEAN: B.** "Don't reinvent the standard" is satisfied by conforming at the export boundary, not by importing the SDK into the core.

**Operator must rule?** No.

---

### D19 — Security / permissions / secrets

**Without it:** credentials land in config files and journals, a mission-scoped agent quietly widens its own tool set, and enforcement is spread over five places.

- **Shape.** Per-Role permission policy is part of the Role contract; **Mission narrows, never widens**; Subagent ≤ parent; plugin `permissions[]` are checked at load. **Hooks are the single enforcement point in the agent path** — `before_tool` (deny/ask/defer, fail-closed on timeout), `before_task_complete`, `review_required`, `before_ledger_append`, `before_memory_write`. Precedence is D7's total order `block_stop > deny > defer > ask > allow > observe`; deny rules bind even under any permissive mode.
- **Secrets (L34, non-negotiable).** Components handle secret **references**, never values; the Credential Broker resolves refs from the OS secret store (Windows Credential Manager, where the operator's broker creds already live); secrets never appear in repositories, configuration artifacts, journals, evidence, fingerprints or logs. This is the concrete reason OCX's plaintext home-dir credential files stay outside QMA's custody (D10). **Egress rule, stated because D3 makes the daemon one Python process and D16 lets first-party plugins register hooks inside it — so plugin-authored code shares an address space with the Credential Broker, and "isolation is Docker-per-worker" leaves the daemon side with none.** Resolved secret values exist **only inside the model-proxy / provider-adapter egress call frame** and are never stored on, attached to, or reachable from any object handed to a hook, plugin or graph. **`CredentialBroker.resolve` is callable only from the adapter layer**; the hook/plugin context type exposes `credential_ref` **strings exclusively**. A hook needing an authenticated call makes it through a **registered tool**, never by resolving a ref itself. Secrets are excluded from `updated_input` / `updated_output` / `injected_context` by a **schema check, not author discipline**. This is L34 enforced structurally rather than by convention.
- **Reject:** four-tier settings-file precedence, an LLM classifier deciding permissions, unauthenticated loopback binding with a `0.0.0.0` escape hatch (a footgun the reference itself warns about), and full-trust same-origin UI plugins. Isolation is Docker-per-worker; publisher trust is a non-problem for one operator.

**LEAN: as above** — one enforcement surface (hooks), one secret custody (OS store), one isolation mechanism (container).

**Operator must rule?** No.

---

### D20 — Deployment envelope

**Without it:** the agentic system quietly acquires authority over live trading, or the daemon is assumed to live wherever the developer's laptop is.

- **Topology.** Daemon on the always-on host chosen in D15; workers in Docker on that host, the workstation and the research node; **one Windows VPS, persistent, registered as a provider** with the single computer-use agent; the Rust UI is a client on the workstation attaching over WS/TLS with auth completing before protocol bytes. Inherited from the parent spine unchanged: operator workstation Windows 11 → planned Linux; always-on Linux VPS runs the trading node + tick recorder; factory agents in disposable sandboxes.
- **Environment boundary — this is the safety line.** QMA runs against **dev and paper only**. L17: only a human may promote a registered artifact into the live zone. L36 authority order and L39's exit-preservation invariant belong to the node, and nothing in QMA may invert, shortcut or automate them. QMA's output into the money path is a *candidate artifact a human promotes*, never a binding, a sizing decision or an order — and therefore no execution tool exists in the Tool Registry at any account role (D11). **Strategy and Bot semantics are QML / `qmf-registry`-owned**; QMA holds references and candidates only (D9's bounded `StrategyHandle`), and no QMA contract redefines either noun.
- **Alternative considered:** giving a Trading-desk Steward supervised live authority. Rejected on the constitution, not on taste.

**LEAN: as above**, with the live boundary written into the spine as an invariant rather than left to a permission policy.

**Operator must rule?** No — the boundary is constitutional; the host choice was already asked in D15.

---

### D21 — What is DEFERRED, and what INHERITED FASHION is cut outright

**Without it:** every cut idea returns in the next document (the packet already revived three the register had killed), and deferred items become silent scope.

- **A. Ratify both lists as spine law** — each deferred row carries a revisit condition, each cut row carries one reason; anything not on either list and not in D1–D20 is out of scope for v1.
- **B. Advisory lists only.** Cheaper to write, worthless in practice: the register already shows revival happens whenever a cut is merely noted.

**LEAN: A.** The operator's own filter — "we are picking things we need, not everything" and "we are building for a specific purpose, we're not building for the general public" — only has force if it is written as a list something must be checked against.

**Operator must rule?** **Yes** — accepting the cut list is a scope ruling, and it is the cheapest one on the sheet.

---

### D22 — Configurable-variable registry (L38/DEC-0157 applied to QMA)

**Without it:** the numbers this sheet already mints — `quiet_hours`, `max_wakes_per_window`, `sticky_limit`, `budget_hint`, hook timeouts, the RLM depth cap of 2, retention windows, `single-in-flight … unless forced`, ReviewPolicy families — harden into source-code constants, and the deferred UI session inherits a hunt instead of a list.

**The binding invariant this sheet had omitted — L38/DEC-0157:** *"Configurable means UI-editable at platform level: every configurable variable declares `ui-editable` or `uneditable` in its template, and recorded numbers attached to configurable variables are evidence, never ratified constants."* It is an inherited platform law, not a QMA choice, and D21's deferral of "UI architecture … nothing here presumes it" is exactly how it gets skipped by default.

- **A. A machine-readable QMA variables registry mirroring the platform's (lean).** Every configurable variable declares `name · owner_subsystem · scope ∈ desk|role|mission|plugin|global · type · units · default · ui-editable|uneditable`, with every recorded number marked **evidence, not a ratified constant**. It ships in **v1** so the UI session inherits a list rather than inventing one, and so no lean can quietly hard-code a number.
- **B. Declare variables per subsystem as each is built.** Cheaper today; it is how the invariant is skipped by default, and it puts the burden on the deferred UI session to go find every number this sheet scattered.

**LEAN: A.** The registry is a table, not machinery — the cheapest row on this sheet, and the only thing that makes D21's cut list enforceable against *numbers* as well as features.

**Operator must rule?** No — L38 already binds; this is where QMA obeys it.

---

## (i) Proposed vocabulary

| Final term | Meaning | Replaces (transcript term) |
|---|---|---|
| **QMA** | the agentic system: daemon + SDK + its plugins | "the agentic system" / blanket `qmx.` prefix |
| `qma-core / qma-daemon / qma-wire / qma-ui-contract` | package + namespace roster; plugins named by desk | the 37 `qmx.*` + 13 `qmx.ui.*` SDK surfaces |
| **Desk** | organizational + UI workspace (Research, Trading, Dev, Analysis, PM — or fewer) | Desk/Profile (conflated) |
| **Profile** | presentation only; may collapse desks in the UI | Profile (as an ontology object) |
| **Role** | declarative behavioral contract ≈ system prompt; stateless | unchanged |
| **Steward** | persistent named actor from a Role: name, memory scope, desk ledger, missions, routines, mailbox. Role:Steward and Desk:Steward are **1:N**; one per Desk carries `lead`; `ActorId` = `steward:<desk_slug>/<steward_slug>` | **Bot** (reserved: `bot` = trading bot, L36) |
| **Agent** | a running reasoning/execution instance | unchanged |
| **Subagent** | an Agent spawned by an Agent; capabilities ≤ parent | unchanged |
| **Session** | the run container carrying execution model × attachment × autonomy | "background session" type |
| **Worker** | an addressable execution slot; not an ontology object | Worker (as ontology) |
| **Mission / Task** | executable organizational contract owned by a Desk/Steward; bounded unit inside it | unchanged (Goal stays informal intent) |
| **Task Graph** | **daemon-owned runtime work state** — the only place task state lives | Kanban |
| **Graph Template** | authored, plugin-contributed, versioned topology with **no runtime state**; a `cycle` **node kind** carries the runtime-owned stopping condition, budget and escalation; instantiating one emits Tasks only | **Graph + Loop** (Loop folded in) |
| **Skill** | reusable procedure/knowledge with progressive disclosure | unchanged |
| **Hook** | deterministic lifecycle interception; the single enforcement point | unchanged |
| **Desk Ledger** (Research/Development/Analysis/Trading/PM) | agent-authored institutional record, per desk, indexed by Steward/Agent/Mission/Task/experiment/date | "QMX Event Ledger" |
| **Telemetry** | harness-authored logs/traces/metrics/trajectories, OTel-exportable, separate store | "observability" used loosely |
| **Memory** | selective durable adaptive state from experience, provider-backed, promotion-gated | unchanged |
| **Knowledge** | external, versioned, provenance-carrying evidence corpus, read-only | "Knowledge Base" |
| **Context Compiler** | what a given invocation sees; `select_context` is its primary verb | Context Engine |
| **Model Class → Deployment → Credential Broker** | deterministic router chain; harness picks the class | Model Proxy/Router internals |
| **ExecutionEnvironment / Compute Router / JobHandle** | where work runs; what it needs; the detached, reattachable handle | Compute Fabric / workspaces |
| **Agent Bus / Mailbox / Envelope** | non-authoritative durable collaboration channel | Agent Bus (authority unclear) |
| **QMB** | the backtesting product, already ratified and owned elsewhere | "QMX Backtesting Framework" |

## (ii) Deferred, with revisit conditions

| Deferred | Revisit when |
|---|---|
| External memory backend (Hindsight/Mem0) | desks have produced enough real experience to run a QMA-owned eval; re-check the Postgres dependency then |
| Knowledge indexing (Delphi-shaped hybrid retrieval) | the STRATS corpus is populated **and** its layout/serialization are ratified upstream |
| Self-improvement evaluation gates (promotion pipeline) | a trajectory corpus exists; v1 ships invariants + staging only |
| Sandbox / compute vendors (remote-container, desktop) | the environment contract is in use and Docker-per-worker demonstrably falls short |
| Browser stack (Egolite **[UNVERIFIED]** — no study, no source, no verified capability — vs CDP/Playwright) | a browser-heavy mission actually blocks; no study exists yet |
| External A2A / cross-host transport | a second host or an external counterparty needs the mailbox; internal bus first |
| RLM beyond the Analyst desk, and depth > 2 | measured need from Analyst runs |
| UI **presentation** — architecture, Rust extension technology, UI SDK surfaces. The variable **contract** is NOT deferred (D22) | its own session (operator deferred it); nothing here presumes it, but L38 binds the variable registry now |
| Desk consolidation (five vs three vs two) | after the first missions run; roles are settled, desks are presentation |
| Graph engine implementation choice | when the first three authored graph packs exist |
| Journal retention / replay window — **agent trajectories and the session-replay journal are exempt** (D18) | after measured event volume, mirroring the platform's journal-trim rule; the exempt streams may not be trimmed until the three evidence-dependent rows above are evaluated and recorded |

## (iii) Inherited fashion — cut outright

| Cut | One reason |
|---|---|
| QMX Agent Protocol + provider adapters for foreign agent runtimes | QMA owns its runtime bottom-up; nothing needs QMA to host foreign harnesses |
| Extension trust tiers, marketplace/plugin store, install counts | one operator, no third-party publishers, no untrusted-extension problem |
| `provides/requires/optional` capability dependency solver | a package-manager solver for a plugin set numbering in single digits |
| The 20-service `ctx.*` injectable fabric | architecture-by-enumeration; most entries have no described consumer |
| The eight-type memory taxonomy (revived in the packet) | never load-bearing; superseded by one narrow definition + provenance-gated candidates |
| Claude's ~20 TS-only lifecycle events (display, elicitation, config, cwd, directories) | general-public multi-surface IDE plumbing; QMA fires only what its authored graphs need |
| HMR file-watching and reactive re-mount of live plugins | dev nicety against a determinism requirement; explicit `reload` instead |
| `isolate()` / `intercept()` / label-joined config scopes | multi-config, multi-tenant overlay; one operator, one config |
| Nostr/Buzz signing, relays, NIPs as the bus transport | sovereign multi-tenant public messaging for strangers; a single-operator daemon needs none of it |
| Shared account-level cloud computer with per-actor "screens" | not a security boundary; the operator demolished it and Docker-per-worker replaces it |
| The foreign-harness shim layer in the model proxy (masquerading as another product's backend, model-identity spoofing) | QMA owns its caller and records the true deployment honestly |
| Plaintext credential files in a home directory | L34: secret references only, values in the OS store |
| Multi-tenant memory/knowledge machinery (orgs, projects, ACLs, corpus sharing, webhooks, billing) | single operator; keep the engine, drop the tenancy |
| Cloud research-service tiers, telemetry-to-vendor, account slots, mobile clients | the daemon is authoritative and local; there is no service tier |
| Permanent named specialist rosters (Paper Scout, YouTube Extractor, …) | the operator flagged it himself; worker templates spawned on demand instead |
| A Trading-desk execution tool, "paper only" included | D20's own words: QMA's money-path output is never an order; L36: nothing above a bot touches the market, and paper validation is an account role on a real venue, not a sandbox |
| Git-branch-per-parameter-mutation as the lineage mechanism | absurd at QMX scale; content-addressed resolved config, git only when code changes |
| Group-chat as the primary coordination mechanism | parallel workers must synchronise through the Task Graph, not chat |

## (iv) Facts that could NOT be verified and must be flagged

1. **[UNVERIFIED]** **Two studies disagree on the Claude Python SDK hook count** — `research/claude-agent-sdk-hooks.md#Verified fact A` says exactly **10** in-process events (naming `PostToolUseFailure`, `SubagentStart`, `PermissionRequest` among them); `research/daemon-stack-options.md#(a) Daemon language` says **7**. Both claim the same source checked the same day. The D3 lean does not depend on the number, but the discrepancy must be resolved before any Claude-worker adapter is specified.
2. **[UNVERIFIED]** **`/goal` documentation was not independently fetched** — it is cited from the hooks reference only; the "keep working toward a condition" surface is second-hand.
3. **[UNVERIFIED]** **The Claude TypeScript SDK page was not independently opened**; the per-language event split is taken from the hooks page's columns.
4. **[UNVERIFIED]** **Egolite** — the browser product the operator wants reverse-engineered has no study, no source, no verified capability. Nothing in this sheet depends on it; the browser stack stays deferred.
5. **[UNVERIFIED]** **Rust UI extension technology** (Tauri host + web components vs WASM component model vs declarative-only) — no study exists; the register lists three options and none was chosen.
6. **[UNVERIFIED]** **The in-house "threading node"** and other existing QMX plugin primitives are named in the transcript but nowhere specified; the plugin model must accommodate an object whose shape is unknown.
7. **[UNVERIFIED]** **Graph engine candidates** — none studied anywhere; D8's registry is specified as a contract with no implementation evidence.
8. **[UNVERIFIED]** **STRATS is currently empty** (only `IDEA.md` + the ground-state file); the Knowledge contract is designed against a spec, not a corpus. Its folder layout, serialization, file extensions and stable-ID scheme are all explicitly unratified upstream, and 9 duplicate entry IDs are unresolved.
9. **[UNVERIFIED]** **OpenCodex facts are partly local-only** — combos, account pool strategy and the routing-history store were read from this machine's install, not from published documentation; and the project's own README disclaims that multi-account pooling protects against provider enforcement. **Whether pooling is acceptable under each provider's ToS is unverified and needs a governance ruling.**
10. **[UNVERIFIED]** **Hindsight's SOTA claims are unevaluated** against QMA's own load, and it has no native `confidence` or TTL field — whether metadata+tags suffice, or a side table is needed, is untested. Whether its LLM extraction preserves structured provenance ("Paper A §3") faithfully is unknown.
11. **[UNVERIFIED]** **Mem0's own docs and README conflict** on whether v3 supersedes or only accumulates; treat "Mem0 supports supersession" as unverified.
12. **[UNVERIFIED]** **Buzz protocol details** (NIP list, event kinds, poll fallback) come partly from third-party integration docs, not Buzz's own primary sources. Nothing is adopted from Buzz, so nothing depends on them.
13. **[UNVERIFIED]** **Unmeasured performance assumptions:** whether an RLM Python kernel inside Docker sustains the parallel-backtest fan-out; whether `dill` namespace snapshots hold QMA's large handles; and the cost/latency of RLM at "800 strategy variants" scale. The reference implementation itself gives no cost or runtime guarantees.

## Adversary amendments — disposition

1. **D1 · port cardinality (incompatible-units) — APPLIED.** Two first-party plugins could each bind MemoryProvider legally; singleton-vs-multi is now declared per contribution point in D1 and D16, with a hard startup error naming both plugin ids.
2. **D1 · `qma-core` mints no parallel base (constraint-violation) — APPLIED.** Verified against L31/DEC-0122; "typed refusals, ids" in a definitions-only core is the re-implementation it forbids, so refusals are now variants and `fp1` is imported.
3. **D2 · one journal + scope vocabulary (incompatible-units) — APPLIED, with one guard the amendment omitted.** The single `journal_seq` law and the seven-value scope vocabulary are in, but the sheet now states explicitly that this is the daemon's internal event journal and **not** a ledger, or it reads as reviving the QMX-wide event ledger register row 36 killed.
4. **D2 · `id` vs `correlation_id` (constraint-violation) — APPLIED.** "`id` carries `correlation_id`" is deleted from Transport A; two fields, minted differently, with the never-regenerate law and gate refusal stated.
5. **D4 · sole-writer invariant (constraint-violation) — APPLIED.** The lean's own "same host only" premise was a store property, not a rule binding D20's three worker hosts; it is now an invariant with the daemon-host fold corollary and the QMB `_ref` carve-out.
6. **D5 · Steward cardinality + `ActorId` grammar (missing-decision) — APPLIED.** D15's `steward:research/lead` was undefined and smuggled register row 18's "Role Lead" back; 1:N both ways, one `lead` per Desk, fixed slug grammar, and no mailbox for Agents or Subagents.
7. **D7 · `before_memory_write` + total precedence (incompatible-units) — APPLIED.** D19 named an enforcement point D7's set lacked; the v1 set is ten, option A is rebuilt as a strict superset so the sizing choice is monotone, and `block_stop`/`observe` are ordered with `deny` named as the timeout value.
8. **D8 · Graph Template vs Task Graph, `cycle` as a node kind (incompatible-units) — APPLIED.** One word over two owners is a real double mutation path; the authored artifact is now Graph Template with no runtime state, the compilation law emits Tasks only, and back-edges are rejected at registration so `stopping_condition`/`budget`/`escalation` have one attachment point.
9. **D9 · `StrategyHandle` bounded (constraint-violation) — APPLIED.** Verified L17 and L33 verbatim; "typed component mutation" over a QML-owned noun contradicted D20's own sentence, so the handle is now dev-zone candidates plus a `lineage[]` edge, and the same line is added to D20.
10. **D10 · drop `VISION`, `needs` is the sole eligibility input (incompatible-units) — APPLIED, and the finding understated it.** `VISION` appears in neither register row 54 nor delta §2.10; the sheet had invented a fifth value while claiming to re-mint the enum. `NoEligibleDeployment` and the never-substitute rule are in.
11. **D11 · delete the Trading execution tool (constraint-violation) — APPLIED.** Verified L36 ("nothing above a bot touches the market") against D20's own "never … an order"; rewritten as a registry-level prohibition, not a `check_fn` policy, with a matching D21 cut row.
12. **D12 · `UNKNOWN` JobHandle state (constraint-violation) — APPLIED, reclassified.** L35/DEC-0137 literally binds QMF *venue submissions*, not compute jobs, so the sheet now says QMA **adopts** the discipline rather than inheriting it; the substance (never `failed` on a lost supervisor, lease held until recorded resolution) stands unchanged.
13. **D13 · row-43 honesty + bounded C (constraint-violation) — APPLIED.** Row 43 is [OPERATOR] and lean C is in-house code against it; the ask is re-framed as an amendment request, and C is bounded to candidates + `validation_state` with exact-match recall and no embeddings, consolidation, reflection or ranking.
14. **D14 · Knowledge query surface into the Tool Registry (incompatible-units) — APPLIED, though the finding overstated it.** D14-A already listed `search/retrieve/cite`, so the desks were not tool-less; but the lean's claim that the RLM read path *is* v1 retrieval did contradict D9's Analyst-only scoping, and that is now corrected and the surface assigned to D11.
15. **D14 · `evidence_confidence` vs `promotion_confidence` (incompatible-units) — APPLIED.** Six opaque corpus dimensions and one QMA scalar cannot share a field name; renamed at the contract level in D13 and D14 with the no-derivation law and verbatim carry-through.
16. **D16 · migration `down` / `rollback: forward_only` (constraint-violation) — APPLIED.** An `AsyncExitStack` LIFO cannot undo a schema migration, so "answers the upgrade fear end to end" was false for data; journal checkpoint, in-session confirmation, and disable-but-never-roll-back are stated, and the overclaim is removed from the lean.
17. **D17 · `role.base` / `role.overlay`, `worker_template` (incompatible-units) — APPLIED.** "immutable base prompt" and an editable `kind: role` were unenforceable together against D5's Role ≈ system prompt; `subagent` is replaced by `worker_template` (register row 17) since a running instance cannot be staged.
18. **D19 · secret egress rule (constraint-violation) — APPLIED.** Verified L34 verbatim ("secret values live only in the adapter's connection manager"); with D3's single process and D16's in-daemon plugin hooks, convention was the only barrier, so `resolve` is now adapter-only and secrets are schema-excluded from hook payloads.
19. **D21 · new D22 variables registry (missing-decision) — APPLIED.** L38/DEC-0157 verified verbatim in `docs/constitution.md` and absent from the sheet; D22 added, and the deferred row now reads UI *presentation* deferred, variable contract not.
20. **D6 · clock law (missing-decision) — APPLIED.** The daemon moved off the workstation in D15/D20 while `quiet_hours` and a date-indexed ledger stayed unqualified; UTC persistence via `qmf-core`'s clock, explicit IANA zone on every wall-clock policy, no local-time persistence.
21. **D18 · trajectory + session-replay retention exemption (missing-decision) — APPLIED.** Three D21 deferrals revisit on evidence an unwritten retention policy could delete first; the exemption holds until those rows are evaluated and recorded, and any trim is a recorded operator action.
